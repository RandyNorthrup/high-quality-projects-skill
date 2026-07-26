# Repository metadata

The GitHub description and topics that make this findable. Apply with `gh`
after the repo exists, or paste into the repo settings page.

## Description

GitHub truncates around 350 characters and indexes this text for search, so it
leads with the searchable nouns rather than a tagline.

```
Two Claude Code skills for production-grade code standards: /project_setup scaffolds new projects with strict linting, type checking, dead-code detection and sanitizers; /quality_retrofit brings existing codebases into compliance in reviewable phases. Python, TypeScript, Rust, C++, C#, PowerShell, Shell.
```

## Topics

GitHub allows up to 20. Lowercase, hyphen-separated. These mix three groups:
how people find Claude Code plugins, what problem they are searching for, and
the specific tool names they might search by.

```
claude-code
claude-code-plugin
claude-code-skill
code-quality
quality-gates
static-analysis
linting
dead-code
code-standards
technical-debt
refactoring
pre-commit
sanitizers
addresssanitizer
eslint
ruff
clang-tidy
clippy
developer-tools
ai-coding-assistant
```

## Apply

```bash
gh repo edit RandyNorthrup/high-quality-projects-skill \
  --description "Two Claude Code skills for production-grade code standards: /project_setup scaffolds new projects with strict linting, type checking, dead-code detection and sanitizers; /quality_retrofit brings existing codebases into compliance in reviewable phases. Python, TypeScript, Rust, C++, C#, PowerShell, Shell." \
  --homepage "https://github.com/RandyNorthrup/high-quality-projects-skill" \
  --add-topic claude-code \
  --add-topic claude-code-plugin \
  --add-topic claude-code-skill \
  --add-topic code-quality \
  --add-topic quality-gates \
  --add-topic static-analysis \
  --add-topic linting \
  --add-topic dead-code \
  --add-topic code-standards \
  --add-topic technical-debt \
  --add-topic refactoring \
  --add-topic pre-commit \
  --add-topic sanitizers \
  --add-topic addresssanitizer \
  --add-topic eslint \
  --add-topic ruff \
  --add-topic clang-tidy \
  --add-topic clippy \
  --add-topic developer-tools \
  --add-topic ai-coding-assistant
```

## Also worth setting

- **Releases** — tag `v0.1.0` so the plugin can be pinned to a version rather
  than tracking `main`.
- **Social preview image** — repos with one get noticeably more clicks from
  search and social embeds.
- **Issues enabled**, Wiki and Projects disabled unless used. An enabled-but-
  empty wiki tab reads as abandoned.
