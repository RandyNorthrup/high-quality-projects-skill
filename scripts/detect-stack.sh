#!/usr/bin/env bash
# detect-stack.sh — inventory a workspace before changing anything.
#
# Emits JSON on stdout describing which languages are present, which quality
# tools are already configured, and which of the required tools are installed
# on this machine. Both skills run this FIRST so they extend what exists
# instead of overwriting it.
#
#   ./detect-stack.sh [path]     default: cwd
#
# Exit codes: 0 always (a scan finding nothing is not an error).

set -uo pipefail
ROOT="${1:-.}"
cd "$ROOT" 2>/dev/null || { echo '{"error":"unreadable path"}'; exit 0; }

# ── helpers ─────────────────────────────────────────────────────────────
# Count files by extension, excluding vendor/build dirs. Uses -print -quit
# style short-circuit via head so huge trees stay fast.
PRUNE=(-name node_modules -o -name .git -o -name dist -o -name build
       -o -name target -o -name vendor -o -name .venv -o -name venv
       -o -name __pycache__ -o -name bin -o -name obj)

count_ext() {
    find . \( "${PRUNE[@]}" \) -prune -o -type f -name "$1" -print 2>/dev/null | head -5000 | wc -l
}
has_file() { [ -e "$1" ] && echo true || echo false; }
has_tool() { command -v "$1" >/dev/null 2>&1 && echo true || echo false; }

# ── language detection by source-file count ─────────────────────────────
py=$(count_ext '*.py')
ts=$(( $(count_ext '*.ts') + $(count_ext '*.tsx') ))
js=$(( $(count_ext '*.js') + $(count_ext '*.jsx') + $(count_ext '*.mjs') ))
rs=$(count_ext '*.rs')
cs=$(count_ext '*.cs')
cpp=$(( $(count_ext '*.cpp') + $(count_ext '*.cc') + $(count_ext '*.cxx') + $(count_ext '*.hpp') + $(count_ext '*.h') ))
ps=$(( $(count_ext '*.ps1') + $(count_ext '*.psm1') ))
css=$(( $(count_ext '*.css') + $(count_ext '*.scss') ))
html=$(count_ext '*.html')
sh=$(count_ext '*.sh')
go=$(count_ext '*.go')

# ── existing quality config (the "do not clobber" list) ─────────────────
cat <<JSON
{
  "root": "$(pwd)",
  "git": {
    "is_repo": $(has_file .git),
    "has_remote": $(git remote 2>/dev/null | grep -q . && echo true || echo false),
    "tracked_files": $(git ls-files 2>/dev/null | wc -l)
  },
  "languages": {
    "python": $py,
    "typescript": $ts,
    "javascript": $js,
    "rust": $rs,
    "csharp": $cs,
    "cpp": $cpp,
    "powershell": $ps,
    "css": $css,
    "html": $html,
    "shell": $sh,
    "go": $go
  },
  "existing_config": {
    "pyproject_toml":        $(has_file pyproject.toml),
    "ruff_toml":             $(has_file ruff.toml),
    "setup_cfg":             $(has_file setup.cfg),
    "mypy_ini":              $(has_file mypy.ini),
    "tox_ini":               $(has_file tox.ini),
    "package_json":          $(has_file package.json),
    "tsconfig_json":         $(has_file tsconfig.json),
    "eslint_config_mjs":     $(has_file eslint.config.mjs),
    "eslint_config_js":      $(has_file eslint.config.js),
    "eslintrc_json":         $(has_file .eslintrc.json),
    "eslintrc_cjs":          $(has_file .eslintrc.cjs),
    "prettierrc":            $(has_file .prettierrc),
    "stylelintrc_json":      $(has_file .stylelintrc.json),
    "knip_json":             $(has_file knip.json),
    "cargo_toml":            $(has_file Cargo.toml),
    "clippy_toml":           $(has_file clippy.toml),
    "deny_toml":             $(has_file deny.toml),
    "rustfmt_toml":          $(has_file rustfmt.toml),
    "clang_tidy":            $(has_file .clang-tidy),
    "clang_format":          $(has_file .clang-format),
    "cmakelists":            $(has_file CMakeLists.txt),
    "directory_build_props": $(has_file Directory.Build.props),
    "editorconfig":          $(has_file .editorconfig),
    "psscriptanalyzer":      $(has_file PSScriptAnalyzerSettings.psd1),
    "pre_commit":            $(has_file .pre-commit-config.yaml),
    "gitignore":             $(has_file .gitignore),
    "gitattributes":         $(has_file .gitattributes),
    "env_example":           $(has_file .env.example),
    "dockerfile":            $(has_file Dockerfile),
    "github_workflows":      $(has_file .github/workflows),
    "readme":                $(has_file README.md),
    "changelog":             $(has_file CHANGELOG.md),
    "plan":                  $(has_file PLAN.md),
    "license":               $(has_file LICENSE),
    "agents_md":             $(has_file AGENTS.md),
    "claude_md":             $(has_file CLAUDE.md)
  },
  "tools_installed": {
    "ruff":          $(has_tool ruff),
    "mypy":          $(has_tool mypy),
    "vulture":       $(has_tool vulture),
    "bandit":        $(has_tool bandit),
    "pip_audit":     $(has_tool pip-audit),
    "deptry":        $(has_tool deptry),
    "pytest":        $(has_tool pytest),
    "semgrep":       $(has_tool semgrep),
    "node":          $(has_tool node),
    "npm":           $(has_tool npm),
    "tsc":           $(has_tool tsc),
    "eslint":        $(has_tool eslint),
    "prettier":      $(has_tool prettier),
    "stylelint":     $(has_tool stylelint),
    "knip":          $(has_tool knip),
    "htmlhint":      $(has_tool htmlhint),
    "jscpd":         $(has_tool jscpd),
    "madge":         $(has_tool madge),
    "cargo":         $(has_tool cargo),
    "cargo_audit":   $(has_tool cargo-audit),
    "cargo_machete": $(has_tool cargo-machete),
    "cargo_deny":    $(has_tool cargo-deny),
    "dotnet":        $(has_tool dotnet),
    "roslynator":    $(has_tool roslynator),
    "gcc":           $(has_tool gcc),
    "clang":         $(has_tool clang),
    "clang_tidy":    $(has_tool clang-tidy),
    "clang_format":  $(has_tool clang-format),
    "cppcheck":      $(has_tool cppcheck),
    "valgrind":      $(has_tool valgrind),
    "gcovr":         $(has_tool gcovr),
    "pwsh":          $(has_tool pwsh),
    "shellcheck":    $(has_tool shellcheck),
    "shfmt":         $(has_tool shfmt),
    "gitleaks":      $(has_tool gitleaks),
    "pre_commit":    $(has_tool pre-commit)
  }
}
JSON
