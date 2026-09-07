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
- This v0.5.0 template review did not include live agent trials. The v0.6.0
  evaluation below covers specific decisions and outcomes; prompt text checks
  and tool drills do not establish behavior for every agent and project.

Ongoing verification: exercise all workflows on representative projects and record
missed behavior. Every release still requires its tagged cross-platform workflow
and independent verification of the published artifacts.

## Native delivery verification for v0.6.0

The shared lifecycle, native ledger, feature-delivery entry point, structural
validator, atomic writer, and workflow handoffs are implemented. New delivery
and evaluation machinery is first-party Python using its standard library.
The previous language-template evidence remains scoped as described above.

Local verification currently passes 46 unittest tests, strict mypy for the ten
delivery source files, Ruff 0.16.4 lint/format, PowerShell 5.1/7 smoke red drills,
and reproducible archive inspection. Tests cover malformed records, coverage,
cycles, stale input/context, false completion, actual file outcomes, artifact
integrity, red-proof rejection, atomic conflicts, interruption, and idempotence.
Two real validator mutations fail existing assertions, restore exact bytes,
and return green. Independent outcome controls reject broken behavior, vacuous
or zero tests, duplicate domain logic, premature changes, forged environment
claims, and replayed side effects.

The first hosted run found missing executable bits on the two new entry points.
Commit `2e39813` corrected their Git modes. All twelve jobs then passed in
[run 34164930093](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/34164930093):
Python 3.12/3.14 on Windows/Linux/macOS, native PowerShell including 5.1,
Bash/PowerShell inventory parity, and release-package checks. Final release
source must pass the same matrix again after evidence reconciliation.

The README uses the tracked warm-ivory, charcoal, and copper artwork. The
GitHub Markdown rendering was inspected with official styles in light/dark
themes at 375px and 1440px widths: no page overflow, one primary heading,
loaded images with meaningful alternatives, and readable comparisons. The
published README and saved GitHub social-preview setting were visually checked.
This is README presentation evidence, not accessibility certification of an
application produced by a workflow.

Live agent trials and their final evidence reconciliation are in progress under
the [behavioral protocol](../tests/behavioral/README.md). Their acceptance is
independent of deterministic test and hosted CI success. Exact-tag publication,
published artifact/provenance verification, and installed discovery remain open
until the release has actually completed.
