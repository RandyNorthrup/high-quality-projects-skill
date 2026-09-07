# Quality review: 2026-09-07

Scope: the initial local review of source based on `753a866`, plus the workflow,
template, test, and documentation changes prepared for v0.5.0. Primary sources
and decisions are linked beside the relevant guidance in
[CODE-QUALITY.md](CODE-QUALITY.md). These results
supersede only the corresponding older template observations.

## Findings corrected

| Area | Finding | Correction |
|---|---|---|
| Workflow | Reuse and failure verification uneven across workflows | Shared red-drill procedure, focused rescans, canonical-path evidence, recurring verification |
| Python | Production assertions and untyped test helpers broadly exempt | Assertions limited to test paths; fixture annotations retained |
| TypeScript | Runtime defaults, global constants bucket, broad local/test/MJS exemptions | Project-owned host settings, domain-local constants, narrow exemptions |
| ESLint | Existing presets accepted self-comparison | Explicit `no-self-compare`; exhaustive union-switch checks |
| Rust | Workspace inheritance unclear; duplicated unwrap bans defeated allowances | Explicit member inheritance and one canonical panic policy |
| C++ | Relative-only header filter missed absolute header paths | Owned directory-component filter for Windows and POSIX |
| C# | Early props forced a TFM and `LangVersion=latest` | Project-owned frameworks/language choice; SDK pinning guidance |
| PowerShell | State-change rule excluded; Core profiles did not exist | Rule restored; real shipped inventories with historical limits |
| SAST | Ordinary Semgrep findings could exit zero | `semgrep scan --error` and verified console-entrypoint guidance |
| Maintainer safety | Reviewer guidance deleted pre-existing environments | Explicit scope or isolated copies |

## Executed template drills

Each row used the current template in a disposable project. The command first
passed, then rejected the intended defect, then passed after restoration of the
original bytes. Unrelated errors received no credit. Commands are relative to
the fixture project with the listed tools installed; use the selected
interpreter/console entry point if an executable is absent from PATH.

| Gate command | Injected defect | Required diagnostic | Exit sequence |
|---|---|---|---|
| `ruff check .` | Production assertion | `S101` | 0 -> 1 -> 0 |
| `ruff check .` | Integer self-comparison | `PLR0124` | 0 -> 1 -> 0 |
| `mypy .` | Code after unconditional return | `unreachable` | 0 -> 1 -> 0 |
| `eslint src --max-warnings=0` | Self-comparison | `no-self-compare` | 0 -> 1 -> 0 |
| `eslint src --max-warnings=0` | Unused `_dead` local | `no-unused-vars` | 0 -> 1 -> 0 |
| `eslint src --max-warnings=0` | Missing union switch case | `switch-exhaustiveness-check` | 0 -> 1 -> 0 |
| `tsc --noEmit` | Undefined returned from boolean function | `TS2322` | 0 -> 2 -> 0 |
| `cargo clippy --offline --workspace --all-targets --all-features -- -D warnings` | Self-comparison in package | `eq_op` | 0 -> 101 -> 0 |
| Same Clippy command in a virtual workspace | Self-comparison in inheriting member | `eq_op` | 0 -> 101 -> 0 |
| `dotnet build --nologo --verbosity quiet` | Redundant condition after early return | `CA1508` | 0 -> 1 -> 0 |
| `clang-tidy src/main.cpp -- -std=c++23` | Self-comparison in included owned header | `tautological-compare` | 0 -> 1 -> 0 |
| `Invoke-ScriptAnalyzer -Path ./canary.ps1 -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit` | Remove `SupportsShouldProcess` while calling guard | `PSShouldProcess` and state-change warning | 0 -> 2 -> 0 |
| `stylelint domain.css --max-warnings=0` | Duplicate selector | `no-duplicate-selectors` | 0 -> 2 -> 0 |
| `htmlhint domain.html` | Duplicate element ID | `id-unique` | 0 -> 1 -> 0 |
| `semgrep scan --error --metrics=off --disable-version-check --config rules.yml domain.py` | Self-comparison matched by local synthetic rule | `self-comparison` | 0 -> 1 -> 0 |

Additional positive controls:

- A named TypeScript constant local to its domain passes without a file-wide
  exemption; NodeNext module/resolution settings work with the strict base.
- The C# fixture builds both project-owned `net8.0` and `net10.0` targets.
- The PowerShell fixture preserves an absent resource under `-WhatIf`, writes
  under normal execution, and surfaces an invalid-destination failure.
- Every PowerShell compatibility profile exists in the installed analyzer.

Environment: Windows; Python 3.14.0; Ruff 0.16.4; mypy 2.3.1; Node 24.20.0;
ESLint 10.10.0; `@eslint/js` 10.0.1; typescript-eslint 8.69.0; TypeScript 6.0.3;
Unicorn 74.0.0; Rust/Clippy 1.96.0; .NET SDK 10.0.400; clang-tidy 22.1.1;
PSScriptAnalyzer 1.25.0; Stylelint 17.15.0 with standard config 40.0.0;
HTMLHint 1.9.2; Semgrep 1.174.0. npm peer constraints were queried before the
temporary JS install; none were bypassed. Python/JS audit dependencies were
installed only in disposable directories. Existing host tools were reused.

## Package drill harness

`tests/cross-platform-smoke.ps1 -RedDrills` maintains three repeatable drills
using the existing suite: directory pruning, explicit root override, and
unreadable-path errors. Each completed green/red/restored-green under PowerShell
7 and Windows PowerShell 5.1.

The harness was itself checked in an isolated snapshot under both shells. A
surviving mutation, wrong expected diagnostic, and stale mutation anchor each
caused a non-zero parent exit. The snapshot was restored clean afterwards.
Release archives from the isolated current-source snapshot passed structure,
metadata, notes, checksums, and cross-time-zone reproducibility under both shells.

## Limits and follow-up gates

- These are selected semantic canaries, not exhaustive verification of every
  rule, template combination, feature set, or generated project.
- Go, ShellCheck/shfmt, and a standalone C compiler gate were not executed.
  Go/shell guidance uses primary sources; runtime checks remain required in
  target projects. C++ evidence does not certify C. Sanitizers were not rerun.
- HTML/CSS checks prove the named static diagnostics, not keyboard,
  screen-reader, browser, or responsive behavior of an application.
- This local template review ran on Windows. The separate package release gate
  runs the smoke/red-drill suite and archive checks on Windows, Linux, and macOS.
  Consult the [release workflow](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/workflows/release.yml)
  for the tagged commit's result and verify published archive provenance using
  [the installation guide](INSTALLATION.md). Package CI does not expand these
  selected template canaries into cross-platform validation of every language.
- The generic skill validator rejects established underscore names. Names were
  retained for adapter compatibility and checked against folders; remaining
  frontmatter/body checks were exercised on disposable copies with only the
  name normalized.
- Skill prompt behavior still needs representative setup/retrofit trials.
  Prompt text checks and executable tool drills do not establish that every
  agent will follow the instructions in every project.

Ongoing follow-up: exercise both workflows on representative projects and record
missed behavior. Every release still requires its tagged cross-platform workflow
and independent verification of the published artifacts.
