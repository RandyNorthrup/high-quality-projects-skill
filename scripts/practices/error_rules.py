"""Refuse error handlers that drop the caught error and report a fixed message instead.

A catch-all handler that answers every failure with one sentence, such as "not
available", hides the real cause: a usage limit, a network failure, and a bug
then read the same, and whoever reads the message fixes the wrong thing. A
handler that catches everything must keep the cause: re-raise it, chain it, log
it, or include it in the message.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

from .masking import matching_close
from .model import Finding

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from .masking import Masked
    from .source import SourceFile

MESSAGE = (
    "catches every error and reports a fixed message instead; name the real cause "
    "by re-raising, chaining, logging, or including the caught error"
)
BROAD_PYTHON = frozenset({"Exception", "BaseException"})
# Calls that record the active exception without naming its variable.
CAUSE_RECORDERS = frozenset(
    {"exception", "print_exc", "format_exc", "print_exception", "format_exception", "exc_info"}
)
# Handler heads that catch every error, by language. The optional `name` group
# is the variable that holds the caught error.
CATCH_ALL_HEADS: Mapping[str, re.Pattern[str]] = {
    "script": re.compile(r"\bcatch\s*(?:\(\s*(?P<name>[A-Za-z_$][\w$]*)?[^()]*\))?\s*\{"),
    "csharp": re.compile(
        r"\bcatch\s*(?:\(\s*(?:global::)?(?:System\.)?Exception"
        r"(?:\s+(?P<name>\w+))?\s*\))?\s*\{"
    ),
    "java": re.compile(
        r"\bcatch\s*\(\s*(?:final\s+)?(?:java\.lang\.)?(?:Exception|Throwable)"
        r"\s+(?P<name>\w+)\s*\)\s*\{"
    ),
    "kotlin": re.compile(
        r"\bcatch\s*\(\s*(?P<name>\w+)\s*:\s*(?:java\.lang\.|kotlin\.)?"
        r"(?:Exception|Throwable)\s*\)\s*\{"
    ),
    "cpp": re.compile(
        r"\bcatch\s*\(\s*(?:\.\.\.|(?:const\s+)?(?:std::)?exception\s*&\s*(?P<name>\w+)?)"
        r"\s*\)\s*\{"
    ),
    "go": re.compile(r"\bif\s+(?:[^{};\n]*;\s*)?(?P<name>err\w*)\s*!=\s*nil\s*\{"),
}
# A promise rejection handler written as an arrow function, with its parameter.
PROMISE_CATCH = re.compile(
    r"\.\s*catch\s*\(\s*(?:async\s*)?"
    r"(?:\(\s*(?P<listed>[A-Za-z_$][\w$]*)?[^()]*\)|(?P<bare>[A-Za-z_$][\w$]*))\s*=>"
)
# A Rust closure that discards the error it maps.
DISCARDED_RUST_ERROR = re.compile(r"\.\s*map_err\s*\(\s*(?:move\s*)?\|\s*_\w*\s*\|")
RETHROW = re.compile(r"\bthrow\s*;")
EMITS = re.compile(r"\bthrow\b|\bpanic\s*\(")


def type_name(node: ast.expr | None) -> str:
    """Return the final name of a caught exception type, or '' for a bare handler."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def catches_everything(handler: ast.ExceptHandler) -> bool:
    """Report a bare handler or one that names Exception or BaseException."""
    if handler.type is None:
        return True
    kinds = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(type_name(kind) in BROAD_PYTHON for kind in kinds)


def handler_nodes(handler: ast.ExceptHandler) -> Iterator[ast.AST]:
    """Walk a handler body without entering nested functions or classes."""
    pending: list[ast.AST] = list(handler.body)
    while pending:
        node = pending.pop()
        yield node
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef):
            pending.extend(ast.iter_child_nodes(node))


def keeps_cause(handler: ast.ExceptHandler, nodes: list[ast.AST]) -> bool:
    """Report a handler that re-raises, names the caught error, or logs the active one."""
    for node in nodes:
        if isinstance(node, ast.Raise) and node.exc is None:
            return True
        if handler.name and isinstance(node, ast.Name) and node.id == handler.name:
            return True
        if isinstance(node, ast.Call) and (
            type_name(node.func) in CAUSE_RECORDERS
            or any(keyword.arg == "exc_info" for keyword in node.keywords)
        ):
            return True
    return False


def has_text(node: ast.AST) -> bool:
    """Report a string literal or f-string anywhere inside a node."""
    return any(
        isinstance(item, ast.JoinedStr)
        or (isinstance(item, ast.Constant) and isinstance(item.value, str))
        for item in ast.walk(node)
    )


def emits_message(nodes: list[ast.AST]) -> bool:
    """Report a handler that raises a new error or produces text in its place."""
    for node in nodes:
        if isinstance(node, ast.Raise) and node.exc is not None:
            return True
        if isinstance(node, ast.Return) and node.value is not None and has_text(node.value):
            return True
        if isinstance(node, ast.Call) and any(
            has_text(argument)
            for argument in (*node.args, *(keyword.value for keyword in node.keywords))
        ):
            return True
    return False


def python_error_findings(source: SourceFile, tree: ast.Module) -> list[Finding]:
    """Refuse catch-all handlers in product code that replace the error with a message."""
    if source.is_test:
        return []
    findings = []
    for handler in ast.walk(tree):
        if not isinstance(handler, ast.ExceptHandler) or not catches_everything(handler):
            continue
        nodes = list(handler_nodes(handler))
        if emits_message(nodes) and not keeps_cause(handler, nodes):
            findings.append(Finding(source.relative, handler.lineno, "error-cause", MESSAGE))
    return findings


def drops_cause(masked: Masked, start: int, end: int, name: str | None) -> bool:
    """Report a handler body that emits text or a new error without naming the caught one."""
    bare = masked.bare[start:end]
    if RETHROW.search(bare):
        return False
    if name and re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", bare):
        return False
    return masked.code[start:end] != bare or EMITS.search(bare) is not None


def masked_error_findings(source: SourceFile, masked: Masked) -> list[Finding]:
    """Refuse catch-all handlers in JavaScript-family and C-family product code."""
    if source.is_test:
        return []
    found: list[int] = []
    head = CATCH_ALL_HEADS.get(source.language)
    for match in head.finditer(masked.bare) if head else ():
        opening = match.end() - 1
        closing = matching_close(masked.bare, opening)
        if closing > opening and drops_cause(masked, opening + 1, closing, match["name"]):
            found.append(match.start())
    if source.language == "script":
        for match in PROMISE_CATCH.finditer(masked.bare):
            opening = masked.bare.index("(", match.start())
            closing = matching_close(masked.bare, opening)
            name = match["listed"] or match["bare"]
            if closing > opening and drops_cause(masked, match.end(), closing, name):
                found.append(match.start())
    if source.language == "rust":
        found.extend(match.start() for match in DISCARDED_RUST_ERROR.finditer(masked.bare))
    return [
        Finding(source.relative, masked.line_of(offset), "error-cause", MESSAGE) for offset in found
    ]
