"""Check JavaScript and TypeScript sources on masked text, so comments and strings never match."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .masking import Masked, matching_close
from .model import Finding
from .python_rules import DOUBLE_MESSAGES, DOUBLE_PREFIXES, ONE_OFF_COPIES

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from .source import SourceFile

SCRIPT_PACKAGES: Mapping[str, str] = {
    "sinon": "mock",
    "testdouble": "mock",
    "jest-mock": "mock",
    "jest-mock-extended": "mock",
    "vitest-mock-extended": "mock",
    "ts-mockito": "mock",
    "proxyquire": "mock",
    "rewire": "mock",
    "@sinonjs/fake-timers": "fake-timer",
    "@jest/fake-timers": "fake-timer",
    "mockdate": "fake-timer",
    "timekeeper": "fake-timer",
    "nock": "fake-server",
    "msw": "fake-server",
    "fetch-mock": "fake-server",
    "jest-fetch-mock": "fake-server",
    "vitest-fetch-mock": "fake-server",
    "axios-mock-adapter": "fake-server",
    "mockttp": "fake-server",
    "miragejs": "fake-server",
    "json-server": "fake-server",
    "pretender": "fake-server",
    "memfs": "stand-in",
    "mock-fs": "stand-in",
    "ioredis-mock": "stand-in",
    "redis-mock": "stand-in",
    "fake-indexeddb": "stand-in",
}
MODULE_SPECIFIER = re.compile(
    r"(?:\bfrom\s*|\brequire\s*\(\s*|\bimport\s*\(\s*|\bimport\s+)(['\"])(?P<module>[^'\"\n]+)\1"
)
CALL_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"\b(?:vi|jest)\s*\.\s*(?:mock|doMock|unstable_mockModule|fn|spyOn|stubGlobal"
            r"|createMockFromModule|replaceProperty)\s*\("
        ),
        "mock",
    ),
    (
        re.compile(
            r"\b(?:vi|jest)\s*\.\s*(?:useFakeTimers|advanceTimersByTime|advanceTimersToNextTimer"
            r"|runAllTimers|runOnlyPendingTimers|setSystemTime)\s*\("
        ),
        "fake-timer",
    ),
    (re.compile(r"\bnew\s+MockAgent\s*\("), "fake-server"),
    (re.compile(r"\bjest\s*\.\s*retryTimes\s*\(|\bthis\s*\.\s*retries\s*\("), "rerun"),
)
TEST_CALL_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b(?:jest|vi)\s*\.\s*setTimeout\s*\(|\bthis\s*\.\s*timeout\s*\("
            r"|\btest\s*\.\s*(?:setTimeout|slow)\s*\(|\btestTimeout\s*:"
        ),
        "timeout-override",
        "overrides the test timeout; keep the repository default and fix the slowness",
    ),
    (
        re.compile(
            r"\bwaitForTimeout\s*\(|\bcy\s*\.\s*wait\s*\(\s*\d"
            r"|\bsetTimeout\s*\(\s*[\w$]+\s*,\s*0*[1-9]"
        ),
        "fixed-delay",
        "waits a fixed delay; wait until the expected condition holds",
    ),
    (
        # A server whose request handler is written inline in the test.
        re.compile(
            r"\bcreate(?:Secure)?Server\s*\(\s*(?:async\s+)?"
            r"(?:function\b|\([^()]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"
        ),
        "fake-server",
        f"starts a local server that {DOUBLE_MESSAGES['fake-server']}",
    ),
    (
        # A class, or a function bound to a double's name, written in the test.
        re.compile(
            rf"\bclass\s+(?:{DOUBLE_PREFIXES})(?:[A-Z0-9_$][\w$]*)?(?![\w$])"
            r"|\b(?:const|let|var)\s+(?:fake|stub|mock|spy|dummy|inMemory|scripted|canned)"
            r"(?:[A-Z0-9_$][\w$]*)?\s*(?::[^=;\n]+)?=\s*"
            r"(?:async\b|function\b|class\b|new\s+class\b|\([^()]*\)\s*(?::[^=;\n]+)?=>"
            r"|[A-Za-z_$][\w$]*\s*=>)"
        ),
        "hand-written-double",
        f"declares a double that {DOUBLE_MESSAGES['hand-written-double']}",
    ),
)
TEST_BLOCK = re.compile(
    r"(?<![\w$.])(?:it|test)(?:\s*\.\s*(?:only|concurrent|skip|todo|failing))?\s*\("
)
CALLED_NAME = re.compile(r"(?<![\w$])([A-Za-z_$][\w$]*)\s*\(")
MATCHER = re.compile(
    r"\.\s*(?:(?:not|resolves|rejects)\s*\.\s*)*(?P<name>to[A-Z]\w*)\s*\(\s*(?P<true>true\b)?"
)
NODE_ASSERT = re.compile(r"\bassert\s*(?:\.\s*(?P<name>\w+)\s*)?\(")
KEYWORDS = frozenset({"if", "for", "while", "switch", "catch", "function", "return", "async"})
FILE_READS = frozenset(
    {
        "readFileSync",
        "readFile",
        "existsSync",
        "exists",
        "access",
        "accessSync",
        "stat",
        "statSync",
        "lstatSync",
        "readdirSync",
        "readdir",
    }
)
INSPECTION_CALLS = FILE_READS | frozenset(
    {
        "expect",
        "join",
        "resolve",
        "dirname",
        "basename",
        "relative",
        "fileURLToPath",
        "URL",
        "includes",
        "split",
        "trim",
        "toString",
        "toLowerCase",
        "toUpperCase",
        "match",
        "matchAll",
        "replace",
        "startsWith",
        "endsWith",
        "indexOf",
        "parse",
        "keys",
        "values",
        "entries",
        "map",
        "filter",
        "some",
        "every",
        "find",
        "String",
        "Object",
        "Array",
        "from",
    }
)
EXISTENCE_MATCHERS = frozenset(
    {"toContain", "toMatch", "toHaveProperty", "toBeTruthy", "toBeFalsy", "toBeDefined"}
)
TRUE_MATCHERS = frozenset({"toBe", "toEqual", "toStrictEqual"})
EXISTENCE_ASSERTS = frozenset({"assert", "ok", "match", "doesNotMatch"})
ID_TITLE = re.compile(
    r"\b(?:finding|item|checklist|rule|lesson|pitfall|issue|ticket|bug)\s*[#:-]?\s*\d+\b",
    re.IGNORECASE,
)
NUMBER = re.compile(r"(?<![\w$])\d[\w.]*")
NUMBER_ARGUMENT = re.compile(r"\d[\d_]*(?:\.\d+)?")


@dataclass(frozen=True)
class TestBlock:
    """One `it(...)` or `test(...)` call with its argument text in both views."""

    line: int
    code: str
    bare: str


def package_of(specifier: str) -> str:
    """Return the npm package that a module specifier names."""
    parts = specifier.split("/")
    return "/".join(parts[:2]) if specifier.startswith("@") else parts[0]


def double_findings(source: SourceFile, masked: Masked) -> list[Finding]:
    """Refuse doubling imports and calls, and test-only delays and timeout overrides."""
    findings = []
    for match in MODULE_SPECIFIER.finditer(masked.code):
        check = SCRIPT_PACKAGES.get(package_of(match["module"]))
        if check:
            message = f"{match['module']} {DOUBLE_MESSAGES[check]}"
            findings.append(Finding(source.relative, masked.line_of(match.start()), check, message))
    for pattern, check in CALL_RULES:
        findings.extend(
            Finding(
                source.relative,
                masked.line_of(match.start()),
                check,
                f"{match.group().rstrip('( ')} {DOUBLE_MESSAGES[check]}",
            )
            for match in pattern.finditer(masked.bare)
        )
    if source.is_test:
        for pattern, check, message in TEST_CALL_RULES:
            findings.extend(
                Finding(source.relative, masked.line_of(match.start()), check, message)
                for match in pattern.finditer(masked.bare)
            )
    return findings


def test_blocks(masked: Masked) -> Iterator[TestBlock]:
    """Yield each test call's argument text."""
    for match in TEST_BLOCK.finditer(masked.bare):
        opening = match.end() - 1
        closing = matching_close(masked.bare, opening)
        if closing > opening:
            yield TestBlock(
                masked.line_of(match.start()),
                masked.code[opening + 1 : closing],
                masked.bare[opening + 1 : closing],
            )


def top_level_arguments(bare: str) -> list[tuple[int, int]]:
    """Split call arguments at commas outside any bracket."""
    spans, depth, start = [], 0, 0
    for position, char in enumerate(bare):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and not depth:
            spans.append((start, position))
            start = position + 1
    spans.append((start, len(bare)))
    # A literal argument is blank in this view, so only a trailing comma's
    # empty final span is dropped; earlier blank spans are real arguments.
    if len(spans) > 1 and not bare[spans[-1][0] :].strip():
        spans.pop()
    return spans


def option_findings(source: SourceFile, block: TestBlock) -> list[Finding]:
    """Refuse per-test timeout and retry options passed to the test call."""
    findings = []
    arguments = top_level_arguments(block.bare)
    for index, (begin, end) in enumerate(arguments[1:], start=1):
        text = block.bare[begin:end].strip()
        if text.startswith("{") and re.search(r"\bretry\s*:\s*0*[1-9]", text):
            message = f"passes a retry option {DOUBLE_MESSAGES['rerun']}"
            findings.append(Finding(source.relative, block.line, "rerun", message))
        if (text.startswith("{") and re.search(r"\btimeout\s*:", text)) or (
            index == len(arguments) - 1
            and index > 1
            and NUMBER_ARGUMENT.fullmatch(text) is not None
        ):
            message = "overrides the test timeout; keep the repository default and fix the slowness"
            findings.append(Finding(source.relative, block.line, "timeout-override", message))
    return findings


def only_checks_presence(block: TestBlock) -> bool:
    """Report a test that reads files and asserts only that text, keys, or files exist."""
    kinds = [
        match["name"] in EXISTENCE_MATCHERS
        or (match["name"] in TRUE_MATCHERS and bool(match["true"]))
        for match in MATCHER.finditer(block.bare)
    ]
    asserts = [match["name"] or "assert" for match in NODE_ASSERT.finditer(block.bare)]
    kinds.extend(name in EXISTENCE_ASSERTS for name in asserts)
    assertion_names = {match["name"] for match in MATCHER.finditer(block.bare)} | set(asserts)
    calls = {name for name in CALLED_NAME.findall(block.bare) if name not in KEYWORDS}
    calls -= assertion_names
    return bool(kinds) and all(kinds) and calls <= INSPECTION_CALLS and bool(calls & FILE_READS)


def title_of(block: TestBlock) -> str:
    """Return the literal test title, without quotes."""
    arguments = top_level_arguments(block.bare)
    if not arguments:
        return ""
    begin, end = arguments[0]
    return block.code[begin:end].strip().strip("'\"`")


def shape_findings(source: SourceFile, masked: Masked) -> list[Finding]:
    """Refuse presence-only tests, tests titled after findings, and copied test bodies."""
    findings = []
    groups: defaultdict[str, list[TestBlock]] = defaultdict(list)
    for block in test_blocks(masked):
        findings.extend(option_findings(source, block))
        title = title_of(block)
        if only_checks_presence(block):
            message = (
                f"'{title}' only checks that text, a key, or a file exists; "
                "assert behavior a user depends on"
            )
            findings.append(Finding(source.relative, block.line, "text-existence", message))
        if ID_TITLE.search(title):
            message = (
                f"'{title}' is named after a finding or checklist item; name the behavior "
                "and fold the case into that behavior's test"
            )
            findings.append(Finding(source.relative, block.line, "one-off", message))
        groups[" ".join(NUMBER.sub("0", block.bare).split())].append(block)
    for copies in groups.values():
        if len(copies) >= ONE_OFF_COPIES:
            lines = ", ".join(str(item.line) for item in copies)
            message = f"tests on lines {lines} differ only in literal values; write one table"
            findings.append(Finding(source.relative, copies[0].line, "one-off", message))
    return findings
