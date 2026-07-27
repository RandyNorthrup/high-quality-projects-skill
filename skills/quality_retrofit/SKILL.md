---
name: quality_retrofit
description: Scan an existing codebase and bring it into compliance with strict quality standards — style, formatting, linting, type checking, dead-code removal, magic-number and literal extraction, sanitizer wiring, secret scanning, and CI-ready gates. Extends existing configuration rather than replacing it, and lands changes in reviewable phases with tests green between each. Use when the user says "retrofit", "clean up this codebase", "add quality gates", "enforce standards", "fix lint", "remove dead code", or runs /quality_retrofit. For a brand-new project with no source files, use project_setup instead.
---

# Quality retrofit — bring an existing codebase into compliance

Take a working codebase and raise it to strict standards without breaking it.

The hard constraint that shapes everything below: **this code already works and
someone depends on it.** A retrofit that lands 4,000 mechanical changes in one
commit is unreviewable and will be reverted. Phase the work.

## Communication style

Status updates: short, direct, no filler. Caveman style if that plugin is
active. Never compress code comments, documentation, findings rationale, or
risk notes.

## Locating this package

Paths below are written `${SKILL_ROOT}/...` — the directory holding this
package's `scripts/` and `templates/`. Resolve it once, first:

```bash
SKILL_ROOT="$(bash /path/to/high-quality-projects-skill/scripts/skill-root.sh)"
```

`skill-root.sh` locates itself, so it works from a plain clone, a vendored copy,
or a submodule with no environment set at all. It honours an exported
`$SKILL_ROOT`, and `$CLAUDE_PLUGIN_ROOT` when running under Claude Code.

Nothing here is specific to one vendor. If your agent cannot run shell commands,
read the files directly out of the repository — the templates are plain config
files and the phases below are plain instructions.

## Rule zero: scan, report, then ask

```bash
"${SKILL_ROOT}/scripts/detect-stack.sh" .
```

Returns languages present, existing config, and installed tools. **Do not
change anything yet.** Report:

- Languages found, by file count
- Quality config that already exists
- Required tools that are missing from this machine
- Estimated blast radius: how many findings, in how many files. Run the
  strict template against the tree to get a real number — do not guess

Then get agreement on scope before writing. A retrofit that surprises someone
is a failed retrofit.

### Extend, never replace

For every config file that already exists:

1. Read it.
2. Keep every rule the project already chose — those choices encode knowledge
   you do not have.
3. Add missing strictness on top.
4. Where the existing config and the strict template genuinely conflict, keep
   the project's and note the divergence in the report.

Copy a template wholesale **only** when no config of that type exists. Templates
live in `${SKILL_ROOT}/templates/`.

Special cases:

- `pyproject.toml` already has `[tool.ruff]` → merge into that table. Do not add
  a competing `ruff.toml`; both existing means the standalone file wins and the
  project's settings silently stop applying.
- `.eslintrc.*` (legacy) present → migrating to flat config is a breaking change
  for their editor setup. Ask first.
- `eslint.config.js` present and ESM → leave the name alone. Only use `.mjs` for
  a file you are creating.

## Safety rails

Before the first modification:

```bash
git status --porcelain     # must be clean, or stop and ask
git rev-parse HEAD         # record for rollback
```

- **Never retrofit a dirty working tree.** Uncommitted work will be tangled
  with mechanical changes and become impossible to separate.
- **Not a git repo** → offer `git init` and an initial commit first. Refuse to
  bulk-modify unversioned code.
- Establish the test baseline **before** touching anything. If tests already
  fail, record which ones. You cannot tell what you broke otherwise.
- One phase per commit. Each commit passes the gates that existed before it.
- **A green test suite is not evidence that the tests check anything.** An
  inherited suite can contain assertions that cannot fail. One found this way:
  a test pressed the arrow keys and asserted the page had not scrolled — but the
  layout fitted the viewport, so the page could never scroll, and it passed just
  as happily against a build with the `preventDefault` call deleted. When a test
  guards behaviour you are about to touch, break that behaviour on purpose once
  and confirm the test goes red before trusting it.

## Phases

Run in order. Each is independently reviewable and independently revertible.
Stop and report between phases; do not chain them silently.

### Phase 0 — baseline
Record: test results, build status, current lint/type error counts. This is the
number every later phase is measured against. Write it into the report.

### Phase 1 — formatting (zero-risk, huge diff)
`prettier` · `ruff format` · `rustfmt` · `clang-format` · `dotnet format` ·
`shfmt`

Layout only — no behaviour change. Land it as **one isolated commit**.

**Prove it before committing.** "Formatting is safe" is an assumption, not a
fact, and a byte-diff cannot check it: `ruff format` and `black` also add magic
trailing commas and normalize quotes, so the file legitimately changes beyond
whitespace. Comparing the parsed AST is the correct test — it ignores layout
entirely and fails only if something behavioural moved:

```bash
cp target.py /tmp/before.py
ruff format target.py
"${SKILL_ROOT}/scripts/verify-format-safe.py" /tmp/before.py target.py
```

Exit 0 means semantically identical. **This tool belongs to phase 1 only** —
phases 3 onward change the AST on purpose (removing an unused import deletes a
node), so a difference there is expected, not a failure.

For non-Python stacks the equivalent is a token-stream or AST diff; where no
such tool exists, at minimum re-run the test suite and read the diff.

Then add the commit to `.git-blame-ignore-revs`:

```bash
git rev-parse HEAD >> .git-blame-ignore-revs
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Without that file, this commit destroys `git blame` for the whole repo. This
step is not optional.

### Phase 2 — config and gates (no code change)
Install or extend the strict configs. Wire the gate scripts. Add pre-commit.
Add CI workflow. Nothing under `src/` changes in this phase.

At the end, run every gate and **record the failure counts**. Those counts are
the work list for phases 3–6.

### Phase 3 — autofixable lint
`ruff check --fix` · `eslint --fix` · `cargo clippy --fix` · `stylelint --fix` ·
`dotnet format`

Machine-applied only. After the run:

- Tests must still pass.
- **Read the diff.** `--fix` is not always semantically neutral —
  `no-unused-vars` autofix can delete a call whose side effect mattered.

### Phase 4 — types
Turn on strict type checking, then fix the fallout. Highest-value flags, and
also the loudest:

- TypeScript: `strict`, then `noUncheckedIndexedAccess` — the latter is not part
  of `strict` and typically produces the largest error count. It is also the one
  that finds real bugs.
- Python: `mypy --strict`, then the extra flags in the template.
- C#: `<Nullable>enable</Nullable>` with `<TreatWarningsAsErrors>`.

If the error count is in the hundreds, do **not** fix them all in one commit.
Enable per-directory or per-file and work inward. Every `any`, `# type: ignore`,
or `!` you add to make it compile is a debt entry — record it in the report.

### Phase 5 — dead code
Each tool sees something the others structurally cannot:

- `knip --strict` — unused files, exports, and dependencies (whole-graph)
- `tsc --noEmit` with `noUnusedLocals` — unused symbols within a file
- `vulture` — Python, heuristic
- `cppcheck --enable=all` — includes `unusedFunction`
- `cargo machete` — unused Cargo deps
- Roslyn `IDE0051`/`IDE0052` — unused C# private members
- `dpdm --no-warning --no-tree --exit-code circular:1 <entry>` — import cycles

**Confirm the tool fires before trusting a clean run.** A dead-code tool that
reports nothing is indistinguishable from one that is misconfigured, and the
failure is silent by construction. Add an unused export, confirm the tool
catches it, then remove it.

Three that were found reporting nothing while appearing configured:
`import-x/no-cycle`, knip 6's `cycles` rule (both silent against a deliberately
circular pair of modules), and `madge`, which cannot install alongside
TypeScript 6+ at all because it declares `peerOptional typescript@^5.4.4`. Use
`dpdm` for cycles; it was verified to exit 1 on a real cycle and 0 once removed.

Note also that knip 6 rejects unknown config keys, so a knip 5 config using the
`"//": [...]` comment convention fails to load outright — rename to
`knip.jsonc` and use real comments.

**Coverage can find dead code the dead-code tools miss.** A branch a coverage
threshold flags as unreachable may genuinely be unreachable. Work out whether it
can ever execute; if it cannot, delete it rather than lowering the threshold.

**Verify every deletion before making it.** These tools produce false positives
on:

- dynamic dispatch — `getattr`, reflection, DI containers, plugin registries
- string-keyed lookup — route tables, event maps, serializer registries
- public API of a library — "unused" internally is the entire point
- test-only helpers, fixtures, conftest
- entry points invoked by a framework, not by your code

Grep for the symbol name across the whole repo, including config, templates, and
docs, before deleting. When in doubt, list it in the report rather than removing
it.

### Phase 6 — magic numbers and literals
The judgment-heavy phase. Extract unexplained literals into named constants,
enums, literal unions, or schema-validated config.

**Extract:**
```
setTimeout(fn, 86400000)          → const CACHE_TTL_MS = 24 * 60 * 60 * 1000
if (status === 3)                 → if (status === OrderStatus.Shipped)
retry(5)                          → const MAX_RETRIES = 5
if (role === "adm")               → if (role === Role.Admin)
buffer[1024]                      → constexpr size_t kBufferSize = 1024
```

**Leave alone** — extracting these makes code worse:
```
if (xs.length === 0)      i = 0, i++, i - 1      return []      x * 2
arr[0]                    if (flag)              ""             .5 in a midpoint
HTTP 200/404 in a switch that reads as status codes
```

The test: does the name add information the value lacks? `const TWO = 2` adds
nothing. `const RETRY_LIMIT = 2` does.

Do this **per-module with tests green after each**, never as a bulk sweep. This
phase changes behavior if you get a unit wrong — `86400` seconds and
`86400000` milliseconds look alike in a diff.

### Handing the tree to an external reviewer

If a step invokes an outside reviewer (Codex, a SAST service, another agent),
**scope it to specific files or the diff.** Those tools read the filesystem, not
git, so `.gitignore` does not protect them: a `.venv/`, `node_modules/`, or
`target/` you created during the retrofit will be crawled, burning the entire
budget on vendored stubs before it reaches your code.

Delete build and environment directories first, or name the files explicitly:

```bash
rm -rf .venv .mypy_cache .ruff_cache __pycache__
# then scope the request: "review only src/foo.py and the diff A..B"
```

### Phase 7 — security and sanitizers
- `gitleaks detect` over full history. **A hit here is an incident**, not a
  lint finding: the secret is in history, so rotate it first, then scrub.
  Report and stop; do not rewrite history unprompted.
- `semgrep --config=auto`, `bandit`, `npm audit`, `pip-audit`, `cargo audit`
- C/C++/Rust: wire sanitizer CI jobs. ASan+UBSan in one job, TSan in a
  **separate** one — they use incompatible shadow memory and cannot be combined.
  `-fno-sanitize-recover=all` or UBSan prints and continues, and the job still
  exits 0.
- Existing sanitizer findings are real bugs. Report them; do not paper over
  them to make the gate green.

### Phase 8 — documentation reconciliation
Now that the code is known-good, make the docs match it:

- Every command in `README.md` — run it. Fix or delete what fails.
- `CHANGELOG.md` — add a retrofit entry describing what actually changed.
- Create `PLAN.md` if absent, recording remaining debt as tracked items.
- Remove stale claims and obsolete instructions.

## Compliance checklist

Report against this. Mark each **pass / fail / deferred** with a reason — never
silently omit a row.

```
[ ] Formatter clean, whole tree
[ ] Linter clean at max strictness, warnings-as-errors
[ ] Type checker clean at strict (or documented per-file exemptions)
[ ] No dead code (verified, not just tool-reported)
[ ] No unused dependencies
[ ] No magic numbers outside the idiomatic allowlist
[ ] No commented-out legacy code
[ ] No silent fallbacks or placeholder production code
[ ] No unjustified any / ignore / suppression
[ ] Secret scan clean over full history
[ ] Dependency audit clean, or exceptions documented
[ ] Sanitizers wired (native code) and passing
[ ] Tests pass; coverage recorded
[ ] Build succeeds
[ ] Pre-commit installed
[ ] CI workflow runs the same gates as local
[ ] README commands verified working
[ ] CHANGELOG updated
```

## Report format

```
BASELINE     tests X/Y · build ok/fail · lint N · types M
AFTER        tests X/Y · build ok/fail · lint 0 · types 0

PHASE 1 format      1,240 files · whitespace only · blame-ignore added
PHASE 3 lint        312 auto · 47 manual
PHASE 4 types       89 fixed · 6 any added  ← debt, listed below
PHASE 5 dead code   23 removed · 4 kept (dynamic dispatch, listed)
PHASE 6 literals    31 extracted · 12 left as idiomatic
PHASE 7 security    2 findings — see below

DEBT
  src/legacy/parse.ts:88   any — untyped third-party response, no @types
  src/api/handler.ts:142   ts-expect-error — upstream bug, tracked <link>

NOT DONE
  MSan — needs instrumented libc++, not available. Deferred.
  e2e tests — no framework present. Out of scope, flagged.
```

## Refuse to

- Modify a dirty working tree.
- Bulk-modify code that is not under version control.
- Delete code you have not verified is unreachable.
- Rewrite git history to remove a leaked secret without explicit instruction.
- Weaken an existing rule that is already stricter than the template.
- Report a gate as passing when it was skipped, deferred, or its tool is
  missing. A false green is worse than a red.
