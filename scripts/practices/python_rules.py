"""Check Python sources through their syntax tree, so strings and comments never match."""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from typing import TYPE_CHECKING

from .error_rules import python_error_findings
from .model import Finding
from .parallel_rules import python_command_findings

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from .source import SourceFile

DOUBLE_MODULES: Mapping[str, str] = {
    "unittest.mock": "mock",
    "mock": "mock",
    "pytest_mock": "mock",
    "flexmock": "mock",
    "doublex": "mock",
    "freezegun": "fake-timer",
    "time_machine": "fake-timer",
    "responses": "fake-server",
    "respx": "fake-server",
    "requests_mock": "fake-server",
    "httpretty": "fake-server",
    "aioresponses": "fake-server",
    "pytest_httpserver": "fake-server",
    "pytest_localserver": "fake-server",
    "pytest_httpx": "fake-server",
    "fakeredis": "stand-in",
    "mongomock": "stand-in",
    "moto": "stand-in",
    "pyfakefs": "stand-in",
    "flaky": "rerun",
    "pytest_rerunfailures": "rerun",
}
DOUBLE_MESSAGES: Mapping[str, str] = {
    "mock": "replaces real behavior with a test double; exercise the real code",
    "fake-timer": "fakes the clock; wait for the real condition instead",
    "fake-server": "answers as a server with hand-written responses; test the real service live",
    "stand-in": "stands in for a real store, keyring, or filesystem; use the real one",
    "rerun": "re-runs failing tests until they pass; find and fix the cause",
    "hand-written-double": (
        "is a hand-written stand-in for a dependency, with or without a mocking library; "
        "test against the real one"
    ),
}
# Names that declare a hand-written double: a class, function, or namespace that
# pretends to be a dependency. A following capital, digit, or underscore keeps
# words such as Mockingbird or Stubborn out.
DOUBLE_PREFIXES = "Fake|Stub|Mock|Spy|Dummy|InMemory|Scripted|Canned"
DOUBLE_CLASS = re.compile(rf"^(?:{DOUBLE_PREFIXES})(?:[A-Z0-9_]\w*)?$")
DOUBLE_FUNCTION = re.compile(
    r"^(?:fake|stub|mock|spy|dummy|in_?memory|scripted|canned)(?:[A-Z0-9_]\w*)?$"
)
TYPE_BUILDER_ARGS = 3
HANDLER_BASES = frozenset(
    {
        "BaseHTTPRequestHandler",
        "SimpleHTTPRequestHandler",
        "BaseRequestHandler",
        "StreamRequestHandler",
        "DatagramRequestHandler",
    }
)
REPLACING_MONKEYPATCH = frozenset({"setattr", "delattr"})
SLEEP_OWNERS = frozenset({"time", "asyncio", "trio", "anyio"})
FILE_READS = frozenset(
    {
        "open",
        "read_text",
        "read_bytes",
        "exists",
        "is_file",
        "is_dir",
        "isfile",
        "isdir",
        "glob",
        "rglob",
        "iterdir",
        "listdir",
        "scandir",
    }
)
# Calls that only look at files or text. A test made of nothing else never
# runs the product, so it cannot notice the product breaking.
INSPECTION_CALLS = FILE_READS | frozenset(
    {
        "Path",
        "PurePath",
        "joinpath",
        "relative_to",
        "as_posix",
        "resolve",
        "absolute",
        "with_name",
        "with_suffix",
        "read",
        "readlines",
        "splitlines",
        "strip",
        "lstrip",
        "rstrip",
        "lower",
        "upper",
        "casefold",
        "startswith",
        "endswith",
        "find",
        "count",
        "split",
        "rsplit",
        "join",
        "replace",
        "encode",
        "decode",
        "format",
        "loads",
        "load",
        "safe_load",
        "search",
        "findall",
        "finditer",
        "match",
        "fullmatch",
        "compile",
        "escape",
        "len",
        "any",
        "all",
        "sorted",
        "set",
        "frozenset",
        "list",
        "dict",
        "tuple",
        "str",
        "keys",
        "values",
        "items",
        "get",
        "iter",
        "next",
        "enumerate",
        "zip",
        "range",
        "isinstance",
        "subTest",
        "dirname",
        "basename",
        "abspath",
        "realpath",
        "normpath",
    }
)
EXISTENCE_ASSERTIONS = frozenset(
    {
        "assertIn",
        "assertNotIn",
        "assertTrue",
        "assertFalse",
        "assertRegex",
        "assertNotRegex",
        "assertIsNone",
        "assertIsNotNone",
    }
)
ID_NAMED_TEST = re.compile(
    r"(?:^|_)(?:finding|item|checklist|rule|lesson|pitfall|issue|ticket|bug)_?\d+(?:_|$)",
    re.IGNORECASE,
)
# Three tests whose bodies differ only in literal values are one behavior
# written out per case; a table-driven test states it once.
ONE_OFF_COPIES = 3


def dotted(node: ast.expr) -> str:
    """Return a dotted name for a Name/Attribute chain, or an empty string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        owner = dotted(node.value)
        return f"{owner}.{node.attr}" if owner else ""
    return ""


def call_name(node: ast.Call) -> str:
    """Return the called function's final name, or '<dynamic>' when it has none."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return "<dynamic>"


def double_check(module: str) -> str | None:
    """Map an imported module to the double it provides."""
    for prefix, check in DOUBLE_MODULES.items():
        if module == prefix or module.startswith(prefix + "."):
            return check
    return None


def builds_behavior(value: ast.expr) -> bool:
    """Report a lambda or an in-place namespace, the shapes a hand-written double takes."""
    if isinstance(value, ast.Lambda):
        return True
    if not isinstance(value, ast.Call):
        return False
    name = call_name(value)
    # type(name, bases, namespace) builds a class; type(value) only reads one.
    return name == "SimpleNamespace" or (name == "type" and len(value.args) == TYPE_BUILDER_ARGS)


def imported_modules(node: ast.AST) -> list[str]:
    """Return the full module names an import statement brings in."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
        return [node.module, *(f"{node.module}.{alias.name}" for alias in node.names)]
    return []


class _Visitor:
    """Collect per-node findings for one file in a single walk."""

    def __init__(self, source: SourceFile) -> None:
        self.source = source
        self.findings: list[Finding] = []

    def add(self, node: ast.AST, check: str, message: str) -> None:
        """Record a finding at a node's line."""
        self.findings.append(
            Finding(self.source.relative, getattr(node, "lineno", 1), check, message)
        )

    def visit(self, tree: ast.Module) -> None:
        """Inspect every node once."""
        for node in ast.walk(tree):
            self.imports(node)
            if isinstance(node, ast.Attribute) and dotted(node) == "unittest.mock":
                self.add(node, "mock", f"unittest.mock {DOUBLE_MESSAGES['mock']}")
            if isinstance(node, ast.Call):
                self.call(node)
            if self.source.is_test:
                self.test_node(node)
                self.hand_written_double(node)

    def hand_written_double(self, node: ast.AST) -> None:
        """Refuse a class, function, lambda, or namespace named as a double in test code."""
        names: list[str] = []
        if isinstance(node, ast.ClassDef):
            bases = {dotted(base).rsplit(".", 1)[-1] for base in node.bases}
            # A request-handler class is already refused as a fake server.
            if DOUBLE_CLASS.match(node.name) and not bases & HANDLER_BASES:
                names.append(node.name)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if DOUBLE_FUNCTION.match(node.name):
                names.append(node.name)
        elif isinstance(node, ast.Assign) and builds_behavior(node.value):
            names.extend(
                target.id
                for target in node.targets
                if isinstance(target, ast.Name) and DOUBLE_FUNCTION.match(target.id)
            )
        for name in names:
            message = f"{name} {DOUBLE_MESSAGES['hand-written-double']}"
            self.add(node, "hand-written-double", message)

    def imports(self, node: ast.AST) -> None:
        """Refuse imports of doubling, fake-clock, fake-server, stand-in, or re-run tools."""
        for module in imported_modules(node):
            check = double_check(module)
            if check:
                self.add(node, check, f"{module} {DOUBLE_MESSAGES[check]}")
                return

    def call(self, node: ast.Call) -> None:
        """Refuse behavior replacement through monkeypatch and the mocker fixture."""
        owner = dotted(node.func.value) if isinstance(node.func, ast.Attribute) else ""
        name = call_name(node)
        if owner == "monkeypatch" and name in REPLACING_MONKEYPATCH:
            self.add(node, "mock", f"monkeypatch.{name} {DOUBLE_MESSAGES['mock']}")
        if self.source.is_test and name == "sleep" and owner in {"", *SLEEP_OWNERS}:
            first = node.args[0] if node.args else None
            if not (isinstance(first, ast.Constant) and first.value == 0):
                self.add(
                    node,
                    "fixed-delay",
                    "sleeps for a fixed delay; wait until the expected condition holds",
                )

    def test_node(self, node: ast.AST) -> None:
        """Refuse fake servers, mocker parameters, re-run markers, and timeout overrides."""
        if isinstance(node, ast.ClassDef):
            bases = {dotted(base).rsplit(".", 1)[-1] for base in node.bases}
            if bases & HANDLER_BASES:
                self.add(node, "fake-server", f"{node.name} {DOUBLE_MESSAGES['fake-server']}")
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            return
        if any(argument.arg == "mocker" for argument in node.args.args):
            self.add(node, "mock", f"the mocker fixture {DOUBLE_MESSAGES['mock']}")
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            name = dotted(target)
            if name.rsplit(".", 1)[-1] == "flaky":
                self.add(decorator, "rerun", f"@{name} {DOUBLE_MESSAGES['rerun']}")
            elif name.endswith("mark.timeout"):
                self.add(
                    decorator,
                    "timeout-override",
                    "overrides the test timeout; keep the repository default and fix the slowness",
                )


def test_functions(tree: ast.Module) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield module-level and class-level test functions."""
    for node in tree.body:
        candidates = node.body if isinstance(node, ast.ClassDef) else [node]
        for item in candidates:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef) and item.name.startswith(
                "test"
            ):
                yield item


def is_existence_assertion(node: ast.AST) -> bool | None:
    """Classify an assertion: True for presence-only, False for others, None if not one."""
    if isinstance(node, ast.Call) and call_name(node).startswith("assert"):
        return call_name(node) in EXISTENCE_ASSERTIONS
    if not isinstance(node, ast.Assert):
        return None
    test = node.test.operand if isinstance(node.test, ast.UnaryOp) else node.test
    if isinstance(test, ast.Compare):
        return all(isinstance(op, ast.In | ast.NotIn) for op in test.ops)
    if isinstance(test, ast.Call):
        return call_name(test) in FILE_READS
    return isinstance(test, ast.Name | ast.Attribute)


def only_checks_presence(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Report a test that reads files and asserts only that text, keys, or files exist."""
    kinds = [
        kind for node in ast.walk(function) if (kind := is_existence_assertion(node)) is not None
    ]
    calls = {
        call_name(node)
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and not call_name(node).startswith("assert")
    }
    return bool(kinds) and all(kinds) and calls <= INSPECTION_CALLS and bool(calls & FILE_READS)


def shape(node: ast.AST) -> str:
    """Describe a syntax tree with every literal value removed."""
    if isinstance(node, ast.Constant):
        return "Constant"
    fields = []
    for name, value in ast.iter_fields(node):
        if isinstance(value, list):
            items = ",".join(
                shape(item) if isinstance(item, ast.AST) else repr(item) for item in value
            )
            fields.append(f"{name}=[{items}]")
        elif isinstance(value, ast.AST):
            fields.append(f"{name}={shape(value)}")
        else:
            fields.append(f"{name}={value!r}")
    return f"{type(node).__name__}({','.join(fields)})"


def test_shape_findings(source: SourceFile, tree: ast.Module) -> list[Finding]:
    """Refuse presence-only tests, tests named after findings, and copied test bodies."""
    findings = []
    groups: defaultdict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = defaultdict(list)
    for function in test_functions(tree):
        if only_checks_presence(function):
            message = (
                f"{function.name} only checks that text, a key, or a file exists; "
                "assert behavior a user depends on"
            )
            findings.append(Finding(source.relative, function.lineno, "text-existence", message))
        if ID_NAMED_TEST.search(function.name):
            message = (
                f"{function.name} is named after a finding or checklist item; name the "
                "behavior and fold the case into that behavior's test"
            )
            findings.append(Finding(source.relative, function.lineno, "one-off", message))
        groups["".join(shape(statement) for statement in function.body)].append(function)
    for copies in groups.values():
        if len(copies) >= ONE_OFF_COPIES:
            names = ", ".join(item.name for item in copies)
            message = f"{names} differ only in literal values; write one table-driven test"
            findings.append(Finding(source.relative, copies[0].lineno, "one-off", message))
    return findings


def analyze(source: SourceFile, text: str) -> list[Finding]:
    """Run every Python check on one file."""
    try:
        tree = ast.parse(text, filename=source.relative)
    except (SyntaxError, ValueError) as error:
        message = f"cannot parse Python, so its practices were not checked: {error}"
        return [Finding(source.relative, 1, "unparsed", message)]
    visitor = _Visitor(source)
    visitor.visit(tree)
    findings = visitor.findings
    findings.extend(python_error_findings(source, tree))
    findings.extend(python_command_findings(source, tree))
    if source.is_test:
        findings.extend(test_shape_findings(source, tree))
    return findings
