# Smoke tests and isolated red drills for the PowerShell-native package scripts.

[CmdletBinding()]
param(
    [switch] $RedDrills
)

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

function Invoke-SmokeProcess {
    param(
        [Parameter(Mandatory)]
        [string] $TestPath
    )

    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = (Get-Process -Id $PID).Path
    $startInfo.Arguments = '-NoLogo -NoProfile -NonInteractive -File "{0}"' -f $TestPath
    $startInfo.WorkingDirectory = Split-Path -Parent (Split-Path -Parent $TestPath)
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        [void] $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        $timeoutMilliseconds = 60000
        if (-not $process.WaitForExit($timeoutMilliseconds)) {
            $process.Kill()
            $process.WaitForExit()
            throw 'Smoke test timed out; this is not an expected red drill.'
        }
        return @{
            ExitCode = $process.ExitCode
            Output = $stdout.GetAwaiter().GetResult() + $stderr.GetAwaiter().GetResult()
        }
    }
    finally {
        $process.Dispose()
    }
}

$repositoryRoot = [IO.Path]::GetFullPath((Join-Path -Path $PSScriptRoot -ChildPath '..'))
$rootScript = Join-Path -Path $repositoryRoot -ChildPath 'scripts/skill-root.ps1'
$scanScript = Join-Path -Path $repositoryRoot -ChildPath 'scripts/detect-stack.ps1'
$projectSetupSkill = Join-Path -Path $repositoryRoot -ChildPath 'skills/project_setup/SKILL.md'
$qualityRetrofitSkill = Join-Path -Path $repositoryRoot -ChildPath 'skills/quality_retrofit/SKILL.md'
$redDrillReference = Join-Path -Path $repositoryRoot -ChildPath 'docs/RED-DRILLS.md'
$codeQualityReference = Join-Path -Path $repositoryRoot -ChildPath 'docs/CODE-QUALITY.md'
$grillMeReference = Join-Path -Path $repositoryRoot `
    -ChildPath 'skills/project_setup/references/grill-me.md'
$projectBriefAsset = Join-Path -Path $repositoryRoot `
    -ChildPath 'skills/project_setup/assets/PROJECT_BRIEF.md'
$pluginManifest = Join-Path -Path $repositoryRoot -ChildPath '.claude-plugin/plugin.json'
$releaseBuilder = Join-Path -Path $repositoryRoot -ChildPath 'scripts/build-release.ps1'
$releaseWorkflow = Join-Path -Path $repositoryRoot -ChildPath '.github/workflows/release.yml'
$installationGuide = Join-Path -Path $repositoryRoot -ChildPath 'docs/INSTALLATION.md'
$temporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$temporaryRoot = Join-Path -Path $temporaryBase -ChildPath (
    'high-quality-projects-skill-test-{0}' -f [Guid]::NewGuid().ToString('N')
)

$originalSkillRoot = [Environment]::GetEnvironmentVariable('SKILL_ROOT')
$originalPluginRoot = [Environment]::GetEnvironmentVariable('CLAUDE_PLUGIN_ROOT')

try {
    if ($RedDrills) {
        # Copy the current source, including pending edits, without copying Git
        # metadata, ignored environments, or build output. Never mutate the source tree.
        $sourceFiles = @(& git -C $repositoryRoot -c core.quotepath=false ls-files --cached --others --exclude-standard)
        Confirm-Equal -Actual $LASTEXITCODE -Expected 0 -Message 'Could not inventory drill source.'
        [void] (New-Item -ItemType Directory -Path $temporaryRoot)
        foreach ($relativePath in $sourceFiles) {
            $sourcePath = Join-Path -Path $repositoryRoot -ChildPath $relativePath
            if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
                continue
            }
            $copyPath = Join-Path -Path $temporaryRoot -ChildPath $relativePath
            [void] (New-Item -ItemType Directory -Path (Split-Path -Parent $copyPath) -Force)
            Copy-Item -LiteralPath $sourcePath -Destination $copyPath
        }
        $copiedTest = Join-Path -Path $temporaryRoot -ChildPath 'tests/cross-platform-smoke.ps1'
        $green = Invoke-SmokeProcess -TestPath $copiedTest
        Confirm-Equal -Actual $green.ExitCode -Expected 0 -Message "Baseline failed: $($green.Output)"
        $successMessage = 'PASS: package contract, PowerShell root resolution, and stack detection'
        Confirm-Condition -Condition $green.Output.Contains($successMessage) `
            -Message 'Baseline did not complete the smoke suite.'
        Write-Output 'GREEN: existing smoke suite completed before mutations (exit 0)'

        $drills = @(
            @{
                Name = 'generated-directory pruning'
                Path = 'scripts/detect-stack.ps1'
                Before = "'node_modules', '.git',"
                After = "'.git',"
                Diagnostic = 'Python count or directory pruning is wrong.'
            },
            @{
                Name = 'explicit root override'
                Path = 'scripts/skill-root.ps1'
                Before = 'Write-Output (ConvertTo-AbsolutePath -Path $env:SKILL_ROOT)'
                After = 'Write-Output (Join-Path -Path (ConvertTo-AbsolutePath -Path $env:SKILL_ROOT) -ChildPath wrong-root)'
                Diagnostic = 'SKILL_ROOT override did not win.'
            },
            @{
                Name = 'unreadable-path error contract'
                Path = 'scripts/detect-stack.ps1'
                Before = "Write-ScanError -Message 'unreadable path'"
                After = "Write-ScanError -Message 'scan failed'"
                Diagnostic = 'Unreadable path did not return JSON error contract.'
            },
            @{
                Name = 'case-insensitive directory pruning'
                Path = 'scripts/detect-stack.ps1'
                Before = '[StringComparer]::OrdinalIgnoreCase'
                After = '[StringComparer]::Ordinal'
                Diagnostic = 'Python count or directory pruning is wrong.'
            },
            @{
                Name = 'knip.jsonc configuration detection'
                Path = 'scripts/detect-stack.ps1'
                Before = "-RelativePath 'knip.jsonc'"
                After = "-RelativePath 'knip.json'"
                Diagnostic = 'knip.jsonc configuration detection failed.'
            },
            @{
                # The anchor omits the SHA so routine Dependabot bumps keep it valid.
                Name = 'immutable workflow actions'
                Path = '.github/workflows/release.yml'
                Before = 'uses: actions/attest@'
                After = 'uses: actions/attest@v4 #'
                Diagnostic = 'Workflow action is not pinned to a commit SHA'
            }
        )
        foreach ($drill in $drills) {
            $targetPath = Join-Path -Path $temporaryRoot -ChildPath $drill.Path
            $originalBytes = [IO.File]::ReadAllBytes($targetPath)
            $originalHash = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash
            $originalText = [IO.File]::ReadAllText($targetPath)
            Confirm-Equal -Actual ([regex]::Matches($originalText, [regex]::Escape($drill.Before)).Count) `
                -Expected 1 -Message "Mutation must match exactly once: $($drill.Name)"
            try {
                [IO.File]::WriteAllText($targetPath, $originalText.Replace($drill.Before, $drill.After))
                $red = Invoke-SmokeProcess -TestPath $copiedTest
                Confirm-Condition -Condition ($red.ExitCode -ne 0) `
                    -Message "Mutation survived: $($drill.Name). $($red.Output)"
                Confirm-Condition -Condition $red.Output.Contains($drill.Diagnostic) `
                    -Message "Wrong failure for $($drill.Name): $($red.Output)"
                Write-Output "RED: $($drill.Name) (exit $($red.ExitCode)): $($drill.Diagnostic)"
            }
            finally {
                [IO.File]::WriteAllBytes($targetPath, $originalBytes)
                Confirm-Equal -Actual (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash `
                    -Expected $originalHash -Message "Restoration failed: $($drill.Name)"
            }
            $restored = Invoke-SmokeProcess -TestPath $copiedTest
            Confirm-Equal -Actual $restored.ExitCode -Expected 0 `
                -Message "Restored suite failed after $($drill.Name): $($restored.Output)"
            Confirm-Condition -Condition $restored.Output.Contains($successMessage) `
                -Message "Restored suite did not complete after $($drill.Name)."
            Write-Output "GREEN: $($drill.Name) restored byte-for-byte; smoke suite passed (exit 0)"
        }
        Write-Output "PASS: $($drills.Count) red drills caught intended defects and restored green"
        return
    }

    foreach ($requiredFile in @(
            $projectSetupSkill,
            $qualityRetrofitSkill,
            (Join-Path $repositoryRoot 'skills/feature_delivery/SKILL.md'),
            (Join-Path $repositoryRoot 'docs/DELIVERY.md'),
            (Join-Path $repositoryRoot 'templates/workflow/PLAN.md'),
            (Join-Path $repositoryRoot 'scripts/verify-delivery.py'),
            (Join-Path $repositoryRoot 'scripts/update-delivery.py'),
            $redDrillReference,
            $codeQualityReference,
            $grillMeReference,
            $projectBriefAsset,
            $pluginManifest,
            $releaseBuilder,
            $releaseWorkflow,
            $installationGuide
        )) {
        Confirm-Condition -Condition (Test-Path -LiteralPath $requiredFile -PathType Leaf) `
            -Message "Required package file is missing: $requiredFile"
    }

    $projectSetupContent = Get-Content -LiteralPath $projectSetupSkill -Raw -Encoding UTF8
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

    $grillMeContent = Get-Content -LiteralPath $grillMeReference -Raw -Encoding UTF8
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

    $projectBriefContent = Get-Content -LiteralPath $projectBriefAsset -Raw -Encoding UTF8
    Confirm-Condition -Condition $projectBriefContent.Contains('## Decision ledger') `
        -Message 'PROJECT_BRIEF asset is missing its decision ledger.'
    Confirm-Condition -Condition $projectBriefContent.Contains('## Readiness confirmation') `
        -Message 'PROJECT_BRIEF asset is missing its readiness confirmation.'
    Confirm-Condition -Condition $projectBriefContent.Contains('Existing branding items') `
        -Message 'PROJECT_BRIEF asset is missing its branding inventory.'
    Confirm-Condition -Condition $projectBriefContent.Contains('to reuse or extend') `
        -Message 'PROJECT_BRIEF asset is missing its reuse decision record.'

    $manifest = Get-Content -LiteralPath $pluginManifest -Raw -Encoding UTF8 | ConvertFrom-Json
    Confirm-Equal -Actual $manifest.version -Expected '0.6.0' `
        -Message 'Plugin manifest version does not match the automated release.'

    $releaseWorkflowContent = Get-Content -LiteralPath $releaseWorkflow -Raw -Encoding UTF8
    foreach ($requiredReleaseText in @(
            'uses: ./.github/workflows/cross-platform.yml',
            './scripts/build-release.ps1',
            'uses: actions/attest@',
            'gh release create'
        )) {
        Confirm-Condition -Condition $releaseWorkflowContent.Contains($requiredReleaseText) `
            -Message "Release workflow is missing required gate: $requiredReleaseText"
    }
    # Third-party actions in a job that can publish and sign must be immutable.
    foreach ($workflowPath in @(Get-ChildItem -LiteralPath (Join-Path $repositoryRoot '.github/workflows') -File)) {
        $workflowContent = Get-Content -LiteralPath $workflowPath.FullName -Raw -Encoding UTF8
        foreach ($use in [regex]::Matches($workflowContent, '(?m)^\s*(?:-\s+)?uses:\s*(\S+)')) {
            $reference = $use.Groups[1].Value
            Confirm-Condition -Condition (
                $reference.StartsWith('./') -or $reference -match '^[^@\s]+@[0-9a-f]{40}$'
            ) -Message "Workflow action is not pinned to a commit SHA: $($workflowPath.Name) $reference"
        }
    }

    $analyzerSettings = Import-PowerShellDataFile -LiteralPath (
        Join-Path $repositoryRoot 'templates/powershell/PSScriptAnalyzerSettings.psd1'
    )
    Confirm-Condition -Condition ($analyzerSettings.Rules.Count -gt 0) `
        -Message 'PSScriptAnalyzer template does not load as a data file.'

    $installationContent = Get-Content -LiteralPath $installationGuide -Raw -Encoding UTF8
    foreach ($requiredInstallText in @(
            'v0.6.0',
            'SHA256SUMS.txt',
            'gh attestation verify',
            'Bash is not required on Windows'
        )) {
        Confirm-Condition -Condition $installationContent.Contains($requiredInstallText) `
            -Message "Installation guide is missing release instruction: $requiredInstallText"
    }

    [Environment]::SetEnvironmentVariable('SKILL_ROOT', $null)
    [Environment]::SetEnvironmentVariable('CLAUDE_PLUGIN_ROOT', $null)

    [void] (New-Item -ItemType Directory -Path $temporaryRoot)
    $workspace = Join-Path -Path $temporaryRoot -ChildPath 'workspace with spaces'
    [void] (New-Item -ItemType Directory -Path $workspace)
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace 'src'))
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace 'node_modules'))
    # Generated-directory pruning is case-insensitive in both scanners.
    [void] (New-Item -ItemType Directory -Path (Join-Path $workspace 'Build'))
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
            'src/app.py', 'src/app.ts', 'src/view.tsx', 'src/Legacy.TS', 'src/browser.js',
            'src/lib.rs', 'src/App.cs', 'src/native.cpp', 'src/module.psm1',
            'src/style.scss', 'src/index.html', 'src/run.sh', 'src/main.go',
            'README.md', '.prettierrc', 'knip.jsonc', 'uv.lock', 'Cargo.lock', 'global.json',
            'node_modules/ignored.py', 'Build/generated.py'
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
    Confirm-Equal -Actual $scan.languages.typescript -Expected 3 `
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
    Confirm-Condition -Condition $scan.existing_config.knip_jsonc `
        -Message 'knip.jsonc configuration detection failed.'
    Confirm-Equal -Actual ($scan.lockfiles -join ',') -Expected 'uv.lock,Cargo.lock' `
        -Message 'Lockfile inventory or its declared order is wrong.'
    Confirm-Equal -Actual ($scan.toolchain_pins -join ',') -Expected 'global.json' `
        -Message 'Toolchain pin inventory is wrong.'
    foreach ($toolKey in @('dpdm', 'go', 'psscriptanalyzer', 'pester', 'actionlint', 'zizmor')) {
        Confirm-Condition -Condition ($scan.tools_installed.$toolKey -is [bool]) `
            -Message "Tool inventory is missing boolean key: $toolKey"
    }
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
