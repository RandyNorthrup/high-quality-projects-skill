# Repository metadata

The GitHub description and topics that make this findable. Apply with `gh`
after the repo exists, or paste into the repo settings page.

## Description

Keep the description concise and lead with searchable nouns rather than a
tagline.

```
Two vendor-neutral Markdown workflows for coding agents: scaffold projects or retrofit existing codebases with strict quality-gate guidance. Cross-platform stack detection for PowerShell and Bash; optional Claude Code plugin.
```

## Topics

GitHub allows up to 20. Lowercase, hyphen-separated. These mix three groups:
how people find Claude Code plugins, what problem they are searching for, and
the specific tool names they might search by.

```
claude-code
claude-code-plugin
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
developer-tools
ai-coding-assistant
agents-md
ai-agents
coding-agent
cursor
vendor-neutral
```

## Apply

This one-line form works unchanged in PowerShell and POSIX shells:

```console
gh repo edit RandyNorthrup/high-quality-projects-skill --description "Two vendor-neutral Markdown workflows for coding agents: scaffold projects or retrofit existing codebases with strict quality-gate guidance. Cross-platform stack detection for PowerShell and Bash; optional Claude Code plugin." --homepage "https://github.com/RandyNorthrup/high-quality-projects-skill" --add-topic claude-code --add-topic claude-code-plugin --add-topic code-quality --add-topic quality-gates --add-topic static-analysis --add-topic linting --add-topic dead-code --add-topic code-standards --add-topic technical-debt --add-topic refactoring --add-topic pre-commit --add-topic sanitizers --add-topic developer-tools --add-topic ai-coding-assistant --add-topic agents-md --add-topic ai-agents --add-topic coding-agent --add-topic cursor --add-topic vendor-neutral
```

## Social preview

The tracked upload source is
[`docs/assets/github-social-preview.png`](assets/github-social-preview.png).
It is an opaque 1280×640 PNG under 1 MB, matching GitHub's preferred social
preview dimensions and upload limit.

Git does not apply this setting. Upload the file under **Settings → General →
Social preview → Edit → Upload an image**, then verify the preview before
closing the settings page.

## Also worth setting

- **Version tags** — after publishing, tag the manifest version (currently
  `v0.3.0`) if consumers need an immutable Git reference instead of `main`.
- **Social preview image** — keep the uploaded setting synchronized with the
  tracked source above.
- **Issues enabled**, Wiki and Projects disabled unless used. An enabled-but-
  empty wiki tab reads as abandoned.
