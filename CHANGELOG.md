# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  formats. All three are thin pointers to the same workflow files so they cannot
  drift.

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

Everything below came from running `/project_setup` end to end against a real
project for the first time — a TypeScript canvas game, taken from empty
directory to a published repository with green CI. The skill had only ever been
exercised via `/quality_retrofit` before this, and the exercise found defects in
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

- **A TypeScript 7 compatibility warning, in both skills and the templates.**
  As of 2026-07-26 `typescript` latest is 7.0.2, but every published
  `typescript-eslint` — canary included — declares
  `peerDependencies.typescript: ">=4.8.4 <6.1.0"`. Taking the latest TypeScript
  installs cleanly and silently removes every type-aware lint rule:
  `no-floating-promises`, `no-misused-promises`, `await-thenable`, and the whole
  `no-unsafe-*` family. This is now a worked example under "Verify compatibility
  — do not guess", since it is exactly the failure that section exists to catch.

- **"Prove each gate fires before relying on it"**, a new section in
  `project_setup`, and the equivalent guidance in `quality_retrofit`'s dead-code
  phase. Three tools were found that loaded their config without complaint and
  checked nothing:

  - `import-x/no-cycle` reported nothing against a deliberately circular pair of
    modules, while `import-x/no-self-import` and `import-x/no-unresolved`
    correctly flagged their cases in the same run.
  - knip 6's `cycles` rule was equally silent, by default and under
    `--include cycles`.
  - `madge` cannot be installed alongside TypeScript 6+ at all, because it
    declares `peerOptional typescript@^5.4.4`.

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

## [0.1.0] — 2026-07-26

Initial release.

### Added

- **`/project_setup <description>`** — scaffolds a new project to production
  standards. Scans before creating, batches clarification questions, verifies
  dependency compatibility against official sources rather than guessing,
  writes `PLAN.md` before code, and proves every gate passes on the empty
  scaffold before milestone one.

- **`/quality_retrofit`** — brings an existing codebase into compliance across
  nine phases (baseline, formatting, config, autofix lint, types, dead code,
  literals, security/sanitizers, docs). Each phase is independently reviewable
  and revertible. Refuses to modify a dirty working tree, bulk-modify
  unversioned code, delete unverified code, or rewrite history to scrub a
  leaked secret.

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

Templates were validated by running each gate against deliberately broken code
and confirming it fired — ruff, vulture, bandit, cppcheck, clang-tidy, eslint,
tsc, stylelint, shellcheck, PSScriptAnalyzer, and gitleaks all caught their
planted defects. Sanitizers were verified trapping real use-after-free, leak,
UB, data-race, and uninitialized-read bugs on gcc 15, clang 21, and Rust
nightly.

[Unreleased]: https://github.com/RandyNorthrup/high-quality-projects-skill/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/RandyNorthrup/high-quality-projects-skill/releases/tag/v0.1.0
