"""Separate code from comments and literals in JavaScript-family and C-family source.

Pattern checks must not fire on a word inside a comment or a string, and paren
matching must not count a parenthesis inside a literal. Blanking keeps every
offset and newline in place, so a match position still maps to its line.
"""

from bisect import bisect_right
from dataclasses import dataclass

# A slash after one of these characters, or at the start, begins a regular
# expression literal rather than a division.
REGEX_PRECEDERS = frozenset("(,=:[!&|?{};+-*%<>~^")
REGEX_KEYWORDS = frozenset(
    {
        "return",
        "typeof",
        "case",
        "do",
        "else",
        "in",
        "of",
        "new",
        "delete",
        "void",
        "throw",
        "yield",
        "await",
        "instanceof",
    }
)


@dataclass(frozen=True)
class Masked:
    """Hold two blanked views of one source text and its comments by line."""

    code: str
    bare: str
    comments: tuple[tuple[int, str], ...]
    line_starts: tuple[int, ...]

    def line_of(self, offset: int) -> int:
        """Return the one-based line number holding a character offset."""
        return bisect_right(self.line_starts, offset)


@dataclass(frozen=True)
class Dialect:
    """Describe which literal forms a language family has."""

    regex_literals: bool
    template_expressions: bool


SCRIPT = Dialect(regex_literals=True, template_expressions=True)
C_FAMILY = Dialect(regex_literals=False, template_expressions=False)


class _Scanner:
    """Walk a source text once, blanking comments and literals in place."""

    def __init__(self, text: str, dialect: Dialect) -> None:
        self.text = text
        self.dialect = dialect
        self.code = list(text)
        self.bare = list(text)
        self.comments: list[tuple[int, str]] = []
        self.index = 0
        # Brace depth inside each open `${ ... }` template expression.
        self.template_depths: list[int] = []
        starts = [0]
        starts.extend(position + 1 for position, char in enumerate(text) if char == "\n")
        self.line_starts = tuple(starts)

    def masked(self) -> Masked:
        """Scan the whole text and return both views."""
        while self.index < len(self.text):
            self.step()
        return Masked(
            "".join(self.code), "".join(self.bare), tuple(self.comments), self.line_starts
        )

    def blank(self, start: int, end: int, *, comment: bool) -> None:
        """Replace a span with spaces in the bare view, and in the code view for comments."""
        for position in range(start, end):
            if self.text[position] != "\n":
                self.bare[position] = " "
                if comment:
                    self.code[position] = " "

    def step(self) -> None:
        """Consume one token-starting character."""
        char = self.text[self.index]
        pair = self.text[self.index : self.index + 2]
        if pair == "//":
            self.comment(self.text.find("\n", self.index), 0)
        elif pair == "/*":
            self.comment(self.text.find("*/", self.index + 2), len("*/"))
        elif char in "'\"":
            self.string(char)
        elif char == "`":
            self.template(self.index + 1)
        elif char == "/" and self.dialect.regex_literals and self.regex_allowed():
            self.regex()
        else:
            self.code_char(char)

    def comment(self, end: int, terminator: int) -> None:
        """Blank a comment through its terminator or the end of the text."""
        stop = len(self.text) if end < 0 else end + terminator
        line = bisect_right(self.line_starts, self.index)
        self.comments.append((line, self.text[self.index : stop]))
        self.blank(self.index, stop, comment=True)
        self.index = stop

    def string(self, quote: str) -> None:
        """Blank a quoted literal, ending at its closing quote or the line end."""
        position = self.index + 1
        while position < len(self.text) and self.text[position] not in (quote, "\n"):
            position += 2 if self.text[position] == "\\" else 1
        stop = min(position + 1, len(self.text))
        self.blank(self.index, stop, comment=False)
        self.index = stop

    def template(self, position: int) -> None:
        """Blank template text up to its closing backtick or an embedded expression."""
        start = self.index
        while position < len(self.text):
            char = self.text[position]
            if char == "\\":
                position += 2
                continue
            if char == "`":
                position += 1
                break
            if self.dialect.template_expressions and self.text[position : position + 2] == "${":
                self.blank(start, position, comment=False)
                self.template_depths.append(0)
                self.index = position + 2
                return
            position += 1
        stop = min(position, len(self.text))
        self.blank(start, stop, comment=False)
        self.index = stop

    def code_char(self, char: str) -> None:
        """Track template-expression braces; every other code character stays."""
        if self.template_depths:
            if char == "{":
                self.template_depths[-1] += 1
            elif char == "}":
                if not self.template_depths[-1]:
                    self.template_depths.pop()
                    self.index += 1
                    self.template(self.index)
                    return
                self.template_depths[-1] -= 1
        self.index += 1

    def regex_allowed(self) -> bool:
        """Decide whether a slash starts a regular expression literal."""
        position = self.index - 1
        while position >= 0 and self.bare[position].isspace():
            position -= 1
        if position < 0 or self.bare[position] in REGEX_PRECEDERS:
            return True
        end = position + 1
        while position >= 0 and (self.bare[position].isalnum() or self.bare[position] in "_$"):
            position -= 1
        return "".join(self.bare[position + 1 : end]) in REGEX_KEYWORDS

    def regex(self) -> None:
        """Blank a regular expression literal and its flags."""
        position = self.index + 1
        in_class = False
        while position < len(self.text):
            char = self.text[position]
            if char == "\n":
                self.index += 1
                return
            if char == "\\":
                position += 2
                continue
            if char == "[":
                in_class = True
            elif char == "]":
                in_class = False
            elif char == "/" and not in_class:
                break
            position += 1
        position += 1
        while position < len(self.text) and self.text[position].isalpha():
            position += 1
        stop = min(position, len(self.text))
        self.blank(self.index, stop, comment=False)
        self.index = stop


def mask(text: str, dialect: Dialect) -> Masked:
    """Return comment-free and literal-free views of source text."""
    return _Scanner(text, dialect).masked()


def matching_close(bare: str, open_index: int) -> int:
    """Return the offset of the bracket closing the one at `open_index`, or -1."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    expected: list[str] = []
    for position in range(open_index, len(bare)):
        char = bare[position]
        if char in pairs:
            expected.append(pairs[char])
        elif char in ")]}":
            if not expected or expected.pop() != char:
                return -1
            if not expected:
                return position
    return -1
