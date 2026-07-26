---
name: project_setup
description: Scaffold a new project to production-grade standards from the first commit — strictest practical linting, type checking, dead-code detection, sanitizers, security scanning, and CI-ready quality gates for the chosen stack. Verifies dependency compatibility against official sources rather than guessing. Creates README, CHANGELOG, and PLAN with milestone certification gates. Use when starting a new project, bootstrapping a repo, or when the user says "set up a project", "new project", "scaffold", or runs /project_setup. Takes a project description as its argument. For an existing codebase that needs standards applied, use quality_retrofit instead.
---

# Project setup — production-grade from commit one

Scaffold a new project with the strictest practical standards for its stack.
The argument to this skill is the **project description**. If it is missing or
one line, ask what is being built before touching anything.

## Communication style

Status updates to the user: short, direct, no filler. Caveman style if the
[caveman](https://github.com/JuliusBrussee/caveman) plugin is active.

**Never compress**: code comments, documentation, `PLAN.md` rationale,
architectural reasoning, security notes, or commit messages. Brevity applies to
chat only. A terse status line and a thorough `PLAN.md` are not in tension.

## Rule zero: scan before you create

Run this before anything else, even when the directory looks empty:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.sh" .
```

It returns JSON: languages present, config files that already exist, tools
installed on this machine. Then:

- **A config file already exists** → read it, extend it, preserve its choices.
  Never overwrite a config you did not write in this session.
- **Source files already exist** → this is not a new project. Say so and offer
  `/quality_retrofit` instead.
- **A tool is not installed** → do not silently skip its gate. Either install
  it or record it in `PLAN.md` under deferred gates with the reason.

Creating a file that already exists, with different content, is the single
worst failure mode of this skill.

## Phase 1 — resolve the stack

Ask before making stack-defining or irreversible decisions:

- Application type · framework/runtime · language · package manager
- Target deployment environment · hosting provider · CI provider
- Database/storage · authentication · required integrations
- UI/design system · browser and platform support
- Testing expectations (unit / integration / e2e)

Rules:

- If the answer is already in project files or earlier instructions, use it.
  Do not ask twice.
- If a reasonable default exists and the choice is cheap to reverse, take the
  default and record the assumption in `PLAN.md`.
- Batch the questions. One round of questions, not twelve.

### Verify compatibility — do not guess

Before installing anything, confirm versions actually work together. Check
official docs, release notes, peer dependencies, or a published compatibility
matrix.

`context7` MCP is the fastest source for current library docs when available.
`npm info <pkg> peerDependencies`, `cargo info`, and `dotnet list package
--outdated` all work offline against the real registry.

Record every version decision and its source in `PLAN.md`. "Latest" is not a
version; pin what you install.

## Phase 2 — quality gates

Set up the strictest practical gate set for the stack. Copy from
`${CLAUDE_PLUGIN_ROOT}/templates/` — those configs are pre-tuned and tested,
and each documents its own deliberate loosenings.

| Stack | Format | Lint | Types | Dead code | Security | Test |
|---|---|---|---|---|---|---|
| Python | ruff format | ruff (`ALL`) | mypy strict | vulture, deptry | bandit, pip-audit | pytest |
| TS/JS | prettier | eslint strictTypeChecked | tsc strict+ | knip | npm audit, semgrep | vitest |
| Rust | rustfmt | clippy pedantic | (compiler) | cargo-machete | cargo-audit, cargo-deny | cargo test |
| C++ | clang-format | clang-tidy, cppcheck | (compiler) | cppcheck unusedFunction | sanitizers, valgrind | ctest |
| C# | dotnet format | AnalysisLevel latest-all | nullable+warnaserror | IDE0051/0052 | NuGetAudit | dotnet test |
| CSS | prettier | stylelint | — | — | — | — |
| HTML | prettier | htmlhint | — | — | — | — |
| PowerShell | PSScriptAnalyzer | PSScriptAnalyzer | — | — | — | Pester |
| Shell | shfmt | shellcheck | — | — | gitleaks | bats |

Cross-cutting regardless of stack: `gitleaks` (secrets, scans history),
`semgrep` (multi-language SAST), `jscpd` (copy-paste detection).

### The flags that make a linter a gate

Without these the tool prints findings and exits 0, so CI passes over real
problems. This is the most common way a "configured" gate turns out to be
decorative:

```
eslint --max-warnings=0          stylelint --max-warnings=0
cargo clippy -- -D warnings      cppcheck --error-exitcode=1
knip --strict                    Invoke-ScriptAnalyzer -EnableExit
ruff check          (nonzero by default)
mypy                (nonzero by default)
<EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>   ← C#, else IDE-only
<TreatWarningsAsErrors>true</TreatWarningsAsErrors>       ← C#
-fno-sanitize-recover=all        ← UBSan, else prints and continues
```

### Sanitizers (C/C++/Rust)

Wire these as a separate CI job, not the default build. Full reference:
`${CLAUDE_PLUGIN_ROOT}/templates/cpp/sanitizers.md`.

```bash
# Default pairing for debug/test builds.
-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -g -O1
# TSan is a SEPARATE build — ASan and TSan use incompatible shadow memory.
-fsanitize=thread -fno-omit-frame-pointer -g -O1
```

Rust needs nightly plus `-Zbuild-std`, because the shipped `std` is not
instrumented and you get false negatives without rebuilding it:

```bash
RUSTFLAGS="-Zsanitizer=address" cargo +nightly test -Zbuild-std --target x86_64-unknown-linux-gnu
```

MSan is clang-only and needs an instrumented libc++ to be usable on real C++.
Do not add an MSan gate unless the project builds its own standard library —
otherwise it reports false positives from uninstrumented library internals.

### Script names

Expose gates under conventional names so CI and humans agree:

`format` · `format:check` · `lint` · `typecheck` · `test` · `test:unit` ·
`test:integration` · `test:e2e` · `build` · `security:audit` · `deadcode` ·
`quality` · `quality:ci`

`quality` runs everything and **fails on any blocking issue**. For stacks
without a script runner (C++, C#), put the same commands in a `Makefile`,
`justfile`, or `Directory.Build.props` target and document them in `README.md`.

## Phase 3 — code standards

Enforce throughout. These are the rules the generated agent-instruction files
must also carry.

**Constants and literals**
- No unexplained magic numbers, strings, booleans, or timeout values.
- Use named constants, typed constants, enums, literal unions, config objects,
  or schema-validated configuration.
- Idiomatic literals are fine where clarity is not reduced: `0`, `1`, `-1`,
  empty array/string/object, booleans in direct conditions, and array index `0`.
  A magic-number linter that rejects `if (xs.length === 0)` is misconfigured.

**Dead code**
- No dead code, commented-out legacy code, unused files, unused exports, unused
  dependencies, or stale configuration.

**Honesty**
- No silent fallbacks, fake implementations, or placeholder production code.
- No mock data outside test/dev/demo boundaries.
- A function that cannot do its job raises or returns an explicit error. It
  does not return an empty result that reads like success.

**Escape hatches**
- No broad `any`, unchecked casts, suppressed lint rules, or ignored type
  errors unless justified inline **and** tracked in `PLAN.md`.
- Suppressions name the specific rule and the reason. Never blanket-disable.

**Dependencies**
- Nothing added without purpose, compatibility check, and security review.
- No global installs unless explicitly required and documented.

## Phase 4 — security

- Dependency vulnerability scanning wired into `security:audit`.
- Secret scanning (`gitleaks`) in pre-commit **and** CI. Note: gitleaks
  allowlists well-known example keys such as `AKIAIOSFODNN7EXAMPLE`, so a clean
  run is not proof the scanner is working — verify with a real-shaped test
  secret once, then delete it.
- Environment variable validation at startup, schema-checked where the stack
  supports it.
- `.env.example` documents every required variable with no real values.
- `.env` in `.gitignore` before the first commit.
- Secure headers, input validation, output encoding where applicable.
- Least-privilege defaults.

Document security assumptions and accepted residual risk in `PLAN.md`.

## Phase 5 — required documents

### `README.md`
Overview · stack · requirements · installation · development commands · build ·
test · quality gate commands · environment variables · project structure ·
deployment notes · security notes · troubleshooting.

Never contains false claims, unverified claims, stale commands, or features
that do not exist. Every command in it must have been run successfully.

### `CHANGELOG.md`
Real implementation history. Update after meaningful change. Track what
happened, not what was planned. Keep superseded entries. Keep a Changelog
format, semver.

### `PLAN.md`
Assumptions · resolved decisions · open questions · architecture notes ·
research and version-verification notes · milestones · per-milestone tasks,
tests, and certification gates · security gates · performance gates ·
documentation requirements · definition of done.

Each milestone carries: goal · scope · files affected · implementation steps ·
acceptance criteria · required tests · required gates · required doc updates ·
required security checks · required performance checks · certification
checklist.

**A milestone is not complete until its certification checklist passes.**

### Agent instruction files
Create project-local files for the active tooling: `AGENTS.md`, `CLAUDE.md`,
`.cursor/rules/*`, `.github/copilot-instructions.md`.

They must reinforce: code standards, quality gates, documentation rules,
testing rules, security rules, changelog discipline, planning discipline.

**Never create or modify global user memory, global IDE settings, or
machine-wide agent instructions without explicit approval.** Project-local only.

## Phase 6 — performance and visual gates

Where applicable:

- Production build validation — the build must actually succeed.
- Bundle size awareness with a recorded budget.
- Lighthouse on visual milestones: **Performance, Accessibility, Best
  Practices**. SEO excluded unless explicitly requested.
- Prefer static/server-side work where the stack favors it.
- Measurable targets, not adjectives.

For UI projects, milestone certification includes visual verification: local
preview instructions plus a screenshot or an explicit manual-check record. The
`chrome-devtools` and `playwright` MCP servers can drive this when available.

## Execution

1. Scan (rule zero). Report what exists.
2. Ask the batched clarification questions.
3. Write `PLAN.md` first — decisions and milestones before code.
4. Scaffold structure, configs, and gates.
5. Install dependencies. Lock them. Verify the install.
6. Run every gate. They must pass on the empty scaffold before milestone one.
7. Write `README.md` and `CHANGELOG.md` from what actually exists.
8. Commit.

Work milestone by milestone after that. Do not skip certification gates. Do not
write fallback, legacy, or temporary code to force progress. When blocked by a
product decision, ask.

## Completion report

- Files created
- Dependencies installed, with pinned versions
- Quality gates configured, and the command for each
- Commands to run
- Assumptions made
- Open questions
- First milestone status
- **Gates that failed or were deferred, and why**
- Next recommended action

Do not call the project production-ready unless every documented
production-readiness gate actually passed. If a gate was skipped because a tool
is missing, say that plainly — a deferred gate reported as passing is the one
failure this skill exists to prevent.
