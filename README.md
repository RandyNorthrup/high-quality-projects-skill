<h1 align="center">High-Quality Projects</h1>

<p align="center">
  Turn new ideas into confirmed, release-ready project contracts<br>
  and raise existing codebases with evidence-backed quality gates.
</p>

<p align="center">
  <a href="https://github.com/RandyNorthrup/high-quality-projects-skill/actions/workflows/cross-platform.yml"><img alt="Cross-platform package checks" src="https://github.com/RandyNorthrup/high-quality-projects-skill/actions/workflows/cross-platform.yml/badge.svg"></a>
  <a href="https://github.com/RandyNorthrup/high-quality-projects-skill/tags"><img alt="Latest Git tag" src="https://img.shields.io/github/v/tag/RandyNorthrup/high-quality-projects-skill?label=version"></a>
  <a href="LICENSE"><img alt="MIT license" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#workflows">Workflows</a> ·
  <a href="#reference-tooling">Tooling</a> ·
  <a href="#design-principles">Principles</a> ·
  <a href="#documentation">Documentation</a>
</p>

> [!IMPORTANT]
> Windows runs natively through PowerShell 5.1 or newer. Bash, WSL, and Git
> Bash are not required on Windows. Linux and macOS use the POSIX/Bash scripts.

## Why this exists

A quality tool being installed does not prove that it checks the intended code,
fails CI on findings, or works with the rest of the toolchain. These workflows
make those details explicit:

- inventory the project before writing anything;
- reuse or extend existing code, components, assets, documentation, and
  configuration instead of creating parallel replacements;
- confirm important gates can fail on a deliberate test case;
- separate mechanical work from judgment-heavy changes;
- report every gate as **pass**, **fail**, or **deferred**, with evidence.

The package provides instructions and templates. It does not claim that a
target project is compliant merely because the files were copied.

## At a glance

| New projects | Existing projects | Portable execution |
|---|---|---|
| Grill the idea across users, outcomes, scope, experience, signing, distribution, operations, and release; then verify the stack and scaffold gates. | Establish a baseline, then apply formatting, lint, types, dead-code work, security, and documentation in reviewable phases. | Plain Markdown workflows, native PowerShell on Windows, and Bash on Linux/macOS. |

## Quick start

### Any coding agent

Clone or vendor the repository, then direct the agent to read the appropriate
workflow in full:

```console
git clone https://github.com/RandyNorthrup/high-quality-projects-skill.git
```

- New project: [`skills/project_setup/SKILL.md`](skills/project_setup/SKILL.md)
- Existing project: [`skills/quality_retrofit/SKILL.md`](skills/quality_retrofit/SKILL.md)

[`AGENTS.md`](AGENTS.md) is the shared entry point for agents that support that
convention. Thin discovery adapters are also included for Cursor and GitHub
Copilot; agents without automatic discovery can read the workflow files
directly.

Resolve the package root with the active shell before using paths from a
workflow.

PowerShell on Windows:

```powershell
$SkillRoot = & 'C:\path\to\high-quality-projects-skill\scripts\skill-root.ps1'
```

Bash on Linux or macOS:

```bash
SKILL_ROOT="$(bash /path/to/high-quality-projects-skill/scripts/skill-root.sh)"
```

Both resolvers honor an explicit `SKILL_ROOT`, then Claude Code's optional
`CLAUDE_PLUGIN_ROOT`, then locate the package from the script itself.

### Claude Code plugin

From Claude Code, add this repository as a marketplace and install its plugin:

```text
/plugin marketplace add RandyNorthrup/high-quality-projects-skill
/plugin install high-quality-projects-skill@high-quality-projects-skill
/reload-plugins
```

The installed skills are namespaced:

```text
/high-quality-projects-skill:project_setup Grill me on a project that ...
/high-quality-projects-skill:quality_retrofit
```

## Workflows

### Project setup

[`project_setup`](skills/project_setup/SKILL.md) is for a new or effectively
empty project. It:

1. scans code, configuration, documentation, and brand assets, then reuses or
   extends canonical work instead of creating duplicates;
2. runs a focused, multi-round **Grill Me** interview covering the who, why,
   what, where, when, logos, icons, favicons, colors, accessibility, signing,
   distribution, service model, security, operations, and release pipeline;
3. writes a decision ledger and requires owner confirmation of
   `PROJECT_BRIEF.md` before stack selection;
4. verifies version compatibility using current official sources or registries;
5. creates project-local quality, security, test, and CI gates appropriate to
   the chosen stack;
6. writes `README.md`, `CHANGELOG.md`, and `PLAN.md` from confirmed scope and
   what actually exists;
7. runs every available gate and records anything that could not be verified.

The project description seeds discovery; it does not skip it. Questions arrive
in focused rounds, with known answers reused and critical unknowns blocking
irreversible choices instead of becoming silent assumptions.

### Quality retrofit

[`quality_retrofit`](skills/quality_retrofit/SKILL.md) is for an existing,
version-controlled codebase. It requires a clean working tree, records the
baseline first, and separates work into nine independently reviewable phases.

| Phase | Focus | Typical risk |
|---:|---|---|
| 0 | Baseline: tests, build, and finding counts | Low; commands may create caches, which the workflow tracks |
| 1 | Formatting | Low; still requires semantic checks, tests, and diff review |
| 2 | Configuration and gates | Low–medium; changes developer and CI behavior |
| 3 | Autofixable lint | Medium; automated fixes can alter behavior |
| 4 | Strict types | Medium–high; often exposes broad design debt |
| 5 | Dead-code analysis and removal | High; dynamic entry points can look unused |
| 6 | Literal and constant cleanup | High; unit mistakes can change behavior |
| 7 | Security scans and native-code sanitizers | High; findings require triage and secrets may require incident response |
| 8 | Documentation reconciliation | Low; commands and claims must match the resulting project |

These risk labels are planning guidance, not guarantees. The workflow requires
tests and evidence at each boundary and does not authorize silent phase
chaining.

It also refuses to:

- retrofit a dirty tree or bulk-edit an unversioned codebase;
- delete code without checking whether it is reachable through dynamic or
  framework-driven paths;
- rewrite Git history for a leaked secret without explicit authorization;
- weaken an existing rule that is stricter than the supplied template;
- report a skipped, missing, or unverified gate as passing.

## Reference tooling

The workflows select tools to fit the target project. This table describes the
reference configurations and guidance included here; it is not a promise that
every tool applies to every project.

| Stack | Format | Lint / analysis | Types | Dead code | Security | Tests |
|---|---|---|---|---|---|---|
| Python | Ruff | Ruff | mypy | vulture, deptry | Bandit, pip-audit | pytest |
| TypeScript / JavaScript | Prettier | ESLint | TypeScript | knip, dpdm | npm audit, Semgrep | project-selected runner |
| Rust | rustfmt | Clippy | compiler | cargo-machete | cargo-audit, cargo-deny | cargo test |
| C++ | clang-format | clang-tidy, cppcheck | compiler | cppcheck | sanitizers, Valgrind where supported | CTest or project runner |
| C# / .NET | dotnet format | .NET analyzers | nullable, warnings as errors | Roslyn diagnostics | NuGet audit | dotnet test |
| CSS / HTML | Prettier | Stylelint / HTMLHint | — | — | — | project-selected runner |
| PowerShell | PSScriptAnalyzer | PSScriptAnalyzer | — | — | — | Pester where used |
| Shell | shfmt | ShellCheck | — | — | — | bats where used |

Cross-cutting guidance covers Gitleaks for secrets, Semgrep for multi-language
static analysis, and jscpd for duplication. Tool availability and compatibility
are checked in the target environment rather than assumed from this table.

## Design principles

### Scan before writing

The native inventory scripts emit the same JSON shape:

```powershell
& "$SkillRoot\scripts\detect-stack.ps1" .
```

```bash
"${SKILL_ROOT}/scripts/detect-stack.sh" .
```

They report detected languages, existing quality configuration, Git state, and
locally available tools. They do not install dependencies or modify the target
workspace. Callers must inspect the JSON for an `error` property; the scripts
return their JSON contract even when inventory fails.

### Prove gates can fail

A clean report is useful only after the gate has been exercised against an
input it should reject. The workflows require a deliberate failure check where
practical, followed by removal of the test defect. This catches decorative
configuration, wrong include paths, broken resolvers, and warning-only CI.

### Treat automatic fixes as code changes

Formatting and autofix output still need review. For Python formatting,
[`verify-format-safe.py`](scripts/verify-format-safe.py) compares parsed ASTs
before and after formatting; tests and diff review remain necessary, especially
for non-Python files.

### Keep security claims scoped

The supplied pre-commit hook checks staged changes. The explicit
`gitleaks git --redact` workflow scans reachable checked-out Git history. A
history finding is handled as a potential credential incident: rotate first,
then decide whether authorized history cleanup is needed.

### Keep sanitizer builds honest

For C and C++, the reference uses ASan with UBSan for one debug/test build and
TSan in a separate build. Recoverable UBSan checks need
`-fno-sanitize-recover=all` when a finding must fail the gate. Rust sanitizer
support depends on the target and toolchain; full standard-library coverage may
require nightly Rust and `-Zbuild-std`. See the
[`sanitizer reference`](templates/cpp/sanitizers.md) before wiring CI.

## Documentation

- [`AGENTS.md`](AGENTS.md) — shared agent entry point and non-negotiable rules
- [`skills/project_setup/references/grill-me.md`](skills/project_setup/references/grill-me.md)
  — complete product, delivery, signing, and operations discovery coverage
- [`skills/project_setup/assets/PROJECT_BRIEF.md`](skills/project_setup/assets/PROJECT_BRIEF.md)
  — reusable decision record and readiness confirmation template
- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — why the standards exist and when
  strictness is the wrong choice
- [`templates/README.md`](templates/README.md) — template locations, commands,
  deliberate loosenings, and dated compatibility evidence
- [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md) — C/C++ and Rust
  sanitizer reference
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and verification contract
- [`CHANGELOG.md`](CHANGELOG.md) — released and unreleased changes

<details>
<summary>Repository layout</summary>

```text
skills/       workflow contracts
scripts/      native inventory and path-resolution helpers
templates/    strict, adaptable configuration examples
tests/        cross-platform smoke and parity checks
docs/         design rationale and repository notes
```

</details>

## Requirements

- Git for cloning and version-control checks
- Windows: Windows PowerShell 5.1 or newer, or PowerShell 7
- Linux/macOS: Bash and standard POSIX command-line tools
- Python 3 only for `scripts/verify-format-safe.py`

Individual quality gates require their own project-local tools. The inventory
scripts report availability; they do not install anything.

## License

[MIT](LICENSE)
