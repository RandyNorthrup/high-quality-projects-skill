# Build and inspect release artifacts from the current committed tree.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Confirm-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..'))
$builder = Join-Path -Path $repositoryRoot -ChildPath 'scripts/build-release.ps1'
$manifestPath = Join-Path -Path $repositoryRoot -ChildPath '.claude-plugin/plugin.json'
$changelogPath = Join-Path -Path $repositoryRoot -ChildPath 'CHANGELOG.md'
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$tag = 'v{0}' -f $manifest.version
$packageBase = 'high-quality-projects-skill-{0}' -f $tag
$distRoot = [IO.Path]::GetFullPath((Join-Path -Path $repositoryRoot -ChildPath 'dist'))
$temporaryRoot = Join-Path -Path $distRoot -ChildPath (
    'release-package-test-{0}' -f [Guid]::NewGuid().ToString('N')
)
$comparisonRoot = "${temporaryRoot}-comparison"
$originalTimezone = [Environment]::GetEnvironmentVariable('TZ', 'Process')

try {
    [Environment]::SetEnvironmentVariable('TZ', 'America/Los_Angeles', 'Process')
    & $builder -OutputDirectory $temporaryRoot -Version $manifest.version | Out-Null
    Confirm-Condition -Condition ($env:TZ -eq 'America/Los_Angeles') `
        -Message 'Release builder did not restore the caller timezone.'

    [Environment]::SetEnvironmentVariable('TZ', 'Asia/Tokyo', 'Process')
    & $builder -OutputDirectory $comparisonRoot -Version $manifest.version | Out-Null
    Confirm-Condition -Condition ($env:TZ -eq 'Asia/Tokyo') `
        -Message 'Release builder did not restore the comparison timezone.'

    $expectedNames = @(
        "$packageBase.zip",
        "$packageBase.tar.gz",
        'release-manifest.json',
        'RELEASE_NOTES.md',
        'SHA256SUMS.txt'
    )
    foreach ($expectedName in $expectedNames) {
        $expectedPath = Join-Path -Path $temporaryRoot -ChildPath $expectedName
        Confirm-Condition -Condition (Test-Path -LiteralPath $expectedPath -PathType Leaf) `
            -Message "Release output is missing: $expectedName"

        $comparisonPath = Join-Path -Path $comparisonRoot -ChildPath $expectedName
        Confirm-Condition -Condition (Test-Path -LiteralPath $comparisonPath -PathType Leaf) `
            -Message "Comparison output is missing: $expectedName"
        $primaryHash = (Get-FileHash -LiteralPath $expectedPath -Algorithm SHA256).Hash
        $comparisonHash = (Get-FileHash -LiteralPath $comparisonPath -Algorithm SHA256).Hash
        Confirm-Condition -Condition ($primaryHash -eq $comparisonHash) `
            -Message "Release output changes with ambient timezone: $expectedName"
    }

    $releaseManifestPath = Join-Path -Path $temporaryRoot -ChildPath 'release-manifest.json'
    $releaseManifest = Get-Content -LiteralPath $releaseManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $head = (& git -C $repositoryRoot rev-parse HEAD).Trim()
    Confirm-Condition -Condition ($releaseManifest.version -eq $manifest.version) `
        -Message 'Release manifest version does not match plugin manifest.'
    Confirm-Condition -Condition ($releaseManifest.tag -eq $tag) `
        -Message 'Release manifest tag is wrong.'
    Confirm-Condition -Condition ($releaseManifest.commit -eq $head) `
        -Message 'Release manifest commit does not match HEAD.'

    $checksumPath = Join-Path -Path $temporaryRoot -ChildPath 'SHA256SUMS.txt'
    $checksumLines = @(Get-Content -LiteralPath $checksumPath -Encoding UTF8)
    Confirm-Condition -Condition ($checksumLines.Count -eq 4) `
        -Message 'Checksum file must cover both archives, manifest, and release notes.'
    foreach ($checksumLine in $checksumLines) {
        Confirm-Condition -Condition ($checksumLine -match '^([0-9a-f]{64})  (.+)$') `
            -Message "Malformed checksum line: $checksumLine"
        $expectedHash = $Matches[1]
        $fileName = $Matches[2]
        $artifactPath = Join-Path -Path $temporaryRoot -ChildPath $fileName
        Confirm-Condition -Condition (Test-Path -LiteralPath $artifactPath -PathType Leaf) `
            -Message "Checksum references missing file: $fileName"
        $actualHash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()
        Confirm-Condition -Condition ($actualHash -eq $expectedHash) `
            -Message "Checksum mismatch: $fileName"
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipPath = Join-Path -Path $temporaryRoot -ChildPath "$packageBase.zip"
    $zip = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $zipEntries = @($zip.Entries | ForEach-Object { $_.FullName })
        $trackedFiles = @(& git -C $repositoryRoot ls-tree -r --name-only HEAD)
        Confirm-Condition -Condition ($LASTEXITCODE -eq 0 -and $trackedFiles.Count -gt 0) `
            -Message 'Could not inventory the committed package resources.'
        foreach ($relativePath in $trackedFiles) {
            Confirm-Condition -Condition ($zipEntries -contains "$packageBase/$relativePath") `
                -Message "ZIP is missing committed resource: $relativePath"
        }
    }
    finally {
        $zip.Dispose()
    }

    $tarCommand = Get-Command -Name tar -ErrorAction SilentlyContinue
    Confirm-Condition -Condition ($null -ne $tarCommand) `
        -Message 'tar is required to inspect the tar.gz release archive.'
    $tarPath = Join-Path -Path $temporaryRoot -ChildPath "$packageBase.tar.gz"
    $tarEntries = @(& $tarCommand.Source -tzf $tarPath)
    Confirm-Condition -Condition ($LASTEXITCODE -eq 0) `
        -Message 'Could not list tar.gz release archive.'
    foreach ($relativePath in $trackedFiles) {
        Confirm-Condition -Condition ($tarEntries -contains "$packageBase/$relativePath") `
            -Message "tar.gz is missing committed resource: $relativePath"
    }

    $releaseNotes = Get-Content -LiteralPath (
        Join-Path -Path $temporaryRoot -ChildPath 'RELEASE_NOTES.md'
    ) -Raw -Encoding UTF8
    $changelogLines = @(Get-Content -LiteralPath $changelogPath -Encoding UTF8)
    $versionHeading = '^##\s+' + [regex]::Escape([string]$manifest.version) + '(?:\s|$)'
    $notesStart = -1
    for ($index = 0; $index -lt $changelogLines.Count; $index++) {
        if ($changelogLines[$index] -match $versionHeading) {
            $notesStart = $index
            break
        }
    }
    Confirm-Condition -Condition ($notesStart -ge 0) `
        -Message 'Current manifest version is missing from CHANGELOG.md.'

    $notesEnd = $changelogLines.Count
    for ($index = $notesStart + 1; $index -lt $changelogLines.Count; $index++) {
        if ($changelogLines[$index] -match '^##\s+') {
            $notesEnd = $index
            break
        }
    }
    $expectedReleaseNotes = (
        $changelogLines[($notesStart + 1)..($notesEnd - 1)] -join "`n"
    ).Trim()
    $actualReleaseNotes = $releaseNotes.Replace("`r`n", "`n").Trim()
    Confirm-Condition -Condition $actualReleaseNotes.Equals(
        $expectedReleaseNotes,
        [StringComparison]::Ordinal
    ) -Message 'Release notes do not exactly match the current changelog entry.'

    Write-Output 'PASS: versioned release archives, manifest, notes, and checksums'
}
finally {
    [Environment]::SetEnvironmentVariable('TZ', $originalTimezone, 'Process')
    $safePrefix = $distRoot.TrimEnd(
        [IO.Path]::DirectorySeparatorChar,
        [IO.Path]::AltDirectorySeparatorChar
    ) + [IO.Path]::DirectorySeparatorChar
    foreach ($testRoot in @($temporaryRoot, $comparisonRoot)) {
        $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot)
        if ($resolvedTestRoot.StartsWith($safePrefix, [StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
