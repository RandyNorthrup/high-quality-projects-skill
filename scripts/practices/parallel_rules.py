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
from pathlib import Path
from typing import TYPE_CHECKING

from .masking import matching_close
from .model import Finding
from .source import language_of, strip_hash_comment

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
# pre-commit loads its configuration as YAML 1.1, where false, no, and off in
# any case are False, and true, yes, and on are True.
IGNORES_CHANGES = re.compile(
    r"^\s*(?:-\s+)?(?:pass_filenames\s*:\s*(?i:false|no|off)|always_run\s*:\s*(?i:true|yes|on))"
    r"\s*$"
)


def is_hook_file(relative: str) -> bool:
    """Recognize a Git hook script or a hook manager's configuration."""
    if relative.startswith(".husky/_/"):
        return False
    return relative.startswith(HOOK_DIRECTORIES) or relative in HOOK_RUNNERS


def is_command_file(relative: str) -> bool:
    """Recognize a Git hook or task runner that holds commands and is not a code file."""
    name = relative.rsplit("/", 1)[-1]
    # Shell scripts are code files, checked with their language's rules instead.
    if language_of(Path(relative)) is not None:
        return False
    return is_hook_file(relative) or (relative == name and name in TASK_RUNNERS)


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
        yield number, (strip_hash_comment(line) if comments else line)


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
        lines = [strip_hash_comment(line) for line in text.splitlines()]
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


def scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Walk one scope without entering the functions defined inside it."""
    pending = list(ast.iter_child_nodes(scope))
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            pending.extend(ast.iter_child_nodes(node))


def literal_bindings(nodes: list[ast.AST]) -> dict[str, list[tuple[int, str]]]:
    """Map each name bound to a literal command in a scope to (line, words) bindings."""
    bindings: dict[str, list[tuple[int, str]]] = {}
    target: ast.expr
    value: ast.expr | None  # `name: type` with no value binds nothing
    for node in nodes:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        else:
            continue
        if isinstance(target, ast.Name) and isinstance(
            value, ast.Constant | ast.List | ast.Tuple | ast.JoinedStr
        ):
            bindings.setdefault(target.id, []).append((node.lineno, literal_words(value)))
    return bindings


def command_words(argument: ast.expr, bindings: dict[str, list[tuple[int, str]]], line: int) -> str:
    """Render an argument, reading a name from its latest literal binding above the call."""
    if isinstance(argument, ast.Name):
        # The walk visits statements out of order, so choose by source line.
        earlier = sorted(
            (bound, words) for bound, words in bindings.get(argument.id, []) if bound <= line
        )
        if earlier:
            return earlier[-1][1]
    return literal_words(argument)


def python_command_findings(source: SourceFile, tree: ast.Module) -> list[Finding]:
    """Refuse shared Git state in commands that Python code starts, inline or via a name."""
    findings = []
    scopes: list[ast.AST] = [tree]
    scopes.extend(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    )
    for scope in scopes:
        nodes = list(scope_nodes(scope))
        bindings = literal_bindings(nodes)
        for node in nodes:
            if isinstance(node, ast.Call) and called_name(node) in PROCESS_CALLS:
                command = " ".join(
                    command_words(argument, bindings, node.lineno) for argument in node.args
                )
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
