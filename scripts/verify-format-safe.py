#!/usr/bin/env python3
"""Check whether a Python formatting pass preserved the parsed AST.

Formatters do more than move whitespace. `ruff format` and `black` also add
magic trailing commas, normalize quote characters, and rewrite string prefixes.
Those change the file's bytes while often leaving its parsed syntax identical,
so a naive byte- or whitespace-diff reports a false alarm.

Comparing parsed ASTs ignores formatting and detects syntax-structure changes.
It does not replace review of comments, generated files, or the full diff.

    verify-format-safe.py BEFORE.py AFTER.py

Exit 0 = parsed AST identical. Exit 1 = AST changed; review before committing.
Exit 2 = a file failed to parse.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_CHANGED = 1
EXIT_PARSE_ERROR = 2

# sys.argv holds the script name plus the two files being compared.
EXPECTED_ARGC = 3


def normalized_ast(path: Path) -> str:
    """Return a formatting-independent dump of the file's syntax tree.

    Line and column attributes are excluded because they legitimately change
    during reformatting and are not part of the syntax structure compared here.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def main(argv: list[str]) -> int:
    """Compare two Python files and report whether their parsed ASTs match."""
    if len(argv) != EXPECTED_ARGC:
        print(__doc__, file=sys.stderr)
        return EXIT_PARSE_ERROR

    before, after = Path(argv[1]), Path(argv[2])

    try:
        before_ast = normalized_ast(before)
        after_ast = normalized_ast(after)
    except SyntaxError as exc:
        print(f"  PARSE ERROR: {exc}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    # Output is deliberately ASCII-only. This runs under whatever console the
    # agent happens to have, and a Windows terminal on the cp1252 code page
    # renders a UTF-8 em dash as a replacement character — turning the one line
    # that reports the verdict into something that looks like a broken tool.
    if before_ast == after_ast:
        print("  RESULT: AST identical - no parsed syntax change detected")
        return EXIT_OK

    print("  RESULT: AST DIFFERS - parsed syntax changed, review the diff")
    return EXIT_CHANGED


if __name__ == "__main__":
    sys.exit(main(sys.argv))
