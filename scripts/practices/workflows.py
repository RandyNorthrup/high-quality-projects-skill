"""Check GitHub Actions workflows as merge gates: every change reports, first run decides.

The standard library has no YAML parser, so these checks read the workflow text
by indentation. They look for the trigger block, job blocks, and specific keys;
anything they cannot locate is reported rather than assumed clean.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .model import Finding

if TYPE_CHECKING:
    from pathlib import Path

ON_KEY = re.compile(r"^(?:\"on\"|'on'|on|true)\s*:\s*(?P<inline>.*)$")
TOP_LEVEL_KEY = re.compile(r"^[^\s#][^:]*:")
NESTED_KEY = re.compile(r"^(?P<indent>\s+)(?:-\s*)?(?P<key>[A-Za-z_][\w-]*)\s*:?")
PULL_REQUEST_TRIGGERS = frozenset({"pull_request", "pull_request_target"})
GATE_TRIGGERS = PULL_REQUEST_TRIGGERS | {"merge_group"}
EXPRESSION = re.compile(r"\$\{\{(?P<body>.*?)\}\}")
# Context and property names in expressions are case-insensitive. A secret is
# read by property, by index, or all at once through toJSON.
SECRET_REFERENCE = re.compile(
    r"\btoJSON\s*\(\s*secrets\s*\)"
    r"|\bsecrets\s*(?:\.\s*(?P<dotted>[\w-]+)|\[\s*(?P<indexed>[^\]]*)\])",
    re.IGNORECASE,
)
INHERITED_SECRETS = re.compile(r"\bsecrets:\s*inherit\b")
# The automatic token is read-only for forks, so a gate may use it.
FORK_SAFE_NAME = "GITHUB_TOKEN"
RETRY_USE = re.compile(
    r"uses:\s*(?:nick-fields/retry|wandalen/wretry\.action|step-security/retry)@"
    r"|\bgh\s+run\s+rerun\b|--reruns\b|--retries[= ]+0*[1-9]|--retry-failed\b",
    re.IGNORECASE,
)
SLEEP = re.compile(r"(?:^|[\s;&|(])(?:sleep\s+\d|Start-Sleep\b)", re.IGNORECASE)
CONTINUE_ON_ERROR = re.compile(r"^\s*continue-on-error:\s*(?P<value>[^#\n]*?)\s*(?:#.*)?$")
# Only a value that is false before the run starts keeps a failing step failing;
# an expression can evaluate to true for some matrix entry or event.
STATICALLY_FALSE = re.compile(r"""["']?(?:false|\$\{\{\s*false\s*\}\})["']?""", re.IGNORECASE)


@dataclass(frozen=True)
class Workflow:
    """A workflow's lines and the trigger names its `on` block declares."""

    relative: str
    lines: tuple[str, ...]
    triggers: frozenset[str]
    on_lines: tuple[int, int]


def read_workflow(path: Path, relative: str) -> Workflow:
    """Locate a workflow's trigger block and the triggers it names."""
    lines = tuple(path.read_text(encoding="utf-8-sig", errors="replace").splitlines())
    for index, line in enumerate(lines):
        match = ON_KEY.match(line)
        if not match:
            continue
        inline = match["inline"].split("#", 1)[0].strip()
        if inline:
            names = frozenset(re.findall(r"[A-Za-z_]+", inline))
            return Workflow(relative, lines, names, (index, index + 1))
        end = index + 1
        while end < len(lines) and not TOP_LEVEL_KEY.match(lines[end]):
            end += 1
        return Workflow(relative, lines, block_keys(lines[index + 1 : end]), (index, end))
    return Workflow(relative, lines, frozenset(), (0, 0))


def block_keys(block: tuple[str, ...]) -> frozenset[str]:
    """Return the keys at the first indentation level of a YAML block."""
    keys: list[tuple[int, str]] = []
    for line in block:
        if line.strip().startswith("#"):
            continue
        match = NESTED_KEY.match(line)
        if match:
            keys.append((len(match["indent"]), match["key"]))
    if not keys:
        return frozenset()
    level = min(indent for indent, _ in keys)
    return frozenset(key for indent, key in keys if indent == level)


def jobs(workflow: Workflow) -> list[tuple[str, int, tuple[str, ...]]]:
    """Return (job id, line, body lines) for each job in the workflow."""
    lines = workflow.lines
    try:
        start = next(index for index, line in enumerate(lines) if line.rstrip() == "jobs:")
    except StopIteration:
        return []
    end = start + 1
    while end < len(lines) and not TOP_LEVEL_KEY.match(lines[end]):
        end += 1
    entries = [
        (index, match)
        for index in range(start + 1, end)
        if (match := NESTED_KEY.match(lines[index])) and not lines[index].strip().startswith("#")
    ]
    if not entries:
        return []
    level = min(len(match["indent"]) for _, match in entries)
    heads = [(index, match["key"]) for index, match in entries if len(match["indent"]) == level]
    found = []
    for position, (index, key) in enumerate(heads):
        stop = heads[position + 1][0] if position + 1 < len(heads) else end
        found.append((key, index + 1, lines[index + 1 : stop]))
    return found


def job_level(body: tuple[str, ...], key: str) -> bool:
    """Report whether a key appears at the job's own indentation."""
    indents = [len(line) - len(line.lstrip()) for line in body if line.strip()]
    if not indents:
        return False
    level = min(indents)
    return any(
        len(line) - len(line.lstrip()) == level and line.strip().startswith(f"{key}:")
        for line in body
    )


def gate_findings(workflow: Workflow) -> list[Finding]:
    """Check a workflow that guards merges: queue trigger, filters, and secrets."""
    findings = []
    first, last = workflow.on_lines
    if workflow.triggers & PULL_REQUEST_TRIGGERS and "merge_group" not in workflow.triggers:
        message = (
            "runs on pull requests but not merge_group; a merge queue then never receives "
            "its required checks"
        )
        findings.append(Finding(workflow.relative, first + 1, "ci-merge-group", message))
    for index in range(first, last):
        if re.match(r"^\s+paths(?:-ignore)?\s*:", workflow.lines[index]):
            message = (
                "filters the trigger by path; a skipped required check stays Pending and "
                "blocks the merge, so skip work inside the job instead"
            )
            findings.append(Finding(workflow.relative, index + 1, "ci-path-filter", message))
    for index, line in enumerate(workflow.lines):
        if uses_secret(line.split("#", 1)[0]):
            message = "a merge gate must run without secrets or keys, including for forks"
            findings.append(Finding(workflow.relative, index + 1, "ci-secret", message))
        setting = CONTINUE_ON_ERROR.match(line)
        if setting and setting["value"] and not STATICALLY_FALSE.fullmatch(setting["value"]):
            message = "continue-on-error lets a failing step report success"
            findings.append(Finding(workflow.relative, index + 1, "ci-continue-on-error", message))
    return findings


def uses_secret(code: str) -> bool:
    """Report a secret read by property, index, or toJSON, or secrets inherited by a call."""
    if INHERITED_SECRETS.search(code):
        return True
    for expression in EXPRESSION.finditer(code):
        for reference in SECRET_REFERENCE.finditer(expression["body"]):
            dotted, indexed = reference["dotted"], reference["indexed"]
            if dotted is None and indexed is None:
                return True  # toJSON(secrets) exposes every secret
            name = dotted or indexed.strip().strip("'\"")
            if name.upper() != FORK_SAFE_NAME:
                return True
    return False


def workflow_findings(path: Path, relative: str) -> list[Finding]:
    """Check one workflow file."""
    workflow = read_workflow(path, relative)
    if not workflow.triggers:
        message = "no trigger block was found, so this workflow was not checked"
        return [Finding(relative, 1, "unparsed", message)]
    findings = gate_findings(workflow) if workflow.triggers & GATE_TRIGGERS else []
    for key, start, body in jobs(workflow):
        if not job_level(body, "timeout-minutes") and not job_level(body, "uses"):
            message = f"job {key} has no timeout-minutes; a hung runner then holds the gate"
            findings.append(Finding(relative, start, "ci-timeout", message))
    for index, line in enumerate(workflow.lines):
        code = line.split("#", 1)[0]
        if RETRY_USE.search(code):
            message = "re-runs a failing step or test until it passes; find and fix the cause"
            findings.append(Finding(relative, index + 1, "rerun", message))
        if SLEEP.search(code):
            message = "waits a fixed delay; poll for the condition the step needs"
            findings.append(Finding(relative, index + 1, "fixed-delay", message))
    return findings


def is_workflow(relative: str) -> bool:
    """Recognize a GitHub Actions workflow file."""
    return relative.startswith(".github/workflows/") and relative.endswith((".yml", ".yaml"))
