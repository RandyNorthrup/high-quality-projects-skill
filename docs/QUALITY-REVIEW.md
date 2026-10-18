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

All 24 live core trials passed independent evaluation: three fresh attempts each
for incomplete discovery, canonical reuse, configuration preservation,
contradictory requirements, vacuous tests, false completion, stale resume, and
uncertain external outcomes. The [compact evidence record](evaluations/v0.6.0.json)
preserves individual outcomes, fixture identities, actual recorded commands,
independent test results, and artifact hashes. Raw workspaces remain under ignored
`dist/behavioral-v0.6.0/` on the evaluation host. No failed outcome was averaged
away or replaced by a self-reported success statement.

A twenty-fifth fresh-agent check resumed an already verified copy of `reuse-1`.
Independent before/after hashing found zero changed existing artifacts. The plan
remained byte-identical at SHA-256
`7e46b9fd7f47d41d104885ba7167470954e1b01ecf23b921bdb8d241bb335164`;
the agent also checked its unchanged modification time. It reran six tests and
Ruff, reviewed still-current red evidence, and created no duplicate task or receipt.

These trials used the supplied Codex collaboration runtime with fresh contexts
on Windows/Python 3.14.0 and Ruff 0.15.9. Session instructions identify the GPT-6
family; the harness does not expose an exact model build, so no build-specific
or cross-model claim is made. Several subjects recovered from an unsupported
PowerShell `-Path` argument by reading the scanner and using `-Root` before any
write. Discovery trials intentionally stop for missing decisions; outcome trials
use local fixture state and do not certify a real deployment. Full application
scaffolding and arbitrary generated projects remain target-project verification,
not capabilities certified by this bounded evaluation.

All three skill files match their folder names. Other generic skill-validator
checks passed on disposable copies with only underscore names normalized, using
Python UTF-8 mode to avoid the system validator's Windows locale-dependent read.
The installed names remain unchanged for package compatibility.

The final code and expanded evidence checks passed all twelve hosted jobs in
[run 34165497453](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/34165497453)
at `40e6d12`. The final documentation/evidence commit `b78723b` also passed all
twelve jobs in [run 34166710142](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/34166710142).

### Publication and installed package receipt

[v0.6.0](https://github.com/RandyNorthrup/high-quality-projects-skill/releases/tag/v0.6.0)
was published from commit `b78723b1a07833e716769678c3af0a612551617a`, annotated tag
object `3674041d48b099e62ab3484e10c374b1ae2e2830`. All thirteen release jobs passed
in [run 34166806043](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/34166806043),
including the reused platform gates and build/attestation/publication job.

All five downloaded assets matched the local exact-tag build byte-for-byte.
Checksums, manifest version/source identity, notes, and all 76 committed files
in both archive formats were independently verified. Archive SHA-256 values:

| Archive | SHA-256 |
|---|---|
| ZIP | `f796d40744836035a93322d1e82bf6217b270c108425dce10173f9ae9f6b8e9f` |
| tar.gz | `3ce31eed4b3e4746772c5f9c180b754d86bfa332430d98b38270f195e74512f6` |

GitHub CLI verified both signed attestations. Their certificate and provenance
fields identify this repository, the exact commit, `refs/tags/v0.6.0`, and
`.github/workflows/release.yml`. A transient verifier initialization error on the
tarball was resolved by a sequential retry; both final verifications succeeded.
Local receipts remain under ignored `dist/verification-v0.6.0/`.

The canonical installed clone was fast-forwarded to the verified release.
All 76 installed files matched the published ZIP byte-for-byte. Existing setup
and retrofit junctions were retained, and the feature-delivery junction was
added. A fresh read-only Codex `skills/list` request with `forceReload` returned
exactly one enabled result for each namespaced workflow. No model turn was
needed for discovery verification.

This post-publication receipt is maintained on main. The installed clone remains
at exact release source; the immutable tagged plan records its prerequisite
boundary, while this audit and the current plan record completed publication.
No implementation or required release gate remains open.

## Post-release audit: 2026-09-24

Scope: an audit of `1789ed0` (v0.6.0 plus evidence commits) for missing tools,
gates this repository prescribed but did not run on itself, and template
defects. Every finding below was reproduced before it was fixed. The earlier
sections remain the record for their own dates.

### Findings corrected

| Area | Finding | Correction |
|---|---|---|
| C# template | `Directory.Build.props` has been malformed XML since v0.5.0 (`--` inside a comment); MSBuild failed with `MSB4024` | Comment reworded; `tests/test_templates.py` parses every template the standard library can read |
| C# template | IDE0051/IDE0052 were listed as the dead-code gate, but no severity was configured, so an unused private method built cleanly | `csharp/.editorconfig` sets IDE0051, IDE0052, IDE0059, IDE0060, and IDE0005 to error |
| PowerShell template | `PSUseCorrectCasing` threw `NullReferenceException` intermittently (1.24.0 and 1.25.0, PowerShell 7.6.6); a planted violation went unreported with exit 0 | Rule disabled with evidence; all documented commands add `-ErrorAction Stop` |
| mypy template | No equivalent of TypeScript's override and exhaustive-switch checks | `explicit-override`, `exhaustive-match`, `mutable-override`, `truthy-iterable`, `deprecated` |
| Pre-commit template | vulture hook exited 2 without paths; mirrors-mypy turned dependencies into `Any`; ShellCheck hook needed Docker; `mixed-line-ending --fix=lf` rewrote CRLF-by-policy files | Hook `args`; project-environment mypy hook; `shellcheck-py`; `--fix=no` |
| Rust template | cargo-deny was a listed gate with no policy; its defaults rejected even an MIT crate | `rust/deny.toml` |
| `verify-format-safe.py` | Missing, undecodable, or directory input exited 1 ("AST changed"); valid Latin-1 source rejected | Parses bytes; input errors exit 2; tests added |
| Plan writer | Replacement plan became owner-only (0600) on POSIX | Mode preserved or umask-derived; directory flushed after rename |
| Release builder | The documented `build-release.ps1 -Version` step recursively deleted the ignored `dist/`, including unrelated local files | Replaces only its own artifacts; refuses a directory holding anything else; release smoke test checks a sentinel |
| `detect-stack.sh` | Unescaped JSON root; case-sensitive matching unlike PowerShell; one tree walk per extension | Escaped strings, one case-insensitive walk, parity-checked |
| Repository gates | ShellCheck, shfmt, PSScriptAnalyzer, vulture, Bandit, gitleaks history, coverage, and mypy on tests were not run by CI | Frozen pre-commit configuration and CI jobs run them all |
| CI supply chain | Actions pinned to movable tags; credentials persisted by checkout; no timeouts; unhashed tool installs; no update automation | SHA pins, `persist-credentials: false`, timeouts, hash lock, Dependabot with cooldown |

### Executed drills

Each row passed first, failed for the named reason, then passed again after
byte-identical restoration, unless the row states otherwise. Commands ran in
disposable copies or fixtures; the working tree was never mutated.

| Gate | Injected defect | Required diagnostic | Exit sequence |
|---|---|---|---|
| `unittest tests.test_verify_format_safe` | Original helper, before the fix | four failures (`1 != 2`, `1 != 0`) | 1 -> 0 after fix |
| `unittest tests.test_update_delivery` (Linux) | Remove mode preservation | `AssertionError: 384 != 420` | 0 -> 1 -> 0 |
| `unittest tests.test_templates` | Original props template | `ParseError: … line 32, column 11` | 1 -> 0 after fix |
| mypy 2.3.1 with the template | Missing `@override`; missing match case; narrowed mutable attribute; truthiness of an `Iterable`; call to a `@deprecated` function | `[explicit-override]`, `[exhaustive-match]`, `[mutable-override]`, `[truthy-iterable]`, `[deprecated]` | 0 -> 1 -> 0 each |
| Template pre-commit hooks | Wrong return type; unused function; lost executable bit; unknown `github` property; unpinned action | `[return-value]`, `unused function 'orphan'`, `marked executable`, `nonexistent_property`, `unpinned-uses` | 0 -> 1 -> 0 each |
| `dotnet build` with both C# templates | Unused private method; unread field; overwritten value; unused parameter; unnecessary `using` | IDE0051, IDE0052, IDE0059, IDE0060, IDE0005 | 0 -> 1 -> 0 each |
| `cargo deny check` with the template | License outside the allow-list; wildcard path dependency | `rejected`; `wildcard` | 0 -> 4 -> 0; 0 -> 2 -> 0 |
| `coverage report` (Linux) | Remove `test_verify_format_safe.py` | `total of 80.7 is less than fail-under=82.0` | 0 -> 2 -> 0 |
| `cross-platform-smoke.ps1 -RedDrills`, PowerShell 7 and 5.1 | Six maintained mutations | Each existing assertion message | 0 -> 1 -> 0 each |

Additional observations:

- PSScriptAnalyzer, ten fresh processes each: the new template exited 0 on a
  clean script every time and 1 on an alias violation every time. With the
  casing rule re-enabled and `-ErrorAction Stop`, three crashes all exited 1.
- The superseded hooks, observed directly: mirrors-mypy rejected correct code
  with `Return type becomes "Any" due to an unfollowed import`; the old vulture
  hook printed `Please pass at least one file or directory`; `--fix=lf`
  rewrote a uniformly CRLF `.ps1` and exited 1, while `--fix=no` passed it and
  still rejected a mixed file.
- A first smoke drill that removed `ToLowerInvariant()` survived: PowerShell
  hashtables already compare keys case-insensitively. It was replaced with the
  case-insensitive directory-pruning drill rather than counted.
- Scanner parity on a mixed-case fixture: bash and PowerShell now agree on every
  section; the previous bash scanner counted `Build/` and missed `.TS` and `.H`.
  On a local multi-project workspace with more than 29,000 counted source
  files, the previous bash scanner took 480.0 s, the new one 16.3 s, and
  PowerShell 16.5 s, with identical counts (Git Bash on Windows). On Linux, a directory
  named with a quote, backslash, and tab produced invalid JSON before the change
  and an exact root afterwards.
- `requirements-dev.txt` installed with `--require-hashes` on Windows (Python
  3.12.14 and 3.14.0) and Linux (3.14.7). Under 3.12 the suite passed 58 tests
  at 84.2% coverage. Coverage measured 83.1% on Windows and 83.3% on Linux.
- The repository pre-commit configuration passed on all 87 files, the smoke
  suite passed under PowerShell 7 and 5.1, actionlint and zizmor reported no
  findings, and gitleaks found no leaks in 31 commits.

Environment: Windows 11, PowerShell 7.6.6 and Windows PowerShell 5.1, Python
3.14.0 and uv-managed 3.12.14; Arch Linux on WSL2 with Python 3.14.7. Ruff
0.16.4, mypy 2.3.1, coverage 7.16.1, Bandit 1.9.4, vulture 2.16, pre-commit
4.6.2, ShellCheck 0.11.0, actionlint 1.7.12, zizmor 1.30.1, PSScriptAnalyzer
1.25.0, .NET SDK 10.0.401, cargo 1.96.0, cargo-deny 0.19.9, gitleaks 8.30.1.
The pinned CI gitleaks 8.30.0 archive matched its published SHA-256.

### Limits and open gates

- Hosted CI: all thirteen jobs passed in
  [run 36073624130](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/36073624130)
  at `1c43b29`, including macOS, the POSIX parity and escaping check, the
  repository hooks, and the full-history gitleaks scan. The release job runs
  only for the v0.7.0 tag; its receipt is recorded after publication.
- `release-package-smoke.ps1` passed on the committed tree under PowerShell 7
  and Windows PowerShell 5.1.
- The release-builder defect was found by running the documented v0.7.0 build
  step, which deleted this checkout's ignored `dist/` before the fix. Its
  earlier contents were not listed first and could not be recovered. If the
  v0.6.0 raw trial workspaces and local verification receipts named above were
  still there, they are gone; the committed evaluation record, hashes, and this
  review are unaffected.
- Dependabot's `uv` and `pre-commit` ecosystems handled this lock and these
  frozen revisions on their first run; see the publication receipt below.
- The release workflow keeps `uses: ./…` instead of zizmor's suggested `$/…`
  self-repository form, because only a tagged release exercises that path.
- New guidance tools (mutation, property/fuzz, benchmark, axe-core,
  OSV-Scanner, Syft, hadolint) cite verified primary sources but were not
  drilled here; target projects must drill them before relying on them.
- No Go, Java/Kotlin, or Swift templates were added. The skill wording changed;
  live agent trials were not rerun for it.
- The scanners' Python interpreter probes (as before) and the new bash
  PowerShell-module probe run without a timeout; a hung interpreter would stall
  the scan. None hung in these runs.

### Publication receipt: v0.7.0

[v0.7.0](https://github.com/RandyNorthrup/high-quality-projects-skill/releases/tag/v0.7.0)
was published from commit `5ceda266cd5e17f63f3ddddb51149a35a6354c8d` by its
annotated tag. That commit first passed all thirteen jobs on main in
[run 36074289824](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/36074289824);
the tag then passed all fourteen release jobs, the thirteen reused gates plus
build, attestation, and publication, in
[run 36074501215](https://github.com/RandyNorthrup/high-quality-projects-skill/actions/runs/36074501215).

All five downloaded assets matched a local build of the same tag byte for byte.
Published checksums, the manifest's version, tag, and commit, and all 87
committed files in both archive formats were verified independently. Both
archive attestations verified with GitHub CLI; their certificates name this
commit, `refs/tags/v0.7.0`, and `.github/workflows/release.yml`.

| Archive | SHA-256 |
|---|---|
| ZIP | `6de488a8c318a42a7ca1512367540ca49f7ee2955643d78b25431370ffae6b7b` |
| tar.gz | `04699ee40c94257ebc29f25df2222966d074abe3e8be9767ce932dfc8d7e0604` |

Dependabot's first run opened three grouped proposals as soon as its
configuration landed: GitHub Actions (checkout v7.0.1, setup-python v7.0.0),
pre-commit hooks (gitleaks v8.30.1, ruff-pre-commit v0.16.8), and the
hash-locked Python tools (ruff 0.16.8, with every hash regenerated). Each
passed all thirteen jobs, and each new SHA matched its upstream tag. All three
were squash-merged after the release and are not part of v0.7.0. The release
workflow has not yet run with checkout and setup-python v7; the next tag is
the first to exercise them.

## Practices enforcement: 2026-10-17

Scope: commits `fd96289`, `85f373e`, and `799b2d6` on branch
`lessons/2026-10-17`, from base `18e47cf` (v0.7.0 plus evidence). They add
`verify-practices.py`, the CI and project-rules templates, and the workflow
changes that route to `docs/PRACTICES.md`. They also make this repository pass
the new checker. The checks are general engineering practice; nothing in them
is specific to one kind of product.

### What the checker found here first

The first run against this repository refused: two uses of `unittest.mock`
(`tests/test_update_delivery.py` and `tests/behavioral/probe.py`), a gate
workflow without `merge_group`, and the absence of `upstreams.json` and a
pitfalls register. Each was fixed in the code, not allowed:

- The atomic-writer tests now meet real OS refusals. On Windows, an open
  handle makes the final replace fail. On POSIX, a no-write umask makes the
  lock's owner file uncreatable after `mkdir`.
- The behavioral oracle observes calls into the canonical helper with
  `sys.setprofile` instead of replacing it.
- `cross-platform.yml` runs on `merge_group`. The CI gitleaks binary moved
  from 8.30.0 to 8.30.1, after the archive matched the release's published
  checksum and the binary scanned this history (44 commits, no leaks, exit 0)
  under WSL.
- `upstreams.json` pins gitleaks, PSScriptAnalyzer, and the GitHub REST API
  version the watch sends (2026-03-10). `CONTRIBUTING.md` carries a register
  of six pitfalls, each enforced by a test or a check.

### Executed drills

Every drill passed first, failed for the named reason with a non-zero exit,
and passed again after restoration. Restoration was compared by SHA-256.
Source was mutated only in disposable copies.

| Gate or test | Injected defect | Required failure |
|---|---|---|
| `tests/test_red_drills.py` (maintained, 27 drills) | Removed or disabled each detection rule of the checker (mock imports and calls, fake servers, stand-ins, flaky markers, comment masking, other-language imports, Pester, manifests, presence-only and copied tests, sleeps, per-test timeouts, `merge_group`, path filters, secrets, timeouts, staleness, pin drift, live tag parsing, register rules, allowance reasons), two validator rules, and the oracle's delegation check | The named test fails with `AssertionError`; each run exits non-zero; then green |
| The drill harness itself | A behavior-neutral mutation; a drifted anchor | `Defect survived` and `Mutation anchor drifted`, harness exit 1 |
| `test_failure_before_replace_preserves_complete_plan` (Windows) | Temporary-file cleanup removed | Leftover `.tmp` listed, exit 1 |
| `test_failed_owner_write_releases_owned_lock` (Linux, WSL) | Lock cleanup on a failed owner write removed | `AssertionError: True is not false`, exit 1 |
| `tests/test_templates.py` | New templates not yet classified | Completeness assertion listed the four files, exit 1 |
| zizmor 1.30.1 on `templates/ci/quality.yml` | `actions/setup-python@v7` instead of a SHA | `unpinned-uses`, exit 14 |

The drill table also caught one of its own stale anchors after a refactor,
failing instead of skipping, as designed.

### Results

- Windows: 69 tests pass with 4 skips: two POSIX mode-bit tests, the POSIX
  umask test, and the symlinked start, because this host cannot create
  symlinks without privilege (WinError 1314). Coverage is 85.1% against the
  82% floor. Every repository hook passes, including `verify-practices`; the
  broken-symlink hook had no files to check.
  `cross-platform-smoke.ps1 -RedDrills` passes its six drills under PowerShell
  7.6.6 and 5.1.26100.9711. `release-package-smoke.ps1` passes under both from
  native PowerShell.
- Linux (Arch on WSL2, Python 3.14.7, non-root): 69 tests pass with 1 skip,
  the Windows-only replace refusal. The symlinked start passes.
- Real use: `verify-practices.py --root . --rules CONTRIBUTING.md` passes on
  45 code files with no allowances. `--watch` queried GitHub live and reported
  all three upstreams current (exit 0). In a scratch project that had last seen
  gitleaks 8.30.0, it reported the real 8.30.1 release (exit 1).
- Both CI templates pass actionlint 1.7.12 and zizmor 1.30.1.

Environment: Windows 11, Python 3.14.0 with the hash-locked tools (Ruff
0.16.8, mypy 2.3.1, coverage 7.16.1, vulture 2.16, Bandit 1.9.4, pre-commit
4.6.2), PSScriptAnalyzer 1.25.0, PowerShell 7.6.6 and Windows PowerShell 5.1.

### Limits and open gates

- Hosted CI has not run on these commits; nothing is pushed. The macOS jobs,
  and the Windows CI symlink case, run only there.
- `test_release_watch_queries_github_live` needs network access and fails,
  never skips, when GitHub is unreachable. CI passes it the automatic
  read-only token to stay within the API rate limit.
- From Git Bash, `release-package-smoke.ps1` fails to list the tar.gz archive,
  because the GNU `tar` first on that PATH reads `C:` as a remote host. The
  script is unchanged; from native PowerShell it passes.
- The checker matches patterns. Test shape is analyzed for Python and the
  JavaScript family only, and comment and literal masking for other languages
  is approximate (`masking.py` is 67% covered). Its documented blind spots,
  such as a fake CLI on `PATH` or a manual re-run in the CI interface, remain
  review work.
- Live agent trials were not rerun for the changed workflow wording. Enabling
  a merge queue and branch protection are repository settings for the owner.

## Seven general practices: 2026-10-17

Scope: commits `6e00973` (plan), `1022541`, `e30be59`, and `d0c2ad1` on branch
`lessons/2026-10-17`, from base `d69b3f8`. Each practice is general; nothing
in it names a kind of product, tool vendor, or contributor.

| Practice | Where it landed | Kind |
|---|---|---|
| Check flagged dead code against unmerged branches and open plans | `PRACTICES.md`, `quality_retrofit` phase 5 and "Refuse to", rules template | Documented |
| Error messages name the real cause | `error-cause` check; `PRACTICES.md`, `CODE-QUALITY.md`, `quality_retrofit` phase 7, rules template | Enforced |
| A hand-written object, scripted port, or local server is a stand-in | `hand-written-double` check and the inline-handler `fake-server` form; `PRACTICES.md`, the workflows, rules template | Enforced for named and inline forms |
| Small single-outcome tasks, finish first, merge small, release-candidate integration | `PRACTICES.md` "Parallel work", `DELIVERY.md`, all three workflows, rules template | Documented |
| Files every change edits become per-item files joined by a script | `PRACTICES.md`, `DELIVERY.md`, `project_setup`, `feature_delivery`, rules template | Documented |
| Worktrees without `git stash` or base-branch checkouts | `git-shared-state` check; `PRACTICES.md`, `feature_delivery`, `quality_retrofit`, rules template | Enforced in checked-in automation |
| Local gates run only touched suites; hosted CI is the full gate | `local-full-suite` check; `PRACTICES.md`, the workflows, rules template, `CONTRIBUTING.md` | Enforced for hook configuration |

The documented practices, and the parts of the enforced ones that no file
pattern shows, are listed under "What the command cannot see" in
`PRACTICES.md`. The four new checks accept reviewed allowances: each matches
names or command text, which can misread a legitimate case.

### Executed drills

The maintained table in `tests/test_red_drills.py` grew from 27 to 43 drills.
Each new drill breaks one rule in a disposable copy, requires the named test
to fail with `AssertionError` and a non-zero exit, restores the bytes
(SHA-256 compared), and requires green again. Four of them break negative
controls instead of detections: the caught-error name, the C#/C++ rethrow, the
three-argument `type()` builder, and the `-b`/`--detach` worktree exception. A
checker that fired on everything fails those, as one that fired on nothing
fails the others.

| Rule | Drills |
|---|---|
| `error-cause` | Python handler condition, caught-name recognition, masked-body emission, rethrow recognition |
| `hand-written-double` and `fake-server` | Python class, `type()` arity, JavaScript-family class, JavaScript-family function binding, inline `createServer`, C-family and Go types |
| `git-shared-state` | Stash pattern, base-worktree pattern, `-b`/`--detach` exception, Python process calls |
| `local-full-suite` | pre-commit change-ignoring settings, Git hook scripts |

### Results

All on Windows 11 at `d0c2ad1`, with temporary files kept under the
repository's ignored `build/tmp/`:

| Gate | Exit |
|---|---|
| `ruff format --check .` (64 files) | 0 |
| `ruff check .` | 0 |
| mypy, package scripts (26 files) | 0 |
| mypy, tests (14 files) | 0 |
| `verify-practices.py --root . --rules CONTRIBUTING.md` (47 code files, no allowances) | 0 |
| Full suite with coverage: 71 tests, 4 skips, 86.3% against the 82% floor | 0, report 0 |
| `pre-commit run --all-files` | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, PowerShell 7.6.6 | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, Windows PowerShell 5.1.26100.9711 | 0 |

The four skips are the same as before: two POSIX mode-bit tests, the POSIX
umask test, and the symlinked start (WinError 1314).

Real use: a scratch project with one planted violation per new check made the
command, started as a child process, exit 1 with exactly `error-cause`,
`hand-written-double`, `git-shared-state`, and `local-full-suite`. With each
violation replaced by its legitimate form (a chained error, a real import, a
branch switch, a related-tests hook) it exited 0. The project was removed.

The new rules found nothing in this repository's code. Applying the practices
by review found two places they apply here:

- `scripts/detect-stack.ps1` reports any internal failure as
  `{"error":"scan failed"}` and drops the cause. PowerShell handlers are
  outside `error-cause`, so no check caught it. The owner then asked for the
  fix; see "Review threads and scanner causes" below.
- This repository's `CHANGELOG.md` and `PLAN.md` are files every change edits.
  Moving them to per-item files joined by a script is separate work.

A first full-suite run, started while `pre-commit run --all-files` ran in
parallel, failed `test_every_template_is_classified`: a
`templates/python/.ruff_cache/` had appeared, and that cache already held an
older `0.15.9` directory from August. After removing it, pre-commit alone and
the suite alone each passed and left no cache there. The writer was found
later: the root `ruff format --check .` and `ruff check .` run before the
suite. See "Review threads and scanner causes" below.

Environment: Windows 11, Python 3.14.0, Ruff 0.16.8, mypy 2.3.1, coverage
7.16.1, pre-commit 4.6.2, PowerShell 7.6.6 and Windows PowerShell 5.1.

### Limits and open gates

- Hosted CI has not run on these commits; nothing is pushed. Linux and macOS
  ran nothing locally for this change.
- Live agent trials were not rerun for the changed workflow wording.

## Review threads and scanner causes: 2026-10-17

Scope: commits `41a4660` (plan) through `787d06b`, from `58e6cdd`. The
automated review of 21:09Z left 11 unresolved threads on `d69b3f8`. None of
the seven-practice commits touched the code they name, and each reproduced at
`58e6cdd`, so each was fixed at its cause. None was answered as no longer
applying. Threads were not resolved or replied to on GitHub.

| Thread | Cause | Fix |
|---|---|---|
| `workflows.py:23` | The secret pattern matched only `${{ secrets.NAME` at the start of an expression | `f27731d`: any secret read inside `${{ }}`, by property, by index, or through `toJSON(secrets)`, with the `GITHUB_TOKEN` exception kept |
| `upstreams.py:232` | The pin was any substring of the file | `f93d2fa`: a whole version token (optional `v`) outside comments; this repository's own `GITLEAKS_VERSION` line sits beside exactly such a comment |
| `python_rules.py:307` | Only regular parameters were read | `0bf88db`: positional-only and keyword-only too |
| `script_rules.py:201` | The module pattern ran on text that keeps literals | `0bf88db`: the `import`, `from`, or `require` keyword must be code |
| `register.py:138` | Runner text included comments | `89417f5`: comments removed before the search |
| `workflows.py:118` | Only `pull_request` required `merge_group` | `f27731d`: `pull_request_target` too |
| `manifests.py:182` | Only `requirements*` file names were manifests | `0bf88db`: `.txt` and `.in` files in a `requirements/` folder too |
| `cli.py:60` | The retry setting did not include `reruns` | `0bf88db`: a non-zero `reruns` is refused |
| `cli.py:279` | Watch mode always printed text | `09866ad`: JSON when asked |
| `workflows.py:30` | Only a literal `true` was refused | `f27731d`: anything but a literal `false` |
| `source.py:105` | Shell files were not code | `cfada06`: `.sh`, `.bash`, `.zsh`, `.ksh`, and `.bats` count, with shared-Git-state and fixed-sleep checks |

`6fae41e` applies practice 2 to the scanners. Both now add `detail` to their
error JSON. The Bash scanner reports the shell's reason ("No such file or
directory", "Not a directory"). The PowerShell scanner reports the caught
error's message and line for both an unreadable root and a failed scan.
`error` stays the stable code that `AGENTS.md` and `CONTRIBUTING.md` tell
callers to match, and both documents now say to report `detail`.

Running the owner's gates in order exposed a defect with a known cause: a root
`ruff check .` treated `templates/python/ruff.toml` as a nested project and
wrote a cache beside it, failing `test_every_template_is_classified` on the
next suite run. One `ruff check .` reproduced it. `787d06b` excludes
`templates/python` from the root configuration; Markdown elsewhere in
`templates/` stays checked (64 files before and after).

### Executed drills

The Python drill table grew from 43 to 58. Five of the new drills break
negative controls: the `GITHUB_TOKEN` exception, the literal-`false` value, the
comment removal for pins, the token boundary for pins, and the literal-text
guard for imports. Three drills were re-anchored because the lines they break
changed: the `merge_group` condition, the secret detection, and the pin
check. `cross-platform-smoke.ps1 -RedDrills` grew from 6 to 7: replacing the
PowerShell scanner's caught message with a fixed sentence fails
`Unreadable path did not name its cause.` with exit 1, and the restored source
passes. The new CI check for the Bash scanner was run locally from Git Bash
against the real script and passed. Hosted CI has not run it.

### Results

All on Windows 11 at `787d06b`, run one after another, with temporary files
under the ignored `build/tmp/`:

| Gate | Exit |
|---|---|
| `ruff format --check .` (64 files) | 0 |
| `ruff check .` | 0 |
| mypy, package scripts (26 files) | 0 |
| mypy, tests (14 files) | 0 |
| `verify-practices.py --root . --rules CONTRIBUTING.md` (49 code files, no allowances) | 0 |
| Full suite with coverage: 71 tests, 4 skips, 87.0% against the 82% floor | 0, report 0 |
| `pre-commit run --all-files` | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, PowerShell 7.6.6 (7 drills) | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, Windows PowerShell 5.1 (7 drills) | 0 |

### Limits and open gates

- Hosted CI has not run on `41a4660` and later; nothing is pushed. The new
  Bash unreadable-root check runs only on the Linux and macOS jobs.
- The scanners' `scan failed` path cannot be triggered from a test here; its
  detail uses the same function as the unreadable-root path, which the smoke
  suite asserts and drills.

## Second review round: 2026-10-18

Scope: commits `7930722` (plan) through `ee76585`, from `193f09e`. The
re-review of `193f09e` resolved the earlier 11 threads and raised 12 new ones.
Each reproduced at `193f09e` and was fixed at its cause; none was answered as
no longer applying. Threads were not resolved or replied to on GitHub.

| Thread | Cause | Fix |
|---|---|---|
| `workflows.py:146` (security) | Expressions were matched per physical line, so a folded `${{ … }}` escaped | `1b0a3da`: matched across the comment-free workflow text, reported at the line where `${{` starts |
| `workflows.py:166` (security) | The `GITHUB_TOKEN` exception held on `pull_request_target`, where the token has the base repository's permissions | `1b0a3da`: on that trigger the token (`secrets.GITHUB_TOKEN` or `github.token`) is refused unless top-level permissions are declared and none is `write` |
| `cli.py:316` | Input errors were plain text in JSON mode | `1b0a3da`: `{"passed": false, "error": ...}` |
| `cli.py:61` | `--reruns` was refused at any count | `1b0a3da`: only a positive count, in runner files and workflows |
| `source.py:170` | Any `#` began a comment, even inside quotes | `1b0a3da`: one quote-aware finder for YAML, TOML, INI, shell, and PowerShell, used for allowances and for stripping comments before checks; a quoted `#` before a secret no longer hides it either |
| `register.py:134` | Any file under `tests/` counted as a test | `3c8c7fa`: test code in a recognized language only |
| `error_rules.py:103` | `exc_info=False` counted as keeping the cause | `3c8c7fa`: only a value that is not statically false |
| `workflows.py:144` | Path filters were refused under any trigger | `1b0a3da`: only under `pull_request`, `pull_request_target`, or `merge_group` |
| `manifests.py:69` | `Include` had to come first, in double quotes | `3c8c7fa`: any attribute order and either quote, for `PackageReference`, `PackageVersion`, and `GlobalPackageReference` |
| `family_rules.py:117` | Rust tests in a `#[cfg(test)]` module of a product file were product code | `3c8c7fa`: the module body is test code; a product type outside it is not |
| `upstreams.py:226` (P1) | A commit SHA in `pinned` never equals a release tag | `ee76585`: a required `version` field records the release a SHA or digest identifies, and `upstream-behind` compares with it; this repository's pins and the templates carry it |
| `parallel_rules.py:233` | A command held in a name was invisible | `3c8c7fa`: names bound to literal commands earlier in the same scope are resolved |

### Executed drills

The Python drill table grew from 58 to 74. Six of the new drills break
negative controls: the read-only-permissions test, the merge-gate trigger
condition on path filters, the quote tracking in comments, the Rust
product-code boundary, the NuGet attribute order, and the SHA pin's version
comparison. Four drills were re-anchored because the lines they break moved:
the secret detection, the path-filter detection, the shell sleep, and the
`upstream-behind` condition.

One drill first survived. The quoted-value allowance case had its `#` right
after the quote, which the whitespace rule already rejects, so disabling quote
tracking changed nothing. The case now puts a space before the `#` inside the
quotes, and the drill fails as intended.

### Results

All on Windows 11 at `ee76585`, run one after another:

| Gate | Exit |
|---|---|
| `ruff format --check .` (64 files) | 0 |
| `ruff check .` | 0 |
| mypy, package scripts (26 files) | 0 |
| mypy, tests (14 files) | 0 |
| `verify-practices.py --root . --rules CONTRIBUTING.md` (49 code files, no allowances) | 0 |
| Full suite with coverage: 71 tests, 4 skips, 87.6% against the 82% floor | 0, report 0 |
| `pre-commit run --all-files` | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, PowerShell 7.6.6 (7 drills) | 0 |
| `cross-platform-smoke.ps1 -RedDrills`, Windows PowerShell 5.1 (7 drills) | 0 |

### Limits and open gates

- Hosted CI has not run on `7930722` and later; nothing is pushed.
- The read-only test for `pull_request_target` reads declared permissions. It
  cannot see a repository's default token setting, so a target workflow that
  declares no permissions is refused even where the default is read-only.
