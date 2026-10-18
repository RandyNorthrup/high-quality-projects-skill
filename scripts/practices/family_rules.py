"""Check Rust, Go, C#, Java, Kotlin, C, C++, and PowerShell sources with masked patterns.

These checks match imports, calls, and type names by pattern, not by a full
parser. They cover the common doubling, hand-written double, fake-clock,
fake-server, re-run, and fixed-delay forms; test shape is analyzed only for
Python and the JavaScript family.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .masking import matching_close
from .model import Finding
from .python_rules import DOUBLE_MESSAGES, DOUBLE_PREFIXES
from .source import strip_hash_comment

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .masking import Masked
    from .source import SourceFile

Rule = tuple[re.Pattern[str], str]

JVM_IMPORT_RULES: tuple[Rule, ...] = (
    (
        re.compile(
            r"^\s*import\s+(?:static\s+)?(?:org\.mockito|org\.easymock|org\.powermock"
            r"|mockit|io\.mockk)\b",
            re.MULTILINE,
        ),
        "mock",
    ),
    (
        re.compile(
            r"^\s*import\s+(?:static\s+)?(?:com\.github\.tomakehurst\.wiremock|org\.mockserver)\b",
            re.MULTILINE,
        ),
        "fake-server",
    ),
    (re.compile(r"@RetryingTest\b"), "rerun"),
)
IMPORT_RULES: Mapping[str, tuple[Rule, ...]] = {
    "csharp": (
        (
            re.compile(
                r"^\s*using\s+(?:static\s+)?(?:Moq|NSubstitute|FakeItEasy|Telerik\.JustMock"
                r"|Rhino\.Mocks)\b",
                re.MULTILINE,
            ),
            "mock",
        ),
        (re.compile(r"^\s*using\s+WireMock\b", re.MULTILINE), "fake-server"),
        (re.compile(r"\bFakeTimeProvider\b"), "fake-timer"),
        (re.compile(r"\[\s*Retry\s*\("), "rerun"),
    ),
    "rust": (
        (re.compile(r"\buse\s+(?:mockall|faux|mockiato)\b|#\[\s*automock\s*\]"), "mock"),
        (re.compile(r"\buse\s+(?:mockito|wiremock|httpmock)\b"), "fake-server"),
    ),
    "go": (
        (
            re.compile(
                r'"(?:github\.com/golang/mock|go\.uber\.org/mock'
                r'|github\.com/stretchr/testify/mock)[/"]'
            ),
            "mock",
        ),
        (
            re.compile(
                r'"github\.com/jarcoal/httpmock"'
                r"|httptest\.NewServer\s*\(\s*http\.HandlerFunc\s*\(\s*func"
            ),
            "fake-server",
        ),
        (re.compile(r'"github\.com/(?:jonboulle/clockwork|benbjohnson/clock)"'), "fake-timer"),
    ),
    "java": JVM_IMPORT_RULES,
    "kotlin": JVM_IMPORT_RULES,
}
DELAY_RULES: Mapping[str, re.Pattern[str]] = {
    "csharp": re.compile(r"\bThread\.Sleep\s*\(|\bTask\.Delay\s*\("),
    "rust": re.compile(r"\b(?:thread|time)::sleep\s*\("),
    "go": re.compile(r"\btime\.Sleep\s*\("),
    "java": re.compile(r"\bThread\.sleep\s*\("),
    "kotlin": re.compile(r"\bThread\.sleep\s*\("),
    "c": re.compile(r"\b(?:u?sleep|nanosleep)\s*\("),
    "cpp": re.compile(r"\b(?:sleep_for|u?sleep|nanosleep)\s*\("),
}
# A type declared in test code under a double's name: C#, Java, Kotlin, Rust, C++.
DOUBLE_TYPE = re.compile(
    rf"\b(?:class|struct|record|object)\s+(?P<name>(?:{DOUBLE_PREFIXES})(?:[A-Z0-9_]\w*)?)\b"
)
# Go names unexported types in lower case.
GO_DOUBLE_TYPE = re.compile(
    r"\btype\s+(?P<name>(?:[Ff]ake|[Ss]tub|[Mm]ock|[Ss]py|[Dd]ummy|[Ii]nMemory|[Ss]cripted"
    r"|[Cc]anned)(?:[A-Z0-9_]\w*)?)\s+struct\b"
)
RUST_TEST_MODULE = re.compile(
    r"#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]\s*(?:pub(?:\s*\([^)]*\))?\s+)?mod\s+\w+\s*\{"
)
PESTER_MOCK = re.compile(r"^\s*Mock\s+[-\w]", re.IGNORECASE)
POWERSHELL_SLEEP = re.compile(r"\bStart-Sleep\b", re.IGNORECASE)
SHELL_SLEEP = re.compile(r"(?:^|[\s;&|(])sleep\s+\d")


def family_findings(source: SourceFile, masked: Masked) -> list[Finding]:
    """Refuse doubling imports in any code and fixed delays in test code."""
    findings = [
        Finding(
            source.relative,
            masked.line_of(match.start()),
            check,
            f"{match.group().strip()} {DOUBLE_MESSAGES[check]}",
        )
        for pattern, check in IMPORT_RULES.get(source.language, ())
        for match in pattern.finditer(masked.code)
    ]
    spans = test_spans(source, masked)

    def in_test(offset: int) -> bool:
        return any(start <= offset < end for start, end in spans)

    delay = DELAY_RULES.get(source.language)
    if delay:
        findings.extend(
            Finding(
                source.relative,
                masked.line_of(match.start()),
                "fixed-delay",
                "sleeps for a fixed delay; wait until the expected condition holds",
            )
            for match in delay.finditer(masked.bare)
            if in_test(match.start())
        )
    findings.extend(
        Finding(
            source.relative,
            masked.line_of(match.start()),
            "hand-written-double",
            f"{match['name']} {DOUBLE_MESSAGES['hand-written-double']}",
        )
        for pattern in (DOUBLE_TYPE, GO_DOUBLE_TYPE)
        for match in pattern.finditer(masked.bare)
        if in_test(match.start())
    )
    return findings


def test_spans(source: SourceFile, masked: Masked) -> list[tuple[int, int]]:
    """Return the offsets that hold test code: the whole of a test file, else Rust test modules.

    Rust keeps unit tests in a `#[cfg(test)]` module inside a product file, so
    the file's path alone does not say where its tests are.
    """
    if source.is_test:
        return [(0, len(masked.bare))]
    if source.language != "rust":
        return []
    spans = []
    for match in RUST_TEST_MODULE.finditer(masked.bare):
        opening = match.end() - 1
        closing = matching_close(masked.bare, opening)
        if closing > opening:
            spans.append((opening, closing))
    return spans


def powershell_findings(source: SourceFile, text: str) -> list[Finding]:
    """Refuse Pester mocks and fixed sleeps in PowerShell tests."""
    if not source.is_test:
        return []
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        code = strip_hash_comment(line)
        if PESTER_MOCK.match(code):
            message = f"Pester Mock {DOUBLE_MESSAGES['mock']}"
            findings.append(Finding(source.relative, number, "mock", message))
        if POWERSHELL_SLEEP.search(code):
            message = "sleeps for a fixed delay; wait until the expected condition holds"
            findings.append(Finding(source.relative, number, "fixed-delay", message))
    return findings


def shell_findings(source: SourceFile, text: str) -> list[Finding]:
    """Refuse fixed sleeps in shell tests, such as Bats suites."""
    if not source.is_test:
        return []
    return [
        Finding(
            source.relative,
            number,
            "fixed-delay",
            "sleeps for a fixed delay; wait until the expected condition holds",
        )
        for number, line in enumerate(text.splitlines(), start=1)
        if SHELL_SLEEP.search(strip_hash_comment(line))
    ]
