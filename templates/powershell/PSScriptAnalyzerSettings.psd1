<#
    Strict PSScriptAnalyzer settings. Copy to project root as
    PSScriptAnalyzerSettings.psd1, then run:

        Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit

    -EnableExit is what makes it a gate: non-zero exit when any rule fires.
#>
@{
    # Every built-in rule, including the ones off by default.
    IncludeDefaultRules = $true
    Severity = @('Error', 'Warning', 'Information')

    ExcludeRules = @(
        # Demands Write-Host be replaced with Write-Output everywhere. For
        # interactive CLI tools coloured Write-Host is correct.
        'PSAvoidUsingWriteHost'
    )

    Rules = @{
        PSPlaceOpenBrace = @{
            Enable = $true
            OnSameLine = $true
            NewLineAfter = $true
            IgnoreOneLineBlock = $true
        }
        PSPlaceCloseBrace = @{
            Enable = $true
            NewLineAfter = $true
            IgnoreOneLineBlock = $true
            NoEmptyLineBefore = $false
        }
        PSUseConsistentIndentation = @{
            Enable = $true
            Kind = 'space'
            IndentationSize = 4
            PipelineIndentation = 'IncreaseIndentationForFirstPipeline'
        }
        PSUseConsistentWhitespace = @{
            Enable = $true
            CheckInnerBrace = $true
            CheckOpenBrace = $true
            CheckOpenParen = $true
            CheckOperator = $true
            CheckPipe = $true
            CheckSeparator = $true
        }
        # Alignment pads assignments with extra spaces, which directly
        # conflicts with PSUseConsistentWhitespace.CheckOperator.
        PSAlignAssignmentStatement = @{ Enable = $false }
        # Full cmdlet names only -- no `ls`, `%`, `?` in committed scripts.
        PSAvoidUsingCmdletAliases = @{ Enable = $true }
        PSUseCorrectCasing = @{ Enable = $true }
        # These are shipped historical command inventories, not proof of current
        # host compatibility. Select installed profiles for the support contract
        # and execute tests on actual supported hosts. Do not invent profile IDs.
        PSUseCompatibleCmdlets = @{
            Compatibility = @(
                'desktop-5.1.14393.206-windows',
                'core-6.1.0-linux',
                'core-6.1.0-windows',
                'core-6.1.0-macos'
            )
        }
    }
}
