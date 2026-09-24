# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.7.0 — 2026-09-24

### Fixed

- The C# `Directory.Build.props` template was malformed XML since 0.5.0: an XML
  comment contained `--`, so MSBuild refused to load it (`MSB4024`).
- The PowerShell template could pass while losing findings. `PSUseCorrectCasing`
  intermittently throws in PSScriptAnalyzer 1.24.0 and 1.25.0; a planted
  violation then went unreported and `-EnableExit` exited 0. The rule is off,
  and every documented command adds `-ErrorAction Stop`.
- The pre-commit template's vulture hook exited 2 without configured paths;
  mypy ran in an isolated environment that turned dependency types into `Any`;
  ShellCheck required Docker; and `mixed-line-ending --fix=lf` rewrote files kept
  in CRLF by `.gitattributes`, failing every commit that touched them.
- `verify-format-safe.py` reported unreadable, undecodable, or missing input as
  "AST changed" (exit 1) and rejected valid PEP 263 source encodings.
- The atomic plan writer replaced plans with owner-only (0600) permissions and
  did not flush the directory entry after the rename on POSIX.
- `detect-stack.sh` wrote unescaped paths into its JSON, matched extensions and
  pruned directories case-sensitively unlike the PowerShell scanner, and walked
  the tree once per extension (480 s versus 16 s on a large local workspace).

### Added

- C# `.editorconfig` template that makes the dead-code rules IDE0051, IDE0052,
  IDE0059, IDE0060, and IDE0005 fail the build; without it they were silent.
- Rust `deny.toml` policy for advisories, licenses, bans, and sources.
- mypy template codes `explicit-override`, `exhaustive-match`,
  `mutable-override`, `truthy-iterable`, and `deprecated`.
- Pre-commit template hooks for executable/shebang consistency, actionlint, and
  zizmor, with guidance to freeze hook revisions to commit SHAs.
- Scanner detection of `knip.jsonc`, Go modules and tools, golangci-lint,
  Dependabot/Renovate configuration, lockfiles, toolchain pins, dpdm, bats,
  actionlint, zizmor, OSV-Scanner, hadolint, and the PSScriptAnalyzer and
  Pester 5 modules.
- Guidance for coverage floors, mutation testing, property and fuzz testing,
  benchmarks, dependency supply chain, accessibility automation, React hook
  rules, and hardened GitHub Actions workflows.

### Changed

- This repository now passes the gates it ships: a frozen pre-commit
  configuration runs Ruff, both mypy scopes with the shipped template,
  vulture, Bandit, ShellCheck, shfmt, PSScriptAnalyzer, actionlint, and zizmor;
  CI adds a checksum-verified full-history gitleaks scan and a coverage floor.
- CI installs hash-locked tools, pins every action to a commit SHA, disables
  persisted checkout credentials, and sets job timeouts. Dependabot proposes
  updates for actions, hooks, and tools after a seven-day cooldown.
- The smoke suite maintains six red drills, adding case-insensitive pruning,
  `knip.jsonc` detection, and SHA-pinned release actions.

### Verification

- Every finding was reproduced first, and every changed rule was red-drilled:
  green, the intended failure, byte-identical restoration, and green again.
- 58 tests on Python 3.12 and 3.14, coverage above the 82% floor, all
  repository hooks, and both smoke suites under PowerShell 7 and 5.1 passed
  locally. All thirteen hosted jobs passed on Windows, Linux, and macOS.
- Evidence, environments, and open limits are in `docs/QUALITY-REVIEW.md`.

## 0.6.0 — 2026-09-07

### Added

- First-party `feature_delivery` workflow for scoped behavior changes, focused
  discovery, readiness review, implementation, reconciliation, and safe resume.
- Shared native delivery contract and versioned plan asset linking requirements,
  acceptance criteria, task ownership, dependencies, and current evidence.
- Read-only Python 3.12+ validator for strict schema/coverage checks, actual file
  outcomes, artifact/input hashes, red-drill proof, and checkpoint freshness.
  Recorded commands remain inert data; semantic review and real tests remain
  required independently of structural success.
- Atomic plan-update helper with candidate validation, observed-digest conflict
  detection, cooperative locks, flushed writes, and idempotent replacement.
- Executable Python entry points on POSIX, verified by the hosted lint gate.
- Deterministic regressions and validator mutation drills, plus isolated live
  agent scenarios with independent product oracles and negative controls.
- Independent trial checks re-observe runtime versions and validate current
  closure receipts, including a negative control for fabricated versions.

### Changed

- Connected setup and retrofit to the shared delivery lifecycle without replacing
  their canonical discovery, code-quality, or red-drill procedures.
- Extended package checks to inspect every committed resource in both archives.
  Added Python 3.12/3.14 validation, strict typing, lint, and tests across Windows,
  Linux, and macOS using the existing CI/release pipeline.
- Reworked README navigation, workflow routing, installation, and documentation
  around a warm ivory, charcoal, and copper visual identity.
- Updated agent adapters, manifests, installation guidance, and contributor docs
  for all three workflows. Delivery code uses only Python's standard library;
  no third-party workflow integration or copied framework code was added.

### Verification

- 46 deterministic tests, including validator mutation drills and independent
  outcome-oracle controls; strict typing and linting; twelve hosted matrix jobs.
- 24 independently reviewed live core trials and one unchanged-plan trial.
  Evaluation scope and model/runtime limits are recorded in `docs/QUALITY-REVIEW.md`.
- Desktop/mobile and light/dark README rendering, plus the saved neutral GitHub
  social-preview image, checked visually.
- Post-publication verification confirmed five exact-build assets, both archive
  attestations, all 76 installed files, and fresh discovery of all three workflows.

## 0.5.0 — 2026-09-07

### Added

- A source-backed language review contract covering semantic organization,
  meaningful abstractions, ownership, errors, resource lifetimes, asynchronous
  work, accessible HTML/CSS, and rejection of tautological tests and vacuous
  behavior. Both workflows require it; Go coverage is explicitly guidance-only.
- Required repeatable red drills for tests and quality gates in both workflows,
  with a shared green/red/restored-green procedure, intended-failure checks,
  isolation and cleanup rules, recurring execution, and scoped evidence.
- Red-drill scope and ownership in project discovery, the brief, generated
  project instructions, milestone verification, and completion reports.
- A `-RedDrills` mode in the existing PowerShell smoke suite, wired into CI,
  that mutates directory pruning, root overrides, and unreadable-path behavior
  in a temporary source copy and requires the existing assertions to catch them.

### Changed

- Removed universal runtime/module choices from TypeScript and C# quality
  templates, retaining them in the owning project's configuration.
- Kept domain constants local, tightened TypeScript unused-variable and test
  checks, and added explicit self-comparison and exhaustive-switch gates.
- Scoped Python assertion allowances to tests and retained fixture annotations;
  removed the repository's duplicated Ruff copyright-rule exclusion.
- Clarified Rust workspace lint inheritance and removed the duplicate unwrap
  prohibition that defeated test-local allowances.
- Strengthened both workflows' scan-and-enhance rules with canonical-path and
  consumer tracing, focused rescans before changes, justified new work, migration
  cleanup, and final duplication checks. Tooling adapters point to canonical
  project instructions instead of creating competing policy copies.
- Replaced retrofit reviewer guidance that deleted environments with explicit
  file scoping or an isolated copy, preserving pre-existing resources.
- Clarified that existing scope authorization is reused, and that zero tests,
  surviving mutations, unrelated errors, and incomplete restoration cannot
  establish verified gates.

### Fixed

- Fixed clang-tidy's owned-header filter for absolute Windows/POSIX paths,
  restored PowerShell state-change checks, and replaced nonexistent compatibility
  profiles with shipped inventories whose historical limits are documented.
- Required Semgrep's `--error` flag for blocking scans and documented its console
  entrypoint exception to the usual Python module invocation.
- Stopped applying a C++ language standard to mixed C/C++ pre-commit inputs.
- Routed JSONC TypeScript configuration validation to the compiler instead of
  the strict JSON pre-commit hook.
- Made smoke-test source and document reads explicitly UTF-8 so Windows
  PowerShell 5.1 checks non-ASCII contracts without relying on its legacy default
  encoding.

### Adoption notes

- When adopting the TypeScript or C# templates, keep runtime, module, language,
  and framework choices explicit in the owning project. The quality bases no
  longer choose those settings for every consumer.
- Re-run affected gates and red drills when applying the narrower Python,
  TypeScript, and PowerShell exceptions. Existing projects may expose findings
  that the older templates did not report.

## 0.4.1 — 2026-08-20

### Fixed — cross-host release reproducibility

- The release builder now pins Git archive timestamp handling to UTC and
  restores the caller's original `TZ` value, making all five generated release
  files byte-identical across supported host time zones for the same commit.
- The release-package smoke test now builds under conflicting Pacific and Asia
  time zones, fails if any archive or metadata file changes, and derives its
  expected release notes from the manifest-matched changelog section instead
  of stale version-specific text.
- Release metadata reads now request UTF-8 explicitly, preventing Windows
  PowerShell 5.1 from mangling non-ASCII changelog punctuation in release notes.

## 0.4.0 — 2026-08-20

### Added — release automation and verified installs

- Added a tag-triggered GitHub Release workflow. It reuses the full
  cross-platform workflow, validates exact tag/manifest/changelog agreement,
  builds versioned ZIP and tar.gz archives from the committed Git tree,
  generates SHA-256 checksums and release metadata, creates signed GitHub build
  provenance, and publishes changelog-derived notes and assets.
- Added `scripts/build-release.ps1` plus a package smoke test covering archive
  structure, source commit, checksums, manifest, and notes under PowerShell 7
  and Windows PowerShell 5.1.
- Added `docs/INSTALLATION.md` with current marketplace, pinned-tag, tagged-clone,
  local-directory, and release-archive install paths; Windows, Linux, and macOS
  checksum commands; provenance verification; extraction; and update behavior.
- Made the cross-platform workflow reusable so release publication executes the
  same gates as normal main/PR validation. Added a pinned Ruff 0.16.4 CI job and
  removed four obsolete inline suppressions exposed by that gate.

## 0.3.1 — 2026-08-20

### Added — brand inventory and reuse-first setup

- Expanded Grill Me branding discovery to explicitly inventory editable logos
  and wordmarks, logo variants, app icons, favicons, social/OG images, store
  artwork, illustrations, fonts, templates, color tokens, and design-system
  files, including authoritative originals, ownership, licensing, and approval.
- Made **scan -> reuse or extend -> create only when needed** a required project
  rule for code, components, utilities, types, schemas, tests, configuration,
  documentation, infrastructure, and assets. Generated agent guidelines must
  carry the same rule and reject renamed or parallel duplicates.
- Extended `PROJECT_BRIEF.md` with brand-asset and reuse-decision inventories,
  and added PowerShell 5.1/7 regression assertions for both contracts.

## 0.3.0 — 2026-08-20

### Added — Grill Me project discovery

- Added a mandatory, multi-round Grill Me phase to `project_setup`. It resolves
  users, outcomes, scope, non-goals, brand and color schemes, accessibility,
  supported environments, signing, distribution, service model, data, security,
  operations, support, lifecycle, and release-pipeline decisions before stack
  selection or product code.
- Added `skills/project_setup/references/grill-me.md`, a comprehensive question
  bank used as a coverage map. The protocol reuses known answers, asks focused
  rounds, explains tradeoffs, challenges contradictions, and scales depth to
  project risk instead of dumping one giant questionnaire.
- Added a reusable `PROJECT_BRIEF.md` asset with a decision ledger and readiness
  checklist. Decisions are tracked as confirmed, assumed, open/blocking, or N/A
  with reason; critical unknowns now stop stack selection rather than becoming
  silent defaults.
- Extended UI certification to cover confirmed responsive targets, keyboard and
  focus behavior, semantics, contrast, zoom/reflow, reduced motion, screen
  readers, touch targets, color tokens, and required theme modes.
- Added PowerShell 5.1/7 smoke assertions for the discovery reference, project-
  brief asset, skill wiring, and manifest version.

### Changed — README presentation and claim audit

- Reworked the README with a clearer overview, status badges, compact
  navigation, streamlined quick starts, and a more readable workflow/risk
  summary.
- Revalidated installation commands, cross-platform requirements, scanner
  behavior, secret-scan scope, sanitizer guidance, links, and live repository
  status. Replaced absolute or dated front-page claims with scoped language and
  pointers to dated evidence where appropriate.
- Corrected two overstatements in the retrofit workflow: formatting is low risk,
  not zero risk, and sanitizer findings require investigation rather than being
  automatically classified as confirmed bugs.
- Clarified that full Rust sanitizer coverage depends on a supported target and
  an instrumented standard library.
- Added a tracked 1280×640 social-preview image and documented how to keep the
  repository setting synchronized with it.

## 0.2.0 — 2026-08-20

### Fixed — Bash-free Windows execution

- Added native `scripts/skill-root.ps1` and `scripts/detect-stack.ps1`
  counterparts. Both run on Windows PowerShell 5.1 and PowerShell 7, preserve
  the existing JSON contract, probe importable Python tools, prune large vendor
  trees, and exit 0 with JSON for unreadable paths.
- Updated both workflows and every agent auto-discovery entry point to select
  scripts by active shell. Windows no longer invokes the `bash.exe` WSL relay,
  which fails with `execvpe(/bin/bash) failed` when WSL has no installed Linux
  distribution.
- Added `tests/cross-platform-smoke.ps1` covering root resolution, environment
  override precedence, language counts, directory pruning, config detection,
  and error JSON. Verified under PowerShell 7 and Windows PowerShell 5.1.
- Added Windows/Linux GitHub Actions coverage for PowerShell 7, Windows
  PowerShell 5.1, the existing Bash scripts, and Bash/PowerShell inventory
  parity.
- The first clean-runner CI execution exposed an empty-array bug when Python had
  none of the optional quality modules installed. Fixed the scanner, added an
  isolated zero-module Python regression case, and separated truthful
  `unreadable path` and `scan failed` JSON errors.
- Reconciled the native scanners' `existing_config.prettierrc` key and stopped
  the Bash scanner from reporting a parent repository's Git state for a nested,
  non-repository workspace.

### Fixed — documentation and gate accuracy

- Audited current instructions, manifests, repository metadata, and command
  examples against the checkout, live npm metadata, Claude Code 2.1.140, and
  current GitHub repository settings. Corrected Claude's namespaced skill names,
  `/reload-plugins`, registry commands incorrectly described as offline,
  cross-shell examples, GitHub topics, dead manifest schema URLs, nonexistent
  release links, and overbroad verification claims.
- Refreshed pre-commit pins with `pre-commit autoupdate` on 2026-08-20. Kept
  gitleaks at v8.30.0 because v8.30.1 is an orphaned tag that autoupdate cannot
  follow; both versions were checked with a randomized real-shape PAT canary.
  Corrected the hook documentation: pre-commit scans staged changes, while
  `gitleaks git --redact` is the explicit reachable-history gate.
- Removed contradictory mypy and Bandit hook arguments. After the relevant
  templates are copied to the target project root, mypy inherits that project's
  strict config and Bandit no longer requires a nonexistent `pyproject.toml`.
- Refreshed the Ruff template for 0.16.4. Its new `CPY001` check is deliberately
  disabled because a mandatory copyright header in every Python file is not a
  universal correctness requirement.
- Loaded the Python, TypeScript, ESLint, Stylelint, knip, .NET, Rust, and
  PowerShell templates with current compatible tool versions. Recorded the
  dated versions in `templates/README.md` so later audits can distinguish
  evidence from evergreen compatibility claims.
- Disabled `PSAlignAssignmentStatement` because its padding requirement
  conflicts with `PSUseConsistentWhitespace.CheckOperator`. The shipped
  PSScriptAnalyzer settings now satisfy themselves and the native scripts,
  accept one-space assignment formatting, and check Windows PowerShell 5.1 as
  well as PowerShell 7.4 on Windows and Linux.

### Changed — the workflows are now vendor-neutral

They were not. The instructions referenced `${CLAUDE_PLUGIN_ROOT}` in six
places, a variable only Claude Code sets. Under any other agent that expands to
the empty string, so `"${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.sh"` became
`/scripts/detect-stack.sh` — a silent failure of the mandatory first step, or a
read of the wrong file. The README, both manifests, and the repository
description also described the package as Claude Code-only.

- **`${SKILL_ROOT}` replaces `${CLAUDE_PLUGIN_ROOT}`** throughout, resolved by
  new **`scripts/skill-root.sh`**. That script locates *itself* rather than
  depending on an environment variable, so it works from a plain clone, a
  vendored copy, or a submodule with nothing configured. Resolution order is
  `$SKILL_ROOT`, then `$CLAUDE_PLUGIN_ROOT`, then its own directory — so Claude
  Code keeps working unchanged while everything else starts working.

  Verified in five scenarios: no environment at all, `CLAUDE_PLUGIN_ROOT` set,
  `SKILL_ROOT` overriding it, invoked through a symlink, and invoked from an
  unrelated working directory.

- **Added `AGENTS.md`** as the universal entry point — the cross-vendor
  convention Codex, Cursor, Aider, Zed and others already look for. Added
  `.cursor/rules/high-quality-projects.mdc` and
  `.github/copilot-instructions.md` for tools that auto-discover their own
  formats. All three are thin pointers to the same workflow files to minimize
  duplicated instructions and drift.

- **Reframed `README.md`, both `.claude-plugin/` manifests, and `CONTRIBUTING.md`.**
  Claude Code is now presented as one packaging option rather than the product.
  `CONTRIBUTING.md` states the constraint explicitly: never reintroduce a
  vendor-set variable into a workflow file, and keep content in the workflows
  rather than in the auto-discovery pointers.

Verified end to end by copying the package to a scratch directory, deleting
`.git`, and running it from an unrelated workspace with `env -u SKILL_ROOT -u
CLAUDE_PLUGIN_ROOT`: root resolved, all four spot-checked templates reachable,
`detect-stack.sh` exited 0 with valid JSON, and `verify-format-safe.py` ran.
Zero remaining uses of `CLAUDE_PLUGIN_ROOT` as a path; the three surviving
mentions are prose describing the fallback.

### Fixed — first Windows run

Found by installing the plugin on Windows 11 and running both workflows against
scratch projects. All three failures are silent ones: nothing errored, the
output was just wrong.

- **`detect-stack.sh` reported installed Python tools as missing.** `has_tool`
  tested `PATH` only, but a Python tool is usable whenever it is *importable* —
  `python -m ruff` works from an unactivated venv, and a Windows install
  routinely has no console-scripts directory on `PATH` at all. On the test
  machine `ruff`, `mypy`, `vulture`, `bandit`, `pip-audit`, `pytest` and
  `pre-commit` were all installed and all reported `false`, which is the exact
  input that makes a workflow defer a working gate or install a second copy of
  a tool it already has.

  Python tools are now resolved with `importlib.util.find_spec` in a single
  interpreter start — import machinery only, nothing is executed. The scan
  cannot assume the first interpreter on `PATH` is the right one either:
  `python3` on Windows is normally the Store alias stub, which is not an
  interpreter and resolves nothing. So every candidate is probed and the one
  resolving the most modules wins; a stub loses by construction.

  New `python_runtime` object reports the interpreter that was verified and
  which tools exist *only* as modules, because those must be invoked as
  `<bin> -m <module>`. Both workflows and `AGENTS.md` now say so. Costs one
  extra interpreter start (~0.5s on the test machine).

- **Phase 0 of `quality_retrofit` dirtied the tree it later requires clean.**
  Running the baseline gates writes `.ruff_cache/`, `.mypy_cache/` and friends,
  which land as untracked files in a repo that does not ignore them yet — and
  `git status --porcelain` is the guard every later phase depends on. Phase 0
  now records which caches existed beforehand and removes only the ones it
  created; a pre-existing cache is the user's and is left alone. Phase 2 adds
  the ignore entries so it stops being a per-phase cleanup.

- **`verify-format-safe.py` printed a mojibake verdict on Windows.** The two
  `RESULT:` lines contained a UTF-8 em dash, which a cp1252 console renders as
  `?` — `RESULT: AST identical ? formatting was semantically neutral`. The one
  line that reports the verdict looked like a broken tool. Both lines are ASCII
  now.

Everything below came from running the `project_setup` skill end to end against a real
project for the first time — a TypeScript canvas game, taken from empty
directory to a published repository with green CI. The skill had only ever been
exercised via the `quality_retrofit` workflow before this, and the exercise found defects in
the templates that would have hit the first person to use them.

### Fixed

- **`templates/web/knip.json` did not load under knip 6.** knip 6 validates its
  config strictly and rejects unknown keys, so the knip 5 `"//": [...]`
  pseudo-comment convention was a hard error —
  `Invalid input (unrecognized_keys: //, //rules)` — and the `classMembers` rule
  no longer exists. Replaced with **`templates/web/knip.jsonc`**, which knip
  reads natively and which takes real comments. Verified to load.

- **`templates/typescript/eslint.config.mjs` omitted `@eslint/js`** from its
  install line while importing it. That fails at config load, not at lint time,
  so the error is confusing.

- **The eslint template did not enforce the skill's own magic-number rule.**
  Phase 3 of `project_setup` requires "no unexplained magic numbers", and the
  template shipped no rule to enforce it. Added
  `@typescript-eslint/no-magic-numbers` with a justified ignore list, plus the
  two overrides that make it satisfiable — the constants module and tests.

### Added

- **A TypeScript compatibility warning, in both skills and the templates.**
  The checked typescript-eslint peer range excludes TypeScript 7. Current npm
  resolution should reject that combination; bypassing the peer check creates
  an unsupported toolchain for type-aware rules such as `no-floating-promises`
  and the `no-unsafe-*` family. The worked example now carries a check date and
  requires re-querying registry metadata before pinning.

- **"Prove each gate fires before relying on it"**, a new section in
  `project_setup`, and the equivalent guidance in `quality_retrofit`'s dead-code
  phase. Three tools were found that loaded their config without complaint and
  checked nothing:

  - `import-x/no-cycle` reported nothing against a deliberately circular pair of
    modules, while `import-x/no-self-import` and `import-x/no-unresolved`
    correctly flagged their cases in the same run.
  - knip 6's `cycles` rule was equally silent, by default and under
    `--include cycles`.
  - `madge@8.0.0` declares optional peer `typescript@^5.4.4`, so normal npm
    resolution rejects it alongside TypeScript 6; bypassing the check does not
    make that combination supported.

  `dpdm` is now the recommended cycle detector, verified in both directions:
  exit 1 on a real cycle, exit 0 once removed.

- **Prettier-conflict guidance.** `unicorn/number-literal-case` wants uppercase
  hex digits and Prettier rewrites them to lowercase, so with both enabled
  `format` and `lint` can never both pass. `unicorn/prefer-global-this` produces
  a hard `TS2345` in browser-only code, because TypeScript types `window` as
  `Window & typeof globalThis` while bare `globalThis` lacks the Window members.
  Both are now disabled in the template with the conflict written out.

- **A note that coverage thresholds find dead code.** A branch flagged as
  unreachable by a coverage gate may genuinely be unreachable — that happened
  during this exercise, and deleting the branch was correct where lowering the
  threshold would have hidden it.

- Two further traps recorded: a resolver that cannot resolve makes every
  import-graph rule report success, and `maxDepth: Infinity` becomes `null` when
  a rule option is JSON-serialised, which can disable traversal outright.

- **Vacuous-assertion guidance**, in both skills. The same "looks configured,
  checks nothing" failure occurs in tests, where it is harder to spot because
  the test is green rather than missing. The case that prompted it: a test
  pressed the arrow keys and asserted the page had not scrolled, and passed on
  every run — including against a build with the `preventDefault` call deleted,
  because the layout fitted the viewport and the page could never scroll at all.

  Two rules now stated explicitly: assert the behaviour rather than a downstream
  side effect, and give every assertion a case that must come back negative. An
  assertion where every input yields the same answer is indistinguishable from a
  broken one. `quality_retrofit` additionally warns that an inherited green
  suite is not evidence the tests check anything.

### Changed

- `templates/README.md` no longer claims every config "was run against
  deliberately-broken code and confirmed to fire". That was not true of the knip
  template, which did not load at all under knip 6. Replaced with the discipline
  itself, stated as a requirement on the reader.

## 0.1.0 — 2026-07-26

Initial release.

### Added

- **`project_setup`** — instructs an agent to scaffold a new project toward
  production standards. It scans before creating, batches clarification
  questions, verifies dependency compatibility against official sources,
  writes `PLAN.md` before code, and requires every runnable gate to pass on the
  empty scaffold before milestone one.

- **`quality_retrofit`** — instructs an agent to bring an existing codebase
  toward compliance across nine phases (baseline, formatting, config, autofix
  lint, types, dead code, literals, security/sanitizers, docs). It requires
  reviewable phases and tells the agent to refuse dirty-tree work, bulk changes
  to unversioned code, unverified deletion, and unprompted history rewrites.

- **`scripts/detect-stack.sh`** — workspace inventory emitting JSON: languages
  by file count, existing quality config, and which required tools are present
  on the machine. Both skills run it first so they extend rather than replace.

- **Strict config templates** for Python (ruff, mypy), TypeScript (tsconfig,
  eslint flat), CSS (stylelint), JS/TS dead code (knip), C++ (clang-tidy),
  C# (`Directory.Build.props`), Rust (clippy), PowerShell (PSScriptAnalyzer),
  and a polyglot `.pre-commit-config.yaml`. Each documents its own deliberate
  loosenings inline.

- **`templates/cpp/sanitizers.md`** — ASan/LSan/UBSan/TSan/MSan reference
  covering flags, runtime options, CMake wiring, and Rust `-Zbuild-std`.

- **`docs/PHILOSOPHY.md`** — the reasoning behind each rule and, explicitly,
  where strictness is the wrong call.

### Notes

The initial release recorded deliberately broken-program checks for ruff,
vulture, bandit, cppcheck, clang-tidy, eslint, tsc, stylelint, shellcheck,
PSScriptAnalyzer, gitleaks, and sanitizer examples. These were dated,
machine-specific observations, not continuing certification; later entries
record the knip exception and other audit corrections.
