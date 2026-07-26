# high-quality-projects-skill

Two paired [Claude Code](https://claude.com/claude-code) skills that hold a
codebase to production-grade standards — one for new projects, one for existing
ones.

```
/project_setup <description>   scaffold a new project with strict gates from commit one
/quality_retrofit              bring an existing codebase into compliance
```

Both **scan before they write**. Neither overwrites configuration you already
have — existing choices are read, preserved, and extended.

---

## Why two skills

They solve opposite problems and the failure modes are different.

`/project_setup` starts from nothing, so the risk is *guessing* — wrong
versions, incompatible packages, gates that were never actually run.

`/quality_retrofit` starts from working code someone depends on, so the risk is
*breaking it* — an unreviewable 4,000-file diff, a deleted function that was
reached by reflection, a magic number extracted with the wrong unit.

Same standards, different safety rails.

---

## Install

```bash
claude plugin marketplace add RandyNorthrup/high-quality-projects-skill
claude plugin install high-quality-projects-skill@high-quality-projects-skill
```

The name appears twice because the syntax is `plugin@marketplace`, and this
repo publishes a single plugin under a marketplace of the same name.

Restart Claude Code — skills are loaded at session start, so a freshly
installed one is not available until you do.

Verify:

```bash
claude plugin list          # high-quality-projects-skill · enabled
```

---

## Usage

### New project

```
/project_setup A REST API for tracking gym workouts. Postgres, JWT auth, deployed on Fly.io.
```

The description is the argument and it matters — a one-liner gets you a round of
clarifying questions, a real description gets you a plan.

What happens:

1. **Scan** — even an "empty" directory gets checked. Existing files change the plan.
2. **Ask** — one batched round covering stack, deployment, database, auth, testing.
3. **Verify** — every dependency version checked against official sources, not guessed.
4. **`PLAN.md` first** — decisions and milestones before any code.
5. **Scaffold** — structure, configs, gates.
6. **Prove** — every gate runs and passes on the empty scaffold before milestone one.

### Existing project

```
/quality_retrofit
```

Runs in phases, each independently reviewable and revertible:

| Phase | What | Risk |
|---|---|---|
| 0 | Baseline: tests, build, error counts | none |
| 1 | Formatting | none — but huge diff, needs blame-ignore |
| 2 | Configs and gates wired | none — no source changes |
| 3 | Autofixable lint | low — read the diff, `--fix` is not always neutral |
| 4 | Strict types | medium — largest error count, finds real bugs |
| 5 | Dead code removal | **high** — false positives on dynamic dispatch |
| 6 | Magic numbers | **high** — wrong unit is a behavior change |
| 7 | Security + sanitizers | findings are real bugs, not lint |
| 8 | Documentation reconciliation | none |

It stops and reports between phases. It will not chain them silently.

**It refuses to** modify a dirty working tree, bulk-modify code outside version
control, delete code it has not verified is unreachable, or rewrite git history
to scrub a leaked secret without being told to.

---

## Standards enforced

**Constants and literals** — no unexplained magic numbers, strings, booleans, or
timeouts. Named constants, enums, literal unions, or schema-validated config.
Idiomatic literals (`0`, `1`, `-1`, `[]`, `""`, booleans in conditions) stay —
a rule that rejects `if (xs.length === 0)` is misconfigured.

**Dead code** — none. No commented-out legacy, unused files, unused exports,
unused dependencies, stale config.

**Honesty** — no silent fallbacks, fake implementations, placeholder production
code, or mock data outside test/dev/demo boundaries. A function that cannot do
its job raises; it does not return an empty result that reads like success.

**Escape hatches** — no broad `any`, unchecked casts, or suppressed rules
without inline justification *and* a tracked debt entry.

**Dependencies** — nothing added without purpose, compatibility check, and
security review.

---

## Stack coverage

| Stack | Format | Lint | Types | Dead code | Security | Test |
|---|---|---|---|---|---|---|
| Python | ruff format | ruff (`ALL`) | mypy strict+ | vulture, deptry | bandit, pip-audit | pytest |
| TS/JS | prettier | eslint strictTypeChecked | tsc strict+ | knip | npm audit, semgrep | vitest |
| Rust | rustfmt | clippy pedantic | compiler | cargo-machete | cargo-audit, cargo-deny | cargo test |
| C++ | clang-format | clang-tidy, cppcheck | compiler | cppcheck | sanitizers, valgrind | ctest |
| C# | dotnet format | AnalysisLevel latest-all | nullable + warnaserror | IDE0051/2 | NuGetAudit | dotnet test |
| CSS | prettier | stylelint | — | — | — | — |
| HTML | prettier | htmlhint | — | — | — | — |
| PowerShell | PSScriptAnalyzer | PSScriptAnalyzer | — | — | — | Pester |
| Shell | shfmt | shellcheck | — | — | gitleaks | bats |

Cross-cutting: `gitleaks` (secrets, full history), `semgrep` (SAST), `jscpd`
(copy-paste).

Config templates live in [`templates/`](templates/) — each documents its own
deliberate loosenings so you can see what was *not* enforced and why.

---

## The part most setups get wrong

A configured linter that exits 0 on findings is decorative. These flags are what
make a gate a gate:

```
eslint --max-warnings=0                stylelint --max-warnings=0
cargo clippy -- -D warnings            cppcheck --error-exitcode=1
knip --strict                          Invoke-ScriptAnalyzer -EnableExit
-fno-sanitize-recover=all              ← UBSan, else prints and continues
<EnforceCodeStyleInBuild>true</...>    ← C#, else IDE-only
<TreatWarningsAsErrors>true</...>      ← C#
```

Both skills wire these by default and report any gate they could not run.

---

## Sanitizers

Verified working on gcc 15, clang 21, and Rust nightly.

| | gcc | clang | Rust | Catches |
|---|---|---|---|---|
| ASan | yes | yes | yes | use-after-free, overflow, double-free |
| LSan | yes | yes | yes | leaks |
| UBSan | yes | yes | — | overflow, bad shift, misaligned, null deref |
| TSan | yes | yes | yes | data races |
| MSan | no | yes | yes | uninitialized reads |

Three things that silently defeat them, handled by the skills:

- **ASan and TSan cannot be combined** — incompatible shadow memory, separate builds
- **`-fno-sanitize-recover=all`** or UBSan prints and the job still exits 0
- **Rust needs `-Zbuild-std`** — the shipped `std` is uninstrumented, so you get
  false negatives without rebuilding it

MSan on real C++ needs an instrumented libc++, which most distros do not ship.
The skills will not add an MSan gate unless the project builds its own standard
library. Full reference: [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md).

---

## Requirements

Claude Code, `git`, `bash`, `jq`.

Everything else is per-stack and optional — `scripts/detect-stack.sh` reports
what is installed, and the skills declare any gate they had to defer rather than
reporting it green. Install what you need for the languages you use.

---

## Documentation

- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — why these rules, and where strict is the wrong call
- [`templates/README.md`](templates/README.md) — every config, its gate command, its loosenings
- [`templates/cpp/sanitizers.md`](templates/cpp/sanitizers.md) — sanitizer flags and caveats
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`CHANGELOG.md`](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
