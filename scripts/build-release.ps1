# Build versioned release archives from the exact committed Git tree.

[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [string]$Version,
    [switch]$RequireTag
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..'))
$distRoot = [IO.Path]::GetFullPath((Join-Path -Path $repositoryRoot -ChildPath 'dist'))
$pathComparison = if ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT) {
    [StringComparison]::OrdinalIgnoreCase
}
else {
    [StringComparison]::Ordinal
}

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = $distRoot
}
elseif (-not [IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path -Path (Get-Location).Path -ChildPath $OutputDirectory
}

$resolvedOutput = [IO.Path]::GetFullPath($OutputDirectory)
$distPrefix = $distRoot.TrimEnd(
    [IO.Path]::DirectorySeparatorChar,
    [IO.Path]::AltDirectorySeparatorChar
) + [IO.Path]::DirectorySeparatorChar

if (
    -not $resolvedOutput.Equals($distRoot, $pathComparison) -and
    -not $resolvedOutput.StartsWith($distPrefix, $pathComparison)
) {
    throw "Release output must stay inside '$distRoot'."
}

function Invoke-Git {
    param([string[]]$ArgumentList)

    $output = & git -C $repositoryRoot @ArgumentList 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($ArgumentList -join ' ') failed: $($output -join [Environment]::NewLine)"
    }

    return $output
}

if (-not (Get-Command -Name git -ErrorAction SilentlyContinue)) {
    throw 'Git is required to build release archives.'
}

$status = @(Invoke-Git -ArgumentList @('status', '--porcelain', '--untracked-files=all'))
if ($status.Count -gt 0) {
    throw 'Release builds require a clean working tree so artifacts match the tagged commit.'
}

$manifestPath = Join-Path -Path $repositoryRoot -ChildPath '.claude-plugin/plugin.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$manifestVersion = [string]$manifest.version

if ($manifestVersion -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
    throw "Plugin manifest version '$manifestVersion' is not valid SemVer."
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = $manifestVersion
}

$normalizedVersion = $Version.Trim()
if ($normalizedVersion.StartsWith('v', [StringComparison]::OrdinalIgnoreCase)) {
    $normalizedVersion = $normalizedVersion.Substring(1)
}

if ($normalizedVersion -ne $manifestVersion) {
    throw "Requested version '$normalizedVersion' does not match manifest '$manifestVersion'."
}

$tag = "v$manifestVersion"
$commit = ((Invoke-Git -ArgumentList @('rev-parse', 'HEAD')) -join "`n").Trim()

if ($RequireTag) {
    $tagsAtHead = @(Invoke-Git -ArgumentList @('tag', '--points-at', 'HEAD'))
    if ($tagsAtHead -notcontains $tag) {
        throw "HEAD must carry exact tag '$tag' before release publication."
    }

    $tagObjectType = ((Invoke-Git -ArgumentList @('cat-file', '-t', "refs/tags/$tag")) -join "`n").Trim()
    if ($tagObjectType -ne 'tag') {
        throw "Release tag '$tag' must be annotated, not lightweight."
    }
}

$changelogPath = Join-Path -Path $repositoryRoot -ChildPath 'CHANGELOG.md'
$changelogLines = @(Get-Content -LiteralPath $changelogPath)
$versionHeading = '^##\s+' + [regex]::Escape($manifestVersion) + '(?:\s|$)'
$notesStart = -1
for ($index = 0; $index -lt $changelogLines.Count; $index++) {
    if ($changelogLines[$index] -match $versionHeading) {
        $notesStart = $index
        break
    }
}

if ($notesStart -lt 0) {
    throw "CHANGELOG.md has no release heading for $manifestVersion."
}

$notesEnd = $changelogLines.Count
for ($index = $notesStart + 1; $index -lt $changelogLines.Count; $index++) {
    if ($changelogLines[$index] -match '^##\s+') {
        $notesEnd = $index
        break
    }
}

$notes = ($changelogLines[($notesStart + 1)..($notesEnd - 1)] -join "`n").Trim()
if ([string]::IsNullOrWhiteSpace($notes)) {
    throw "CHANGELOG.md release notes for $manifestVersion are empty."
}

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Recurse -Force
}
New-Item -ItemType Directory -Path $resolvedOutput | Out-Null

$packageBase = "high-quality-projects-skill-$tag"
$archivePrefix = "$packageBase/"
$zipPath = Join-Path -Path $resolvedOutput -ChildPath "$packageBase.zip"
$tarPath = Join-Path -Path $resolvedOutput -ChildPath "$packageBase.tar.gz"

Invoke-Git -ArgumentList @(
    'archive', '--format=zip', "--prefix=$archivePrefix", "--output=$zipPath", 'HEAD'
) | Out-Null
Invoke-Git -ArgumentList @(
    'archive', '--format=tar.gz', "--prefix=$archivePrefix", "--output=$tarPath", 'HEAD'
) | Out-Null

foreach ($archivePath in @($zipPath, $tarPath)) {
    if (-not (Test-Path -LiteralPath $archivePath -PathType Leaf)) {
        throw "Release archive was not created: $archivePath"
    }
    if ((Get-Item -LiteralPath $archivePath).Length -eq 0) {
        throw "Release archive is empty: $archivePath"
    }
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$releaseNotesPath = Join-Path -Path $resolvedOutput -ChildPath 'RELEASE_NOTES.md'
[IO.File]::WriteAllText($releaseNotesPath, "$notes`n", $utf8NoBom)

$archiveRecords = @(
    foreach ($archivePath in @($zipPath, $tarPath)) {
        $archiveItem = Get-Item -LiteralPath $archivePath
        [ordered]@{
            name = $archiveItem.Name
            bytes = $archiveItem.Length
            sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
)

$commitTime = ((Invoke-Git -ArgumentList @('show', '-s', '--format=%cI', 'HEAD')) -join "`n").Trim()
$releaseManifest = [ordered]@{
    schema_version = 1
    package = 'high-quality-projects-skill'
    version = $manifestVersion
    tag = $tag
    commit = $commit
    source_commit_time = $commitTime
    artifacts = $archiveRecords
}

$releaseManifestPath = Join-Path -Path $resolvedOutput -ChildPath 'release-manifest.json'
$releaseManifestJson = ($releaseManifest | ConvertTo-Json -Depth 6).Replace("`r`n", "`n")
[IO.File]::WriteAllText($releaseManifestPath, "$releaseManifestJson`n", $utf8NoBom)

$checksumTargets = @($zipPath, $tarPath, $releaseManifestPath, $releaseNotesPath)
$checksumLines = @(
    foreach ($targetPath in $checksumTargets | Sort-Object -Property { Split-Path -Leaf $_ }) {
        $hash = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $(Split-Path -Leaf $targetPath)"
    }
)
$checksumPath = Join-Path -Path $resolvedOutput -ChildPath 'SHA256SUMS.txt'
[IO.File]::WriteAllText($checksumPath, (($checksumLines -join "`n") + "`n"), $utf8NoBom)

$result = [ordered]@{
    version = $manifestVersion
    tag = $tag
    commit = $commit
    output_directory = $resolvedOutput
    files = @(
        $zipPath,
        $tarPath,
        $releaseManifestPath,
        $releaseNotesPath,
        $checksumPath
    ) | ForEach-Object { Split-Path -Leaf $_ }
}

$result | ConvertTo-Json -Depth 4
