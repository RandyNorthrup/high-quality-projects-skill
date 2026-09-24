# Run PSScriptAnalyzer with the shipped template settings over the given files.
#
# This repository's pre-commit hook and CI use it so the package passes the
# PowerShell gate it asks other projects to adopt. Any finding or analyzer
# failure exits non-zero; an analyzer error is never reported as a clean file.

[CmdletBinding()]
param(
    [Parameter(Mandatory, ValueFromRemainingArguments)]
    [string[]] $Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$settings = Join-Path -Path $PSScriptRoot -ChildPath '../templates/powershell/PSScriptAnalyzerSettings.psd1'
$findings = @(
    foreach ($file in $Path) {
        Invoke-ScriptAnalyzer -Path $file -Settings $settings -ErrorAction Stop
    }
)

foreach ($finding in $findings) {
    '{0}:{1}:{2}: {3} [{4}]' -f $finding.ScriptPath, $finding.Line, $finding.Column,
    $finding.Message, $finding.RuleName
}

if ($findings.Count -gt 0) {
    exit 1
}
