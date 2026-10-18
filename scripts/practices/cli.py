"""Run every practice check over a project and report findings with a stable exit contract."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .error_rules import masked_error_findings
from .family_rules import family_findings, powershell_findings
from .manifests import is_manifest, manifest_findings
from .model import (
    ALLOWABLE_CHECKS,
    EXIT_FINDINGS,
    EXIT_INPUT,
    EXIT_OK,
    KNOWN_CHECKS,
    Finding,
    PracticeInputError,
)
from .parallel_rules import (
    command_file_findings,
    command_text_findings,
    is_command_file,
    script_command_findings,
)
from .python_rules import analyze
from .register import register_findings
from .script_rules import double_findings, shape_findings
from .source import (
    Allowance,
    SourceFile,
    allowances_in,
    hash_comments,
    masked_source,
    owned_files,
    python_comments,
    read_text,
    source_files,
)
from .upstreams import (
    load_upstreams,
    staleness_findings,
    today_utc,
    watch_findings,
)
from .workflows import is_workflow, workflow_findings

if TYPE_CHECKING:
    from datetime import date

CONFIG_NAMES = re.compile(
    r"^(?:(?:playwright|vitest|vite|jest)\.config\.[cm]?[jt]s|\.mocharc\.\w+|pytest\.ini|tox\.ini"
    r"|setup\.cfg|pyproject\.toml|package\.json|nextest\.toml)$"
)
# `reruns` is pytest-rerunfailures' configuration key for default reruns.
RETRY_SETTING = re.compile(r"\b(?:retr(?:y|ies)|reruns)\s*[:=]\s*(?P<value>[^,\n}]*)")
RETRY_FLAG = re.compile(r"--reruns\b|--retries[= ]+0*[1-9]|\bretryTimes\b|-p\s*rerunfailures")


@dataclass
class Collected:
    """Accumulate findings and allowances across files."""

    findings: list[Finding] = field(default_factory=list)
    allowances: list[Allowance] = field(default_factory=list)


@dataclass(frozen=True)
class Options:
    """The validated command request."""

    root: Path
    rules: str
    upstreams: str
    output_format: str
    watch: bool
    timeout: float


def parser() -> argparse.ArgumentParser:
    """Describe the project check and the separate upstream watch."""
    result = argparse.ArgumentParser(
        description=(
            "Refuse test doubles, hand-written stand-ins, re-runs, presence-only and "
            "one-off tests, error handlers that drop the cause, shared Git state in "
            "automation, full suites in local hooks, merge-gate defects, stale pins, "
            "and unenforced pitfalls."
        )
    )
    result.add_argument("--root", type=Path, default=Path.cwd(), help="Project root to check")
    result.add_argument(
        "--rules", default="AGENTS.md", help="Canonical rules file holding the pitfalls register"
    )
    result.add_argument("--upstreams", default="upstreams.json", help="Pinned upstream versions")
    result.add_argument("--format", choices=("text", "json"), default="text")
    result.add_argument(
        "--watch",
        action="store_true",
        help="Query each watched upstream's latest release instead of checking the project",
    )
    result.add_argument(
        "--timeout", type=float, default=30.0, help="Seconds to wait for each release query"
    )
    return result


def analyze_source(source: SourceFile, collected: Collected) -> None:
    """Run the checks that apply to one code file's language."""
    text = read_text(source.path)
    if source.language == "python":
        collected.findings.extend(analyze(source, text))
        collected.allowances.extend(allowances_in(source.relative, python_comments(text)))
    elif source.language == "powershell":
        collected.findings.extend(powershell_findings(source, text))
        collected.findings.extend(command_text_findings(source.relative, text))
        collected.allowances.extend(allowances_in(source.relative, hash_comments(text)))
    else:
        masked = masked_source(source)
        collected.allowances.extend(allowances_in(source.relative, list(masked.comments)))
        collected.findings.extend(masked_error_findings(source, masked))
        if source.language == "script":
            collected.findings.extend(double_findings(source, masked))
            collected.findings.extend(script_command_findings(source, masked))
            if source.is_test:
                collected.findings.extend(shape_findings(source, masked))
        else:
            collected.findings.extend(family_findings(source, masked))


def retry_config_findings(path: Path, relative: str) -> list[Finding]:
    """Refuse automatic test retries configured in a runner or package file."""
    findings = []
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        setting = RETRY_SETTING.search(line)
        if RETRY_FLAG.search(line) or (setting and re.search(r"[1-9]", setting["value"])):
            message = "configures automatic test retries; a red test is diagnosed, never re-run"
            findings.append(Finding(relative, number, "rerun", message))
    return findings


def analyze_file(path: Path, relative: str, collected: Collected) -> None:
    """Run the checks for manifests, runner configuration, workflows, and command files."""
    if is_manifest(path):
        collected.findings.extend(manifest_findings(path, relative))
    if CONFIG_NAMES.match(path.name):
        collected.findings.extend(retry_config_findings(path, relative))
        if path.suffix in {".toml", ".ini", ".cfg"}:
            collected.allowances.extend(allowances_in(relative, hash_comments(read_text(path))))
    if is_workflow(relative):
        text = read_text(path)
        collected.findings.extend(workflow_findings(path, relative))
        collected.findings.extend(command_text_findings(relative, text))
        collected.allowances.extend(allowances_in(relative, hash_comments(text)))
    elif is_command_file(relative):
        text = read_text(path)
        collected.findings.extend(command_file_findings(relative, text))
        if path.suffix != ".json":
            collected.allowances.extend(allowances_in(relative, hash_comments(text)))


def scan_files(root: Path, collected: Collected) -> int:
    """Run file-level checks and return how many code files were analyzed."""
    files = owned_files(root)
    sources = source_files(files)
    for source in sources:
        analyze_source(source, collected)
    mock_directories = set()
    for path, relative in files:
        analyze_file(path, relative, collected)
        if "__mocks__" in relative.split("/")[:-1]:
            mock_directories.add(relative.rsplit("/__mocks__/", 1)[0] + "/__mocks__")
    collected.findings.extend(
        Finding(directory, 1, "mock", "a __mocks__ directory replaces modules with test doubles")
        for directory in sorted(mock_directories)
    )
    return len(sources)


def project_findings(options: Options, today: date) -> tuple[list[Finding], list[Allowance], int]:
    """Check one project and return findings, accepted allowances, and files analyzed."""
    collected = Collected()
    scanned = scan_files(options.root, collected)
    if not scanned:
        message = "no code files were found, so no practice was checked"
        collected.findings.append(Finding(".", 1, "nothing-scanned", message))
    upstreams_path = options.root / options.upstreams
    if upstreams_path.is_file():
        upstreams = load_upstreams(upstreams_path, today)
        collected.findings.extend(
            staleness_findings(options.root, options.upstreams, upstreams, today)
        )
    else:
        message = (
            "no upstreams.json; record every pinned version with its watch source and review date"
        )
        collected.findings.append(Finding(options.upstreams, 1, "upstreams-missing", message))
    collected.findings.extend(register_findings(options.root, options.rules))
    findings, accepted = apply_allowances(collected.findings, collected.allowances)
    return findings, accepted, scanned


def allowance_problem(allowance: Allowance, used: set[Allowance]) -> str | None:
    """Explain why an allowance is not a valid, used exception."""
    if allowance.check not in KNOWN_CHECKS:
        return f"{allowance.check} is not a verify-practices check"
    if allowance.check not in ALLOWABLE_CHECKS:
        return f"{allowance.check} has no exceptions; fix the code instead"
    if not allowance.reason:
        return "an allowance needs a reason after '--'"
    if allowance not in used:
        return f"no {allowance.check} finding here; remove the stale allowance"
    return None


def apply_allowances(
    findings: list[Finding], allowances: list[Allowance]
) -> tuple[list[Finding], list[Allowance]]:
    """Accept reviewed exceptions on the finding's line or the line above it."""
    index = {(item.relative, item.line, item.check): item for item in allowances}
    used: set[Allowance] = set()
    kept = []
    for finding in findings:
        allowance = index.get((finding.path, finding.line, finding.check)) or index.get(
            (finding.path, finding.line - 1, finding.check)
        )
        if allowance and finding.check in ALLOWABLE_CHECKS and allowance.reason:
            used.add(allowance)
        else:
            kept.append(finding)
    for allowance in allowances:
        problem = allowance_problem(allowance, used)
        if problem:
            check = "allowance-unused" if problem.startswith("no ") else "allowance-invalid"
            if allowance.check in KNOWN_CHECKS and allowance.check not in ALLOWABLE_CHECKS:
                check = "allowance-refused"
            kept.append(Finding(allowance.relative, allowance.line, check, problem))
    return sorted(set(kept)), sorted(used, key=lambda item: (item.relative, item.line))


def render(
    findings: list[Finding], accepted: list[Allowance], scanned: int, output_format: str
) -> str:
    """Render findings and accepted allowances as text or JSON."""
    if output_format == "json":
        payload = {
            "passed": not findings,
            "files_checked": scanned,
            "findings": [asdict(item) for item in findings],
            "allowances": [asdict(item) for item in accepted],
        }
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [f"{item.path}:{item.line}: {item.check}: {item.message}" for item in findings]
    lines.extend(
        f"{item.relative}:{item.line}: allowed {item.check}: {item.reason}" for item in accepted
    )
    verdict = f"FAIL: {len(findings)} findings" if findings else "PASS: no refused practices"
    lines.append(f"{verdict}; {scanned} code files checked; {len(accepted)} allowances accepted")
    return "\n".join(lines)


def render_watch(
    findings: list[Finding], notes: list[str], watched: int, output_format: str
) -> str:
    """Render upstream releases found by the watch as text or JSON."""
    if output_format == "json":
        payload = {
            "changed": bool(findings),
            "upstreams_watched": watched,
            "findings": [asdict(item) for item in findings],
            "notes": notes,
        }
        return json.dumps(payload, indent=2, sort_keys=True)
    lines = [f"{item.path}: {item.check}: {item.message}" for item in findings] + notes
    verdict = f"CHANGED: {len(findings)} upstream releases" if findings else "CURRENT"
    lines.append(f"{verdict}; {watched} upstreams watched")
    return "\n".join(lines)


def execute(options: Options) -> tuple[int, str]:
    """Check the project, or query upstream releases in watch mode."""
    if not options.root.is_dir():
        message = f"project root is not a directory: {options.root}"
        raise PracticeInputError(message)
    today = today_utc()
    if options.watch:
        upstreams = load_upstreams(options.root / options.upstreams, today)
        if not upstreams:
            message = "upstreams.json lists no upstream to watch"
            raise PracticeInputError(message)
        findings, notes = watch_findings(options.upstreams, upstreams, options.timeout)
        code = EXIT_FINDINGS if findings else EXIT_OK
        return code, render_watch(findings, notes, len(upstreams), options.output_format)
    findings, accepted, scanned = project_findings(options, today)
    return (EXIT_FINDINGS if findings else EXIT_OK), render(
        findings, accepted, scanned, options.output_format
    )


def run(argv: list[str] | None = None) -> tuple[int, str]:
    """Parse arguments and return the exit code and report without printing."""
    args = parser().parse_args(argv)
    options = Options(
        args.root.resolve(), args.rules, args.upstreams, args.format, args.watch, args.timeout
    )
    try:
        return execute(options)
    except (PracticeInputError, OSError, UnicodeError) as error:
        return EXIT_INPUT, f"ERROR: {error}"
