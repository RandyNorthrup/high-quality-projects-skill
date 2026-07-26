# QA templates — strict quality gates

Copy-in configs for lint / format / dead-code / test / security gates, tuned to
the strictest setting that is still *correct* rather than merely loud.

**A gate is not configured until it has been seen to fail on a case it is
supposed to catch.** Before relying on any of these, break something on purpose
and confirm the tool exits non-zero. That discipline is not decoration — three
separate tools have been found here that loaded cleanly, reported nothing, and
checked nothing (see Gotchas).

Installed 2026-07-26.

## Layout

| Path | Copy to | Gate |
|---|---|---|
| `python/ruff.toml` | project root | lint + format (`select = ["ALL"]`) |
| `python/mypy.ini` | project root | types (beyond `strict`) |
| `typescript/tsconfig.strict.json` | extend from your tsconfig | types |
| `typescript/eslint.config.mjs` | project root | lint (type-checked) |
| `web/.stylelintrc.json` | project root | CSS |
| `web/knip.jsonc` | project root | dead files / exports / deps |
| `cpp/.clang-tidy` | project root | C++ static analysis |
| `csharp/Directory.Build.props` | solution root | C# compiler + analyzers |
| `rust/clippy-strict.toml` | see file — two parts | Rust lint |
| `powershell/PSScriptAnalyzerSettings.psd1` | project root | PowerShell |
| `.pre-commit-config.yaml` | project root | wires all of the above |

## Quick start

```bash
cd your-project
cp <plugin-root>/templates/.pre-commit-config.yaml .
# delete the language blocks you don't use, then:
pre-commit install
pre-commit run --all-files
```

## Running gates by hand

```bash
# Python
ruff check . && ruff format --check . && mypy . && vulture . && bandit -r . && pip-audit

# TypeScript / JS
tsc --noEmit && eslint . --max-warnings=0 && knip --strict && prettier --check .

# CSS / HTML
stylelint "**/*.css" --max-warnings=0 && htmlhint .

# C++
cppcheck --enable=all --error-exitcode=1 --std=c++23 --suppress=missingIncludeSystem src/
clang-tidy src/*.cpp -- -std=c++23        # .clang-tidy sets WarningsAsErrors: '*'

# Rust
cargo fmt --all -- --check && cargo clippy --all-targets --all-features -- -D warnings
cargo machete && cargo audit && cargo deny check

# C#
dotnet format --verify-no-changes --severity info && dotnet build -warnaserror && roslynator analyze

# PowerShell
pwsh -c "Invoke-ScriptAnalyzer -Path . -Recurse -Settings ./PSScriptAnalyzerSettings.psd1 -EnableExit"

# Shell
shellcheck --severity=style --enable=all **/*.sh && shfmt -i 4 -ci -sr -d .

# Cross-cutting
gitleaks detect --redact          # secrets, scans git history
semgrep --config=auto             # multi-language SAST
jscpd .                           # copy-paste detection
```

## What each dead-code gate actually sees

They do not overlap as much as the names suggest — running only one leaves
real holes.

- **`tsc --noEmit`** with `noUnusedLocals`/`noUnusedParameters` — unused things
  *inside* a file. Blind to unused exports.
- **`knip`** — whole-graph: files nothing imports, exports nobody consumes,
  `package.json` deps nothing requires. This is the one that finds dead
  *modules*; ESLint and tsc structurally cannot.
- **`vulture`** — Python equivalent, heuristic. Confidence < 100% means it
  guesses; verify before deleting. Dynamic dispatch (`getattr`, plugin
  registries) will produce false positives.
- **`cppcheck --enable=all`** — includes `unusedFunction`. The pre-commit hook
  suppresses that one rule because per-file invocation cannot see cross-TU
  callers and it false-positives constantly. Run cppcheck over the whole `src/`
  tree without the suppression to use it properly.
- **`cargo machete`** — unused `Cargo.toml` deps. `cargo-udeps` is more precise
  but needs nightly, so it is not installed.
- **Roslyn IDE0051/IDE0052** — unused C# private members, via
  `EnforceCodeStyleInBuild` in `Directory.Build.props`.

## Deliberate loosenings

Places where "strictest" is the wrong call, and why:

- **`skipLibCheck: true`** (tsconfig) — type-checking every `.d.ts` in
  `node_modules` is slow and fails on third-party bugs you cannot fix.
- **`disallow_any_explicit = false`** (mypy) — banning explicit `Any` forces
  `object` + casts through JSON and `**kwargs` plumbing; reads worse than the
  problem it solves.
- **`-cppcoreguidelines-avoid-magic-numbers`** (clang-tidy) — too noisy to gate
  on. Enable per-project once the codebase is clean.
- **`CS1591` in `NoWarn`** (C#) — an XML doc comment on every public member is
  busywork. Doc generation stays on so other doc warnings still fire.
- **`multiple_crate_versions = "allow"`** (clippy) — you rarely control
  transitive duplicate versions.
- **`PSUseShouldProcessForStateChangingFunctions`** excluded — fires on any
  `Get-`/`Set-`/`New-` function regardless of actual side effects.

Each is a single-line revert in its config file.

## Gotchas

- **`eslint.config.mjs`, not `.js`.** The config is ESM. Naming it `.js` only
  works when `package.json` has `"type": "module"`; otherwise ESLint dies with
  `SyntaxError: Cannot use import statement outside a module`.
- **`--max-warnings=0`** is what turns ESLint and stylelint into gates. Without
  it, warnings exit 0 and CI passes over them.
- **`EnforceCodeStyleInBuild`** is what makes `dotnet format` rules fail a
  build. Without it, `IDExxxx` diagnostics only show in the IDE.
- **`-EnableExit`** is what makes PSScriptAnalyzer fail a build.
- **Clippy lint *levels* go in `Cargo.toml`, not `clippy.toml`.** `clippy.toml`
  only tunes thresholds. See `rust/clippy-strict.toml` — it holds both halves.
- **gitleaks allowlists well-known example keys** (e.g.
  `AKIAIOSFODNN7EXAMPLE`). A clean run does not prove the scanner is off.

### Gates that load cleanly and check nothing

Found by deliberately breaking things. Each of these looked configured.

- **`knip.jsonc`, not `knip.json`.** knip 6 validates its config strictly and
  rejects unknown keys, so the `"//": [ ... ]` pseudo-comment convention that
  works in knip 5 is a hard error: `Invalid input (unrecognized_keys: //,
  //rules)`. knip 6 also dropped the `classMembers` rule.
- **`import-x/no-cycle` does not fire.** Against a deliberately circular pair of
  modules it reported nothing, while `import-x/no-self-import` and
  `import-x/no-unresolved` correctly flagged their cases in the same run — so
  the plugin and resolver were both working and that one rule was not. knip 6's
  `cycles` rule was equally silent, by default and under `--include cycles`.
  Use **`dpdm`**, which was verified in both directions:
  `dpdm --no-warning --no-tree --exit-code circular:1 src/main.ts`
- **`madge` cannot be installed alongside TypeScript 6+.** It declares
  `peerOptional typescript@^5.4.4`. npm will suggest `--legacy-peer-deps`;
  taking it means accepting a resolution npm has just called incorrect.
- **`maxDepth: Infinity`** in any JSON-serialised rule option becomes `null`,
  which can silently disable traversal. Use a finite number.

### TypeScript 7 has no type-aware linting yet

As of 2026-07-26, `typescript` latest is **7.0.2** but every published
`typescript-eslint` — including canary — declares
`peerDependencies.typescript: ">=4.8.4 <6.1.0"`.

Installing TypeScript 7 therefore means **no type-aware linting at all**: no
`no-floating-promises`, no `no-misused-promises`, no `await-thenable`, none of
the `no-unsafe-*` family. Those rules need the type checker and cannot be
approximated syntactically, and they are the most valuable half of
`strictTypeChecked`.

Pin `typescript@6.0.3` — the highest stable release inside the supported range —
until `typescript-eslint` ships TypeScript 7 support. Check before assuming this
is still true:

```bash
npm info typescript-eslint peerDependencies
```

### Prettier conflicts to disable, not fight

`unicorn/number-literal-case` wants uppercase hex digits; Prettier rewrites them
to lowercase. With both enabled, `format` and `lint` can never both pass. The
formatter owns formatting — disable the lint rule.

`unicorn/prefer-global-this` produces a hard type error in browser-only code:
TypeScript types `window` as `Window & typeof globalThis`, while bare
`globalThis` lacks the Window members, so obeying the rule yields
`TS2345: ... Property 'name' is missing`. Disable it rather than reaching for a
cast.
- ESLint/stylelint plugin packages are installed **globally** here so the
  templates work anywhere. Projects with CI should still add them as local
  devDependencies — global installs are not reproducible on another machine.
