# Smoke tests for the PowerShell-native package scripts.

[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Confirm-Condition {
    param(
        [Parameter(Mandatory)]
        [bool] $Condition,

        [Parameter(Mandatory)]
        [string] $Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Confirm-Equal {
    param(
        [Parameter(Mandatory)]
        [AllowNull()]
        [object] $Actual,

        [Parameter(Mandatory)]
        [AllowNull()]
        [object] $Expected,

        [Parameter(Mandatory)]
        [string] $Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..'))
$rootScript = Join-Path -Path $repositoryRoot -ChildPath 'scripts/skill-root.ps1'
$scanScript = Join-Path -Path $repositoryRoot -ChildPath 'scripts/detect-stack.ps1'
$projectSetupSkill = Join-Path -Path $repositoryRoot -ChildPath 'skills/project_setup/SKILL.md'
$grillMeReference = Join-Path -Path $repositoryRoot `
    -ChildPath 'skills/project_setup/references/grill-me.md'
$projectBriefAsset = Join-Path -Path $repositoryRoot `
    -ChildPath 'skills/project_setup/assets/PROJECT_BRIEF.md'
$pluginManifest = Join-Path -Path $repositoryRoot -ChildPath '.claude-plugin/plugin.json'
$temporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temporaryRoot = Join-Path -Path $temporaryBase -ChildPath (
    'high-quality-projects-skill-test-{0}' -f [Guid]::NewGuid().ToString('N')
)

$originalSkillRoot = [Environment]::GetEnvironmentVariable('SKILL_ROOT')
$originalPluginRoot = [Environment]::GetEnvironmentVariable('CLAUDE_PLUGIN_ROOT')

try {
    foreach ($requiredFile in @(
            $projectSetupSkill,
            $grillMeReference,
            $projectBriefAsset,
            $pluginManifest
        )) {
        Confirm-Condition -Condition (Test-Path -LiteralPath $requiredFile -PathType Leaf) `
            -Message "Required package file is missing: $requiredFile"
    }

    $projectSetupContent = Get-Content -LiteralPath $projectSetupSkill -Raw
    foreach ($requiredText in @(
            '## Rule zero: scan, reuse, then create',
            '## Phase 1 — Grill Me: confirm the project contract',
            'references/grill-me.md',
            'assets/PROJECT_BRIEF.md',
            '### Readiness gate',
            '**Reuse before creation**',
            'scan -> reuse or extend -> create only when'
        )) {
        Confirm-Condition -Condition $projectSetupContent.Contains($requiredText) `
            -Message "project_setup is missing required discovery contract: $requiredText"
    }

    $grillMeContent = Get-Content -LiteralPath $grillMeReference -Raw
    foreach ($requiredHeading in @(
            '## Why and outcomes',
            '## Experience, brand, and accessibility',
            '## Signing and trust',
            '## Release pipeline and supply chain',
            '## Operations, support, and retirement'
        )) {
        Confirm-Condition -Condition $grillMeContent.Contains($requiredHeading) `
            -Message "Grill Me guide is missing coverage: $requiredHeading"
    }
    foreach ($requiredBrandingText in @(
            'editable logo',
            'app icons',
            'favicons',
            'social/OG images',
            'which original is authoritative'
        )) {
        Confirm-Condition -Condition $grillMeContent.Contains($requiredBrandingText) `
            -Message "Grill Me guide is missing branding inventory: $requiredBrandingText"
    }

    $projectBriefContent = Get-Content -LiteralPath $projectBriefAsset -Raw
    Confirm-Condition -Condition $projectBriefContent.Contains('## Decision ledger') `
        -Message 'PROJECT_BRIEF asset is missing its decision ledger.'
    Confirm-Condition -Condition $projectBriefContent.Contains('## Readiness confirmation') `
        -Message 'PROJECT_BRIEF asset is missing its readiness confirmation.'
    Confirm-Condition -Condition $projectBriefContent.Contains('Existing branding items') `
        -Message 'PROJECT_BRIEF asset is missing its branding inventory.'
    Confirm-Condition -Condition $projectBriefContent.Contains('to reuse or extend') `
        -Message 'PROJECT_BRIEF asset is missing its reuse decision record.'

    $manifest = Get-Content -LiteralPath $pluginManifest -Raw | ConvertFrom-Json
    Confirm-Equal -Actual $manifest.version -Expected '0.3.1' `
        -Message 'Plugin manifest version does not match the reuse-first release.'

    [Environment]::SetEnvironmentVariable('SKILL_ROOT', $null)
    [Environment]::SetEnvironmentVariable('CLAUDE_PLUGIN_ROOT', $null)

    [void] (New-Item -ItemType Directory -Path $temporaryRoot)
    $workspace = Join-Path -Path $temporaryRoot -ChildPath 'workspace with spaces'
    [void] (New-Item -ItemType Directory -Path $workspace)
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace 'src'))
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace 'node_modules'))
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace '.github/workflows'))

    Push-Location -LiteralPath $workspace
    try {
        $resolvedPackageRoot = & $rootScript
    }
    finally {
        Pop-Location
    }
    Confirm-Equal -Actual $resolvedPackageRoot -Expected $repositoryRoot `
        -Message 'skill-root.ps1 did not resolve from an unrelated directory.'

    foreach ($relativeFile in @(
            'src/app.py', 'src/app.ts', 'src/view.tsx', 'src/browser.js',
            'src/lib.rs', 'src/App.cs', 'src/native.cpp', 'src/module.psm1',
            'src/style.scss', 'src/index.html', 'src/run.sh', 'src/main.go',
            'README.md', '.prettierrc', 'node_modules/ignored.py'
        )) {
        $filePath = Join-Path -Path $workspace -ChildPath $relativeFile
        Set-Content -LiteralPath $filePath -Value '' -Encoding Ascii
    }

    $scanJson = & $scanScript $workspace
    $scan = $scanJson | ConvertFrom-Json

    Confirm-Equal -Actual $scan.root -Expected ([IO.Path]::GetFullPath($workspace)) `
        -Message 'detect-stack.ps1 returned wrong root.'
    Confirm-Equal -Actual $scan.languages.python -Expected 1 `
        -Message 'Python count or directory pruning is wrong.'
    Confirm-Equal -Actual $scan.languages.typescript -Expected 2 `
        -Message 'TypeScript count is wrong.'
    Confirm-Equal -Actual $scan.languages.javascript -Expected 1 `
        -Message 'JavaScript count is wrong.'
    Confirm-Equal -Actual $scan.languages.rust -Expected 1 -Message 'Rust count is wrong.'
    Confirm-Equal -Actual $scan.languages.csharp -Expected 1 -Message 'C# count is wrong.'
    Confirm-Equal -Actual $scan.languages.cpp -Expected 1 -Message 'C++ count is wrong.'
    Confirm-Equal -Actual $scan.languages.powershell -Expected 1 `
        -Message 'PowerShell count is wrong.'
    Confirm-Equal -Actual $scan.languages.css -Expected 1 -Message 'CSS count is wrong.'
    Confirm-Equal -Actual $scan.languages.html -Expected 1 -Message 'HTML count is wrong.'
    Confirm-Equal -Actual $scan.languages.shell -Expected 1 -Message 'Shell count is wrong.'
    Confirm-Equal -Actual $scan.languages.go -Expected 1 -Message 'Go count is wrong.'
    Confirm-Condition -Condition $scan.existing_config.readme `
        -Message 'README configuration detection failed.'
    Confirm-Condition -Condition $scan.existing_config.github_workflows `
        -Message 'GitHub workflow directory detection failed.'
    Confirm-Condition -Condition $scan.existing_config.prettierrc `
        -Message '.prettierrc configuration detection failed.'
    Confirm-Condition -Condition (-not $scan.git.is_repo) `
        -Message 'Non-repository workspace reported as a Git repository.'
    Confirm-Condition -Condition ($null -ne $scan.python_runtime.module_only_tools) `
        -Message 'Python runtime contract is missing module_only_tools.'
    if ($null -ne (Get-Command -Name python -ErrorAction SilentlyContinue)) {
        Confirm-Condition -Condition (-not [string]::IsNullOrWhiteSpace($scan.python_runtime.bin)) `
            -Message 'Available Python runtime was not selected.'

        $pythonExecutable = (Get-Command -Name python -ErrorAction Stop).Source
        $isolatedPythonRoot = Join-Path -Path $temporaryRoot -ChildPath 'isolated-python'
        & $pythonExecutable -m venv --without-pip $isolatedPythonRoot
        Confirm-Equal -Actual $LASTEXITCODE -Expected 0 `
            -Message 'Could not create isolated Python runtime for scanner regression test.'

        $isolatedPythonBin = if (
            [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
        ) {
            Join-Path -Path $isolatedPythonRoot -ChildPath 'Scripts'
        }
        else {
            Join-Path -Path $isolatedPythonRoot -ChildPath 'bin'
        }

        $originalPath = $env:PATH
        try {
            $env:PATH = $isolatedPythonBin
            $isolatedScanJson = & $scanScript $workspace
        }
        finally {
            $env:PATH = $originalPath
        }

        $isolatedScan = $isolatedScanJson | ConvertFrom-Json
        Confirm-Equal -Actual $isolatedScan.root -Expected ([IO.Path]::GetFullPath($workspace)) `
            -Message 'Scanner failed when Python had no optional tools installed.'
        Confirm-Condition -Condition (-not $isolatedScan.tools_installed.pytest) `
            -Message 'Isolated Python runtime unexpectedly reported pytest.'
        Confirm-Equal -Actual $isolatedScan.python_runtime.module_only_tools.Count -Expected 0 `
            -Message 'Zero-module Python runtime did not return an empty tool list.'
    }

    $overrideRoot = Join-Path -Path $temporaryRoot -ChildPath 'override root'
    [void] (New-Item -ItemType Directory -Path $overrideRoot)
    [Environment]::SetEnvironmentVariable('SKILL_ROOT', $overrideRoot)
    $resolvedOverride = & $rootScript
    Confirm-Equal -Actual $resolvedOverride -Expected ([IO.Path]::GetFullPath($overrideRoot)) `
        -Message 'SKILL_ROOT override did not win.'

    [Environment]::SetEnvironmentVariable('SKILL_ROOT', $null)
    [Environment]::SetEnvironmentVariable('CLAUDE_PLUGIN_ROOT', $workspace)
    $resolvedPluginRoot = & $rootScript
    Confirm-Equal -Actual $resolvedPluginRoot -Expected ([IO.Path]::GetFullPath($workspace)) `
        -Message 'CLAUDE_PLUGIN_ROOT fallback failed.'

    $missingPath = Join-Path -Path $temporaryRoot -ChildPath 'missing'
    $errorJson = & $scanScript $missingPath
    $scanError = $errorJson | ConvertFrom-Json
    Confirm-Equal -Actual $scanError.error -Expected 'unreadable path' `
        -Message 'Unreadable path did not return JSON error contract.'

    Write-Output 'PASS: package contract, PowerShell root resolution, and stack detection'
}
finally {
    [Environment]::SetEnvironmentVariable('SKILL_ROOT', $originalSkillRoot)
    [Environment]::SetEnvironmentVariable('CLAUDE_PLUGIN_ROOT', $originalPluginRoot)

    if (Test-Path -LiteralPath $temporaryRoot) {
        $resolvedTemporaryRoot = [IO.Path]::GetFullPath($temporaryRoot)
        Confirm-Condition -Condition $resolvedTemporaryRoot.StartsWith(
            $temporaryBase,
            [StringComparison]::OrdinalIgnoreCase
        ) -Message 'Refusing to remove a temporary path outside the system temp directory.'
        Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force
    }
}
