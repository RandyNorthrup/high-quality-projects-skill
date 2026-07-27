# Contributing

## Layout

```
AGENTS.md                     universal entry point — any agent starts here
.cursor/rules/                Cursor auto-discovery, points at AGENTS.md
.github/copilot-instructions.md  Copilot auto-discovery, same
.claude-plugin/               Claude Code manifests — packaging only
skills/
  project_setup/    SKILL.md — new-project scaffolding
  quality_retrofit/ SKILL.md — existing-codebase compliance
scripts/
  skill-root.sh     resolves SKILL_ROOT from anywhere, no env needed
  detect-stack.sh   workspace inventory, emits JSON
  verify-format-safe.py  AST comparison, proves a reformat was neutral
templates/          strict configs, copied into target projects
docs/               philosophy and extended reference
```

**The workflows are vendor-neutral; only the packaging is not.** The two
`SKILL.md` files are plain Markdown that any agent can follow. Keep them that
way — no vendor-set environment variables, no assumptions about slash commands
or a particular runner.

`skills/` and the underscore directory names exist because Claude Code requires
that layout, and because the directory name becomes the slash command. The
`name:` in each `SKILL.md` frontmatter must match its directory exactly or the
plugin will not load. This is the one place a vendor constraint shows through.

Paths inside the workflows use `${SKILL_ROOT}`, resolved by
`scripts/skill-root.sh`, which locates itself. Never reintroduce
`${CLAUDE_PLUGIN_ROOT}` in a workflow file — it is unset for every other agent,
so the path silently becomes `/scripts/...` and the command fails or, worse,
reads the wrong file.

The three auto-discovery files (`AGENTS.md`, `.cursor/rules/`,
`.github/copilot-instructions.md`) are thin pointers on purpose. Put content in
the workflow files, not in the pointers, so it cannot drift between them.

## Editing a skill

`SKILL.md` is a prompt, not documentation. It is read by a model that will act
on it, so:

- **Be imperative.** "Run X, then Y" beats "X should be run."
- **Give the reason with the rule.** A model that knows *why* ASan and TSan
  cannot be combined will handle a case you did not anticipate. One that only
  knows the rule will not.
- **Show the failure.** "Without `-fno-sanitize-recover=all`, UBSan prints and
  the job still exits 0" is worth more than "use `-fno-sanitize-recover=all`."
- **Keep the refusals explicit.** The "Refuse to" section in
  `quality_retrofit` is load-bearing — it is what stops the skill deleting code
  it has not verified.

Skills cost context every time they load. New content should earn its tokens:
prefer a sentence that changes behavior over a paragraph that restates a
default.

## Editing a template

Every rule that is **off** needs a comment saying why, right next to it. A
future reader must be able to tell "deliberately disabled, here's the tradeoff"
from "nobody thought about this."

Before committing a template change, run its gate against deliberately broken
code and confirm it still fires. A config that silently stops catching things is
worse than no config — see the false-green argument in
[`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md).

## Editing detect-stack.sh

It must:

- Exit 0 always. A scan that finds nothing is not an error.
- Emit valid JSON on stdout, unconditionally. Both skills parse it.
- Never write anything. It is a read-only inventory.
- Stay fast on large trees — prune `node_modules`, `target`, `.git`, `venv`.

Test with:

```bash
./scripts/detect-stack.sh . | jq -e . >/dev/null && echo ok
```

## Testing changes locally

```bash
claude plugin marketplace add ~/path/to/high-quality-projects-skill
claude plugin install high-quality-projects-skill@high-quality-projects-skill
# restart Claude Code — skills load at session start
claude plugin list
```

Then exercise both skills against real repositories: one empty directory for
`/project_setup`, one messy existing codebase for `/quality_retrofit`. Reading
the skill is not testing it.

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
`./scripts/detect-stack.sh` in the affected workspace.
