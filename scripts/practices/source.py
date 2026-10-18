"""Walk owned project files, classify them, and read allowances from comments only."""

import contextlib
import io
import os
import re
import tokenize
from dataclasses import dataclass
from pathlib import Path

from .masking import C_FAMILY, SCRIPT, Dialect, Masked, mask

# Generated, vendored, and environment trees, matched case-insensitively like
# the package's stack scanners. A nested Git repository is pruned as well: it
# is a separate codebase, such as a pinned checkout of this package in CI.
PRUNED_DIRECTORIES = frozenset(
    {
        "node_modules",
        ".git",
        "dist",
        "build",
        "target",
        "vendor",
        ".venv",
        "venv",
        "__pycache__",
        "bin",
        "obj",
    }
)
SCRIPT_SUFFIXES = frozenset({".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts"})
C_FAMILY_SUFFIXES = {
    ".rs": "rust",
    ".go": "go",
    ".cs": "csharp",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
}
POWERSHELL_SUFFIXES = frozenset({".ps1", ".psm1"})
# Bats files are shell test suites.
SHELL_SUFFIXES = frozenset({".sh", ".bash", ".zsh", ".ksh", ".bats"})
TEST_DIRECTORIES = frozenset({"test", "tests", "__tests__", "spec", "specs", "e2e"})
TEST_FILE = re.compile(
    r"^(?:test_.+\.py|.+_test\.(?:py|go)|.+\.(?:test|spec)\.[cm]?[jt]sx?"
    r"|.+\.tests\.ps1|.+tests?\.(?:cs|java|kt)|.+\.bats)$",
    re.IGNORECASE,
)
QUOTES = frozenset("'\"")
# Characters after which a quote begins a value: a key, an assignment, a list.
QUOTE_OPENERS = frozenset(":=[{(,")
ALLOWANCE = re.compile(
    r"verify-practices:\s*allow\s+(?P<check>[a-z][a-z-]*)"
    r"(?:\s+--\s*(?P<reason>.*?))?\s*(?:\*/|#>)?\s*$"
)


@dataclass(frozen=True)
class SourceFile:
    """Identify one owned file and how the checks should read it."""

    path: Path
    relative: str
    language: str
    is_test: bool


@dataclass(frozen=True)
class Allowance:
    """Record one reviewed exception written in a comment."""

    relative: str
    line: int
    check: str
    reason: str


def owned_files(root: Path) -> list[tuple[Path, str]]:
    """List files under the root, pruning generated trees and nested repositories."""
    found: list[tuple[Path, str]] = []
    for directory, subdirectories, files in os.walk(root):
        current = Path(directory)
        subdirectories[:] = sorted(
            name
            for name in subdirectories
            if name.lower() not in PRUNED_DIRECTORIES and not (current / name / ".git").exists()
        )
        found.extend(
            (current / name, (current / name).relative_to(root).as_posix())
            for name in sorted(files)
        )
    return found


def language_of(path: Path) -> str | None:
    """Name the analysis family for a source file, or None for non-code files."""
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in SCRIPT_SUFFIXES:
        return "script"
    if suffix in POWERSHELL_SUFFIXES:
        return "powershell"
    if suffix in SHELL_SUFFIXES:
        return "shell"
    return C_FAMILY_SUFFIXES.get(suffix)


def is_test_path(relative: str) -> bool:
    """Recognize test code by directory or by the common test file names."""
    parts = relative.split("/")
    return any(part.lower() in TEST_DIRECTORIES for part in parts[:-1]) or bool(
        TEST_FILE.match(parts[-1])
    )


def source_files(files: list[tuple[Path, str]]) -> list[SourceFile]:
    """Select code files and classify each as test or product code."""
    selected = []
    for path, relative in files:
        language = language_of(path)
        if language:
            selected.append(SourceFile(path, relative, language, is_test_path(relative)))
    return selected


def read_text(path: Path) -> str:
    """Read source text; undecodable bytes are replaced so patterns still apply."""
    return path.read_bytes().decode("utf-8-sig", errors="replace")


def dialect_of(language: str) -> Dialect:
    """Return the literal grammar used to mask a language family."""
    return SCRIPT if language == "script" else C_FAMILY


def masked_source(source: SourceFile) -> Masked:
    """Mask a JavaScript-family or C-family source file."""
    return mask(read_text(source.path), dialect_of(source.language))


def parse_allowance(relative: str, line: int, comment: str) -> Allowance | None:
    """Extract an allowance from one comment, keeping an empty reason visible."""
    match = ALLOWANCE.search(comment)
    if not match:
        return None
    return Allowance(relative, line, match["check"], (match["reason"] or "").strip())


def python_comments(text: str) -> list[tuple[int, str]]:
    """Return Python comments by line, ignoring text inside strings."""
    # An unparsable file is reported by the syntax check; it has no trustworthy comments.
    with contextlib.suppress(tokenize.TokenError, SyntaxError):
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
        return [
            (token.start[0], token.string) for token in tokens if token.type == tokenize.COMMENT
        ]
    return []


def hash_comment_start(line: str) -> int:
    """Return where a '#' comment starts on a line, or -1 when it has none.

    In YAML, TOML, INI, shell, and PowerShell a '#' starts a comment at the
    start of a line or after whitespace, never inside a quoted value. A quote
    opens a value only where a token can start, so the apostrophe in `don't`
    stays text.
    """
    quote = ""
    index = 0
    while index < len(line):
        char = line[index]
        previous = line[index - 1] if index else " "
        if quote:
            if char == "\\" and quote == '"':
                index += 1
            elif char == quote:
                quote = ""
        elif char in QUOTES and (previous.isspace() or previous in QUOTE_OPENERS):
            quote = char
        elif char == "#" and previous.isspace():
            return index
        index += 1
    return -1


def strip_hash_comment(line: str) -> str:
    """Return a line without its '#' comment."""
    start = hash_comment_start(line)
    return line if start < 0 else line[:start]


def hash_comments(text: str) -> list[tuple[int, str]]:
    """Return '#' comments from YAML, TOML, INI, shell, and PowerShell by line."""
    comments = []
    for number, line in enumerate(text.splitlines(), start=1):
        index = hash_comment_start(line)
        if index >= 0:
            comments.append((number, line[index:]))
    return comments


def allowances_in(relative: str, comments: list[tuple[int, str]]) -> list[Allowance]:
    """Collect every allowance written in the given comments."""
    found = []
    for line, comment in comments:
        allowance = parse_allowance(relative, line, comment)
        if allowance:
            found.append(allowance)
    return found
