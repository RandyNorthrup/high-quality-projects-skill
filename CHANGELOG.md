# Changelog

All notable changes to this project are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/RandyNorthrup/project-forge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/RandyNorthrup/project-forge/releases/tag/v0.1.0
