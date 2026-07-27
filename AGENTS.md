# AGENTS.md

Entry point for **any** coding agent. `AGENTS.md` is the cross-vendor
convention — Codex, Cursor, Aider, Zed, Jules, Continue, and others read it, and
Claude Code reads it too.

This package holds two workflows and the configuration they install. Nothing in
it is specific to one vendor.

## The two workflows

| Workflow | Read this file | Use when |
|---|---|---|
| **Project setup** | [`skills/project_setup/SKILL.md`](skills/project_setup/SKILL.md) | Starting a new project. Takes a project description. |
| **Quality retrofit** | [`skills/quality_retrofit/SKILL.md`](skills/quality_retrofit/SKILL.md) | An existing codebase needs standards applied. |

They are plain Markdown instructions. Read the whole file before acting on it —
both open with a mandatory scan step that must run before anything is created or
modified.

The directory is named `skills/` because Claude Code requires that layout to
load them as plugin skills. The files themselves are vendor-neutral; the name is
packaging, not a dependency.

## Resolving paths

The instructions refer to `${SKILL_ROOT}/scripts/...` and
`${SKILL_ROOT}/templates/...`. `SKILL_ROOT` is the directory containing this
file. Resolve it with:

```bash
SKILL_ROOT="$(bash /path/to/high-quality-projects-skill/scripts/skill-root.sh)"
```

That script locates itself, so it works from a git clone, a vendored copy, or a
submodule with no environment configured. It honours an exported `$SKILL_ROOT`
first, then `$CLAUDE_PLUGIN_ROOT` (which Claude Code sets automatically), then
falls back to its own location.

If your agent cannot execute shell commands, ignore the variable and read the
files directly — `templates/` is plain configuration and the workflows are plain
instructions.

## What is in here

```
skills/project_setup/SKILL.md     scaffold a new project to strict standards
skills/quality_retrofit/SKILL.md  bring an existing codebase into compliance
scripts/skill-root.sh             resolve SKILL_ROOT from anywhere
scripts/detect-stack.sh           read-only workspace inventory, emits JSON
scripts/verify-format-safe.py     prove a reformat did not change the AST
templates/                        tuned strict configs per language
docs/PHILOSOPHY.md                why the gates are set the way they are
```

## Non-negotiables when using this package

These are the rules the workflows themselves enforce. An agent following them
should not need reminding, but they are the ones most often skipped:

- **Scan before creating.** Both workflows open with `detect-stack.sh`. Never
  overwrite a config file you did not write in this session — read it and extend
  it.
- **A gate is not configured until it has been seen to fail.** Break something
  on purpose, confirm a non-zero exit, revert. Several tools in this package's
  history loaded cleanly and checked nothing.
- **Verify the effect, not the write.** Reading back the value you just wrote
  proves the write worked, not that behaviour changed.
- **Never report a skipped or deferred gate as passing.** Say plainly what was
  not run and why.
- **Do not modify global user or machine configuration.** Project-local only.

## Compatibility

Requires `bash` and standard POSIX tools. `verify-format-safe.py` needs Python 3.
Individual gates need their own tools, and `detect-stack.sh` reports which are
present — it never installs anything and always exits 0.
