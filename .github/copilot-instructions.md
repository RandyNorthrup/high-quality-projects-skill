# Copilot instructions

This repository provides two vendor-neutral workflows for holding a codebase to
production standards.

- **Setting up a new project** → follow `skills/project_setup/SKILL.md`
- **Applying standards to existing code** → follow `skills/quality_retrofit/SKILL.md`

Read the whole workflow file before acting on it. Both begin with a mandatory
read-only scan (`scripts/detect-stack.ps1` on PowerShell or
`scripts/detect-stack.sh` on POSIX) that must run before anything is created or
modified, and both extend existing configuration rather than replacing it.

Paths inside those files are written `${SKILL_ROOT}/...`, meaning this
repository's root. Resolve it with `& '.\scripts\skill-root.ps1'` on
PowerShell or `bash scripts/skill-root.sh` on POSIX.

The full contract, including the rules that are most often skipped, is in
[`AGENTS.md`](../AGENTS.md).
