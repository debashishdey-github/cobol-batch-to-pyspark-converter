"""
COBOL Lexer
===========
The lexer (also called a *tokeniser*) is the very first stage of any
compiler or interpreter.  Its job is to read raw source text and break it
into a flat stream of *tokens* — small labelled chunks that the parser can
reason about.

Why do we need a lexer at all?
  Without tokenisation the parser would have to handle raw strings character
  by character, mixing concerns (what is this text?) with logic (what does it
  mean?).  Separating the two makes both stages simpler and more testable.

COBOL tokenisation quirks:
  * COBOL keywords are NOT case-sensitive (READ = read = Read).
  * Literals use single-quotes: 'PREMIUM', 'Y'.
  * Numeric literals are plain digits, optionally with a decimal point.
  * COBOL traditionally lived in fixed-width columns; we normalise that away.
  * Identifiers (field names) use hyphens: CUSTOMER-ID, ACCOUNT-BALANCE.
"""

from __future__ import annotations
import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class TokenType(Enum):
    # Structural keywords
    IDENTIFICATION  = auto()
    ENVIRONMENT     = auto()
    DATA            = auto()
    PROCEDURE       = auto()
    DIVISION        = auto()
    SECTION         = auto()
    WORKING_STORAGE = auto()
    FILE            = auto()

    # Data-definition keywords
    PIC             = auto()
    PICTURE         = auto()
    OCCURS          = auto()
    REDEFINES       = auto()
    VALUE           = auto()

    # Procedure keywords
    MOVE            = auto()
    TO              = auto()
    IF              = auto()
    ELSE            = auto()
    END_IF          = auto()
    PERFORM         = auto()
    UNTIL           = auto()
    TIMES           = auto()
    VARYING         = auto()
    FROM            = auto()
    BY              = auto()
    READ            = auto()
    WRITE           = auto()
    COMPUTE         = auto()
    ADD             = auto()
    SUBTRACT        = auto()
    MULTIPLY        = auto()
    DIVIDE          = auto()
    INTO            = auto()
    GIVING          = auto()
    REMAINDER       = auto()
    STOP            = auto()
    RUN             = auto()
    AT              = auto()
    END             = auto()
    NOT             = auto()
    AND             = auto()
    OR              = auto()
    EQUAL           = auto()
    GREATER         = auto()
    LESS            = auto()
    THAN            = auto()
    GREATER_THAN    = auto()
    LESS_THAN       = auto()
    EQUAL_TO        = auto()
    THRU            = auto()
    AFTER           = auto()
    BEFORE          = auto()
    EXIT            = auto()
    PROGRAM_ID      = auto()
    AUTHOR          = auto()
    DATE_WRITTEN    = auto()

    # Operators / punctuation
    EQUALS          = auto()   # =
    PLUS            = auto()   # +
    MINUS           = auto()   # -
    STAR            = auto()   # *
    SLASH           = auto()   # /
    DOT             = auto()   # .
    LPAREN          = auto()   # (
    RPAREN          = auto()   # )

    # Primitives
    INTEGER         = auto()
    DECIMAL         = auto()
    STRING_LITERAL  = auto()   # 'value'
    IDENTIFIER      = auto()   # field names, paragraph names
    LEVEL_NUMBER    = auto()   # 01, 05, 77 …

    # Housekeeping
    NEWLINE         = auto()
    EOF             = auto()
    UNKNOWN         = auto()


# Map keyword strings → token types (all lower-cased for case-insensitive match)
KEYWORDS: dict[str, TokenType] = {
    "identification":  TokenType.IDENTIFICATION,
    "environment":     TokenType.ENVIRONMENT,
    "data":            TokenType.DATA,
    "procedure":       TokenType.PROCEDURE,
    "division":        TokenType.DIVISION,
    "section":         TokenType.SECTION,
    "working-storage": TokenType.WORKING_STORAGE,
    "file":            TokenType.FILE,
    "pic":             TokenType.PIC,
    "picture":         TokenType.PICTURE,
    "occurs":          TokenType.OCCURS,
    "redefines":       TokenType.REDEFINES,
    "value":           TokenType.VALUE,
    "move":            TokenType.MOVE,
    "to":              TokenType.TO,
    "if":              TokenType.IF,
    "else":            TokenType.ELSE,
    "end-if":          TokenType.END_IF,
    "perform":         TokenType.PERFORM,
    "until":           TokenType.UNTIL,
    "times":           TokenType.TIMES,
    "varying":         TokenType.VARYING,
    "from":            TokenType.FROM,
    "by":              TokenType.BY,
    "read":            TokenType.READ,
    "write":           TokenType.WRITE,
    "compute":         TokenType.COMPUTE,
    "add":             TokenType.ADD,
    "subtract":        TokenType.SUBTRACT,
    "multiply":        TokenType.MULTIPLY,
    "divide":          TokenType.DIVIDE,
    "into":            TokenType.INTO,
    "giving":          TokenType.GIVING,
    "remainder":       TokenType.REMAINDER,
    "stop":            TokenType.STOP,
    "run":             TokenType.RUN,
    "at":              TokenType.AT,
    "end":             TokenType.END,
    "not":             TokenType.NOT,
    "and":             TokenType.AND,
    "or":              TokenType.OR,
    "equal":           TokenType.EQUAL,
    "greater":         TokenType.GREATER,
    "less":            TokenType.LESS,
    "than":            TokenType.THAN,
    "thru":            TokenType.THRU,
    "after":           TokenType.AFTER,
    "before":          TokenType.BEFORE,
    "exit":            TokenType.EXIT,
    "program-id":      TokenType.PROGRAM_ID,
    "author":          TokenType.AUTHOR,
    "date-written":    TokenType.DATE_WRITTEN,
}


@dataclass
class Token:
    """A single lexical unit produced by the Lexer."""
    type: TokenType
    value: str        # the raw text as it appeared in the source
    line: int         # 1-based line number (for error messages)

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


class Lexer:
    """Tokenise a COBOL source string.

    Usage::

        lexer = Lexer(source_code)
        tokens = lexer.tokenise()

    The result is a list of Token objects ending with a single EOF token.
    """

    def __init__(self, source: str) -> None:
        self._source = source
        self._pos = 0
        self._line = 1
        self._tokens: List[Token] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenise(self) -> List[Token]:
        """Convert the source string into a flat list of tokens."""
        while self._pos < len(self._source):
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._source):
                break
            ch = self._source[self._pos]

            if ch == '\n':
                self._line += 1
                self._pos += 1
                continue

            if ch == "'":
                self._read_string_literal()
            elif ch == '.':
                self._emit(TokenType.DOT, '.')
                self._pos += 1
            elif ch == '(':
                self._emit(TokenType.LPAREN, '(')
                self._pos += 1
            elif ch == ')':
                self._emit(TokenType.RPAREN, ')')
                self._pos += 1
            elif ch == '=':
                self._emit(TokenType.EQUALS, '=')
                self._pos += 1
            elif ch == '+':
                self._emit(TokenType.PLUS, '+')
                self._pos += 1
            elif ch == '-' and not self._looks_like_identifier_continuation():
                self._emit(TokenType.MINUS, '-')
                self._pos += 1
            elif ch == '*':
                # A * at the start of a line is a COBOL comment — skip
                if self._at_line_start():
                    self._skip_to_eol()
                else:
                    self._emit(TokenType.STAR, '*')
                    self._pos += 1
            elif ch == '/':
                self._emit(TokenType.SLASH, '/')
                self._pos += 1
            elif ch == '>':
                self._emit(TokenType.GREATER_THAN, '>')
                self._pos += 1
            elif ch == '<':
                self._emit(TokenType.LESS_THAN, '<')
                self._pos += 1
            elif ch.isdigit():
                self._read_number()
            elif ch.isalpha() or ch == '_':
                self._read_word()
            else:
                # Unknown character — skip silently (not worth crashing)
                self._pos += 1

        self._emit(TokenType.EOF, '')
        return self._tokens

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, token_type: TokenType, value: str) -> None:
        self._tokens.append(Token(token_type, value, self._line))

    def _skip_whitespace_and_comments(self) -> None:
        while self._pos < len(self._source) and self._source[self._pos] in (' ', '\t', '\r'):
            self._pos += 1

    def _skip_to_eol(self) -> None:
        while self._pos < len(self._source) and self._source[self._pos] != '\n':
            self._pos += 1

    def _at_line_start(self) -> bool:
        """True if the only characters before the current position on this line are spaces."""
        i = self._pos - 1
        while i >= 0 and self._source[i] != '\n':
            if self._source[i] not in (' ', '\t'):
                return False
            i -= 1
        return True

    def _looks_like_identifier_continuation(self) -> bool:
        """A hyphen is part of an identifier (e.g. CUSTOMER-ID) if it is
        surrounded by alphanumeric characters."""
        before = self._pos > 0 and self._source[self._pos - 1].isalnum()
        after = (self._pos + 1 < len(self._source) and
                 self._source[self._pos + 1].isalpha())
        return before and after

    def _read_string_literal(self) -> None:
        start = self._pos
        self._pos += 1  # skip opening quote
        while self._pos < len(self._source) and self._source[self._pos] != "'":
            if self._source[self._pos] == '\n':
                self._line += 1
            self._pos += 1
        self._pos += 1  # skip closing quote
        self._emit(TokenType.STRING_LITERAL, self._source[start:self._pos])

    def _read_number(self) -> None:
        start = self._pos
        has_dot = False
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch.isdigit():
                self._pos += 1
            elif ch == '.' and not has_dot:
                has_dot = True
                self._pos += 1
            else:
                break
        raw = self._source[start:self._pos]
        # Level numbers are 01–49 or 66, 77, 88
        if not has_dot and int(raw) in self._level_number_set():
            # Peek ahead: next non-space char should be alpha (field name)
            peek = self._pos
            while peek < len(self._source) and self._source[peek] in (' ', '\t'):
                peek += 1
            if peek < len(self._source) and (self._source[peek].isalpha() or self._source[peek] == '\n'):
                self._emit(TokenType.LEVEL_NUMBER, raw)
                return
        self._emit(TokenType.DECIMAL if has_dot else TokenType.INTEGER, raw)

    @staticmethod
    def _level_number_set() -> set:
        return set(range(1, 50)) | {66, 77, 88}

    def _read_word(self) -> None:
        """Read an identifier or keyword.  Hyphens inside words are part of the token."""
        start = self._pos
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch.isalnum() or ch == '_':
                self._pos += 1
            elif ch == '-':
                # Include the hyphen only if next char is alphanumeric
                if (self._pos + 1 < len(self._source) and
                        self._source[self._pos + 1].isalnum()):
                    self._pos += 1
                else:
                    break
            else:
                break
        word = self._source[start:self._pos]
        token_type = KEYWORDS.get(word.lower(), TokenType.IDENTIFIER)
        self._emit(token_type, word)
