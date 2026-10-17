"""Keep a pitfalls register whose every rule is enforced by a test or gate, never by prose.

A lesson written only in a document is read once and then forgotten; the next
contributor or agent repeats the failure. Each register entry names the code that
fails when the pitfall returns: a test file, a gate script the CI runs, or one of
this command's own checks.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from .model import KNOWN_CHECKS, Finding, PracticeInputError
from .source import is_test_path
from .upstreams import reject_duplicates

FENCE = re.compile(
    r"^```pitfalls-register[ \t]*\n(?P<body>.*?)^```[ \t]*$", re.DOTALL | re.MULTILINE
)
ENTRY_FIELDS = frozenset({"id", "pitfall", "rule", "enforced_by"})
DOCUMENT_SUFFIXES = frozenset({".md", ".markdown", ".rst", ".txt", ".adoc", ".mdc"})
# Files that hold the commands CI runs. A gate script named in one of them runs
# on every change; a script named nowhere is a suggestion.
RUNNER_FILES = (
    ".pre-commit-config.yaml",
    "package.json",
    "Makefile",
    "justfile",
    "Taskfile.yml",
    "tox.ini",
    "noxfile.py",
    "pyproject.toml",
)


@dataclass(frozen=True)
class Pitfall:
    """One register entry and the enforcement it names."""

    identifier: str
    paths: tuple[str, ...]
    checks: tuple[str, ...]


def fail(rules: str, message: str) -> NoReturn:
    """Raise an input error naming the malformed register."""
    error = f"{rules} pitfalls register: {message}"
    raise PracticeInputError(error)


def enforcement_of(
    value: object, rules: str, identifier: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split an entry's enforcement into project paths and built-in check identities."""
    if not isinstance(value, list):
        fail(rules, f"{identifier} enforced_by must be a list")
    paths, checks = [], []
    for item in value:
        if isinstance(item, dict) and set(item) == {"path"} and isinstance(item["path"], str):
            paths.append(item["path"])
        elif isinstance(item, dict) and set(item) == {"check"} and isinstance(item["check"], str):
            checks.append(item["check"])
        else:
            message = f'{identifier} enforced_by items are {{"path": ...}} or {{"check": ...}}'
            fail(rules, message)
    return tuple(paths), tuple(checks)


def register_entries(path: Path, rules: str) -> list[object] | None:
    """Return the register's raw entries, or None when the rules file has no register."""
    if not path.is_file():
        return None
    blocks = FENCE.findall(path.read_text(encoding="utf-8-sig"))
    if not blocks:
        return None
    if len(blocks) > 1:
        fail(rules, "keep exactly one register block")
    try:
        data = json.loads(blocks[0], object_pairs_hook=reject_duplicates)
    except ValueError as error:
        fail(rules, f"not valid JSON: {error}")
    if not isinstance(data, dict) or set(data) != {"schema_version", "pitfalls"}:
        fail(rules, 'fields must be exactly "schema_version" and "pitfalls"')
    if data["schema_version"] != 1 or not isinstance(data["pitfalls"], list):
        fail(rules, "schema_version must be 1 and pitfalls a list")
    return list(data["pitfalls"])


def pitfall_of(entry: object, rules: str) -> Pitfall:
    """Validate one register entry."""
    if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
        fail(rules, f"entries need exactly {', '.join(sorted(ENTRY_FIELDS))}")
    texts = [entry[key] for key in ("id", "pitfall", "rule")]
    if not all(isinstance(text, str) and text.strip() for text in texts):
        fail(rules, "id, pitfall, and rule must be non-empty strings")
    paths, checks = enforcement_of(entry["enforced_by"], rules, entry["id"])
    return Pitfall(entry["id"], paths, checks)


def load_register(path: Path, rules: str) -> list[Pitfall] | None:
    """Parse the register block, or return None when the rules file has none."""
    entries = register_entries(path, rules)
    if entries is None:
        return None
    pitfalls = [pitfall_of(entry, rules) for entry in entries]
    identifiers = [item.identifier for item in pitfalls]
    if len(identifiers) != len(set(identifiers)):
        fail(rules, "ids must be unique")
    return pitfalls


def runner_text(root: Path) -> str:
    """Concatenate the CI workflows and gate-runner files, where enforcement must be named."""
    texts: list[str] = []
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        texts.extend(
            item.read_text(encoding="utf-8", errors="replace")
            for item in sorted(workflows.glob("*.y*ml"))
        )
    for name in RUNNER_FILES:
        candidate = root / name
        if candidate.is_file():
            texts.append(candidate.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(texts)


def path_problem(root: Path, relative: str, runners: str) -> str | None:
    """Explain why a named path does not enforce anything, or return None."""
    target = root / relative
    if Path(relative).suffix.lower() in DOCUMENT_SUFFIXES:
        return f"{relative} is a document; a rule enforced by prose is not enforced"
    if not target.is_file():
        return f"{relative} does not exist"
    if not is_test_path(relative) and relative not in runners:
        return f"{relative} is neither a test nor named by a CI workflow or gate runner"
    return None


def register_findings(root: Path, rules: str) -> list[Finding]:
    """Require a register and refuse entries that no code enforces."""
    pitfalls = load_register(root / rules, rules)
    if pitfalls is None:
        message = (
            "no ```pitfalls-register``` block; record each pitfall with the test or gate "
            "that fails if it returns"
        )
        return [Finding(rules, 1, "register-missing", message)]
    runners = runner_text(root)
    findings: list[Finding] = []
    for item in pitfalls:
        problems = [
            problem for path in item.paths if (problem := path_problem(root, path, runners))
        ]
        problems.extend(
            f"{check} is not a verify-practices check"
            for check in item.checks
            if check not in KNOWN_CHECKS
        )
        if not item.paths and not item.checks:
            problems.append("names no test, gate, or check")
        findings.extend(
            Finding(rules, 1, "register-unenforced", f"{item.identifier}: {problem}")
            for problem in problems
        )
    return findings
