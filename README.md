# high-quality-projects-skill

**Two workflows that encode production-grade standards for coding agents.** One
sets a new project up. One brings an existing project toward compliance.

```
project setup <description>   →  new project, strict gates from commit one
quality retrofit              →  existing codebase, brought into compliance
```

Covers Python, TypeScript, JavaScript, Rust, C++, C#, CSS, HTML, PowerShell, and Shell.

**Vendor-neutral workflows.** The workflows are plain Markdown and the gate
configs are plain files. Claude Code has optional marketplace packaging; other
agents can start from [`AGENTS.md`](AGENTS.md). No workflow path depends only on
a vendor-set environment variable.

---

## The problem this solves

Most "quality setup" leaves you with linters that **report findings and exit 0**. CI goes green. The bug ships anyway.

```console
eslint .                    # 47 warnings.  exit 0.  CI passes. ✅❌
eslint . --max-warnings=0   # 47 warnings.  exit 1.  CI fails.  ✅
```

That one flag is the difference between a quality gate and a decoration. Each
listed tool has an equivalent enforcement setting; omitting it can produce the
same false green:

| Tool | Without it | With it |
|---|---|---|
| eslint / stylelint | reports, exits 0 | `--max-warnings=0` |
| clippy | warns | `-D warnings` |
| cppcheck | prints | `--error-exitcode=1` |
| PSScriptAnalyzer | returns objects | `-EnableExit` |
| knip | lists | `--strict` |
| UBSan | many checks may recover | `-fno-sanitize-recover=all` |
| C# style rules | IDE-only | `<EnforceCodeStyleInBuild>` |

Both workflow contracts require these flags and require agents to **report any
gate they could not run** instead of quietly skipping it.

---

## Install

### Any agent

Clone it anywhere and point your agent at it:

```console
git clone https://github.com/RandyNorthrup/high-quality-projects-skill.git
```

Then tell the agent to read [`AGENTS.md`](AGENTS.md), which routes to the two
workflows and explains how paths resolve. Agents that auto-discover
`AGENTS.md`, `.cursor/rules/`, or `.github/copilot-instructions.md` pick it up
with no instruction at all — all three are included and point at the same
source.

To use it against a project without cloning into it, vendor it as a submodule or
leave it beside the project. The workflows locate their own files with
`scripts/skill-root.ps1` on PowerShell or `scripts/skill-root.sh` on POSIX and
never assume a working directory.

Windows uses native PowerShell scripts and does not need Bash, WSL, Git Bash,
or a Linux distribution:

```powershell
$SkillRoot = & '.\high-quality-projects-skill\scripts\skill-root.ps1'
& "$SkillRoot\scripts\detect-stack.ps1" . | ConvertFrom-Json
```

Do not select `bash.exe` merely because Windows reports it on `PATH`: that file
can be a WSL relay even when no distribution or `/bin/bash` exists.

### Claude Code

```console
claude plugin marketplace add RandyNorthrup/high-quality-projects-skill
claude plugin install high-quality-projects-skill@high-quality-projects-skill
```

The name appears twice because the syntax is `plugin@marketplace`, and this repo publishes one plugin under a marketplace of the same name.

Run `/reload-plugins` inside an active Claude Code session after installation.
Restarting Claude Code also reloads plugins.

```console
claude plugin list
```

This registers the namespaced skills
`/high-quality-projects-skill:project_setup` and
`/high-quality-projects-skill:quality_retrofit`. The underlying Markdown files
can also be followed directly without Claude Code.

### Requirements

`git`, plus PowerShell 5.1 or newer on Windows, or Bash and standard POSIX tools
on Linux and macOS. Bash is not required on Windows. `verify-format-safe.py`
needs Python 3. Everything else is per-stack and optional — the workflows
detect what is installed and declare anything they had to defer rather than
skipping it silently.

---

## Project setup

[`skills/project_setup/SKILL.md`](skills/project_setup/SKILL.md) — or
`/high-quality-projects-skill:project_setup` in Claude Code.

```
project setup: A REST API for tracking gym workouts. Postgres, JWT auth, deployed on Fly.io.
```

The description is the argument. The workflow contract requires a clarification
round when the description is missing or only one line, then requires these
steps:

1. **Scans first.** Even an "empty" directory. Existing files change the plan, and may mean you want the retrofit workflow instead.
2. **Asks once.** One batched round: stack, deployment, database, auth, testing. Never asks what the files already answer.
3. **Verifies versions.** Against official docs and registries — no guessed compatibility. Pins what it installs.
4. **Writes `PLAN.md` before code.** Decisions, milestones, and per-milestone certification gates.
5. **Runs the gates.** Every configured gate passes on the empty scaffold before
   milestone one; anything unavailable is named as deferred rather than passing.

The contract requires `README.md`, `CHANGELOG.md`, `PLAN.md`, and project-local
agent instruction files. It forbids global user memory and machine-wide IDE
configuration changes.

---

## Quality retrofit

[`skills/quality_retrofit/SKILL.md`](skills/quality_retrofit/SKILL.md) — or
`/high-quality-projects-skill:quality_retrofit` in Claude Code.

The retrofit contract divides work into independently reviewable phases and
requires the agent to **stop and report between them** rather than chaining
silently.

| Phase | What | Risk |
|---|---|---|
| 0 | Baseline — tests, build, error counts | none |
| 1 | Formatting | none, but huge diff — needs blame-ignore |
| 2 | Configs and gates wired | none — no source changes |
| 3 | Autofixable lint | low — `--fix` is not always semantically neutral |
| 4 | Strict types | medium — biggest error count, finds real bugs |
| 5 | Dead-code removal | **high** — false positives on dynamic dispatch |
| 6 | Magic numbers → constants | **high** — a wrong unit is a behavior change |
| 7 | Security + sanitizers | findings are real bugs, not lint |
| 8 | Documentation reconciliation | none |

### The contract forbids

- Modify a **dirty working tree** — uncommitted work would get tangled with mechanical changes
- Bulk-modify code **not under version control**
- Delete code it has **not verified** is unreachable
- **Rewrite git history** to scrub a leaked secret without being told to
- Weaken a rule your project already set stricter
- Report a gate as passing when it was skipped

### Why phase 1 gets its own commit

Formatting is intended to change layout only, but can touch most files and
obscure `git blame`. The workflow verifies the result, lands it alone, and adds
the commit to `.git-blame-ignore-revs`:

```bash
git rev-parse HEAD >> .git-blame-ignore-revs
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

PowerShell equivalent:

```powershell
git rev-parse HEAD | Add-Content -LiteralPath .git-blame-ignore-revs -Encoding Ascii
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Without that file, blame results for reformatted lines point at the formatting
commit instead of the earlier change.

---

## Standards required by the workflows

These are completion criteria in the workflow contracts, not proof that a
particular agent run satisfied them. The final report must show the gate
evidence and name anything deferred.

**Magic numbers** — extracted into named constants, enums, or validated config. But `if (xs.length === 0)`, `for (i = 0; ...)`, `return []`, and `arr[0]` are left alone. The test is whether the name adds information the value lacks: `const TWO = 2` adds nothing, `const RETRY_LIMIT = 2` adds everything.

**Dead code** — none. No commented-out legacy, unused files, unused exports, unused dependencies, stale config.

**Honesty** — no silent fallbacks, fake implementations, placeholder production code, or mock data outside test/dev/demo boundaries. A function that cannot do its job raises; it does not return an empty result that reads like success.

**Escape hatches** — no broad `any`, unchecked cast, or suppressed rule without inline justification *and* a tracked debt entry in the report.

---

## Stack coverage

| Stack | Format | Lint | Types | Dead code | Security | Test |
|---|---|---|---|---|---|---|
| Python | ruff format | ruff (`ALL`) | mypy strict+ | vulture, deptry | bandit, pip-audit | pytest |
| TypeScript / JS | prettier | eslint strictTypeChecked | tsc strict+ | knip | npm audit, semgrep | vitest |
| Rust | rustfmt | clippy pedantic | compiler | cargo-machete | cargo-audit, cargo-deny | cargo test |
| C++ | clang-format | clang-tidy, cppcheck | compiler | cppcheck | sanitizers, valgrind | ctest |
| C# / .NET | dotnet format | AnalysisLevel latest-all | nullable + warnaserror | IDE0051/2 | NuGetAudit | dotnet test |
| CSS | prettier | stylelint | — | — | — | — |
| HTML | prettier | htmlhint | — | — | — | — |
| PowerShell | PSScriptAnalyzer | PSScriptAnalyzer | — | — | — | Pester |
| Shell | shfmt | shellcheck | — | — | gitleaks | bats |

Cross-cutting: **gitleaks** (`gitleaks git` scans reachable checked-out
history; its pre-commit hook scans staged changes), **semgrep** (SAST), and
**jscpd** (copy-paste detection).

Config templates live in [`templates/`](templates/). Their deliberate
loosenings and required local adaptations are documented in
[`templates/README.md`](templates/README.md) and inline where the format permits
comments.

---

## Sanitizers

Project history records deliberately broken-program validation on 2026-07-26
with gcc 15, clang 21, and Rust nightly. Treat that as dated evidence and rerun
the sanitizer jobs for the target compiler and platform.

| | gcc | clang | Rust | Catches |
|---|---|---|---|---|
| ASan | ✅ | ✅ | ✅ | use-after-free, buffer overflow, double-free |
| LSan | ✅ | ✅ | ✅ | memory leaks |
| UBSan | ✅ | ✅ | — | overflow, bad shift, misaligned, null deref |
| TSan | ✅ | ✅ | ✅ | data races |
| MSan | — | ✅ | ✅ | uninitialized reads |

The workflows call out three common false-negative sources:

- **ASan and TSan cannot be combined** — incompatible shadow memory, so they need separate builds and separate CI jobs
- **`-fno-sanitize-recover=all`** makes recoverable UBSan findings halt the
  process instead of merely reporting and continuing
- **Rust sanitizer coverage can need `-Zbuild-std`** so standard-library code
  is rebuilt with instrumentation

MSan on real C++ needs an instrumented libc++, which most distributions do not ship. The skills will not add an MSan gate unless the project builds its own standard library — otherwise it drowns in false positives from library internals.

Full reference: [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md).

---

## Dead-code tools do not overlap

Running one and calling it done leaves real holes:

- **`tsc --noEmit`** with `noUnusedLocals` — unused symbols *inside* a file. Blind to unused exports.
- **`knip`** — whole-graph: dead *modules*, unused exports, unused dependencies. Finds what tsc structurally cannot.
- **`vulture`** — Python, heuristic, reports a confidence percentage for a reason.
- **`cppcheck --enable=all`** — includes `unusedFunction`, but per-file invocation cannot see cross-TU callers.
- **`cargo machete`** — unused Cargo dependencies.
- **Roslyn IDE0051/0052** — unused C# private members.

These tools can false-positive on dynamic dispatch, string-keyed lookup,
library public API, test fixtures, and framework entry points. The tools produce
*candidates*; repository-wide evidence supports deletions. The workflow lists
unverified candidates instead of removing them.

---

## Documentation

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — the reasoning behind each rule, and explicitly where strict is the wrong call
- [`templates/README.md`](templates/README.md) — every config, its gate command, its loosenings
- [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md) — flags, runtime options, CMake, Rust
- [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
