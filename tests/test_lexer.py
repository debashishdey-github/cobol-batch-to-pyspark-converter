"""
Unit tests for the COBOL Lexer.

Learning objective:
  Understand how a lexer breaks source text into tokens.
  Each test exercises a specific COBOL token type.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cobol_pyspark_converter.parser.lexer import Lexer, TokenType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tokenise(source: str):
    return Lexer(source).tokenise()

def token_types(source: str):
    return [t.type for t in tokenise(source) if t.type != TokenType.EOF]

def token_values(source: str):
    return [t.value for t in tokenise(source) if t.type != TokenType.EOF]


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class TestKeywords:
    def test_move_keyword(self):
        types = token_types("MOVE")
        assert TokenType.MOVE in types

    def test_if_keyword(self):
        assert TokenType.IF in token_types("IF")

    def test_end_if_keyword(self):
        assert TokenType.END_IF in token_types("END-IF")

    def test_compute_keyword(self):
        assert TokenType.COMPUTE in token_types("COMPUTE")

    def test_read_keyword(self):
        assert TokenType.READ in token_types("READ")

    def test_write_keyword(self):
        assert TokenType.WRITE in token_types("WRITE")

    def test_stop_run_keywords(self):
        types = token_types("STOP RUN")
        assert TokenType.STOP in types
        assert TokenType.RUN in types

    def test_keywords_case_insensitive(self):
        assert token_types("move") == token_types("MOVE")
        assert token_types("compute") == token_types("COMPUTE")

    def test_data_division_keywords(self):
        types = token_types("DATA DIVISION.")
        assert TokenType.DATA in types
        assert TokenType.DIVISION in types
        assert TokenType.DOT in types


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

class TestIdentifiers:
    def test_simple_identifier(self):
        toks = tokenise("CUSTOMER-ID")
        assert toks[0].type == TokenType.IDENTIFIER
        assert toks[0].value == "CUSTOMER-ID"

    def test_hyphenated_identifier(self):
        toks = tokenise("ACCOUNT-BALANCE")
        assert toks[0].value == "ACCOUNT-BALANCE"

    def test_identifier_with_digits(self):
        toks = tokenise("FIELD1")
        assert toks[0].type == TokenType.IDENTIFIER

    def test_multiple_identifiers(self):
        values = token_values("CUSTOMER-ID BALANCE OUTPUT-RECORD")
        assert "CUSTOMER-ID" in values
        assert "BALANCE" in values
        assert "OUTPUT-RECORD" in values


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

class TestLiterals:
    def test_string_literal(self):
        toks = tokenise("'PREMIUM'")
        assert toks[0].type == TokenType.STRING_LITERAL
        assert toks[0].value == "'PREMIUM'"

    def test_integer_literal(self):
        toks = tokenise("1000")
        assert toks[0].type == TokenType.INTEGER
        assert toks[0].value == "1000"

    def test_decimal_literal(self):
        toks = tokenise("0.05")
        assert toks[0].type == TokenType.DECIMAL
        assert toks[0].value == "0.05"

    def test_zero_literal(self):
        toks = tokenise("0")
        assert toks[0].type == TokenType.INTEGER


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class TestOperators:
    def test_equals(self):
        assert TokenType.EQUALS in token_types("=")

    def test_greater_than(self):
        assert TokenType.GREATER_THAN in token_types(">")

    def test_less_than(self):
        assert TokenType.LESS_THAN in token_types("<")

    def test_plus(self):
        assert TokenType.PLUS in token_types("+")

    def test_minus_as_operator(self):
        # minus between numbers should be MINUS, not part of an identifier
        types = token_types("5 - 3")
        assert TokenType.MINUS in types

    def test_star(self):
        assert TokenType.STAR in token_types("PRICE * QTY")

    def test_slash(self):
        assert TokenType.SLASH in token_types("100 / 12")


# ---------------------------------------------------------------------------
# Level numbers
# ---------------------------------------------------------------------------

class TestLevelNumbers:
    def test_level_01(self):
        # "01 CUSTOMER-REC" → LEVEL_NUMBER, IDENTIFIER
        types = token_types("01 CUSTOMER-REC.")
        assert TokenType.LEVEL_NUMBER in types

    def test_level_05(self):
        types = token_types("05 BALANCE PIC 9(7)V99.")
        assert TokenType.LEVEL_NUMBER in types

    def test_level_77(self):
        types = token_types("77 WS-COUNTER PIC 9(5).")
        assert TokenType.LEVEL_NUMBER in types


# ---------------------------------------------------------------------------
# PIC clauses
# ---------------------------------------------------------------------------

class TestPICTokenisation:
    def test_pic_keyword(self):
        assert TokenType.PIC in token_types("PIC X(10)")

    def test_pic_string_components(self):
        # PIC X(10) should tokenise X as IDENTIFIER and 10 as INTEGER
        toks = [t for t in tokenise("PIC X(10)") if t.type != TokenType.EOF]
        values = [t.value for t in toks]
        assert "X" in values
        assert "10" in values

    def test_pic_with_parens(self):
        types = token_types("PIC 9(7)V99")
        assert TokenType.LPAREN in types
        assert TokenType.RPAREN in types


# ---------------------------------------------------------------------------
# Comment handling
# ---------------------------------------------------------------------------

class TestComments:
    def test_star_comment_line_skipped(self):
        source = "* This is a comment\nMOVE"
        types = token_types(source)
        assert TokenType.MOVE in types
        # The comment should not produce any tokens
        assert len(types) == 1

    def test_multiline_with_comments(self):
        source = "* comment\nIF BALANCE > 0\n* another comment\nMOVE 'X' TO FLAG"
        types = token_types(source)
        assert TokenType.IF in types
        assert TokenType.MOVE in types


# ---------------------------------------------------------------------------
# Full COBOL snippet
# ---------------------------------------------------------------------------

class TestFullSnippet:
    def test_move_to_tokenisation(self):
        toks = tokenise("MOVE 'PREMIUM' TO CUSTOMER-TYPE.")
        types = [t.type for t in toks]
        assert TokenType.MOVE in types
        assert TokenType.STRING_LITERAL in types
        assert TokenType.TO in types
        assert TokenType.IDENTIFIER in types
        assert TokenType.DOT in types

    def test_if_condition_tokenisation(self):
        toks = tokenise("IF BALANCE > 1000")
        types = [t.type for t in toks if t.type != TokenType.EOF]
        assert TokenType.IF in types
        assert TokenType.IDENTIFIER in types
        assert TokenType.GREATER_THAN in types
        assert TokenType.INTEGER in types

    def test_compute_tokenisation(self):
        toks = tokenise("COMPUTE TOTAL = PRICE * QTY.")
        types = [t.type for t in toks if t.type != TokenType.EOF]
        assert TokenType.COMPUTE in types
        assert TokenType.EQUALS in types
        assert TokenType.STAR in types

    def test_eof_always_present(self):
        toks = tokenise("STOP RUN.")
        assert toks[-1].type == TokenType.EOF
