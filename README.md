# high-quality-projects-skill

**Two workflows that hold a codebase to production-grade standards, for any coding agent.** One sets a new project up right. One cleans an existing one up.

```
project setup <description>   →  new project, strict gates from commit one
quality retrofit              →  existing codebase, brought into compliance
```

Covers Python, TypeScript, JavaScript, Rust, C++, C#, CSS, HTML, PowerShell, and Shell.

**Vendor-neutral.** The workflows are plain Markdown and the gate configs are plain files. Claude Code gets a one-command plugin install; every other agent reads [`AGENTS.md`](AGENTS.md) — the cross-vendor convention that Codex, Cursor, Aider, Zed, and others already look for. Nothing here requires a specific tool, and no path depends on a vendor-set environment variable.

---

## The problem this solves

Most "quality setup" leaves you with linters that **report findings and exit 0**. CI goes green. The bug ships anyway.

```bash
eslint .                    # 47 warnings.  exit 0.  CI passes. ✅❌
eslint . --max-warnings=0   # 47 warnings.  exit 1.  CI fails.  ✅
```

That one flag is the difference between a quality gate and a decoration. There is an equivalent for every tool, and missing any of them produces the same false green:

| Tool | Without it | With it |
|---|---|---|
| eslint / stylelint | reports, exits 0 | `--max-warnings=0` |
| clippy | warns | `-D warnings` |
| cppcheck | prints | `--error-exitcode=1` |
| PSScriptAnalyzer | returns objects | `-EnableExit` |
| knip | lists | `--strict` |
| UBSan | prints and **continues** | `-fno-sanitize-recover=all` |
| C# style rules | IDE-only | `<EnforceCodeStyleInBuild>` |

Both skills wire these by default, and **report any gate they could not run** instead of quietly skipping it.

---

## Install

### Any agent

Clone it anywhere and point your agent at it:

```bash
git clone https://github.com/RandyNorthrup/high-quality-projects-skill.git
```

Then tell the agent to read [`AGENTS.md`](AGENTS.md), which routes to the two
workflows and explains how paths resolve. Agents that auto-discover
`AGENTS.md`, `.cursor/rules/`, or `.github/copilot-instructions.md` pick it up
with no instruction at all — all three are included and point at the same
source.

To use it against a project without cloning into it, vendor it as a submodule or
leave it beside the project; the workflows locate their own files with
`scripts/skill-root.sh` and never assume a working directory.

### Claude Code

```bash
claude plugin marketplace add RandyNorthrup/high-quality-projects-skill
claude plugin install high-quality-projects-skill@high-quality-projects-skill
```

The name appears twice because the syntax is `plugin@marketplace`, and this repo publishes one plugin under a marketplace of the same name.

**Restart Claude Code.** Skills load at session start, so a freshly installed one is not available until you do.

```bash
claude plugin list      # high-quality-projects-skill · enabled
```

This registers `/project_setup` and `/quality_retrofit` as slash commands. It is packaging convenience only — the same files work unchanged without it.

### Requirements

`git` and `bash`. `verify-format-safe.py` needs Python 3. Everything else is per-stack and optional — the workflows detect what is installed and declare anything they had to defer rather than skipping it silently.

---

## Project setup

[`skills/project_setup/SKILL.md`](skills/project_setup/SKILL.md) — or `/project_setup` in Claude Code.

```
project setup: A REST API for tracking gym workouts. Postgres, JWT auth, deployed on Fly.io.
```

The description is the argument, and detail pays off — a one-liner gets you a round of questions, a real description gets you a plan.

1. **Scans first.** Even an "empty" directory. Existing files change the plan, and may mean you want the retrofit workflow instead.
2. **Asks once.** One batched round: stack, deployment, database, auth, testing. Never asks what the files already answer.
3. **Verifies versions.** Against official docs and registries — no guessed compatibility. Pins what it installs.
4. **Writes `PLAN.md` before code.** Decisions, milestones, and per-milestone certification gates.
5. **Proves the gates.** Every gate runs and passes on the empty scaffold before milestone one begins.

Produces `README.md`, `CHANGELOG.md`, `PLAN.md`, and project-local agent instruction files. **Never touches global config** — no global user memory, no machine-wide IDE settings.

---

## Quality retrofit

[`skills/quality_retrofit/SKILL.md`](skills/quality_retrofit/SKILL.md) — or `/quality_retrofit` in Claude Code.

Runs on an existing codebase, in phases. Each is independently reviewable and revertible, and it **stops and reports between them** rather than chaining silently.

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

### It refuses to

- Modify a **dirty working tree** — uncommitted work would get tangled with mechanical changes
- Bulk-modify code **not under version control**
- Delete code it has **not verified** is unreachable
- **Rewrite git history** to scrub a leaked secret without being told to
- Weaken a rule your project already set stricter
- Report a gate as passing when it was skipped

### Why phase 1 gets its own commit

Formatting touches every file and changes no behavior — which makes it simultaneously the safest change and the most destructive to `git blame`. It lands alone, and the commit goes into `.git-blame-ignore-revs`:

```bash
git rev-parse HEAD >> .git-blame-ignore-revs
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Skip that and every `git blame` for the rest of the repo's life points at the formatting commit.

---

## Standards enforced

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

Cross-cutting: **gitleaks** (secrets, full history), **semgrep** (SAST), **jscpd** (copy-paste).

Config templates in [`templates/`](templates/) — each documents its own deliberate loosenings, so you can see what was *not* enforced and why.

---

## Sanitizers

Verified trapping real bugs on gcc 15, clang 21, and Rust nightly.

| | gcc | clang | Rust | Catches |
|---|---|---|---|---|
| ASan | ✅ | ✅ | ✅ | use-after-free, buffer overflow, double-free |
| LSan | ✅ | ✅ | ✅ | memory leaks |
| UBSan | ✅ | ✅ | — | overflow, bad shift, misaligned, null deref |
| TSan | ✅ | ✅ | ✅ | data races |
| MSan | — | ✅ | ✅ | uninitialized reads |

Three things that silently defeat them, all handled:

- **ASan and TSan cannot be combined** — incompatible shadow memory, so they need separate builds and separate CI jobs
- **`-fno-sanitize-recover=all`**, or UBSan prints its finding and the job still exits 0
- **Rust needs `-Zbuild-std`** — the shipped `std` is uninstrumented, so you get false negatives without rebuilding it

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

All of them false-positive on dynamic dispatch, string-keyed lookup, library public API, test fixtures, and framework entry points. So the tools produce *candidates*; a grep across the whole repo produces *deletions*. Unverified candidates get listed in the report, not removed.

---

## Documentation

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — the reasoning behind each rule, and explicitly where strict is the wrong call
- [`templates/README.md`](templates/README.md) — every config, its gate command, its loosenings
- [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md) — flags, runtime options, CMake, Rust
- [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`CHANGELOG.md`](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
