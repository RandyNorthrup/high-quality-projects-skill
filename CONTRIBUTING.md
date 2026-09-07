# Contributing

## Layout

```
AGENTS.md                     universal entry point — any agent starts here
.cursor/rules/                Cursor auto-discovery, points at AGENTS.md
.github/copilot-instructions.md  Copilot auto-discovery, same
.github/workflows/cross-platform.yml  Windows/Linux script regression tests
.github/workflows/release.yml    tag-gated build, attestation, and publication
.claude-plugin/               Claude Code manifests — packaging only
skills/
  project_setup/    SKILL.md — new-project scaffolding
  quality_retrofit/ SKILL.md — existing-codebase compliance
  feature_delivery/ SKILL.md — scoped feature delivery and safe resume
scripts/
  skill-root.ps1/.sh   resolves SKILL_ROOT from anywhere, no env needed
  detect-stack.ps1/.sh workspace inventory, emits JSON
  build-release.ps1     exact-commit archives and release metadata
  verify-format-safe.py  compares Python ASTs before and after formatting
  verify-delivery.py     read-only structural/evidence verification
  update-delivery.py     atomic candidate updates with conflict detection
  delivery/             shared first-party standard-library implementation
templates/          strict configs, copied into target projects
docs/               philosophy and extended reference
```

**The workflows are vendor-neutral; only the packaging is not.** The three
`SKILL.md` files are plain Markdown that any agent can follow. Keep them that
way — no vendor-set environment variables, no assumptions about slash commands
or a particular runner.

`skills/` and the underscore directory names exist because Claude Code requires
that layout, and because the directory name becomes the skill segment of the
plugin's namespaced slash command. The `name:` in each `SKILL.md` frontmatter
must match its directory exactly or the plugin will not load. This is the one
place a vendor constraint shows through.

Paths inside the workflows use `${SKILL_ROOT}` as a placeholder, resolved by the
native `scripts/skill-root.ps1` or `scripts/skill-root.sh`. Both locate
themselves. Never reintroduce `${CLAUDE_PLUGIN_ROOT}` as the only path source in
a workflow file — it is unset for every other agent, so the path silently points
at the wrong place.

The three auto-discovery files (`AGENTS.md`, `.cursor/rules/`,
`.github/copilot-instructions.md`) are thin pointers on purpose. Put content in
the workflow files, not in the pointers, to minimize duplicated text and drift.

## Editing a skill

`SKILL.md` is a prompt, not documentation. It is read by a model that will act
on it, so:

- **Be imperative.** "Run X, then Y" beats "X should be run."
- **Give the reason with the rule.** A model that knows *why* ASan and TSan
  cannot be combined will handle a case you did not anticipate. One that only
  knows the rule will not.
- **Show the failure.** "Without `-fno-sanitize-recover=all`, a recoverable
  UBSan finding can report and continue" is worth more than "use this flag."
- **Keep the refusals explicit.** The "Refuse to" section in
  `quality_retrofit` is load-bearing — it is what stops the skill deleting code
  it has not verified.

Skills cost context every time they load. New content should earn its tokens:
prefer a sentence that changes behavior over a paragraph that restates a
default.

Scan by responsibility before editing, read canonical implementations and their
consumers, and enhance them. Record why any new path cannot reuse existing work;
check for overlap again before completion. Keep the shared red-drill procedure
in `docs/RED-DRILLS.md` and route all workflows to it rather than copying it.
Apply `docs/CODE-QUALITY.md` for the affected languages. Record template canary
commands, versions, intended diagnostics, restoration, and limitations in the
dated `docs/QUALITY-REVIEW.md` when refreshing the guidance.

## Editing a template

Every rule that is **off** needs a comment saying why, right next to it. A
future reader must be able to tell "deliberately disabled, here's the tradeoff"
from "nobody thought about this."

Before committing a template change, run its gate against deliberately broken
code and confirm it still fires. A config that silently stops catching things is
worse than no config — see the false-green argument in
[`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md).

## Editing the detect-stack scripts

Both implementations must return the same JSON contract. Each must:

- Exit 0 always. A scan that finds nothing is not an error.
- Emit valid JSON on stdout, unconditionally. All workflows inspect it.
- Return `{"error":"unreadable path"}` for an invalid root and
  `{"error":"scan failed"}` for an internal inventory failure. Exit 0 is the
  transport contract, not proof that the scan succeeded.
- Never write anything. It is a read-only inventory.
- Stay fast on large trees — prune `node_modules`, `target`, `.git`, `venv`.

Test with:

```bash
./scripts/detect-stack.sh . | jq -e . >/dev/null && echo ok
```

```powershell
& .\scripts\detect-stack.ps1 . | ConvertFrom-Json | Out-Null
& .\tests\cross-platform-smoke.ps1
& .\tests\cross-platform-smoke.ps1 -RedDrills
& .\tests\release-package-smoke.ps1
```

Run the smoke test in both PowerShell 7 and Windows PowerShell 5.1 before
changing the PowerShell scripts. It covers self-location, environment override
precedence, source counts, pruned directories, config detection, and the
unreadable-path JSON contract. GitHub Actions repeats those checks on Windows,
Linux, and macOS, then compares the Bash and PowerShell scanner inventories on
both POSIX runners.

`-RedDrills` reuses the same smoke suite in a temporary copy of current source.
It runs a passing baseline, separately breaks directory pruning, the explicit
root override, and the unreadable-path error, and requires each existing
assertion to fail with a non-zero child exit. Every mutation is restored
byte-for-byte before a fresh green run. The parent command fails on surviving
mutations, wrong failures, timeouts, or failed restoration. CI uses this mode,
which includes the normal suite; run it under both PowerShell 7 and 5.1 locally.

Keep mutation recipes aligned with observable contracts when implementation
changes. A recipe that no longer applies must fail rather than silently skip.
Behavioral drills do not replace exercising the skill on real tasks, and string
checks on prompt wording do not prove an agent will follow the instructions.

The release-package smoke test requires a clean committed tree because it
archives `HEAD`, not uncommitted files. Run it after the release commit. It
builds into ignored `dist/` under conflicting ambient time zones, requires
byte-identical output, checks versioned archive roots, verifies every SHA-256
entry, and removes its test output.

## Testing changes locally

```console
claude plugin marketplace add /absolute/path/to/high-quality-projects-skill
claude plugin install high-quality-projects-skill@high-quality-projects-skill
# in an active Claude Code session, run /reload-plugins (or restart it)
claude plugin list
```

Exercise all three workflows against isolated realistic projects. Follow
[the behavioral protocol](tests/behavioral/README.md): fresh agent trials,
independent product oracles, negative controls, and semantic review of actual
artifacts. Reading a skill or matching its wording is not behavioral testing.

Delivery helpers use Python 3.12+ and the standard library. Before a change:

```console
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m mypy --strict --python-version 3.12 scripts/delivery scripts/verify-delivery.py scripts/update-delivery.py
python -m unittest discover -s tests -p "test_*.py"
```

CI runs these checks on Windows, Linux, and macOS with Python 3.12 and 3.14.
Its two validator mutations reuse existing regression assertions. Outcome-oracle
controls also reject broken behavior, vacuous tests, duplicated domain logic,
premature implementation, and replayed side effects. Live agent trials are
recorded separately; CI does not pretend to rerun a model.

## Releasing

Releases are tag-driven. Never upload a hand-built archive or create a GitHub
Release before its tag workflow.

1. Choose a SemVer version and update `.claude-plugin/plugin.json`.
2. Add the matching top-level `CHANGELOG.md` section, update documented stable
   versions, and update the manifest-version assertion in
   `tests/cross-platform-smoke.ps1`.
3. Commit with a clean tree, then run:

   ```powershell
   $ReleaseVersion = (Get-Content -Raw '.\.claude-plugin\plugin.json' |
       ConvertFrom-Json).version
   & .\tests\cross-platform-smoke.ps1
   & .\tests\release-package-smoke.ps1
   & .\scripts\build-release.ps1 -Version $ReleaseVersion
   ```

4. Push the commit and wait for `Cross-platform package checks` to pass.
5. Create and push annotated tag `v<manifest version>`.

The tag starts `.github/workflows/release.yml`. It reuses all cross-platform
gates, requires exact tag/manifest/changelog agreement, builds ZIP and tar.gz
archives from the tagged Git tree, generates checksums and metadata, creates
GitHub provenance attestations, then publishes the GitHub Release. Verify the
published assets using `docs/INSTALLATION.md` before calling the release done.

## Commits

Conventional Commits. Subject ≤ 50 chars, imperative mood.

```
feat: add Go to detect-stack language table
fix: eslint template must be .mjs, not .js
docs: explain why MSan needs instrumented libc++
```

Update `CHANGELOG.md` in the same commit as the change it describes. Track what
actually happened — never list planned work as done.

## Reporting a bug

Include: the skill invoked, what it did, what you expected, and the output of
`scripts/detect-stack.ps1` on PowerShell or `scripts/detect-stack.sh` on POSIX
in the affected workspace.
