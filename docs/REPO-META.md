# Repository metadata

The GitHub description and topics that make this findable. Apply with `gh`
after the repo exists, or paste into the repo settings page.

## Description

Keep the description concise and lead with searchable nouns rather than a
tagline.

```
Vendor-neutral workflows that grill new project ideas into confirmed, release-ready briefs and retrofit existing codebases with evidence-backed quality gates. Native PowerShell and Bash; optional Claude Code plugin.
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
product-discovery
```

## Apply

This one-line form works unchanged in PowerShell and POSIX shells:

```console
gh repo edit RandyNorthrup/high-quality-projects-skill --description "Vendor-neutral workflows that grill new project ideas into confirmed, release-ready briefs and retrofit existing codebases with evidence-backed quality gates. Native PowerShell and Bash; optional Claude Code plugin." --homepage "https://github.com/RandyNorthrup/high-quality-projects-skill" --add-topic claude-code --add-topic claude-code-plugin --add-topic code-quality --add-topic quality-gates --add-topic static-analysis --add-topic linting --add-topic dead-code --add-topic code-standards --add-topic technical-debt --add-topic refactoring --add-topic pre-commit --add-topic sanitizers --add-topic developer-tools --add-topic ai-coding-assistant --add-topic agents-md --add-topic ai-agents --add-topic coding-agent --add-topic cursor --add-topic vendor-neutral --add-topic product-discovery
```

## Social preview

The tracked upload source is
[`docs/assets/github-social-preview.png`](assets/github-social-preview.png).
It is an opaque 1774×887 PNG (2:1), 1,013,540 bytes. Warm ivory, charcoal, and
restrained copper replace the previous purple/blue artwork. The README uses
this tracked image directly and includes a meaningful text alternative.

Git does not apply this setting. Upload the file under **Settings → General →
Social preview → Edit → Upload an image**, then verify the preview before
closing the settings page.

## Also worth setting

- **Version tags and releases** — pushing an annotated manifest-version tag
  (currently `v0.6.0`) runs the gated release workflow and publishes verified
  archives, checksums, metadata, notes, and build provenance.
- **Social preview image** — keep the uploaded setting synchronized with the
  tracked source above.
- **Issues enabled**, Wiki and Projects disabled unless used. An enabled-but-
  empty wiki tab reads as abandoned.
