"""Keep parallel work private to its worktree, and keep local hooks to the touched suites.

Every worktree of a repository shares one stash list, so automation that stashes
can pop or drop another worktree's work. A branch checked out in one worktree
cannot be checked out in another, so a worktree on the shared base branch blocks
every other worktree from it and invites commits straight onto it. A local hook
that runs the whole test suite on every commit gets bypassed; the merge gate
runs every suite, and local hooks run what the change touches.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from .masking import matching_close
from .model import Finding

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .masking import Masked
    from .source import SourceFile

GIT = r"\bgit(?:\s+-[Cc]\s+\S+)*\s+"
# `git stash list` and `git stash show` only read the shared list.
STASH = re.compile(GIT + r"stash\b(?!\s+(?:list|show)\b)")
BASE_WORKTREE = re.compile(
    GIT + r"worktree\s+add\b(?![^\n;&|]*\s(?:-b|-B|--detach|-d)(?=\s|$))"
    r"[^\n;&|]*\s(?:main|master|trunk|develop)(?=\s*(?:$|[;&|)]))",
    re.MULTILINE,
)
STASH_MESSAGE = (
    "runs git stash; every worktree of a repository shares one stash list, so "
    "commit unfinished work to its own branch instead"
)
WORKTREE_MESSAGE = (
    "checks out a shared base branch in a worktree; create a branch with -b or use --detach instead"
)
# Test runners started with options only, so they select the whole suite.
OPTIONS = r"(?:\s+-[\w-]+(?:=\S*)?)*"
WHOLE_SUITE_COMMANDS = (
    r"(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?test(?:\s+--)?",
    r"(?:npx\s+|pnpm\s+exec\s+|yarn\s+)?(?:jest|vitest(?:\s+run)?|mocha|ava|playwright\s+test)",
    r"(?:python3?\s+-m\s+)?pytest",
    r"python3?\s+-m\s+unittest(?:\s+discover\b[^\n;&|]*)?",
    r"tox|nox|ctest|Invoke-Pester|dotnet\s+test|cargo\s+(?:test|nextest\s+run)",
    r"(?:\./)?(?:mvnw?|gradlew?)\s+(?:test|verify|check)",
    rf"go\s+test{OPTIONS}\s+\./\.\.\.",
)
WHOLE_SUITE = re.compile(
    r"(?:^|[\s;&|(])(?:"
    + "|".join(f"(?:{command}){OPTIONS}" for command in WHOLE_SUITE_COMMANDS)
    + r")\s*(?=$|[;&|)])",
    re.MULTILINE,
)
SUITE_MESSAGE = (
    "runs the whole test suite in a local hook; run the suites the change touches "
    "and leave every suite to the merge gate"
)
# Quotes, commas, and brackets separate the words of a command written as a
# string or an argument list; spaces stand in for them before matching.
SEPARATORS = str.maketrans(dict.fromkeys("\"'`,[]", " "))
SHELL_SUFFIXES = (".sh", ".bash", ".zsh", ".ksh")
HOOK_DIRECTORIES = (".husky/", ".githooks/", ".git-hooks/")
HOOK_RUNNERS = frozenset(
    {"lefthook.yml", "lefthook.yaml", ".lefthook.yml", ".lefthook.yaml", "lefthook-local.yml"}
)
TASK_RUNNERS = frozenset(
    {
        "Makefile",
        "makefile",
        "GNUmakefile",
        "justfile",
        "Justfile",
        ".justfile",
        "Taskfile.yml",
        "Taskfile.yaml",
        "package.json",
        ".pre-commit-config.yaml",
    }
)
PRE_COMMIT = ".pre-commit-config.yaml"
PROCESS_CALLS = frozenset(
    {
        "run",
        "call",
        "check_call",
        "check_output",
        "Popen",
        "system",
        "popen",
        "getoutput",
        "getstatusoutput",
        "create_subprocess_exec",
        "create_subprocess_shell",
    }
)
SCRIPT_PROCESS_CALL = re.compile(
    r"(?<![\w$])(?:exec|execSync|execFile|execFileSync|spawn|spawnSync|execa|execaSync"
    r"|execaCommand|execaCommandSync)\s*\("
)
LIST_ITEM = re.compile(r"^(?P<indent>\s*)-\s+[\w-]+\s*:")
ENTRY = re.compile(r"^(?P<lead>\s*(?:-\s+)?)entry\s*:\s*(?P<value>.*)$")
YAML_KEY = re.compile(r"^\s*(?:-\s+)?[\w-]+\s*:")
# A hook that runs without the changed file names, or even when none changed.
IGNORES_CHANGES = re.compile(r"^\s*(?:-\s+)?(?:pass_filenames\s*:\s*false|always_run\s*:\s*true)\b")


def is_hook_file(relative: str) -> bool:
    """Recognize a Git hook script or a hook manager's configuration."""
    if relative.startswith(".husky/_/"):
        return False
    return relative.startswith(HOOK_DIRECTORIES) or relative in HOOK_RUNNERS


def is_command_file(relative: str) -> bool:
    """Recognize a shell script, Git hook, or task runner that holds commands."""
    name = relative.rsplit("/", 1)[-1]
    return (
        relative.endswith(SHELL_SUFFIXES)
        or is_hook_file(relative)
        or (relative == name and name in TASK_RUNNERS)
    )


def git_state_findings(relative: str, line: int, command: str) -> list[Finding]:
    """Refuse a stash or a base-branch worktree in one command's text."""
    words = command.translate(SEPARATORS)
    findings = []
    if STASH.search(words):
        findings.append(Finding(relative, line, "git-shared-state", STASH_MESSAGE))
    if BASE_WORKTREE.search(words):
        findings.append(Finding(relative, line, "git-shared-state", WORKTREE_MESSAGE))
    return findings


def code_lines(text: str, *, comments: bool) -> Iterator[tuple[int, str]]:
    """Yield numbered lines, without '#' comments when the format has them."""
    for number, line in enumerate(text.splitlines(), start=1):
        yield number, (line.split("#", 1)[0] if comments else line)


def command_text_findings(relative: str, text: str) -> list[Finding]:
    """Refuse shared Git state in a script, workflow, or runner file, line by line."""
    comments = not relative.endswith(".json")
    return [
        finding
        for number, line in code_lines(text, comments=comments)
        for finding in git_state_findings(relative, number, line)
    ]


def indentation(line: str) -> int:
    """Return a line's leading whitespace width."""
    return len(line) - len(line.lstrip())


def yaml_items(lines: list[str]) -> Iterator[tuple[int, list[str]]]:
    """Yield each mapping item of a YAML list with its own lines, nested items split off."""
    starts = [
        (index, len(match["indent"]))
        for index, line in enumerate(lines)
        if (match := LIST_ITEM.match(line))
    ]
    for position, (start, indent) in enumerate(starts):
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        end = next(
            (
                index
                for index in range(start + 1, stop)
                if lines[index].strip() and indentation(lines[index]) <= indent
            ),
            stop,
        )
        yield start, lines[start:end]


def entry_command(item: list[str]) -> tuple[int, str] | None:
    """Return an item's `entry` offset and command, joining folded continuation lines."""
    for offset, line in enumerate(item):
        match = ENTRY.match(line)
        if not match:
            continue
        words = [match["value"]]
        for continuation in item[offset + 1 :]:
            if (
                not continuation.strip()
                or indentation(continuation) <= len(match["lead"])
                or YAML_KEY.match(continuation)
            ):
                break
            words.append(continuation.strip())
        return offset, " ".join(words)
    return None


def hook_findings(relative: str, text: str) -> list[Finding]:
    """Refuse a local hook that runs the whole test suite."""
    findings = []
    if relative == PRE_COMMIT:
        lines = [line.split("#", 1)[0] for line in text.splitlines()]
        for start, item in yaml_items(lines):
            entry = entry_command(item)
            if (
                entry
                and any(IGNORES_CHANGES.match(line) for line in item)
                and WHOLE_SUITE.search(entry[1].translate(SEPARATORS))
            ):
                entry_line = start + entry[0] + 1
                findings.append(Finding(relative, entry_line, "local-full-suite", SUITE_MESSAGE))
    elif is_hook_file(relative):
        for number, line in code_lines(text, comments=True):
            if WHOLE_SUITE.search(line.translate(SEPARATORS)):
                findings.append(Finding(relative, number, "local-full-suite", SUITE_MESSAGE))
    return findings


def command_file_findings(relative: str, text: str) -> list[Finding]:
    """Run the shared-state and local-hook checks on a command file."""
    return command_text_findings(relative, text) + hook_findings(relative, text)


def literal_words(node: ast.expr) -> str:
    """Render a command argument's literal words; anything computed becomes '_'."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.List | ast.Tuple):
        return " ".join(literal_words(item) for item in node.elts)
    if isinstance(node, ast.JoinedStr):
        return " ".join(literal_words(item) for item in node.values)
    return "_"


def called_name(node: ast.Call) -> str:
    """Return the called function's final name."""
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return node.func.id if isinstance(node.func, ast.Name) else ""


def python_command_findings(source: SourceFile, tree: ast.Module) -> list[Finding]:
    """Refuse shared Git state in commands that Python code starts."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and called_name(node) in PROCESS_CALLS:
            command = " ".join(literal_words(argument) for argument in node.args)
            findings.extend(git_state_findings(source.relative, node.lineno, command))
    return findings


def script_command_findings(source: SourceFile, masked: Masked) -> list[Finding]:
    """Refuse shared Git state in commands that JavaScript-family code starts."""
    findings = []
    for match in SCRIPT_PROCESS_CALL.finditer(masked.bare):
        opening = match.end() - 1
        closing = matching_close(masked.bare, opening)
        if closing > opening:
            command = masked.code[opening + 1 : closing]
            line = masked.line_of(match.start())
            findings.extend(git_state_findings(source.relative, line, command))
    return findings
