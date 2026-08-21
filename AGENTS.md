# AGENTS.md

Entry point for coding agents that support `AGENTS.md`, or for any agent
explicitly directed to this file.

This package holds two vendor-neutral workflows and the configuration they
install. The Claude Code, Cursor, and Copilot files are optional packaging and
discovery adapters around that shared content.

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

The instructions use `${SKILL_ROOT}/...` as a placeholder for this package's
root. Resolve it with the script for the active shell. On Windows PowerShell:

```powershell
$SkillRoot = & 'C:\path\to\high-quality-projects-skill\scripts\skill-root.ps1'
```

On Linux, macOS, or another POSIX environment:

```bash
SKILL_ROOT="$(bash /path/to/high-quality-projects-skill/scripts/skill-root.sh)"
```

Both scripts locate themselves, so they work from a git clone, a vendored copy,
or a submodule with no environment configured. They honour `SKILL_ROOT` first,
then `CLAUDE_PLUGIN_ROOT` (which Claude Code sets automatically), then fall back
to their own location. Do not invoke Windows `bash.exe`: it can be a WSL relay
even when no Linux distribution or `/bin/bash` exists.

If your agent cannot execute shell commands, ignore the variable and read the
files directly — `templates/` is plain configuration and the workflows are plain
instructions.

## What is in here

```
skills/project_setup/SKILL.md     scaffold a new project to strict standards
skills/quality_retrofit/SKILL.md  bring an existing codebase into compliance
scripts/skill-root.{ps1,sh}       resolve SKILL_ROOT from anywhere
scripts/detect-stack.{ps1,sh}     read-only workspace inventory, emits JSON
scripts/verify-format-safe.py     compare Python ASTs before and after formatting
templates/                        tuned strict configs per language
docs/PHILOSOPHY.md                why the gates are set the way they are
```

## Non-negotiables when using this package

These are the rules the workflows themselves enforce. An agent following them
should not need reminding, but they are the ones most often skipped:

- **Scan before creating.** Both workflows open with the native
  `detect-stack.ps1` or `detect-stack.sh`. Never overwrite a config file you did
  not write in this session — read it and extend it.
- **A gate is not configured until it has been seen to fail.** Break something
  on purpose, confirm a non-zero exit, revert. Several tools in this package's
  history loaded cleanly and checked nothing.
- **Verify the effect, not the write.** Reading back the value you just wrote
  proves the write worked, not that behaviour changed.
- **Never report a skipped or deferred gate as passing.** Say plainly what was
  not run and why.
- **Do not modify global user or machine configuration.** Project-local only.

## Compatibility

Requires PowerShell 5.1 or newer on Windows, or Bash and standard POSIX tools on
Linux and macOS. Bash is not required on Windows. `verify-format-safe.py` needs
Python 3. Individual gates need their own tools, and the native `detect-stack`
script reports which are present — it never installs anything and always exits
0.

Always inspect the returned JSON for an `error` property. Exit 0 means the
scanner returned its JSON contract; it does not turn `unreadable path` or
`scan failed` into a successful inventory.

Python tools are detected by importability, not by `PATH`, because an
unactivated venv or a Windows install leaves them runnable as
`python -m <module>` with no console script anywhere. The scan names the
interpreter it verified in `python_runtime.bin` and lists the tools that need
that form in `python_runtime.module_only_tools`. Use it: calling those by bare
name fails, and the failure looks like a missing tool rather than a wrong
invocation.
