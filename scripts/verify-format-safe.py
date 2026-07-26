#!/usr/bin/env python3
"""Prove a Python formatting pass changed nothing semantic.

Formatters do more than move whitespace. `ruff format` and `black` also add
magic trailing commas, normalize quote characters, and rewrite string prefixes.
Those change the file's bytes while leaving behavior identical, so a naive
byte- or whitespace-diff reports a false alarm.

Comparing the parsed AST is the correct test: it ignores formatting entirely
and fails only if a token that affects behavior actually moved.

    verify-format-safe.py BEFORE.py AFTER.py

Exit 0 = semantically identical. Exit 1 = real change, review before committing.
Exit 2 = a file failed to parse.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_CHANGED = 1
EXIT_PARSE_ERROR = 2


def normalized_ast(path: Path) -> str:
    """Return a formatting-independent dump of the file's syntax tree.

    Line and column attributes are excluded — those legitimately change during
    reformatting and carry no semantic weight.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return EXIT_PARSE_ERROR

    before, after = Path(argv[1]), Path(argv[2])

    try:
        before_ast = normalized_ast(before)
        after_ast = normalized_ast(after)
    except SyntaxError as exc:
        print(f"  PARSE ERROR: {exc}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    if before_ast == after_ast:
        print("  RESULT: AST identical — formatting was semantically neutral")
        return EXIT_OK

    print("  RESULT: AST DIFFERS — formatter changed behavior, review the diff")
    return EXIT_CHANGED


if __name__ == "__main__":
    sys.exit(main(sys.argv))
