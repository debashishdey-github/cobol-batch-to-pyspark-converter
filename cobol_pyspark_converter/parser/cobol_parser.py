"""
COBOL Parser
============
The parser is the second stage of the compilation pipeline.  It reads the
flat token stream from the Lexer and assembles it into a hierarchical AST.

Parsing strategy — Recursive Descent
--------------------------------------
We use a simple *recursive-descent* parser: one method per COBOL construct,
each consuming tokens from the front of the stream and returning an AST node.

This style is chosen deliberately for learning:
  * The code mirrors the grammar rules one-to-one.
  * There are no external parser-generator dependencies.
  * Errors are easy to trace back to a single method.

Production parsers use more sophisticated techniques (LR, LALR, PEG), but
recursive descent is the right starting point for understanding the concept.

Grammar subset supported (informally):
  program       ::= identification-div data-div procedure-div
  data-div      ::= 'DATA' 'DIVISION' '.' {field-definition}
  field-def     ::= level-number identifier 'PIC' pic-clause '.'
  procedure-div ::= 'PROCEDURE' 'DIVISION' '.' {statement}
  statement     ::= move | if | compute | add | subtract | multiply |
                    divide | read | write | perform | stop-run
"""

from __future__ import annotations
import re
from typing import List, Optional

from .lexer import Lexer, Token, TokenType
from ..ast_nodes.nodes import (
    ProgramNode, DataDivisionNode, FieldDefinitionNode,
    ProcedureDivisionNode, MoveStatement, IfStatement, ElseClause,
    PerformStatement, ReadStatement, WriteStatement, ComputeStatement,
    AddStatement, SubtractStatement, MultiplyStatement, DivideStatement,
    StopRunStatement, ASTNode,
)


class ParseError(Exception):
    """Raised when the parser encounters unexpected input."""


# PIC clause → (cobol_type, length, decimal_places)
_PIC_PATTERN = re.compile(
    r"""^
    (S?)                   # optional sign prefix
    (X|A|9)                # base type  X=alpha, 9=numeric
    (?:\((\d+)\))?         # optional explicit length  (n)
    (V9*)?                 # optional decimal indicator
    (\(\d+\))?             # optional decimal length  (n)
    $""",
    re.IGNORECASE | re.VERBOSE,
)


def _parse_pic(raw: str) -> tuple[str, int, int]:
    """Interpret a PIC/PICTURE clause and return (type, length, decimal_places).

    Examples:
      'X(10)'     → ('alphanumeric', 10, 0)
      '9(7)V99'   → ('decimal', 7, 2)
      '9(5)'      → ('numeric', 5, 0)
      'S9(9)V99'  → ('signed_decimal', 9, 2)
    """
    raw = raw.strip().rstrip('.')

    # Handle repeated character shorthand: e.g. XXXXX → X(5), 999 → 9(3)
    match = re.fullmatch(r'(S?)(X+|9+)(V(9+))?', raw, re.IGNORECASE)
    if match:
        sign = match.group(1)
        body = match.group(2)
        dec_part = match.group(4) or ''
        base = body[0].upper()
        length = len(body)
        dec = len(dec_part)
        if base == 'X':
            return 'alphanumeric', length, 0
        if sign:
            return 'signed_decimal' if dec else 'signed_numeric', length, dec
        return 'decimal' if dec else 'numeric', length, dec

    match = _PIC_PATTERN.match(raw)
    if not match:
        return 'unknown', 0, 0

    sign, base, length_str, v_part, dec_len_str = match.groups()
    base = base.upper()
    length = int(length_str) if length_str else 1

    if v_part:
        dec_len = int(dec_len_str.strip('()')) if dec_len_str else len(v_part) - 1
    else:
        dec_len = 0

    if base == 'X' or base == 'A':
        return 'alphanumeric', length, 0
    if sign:
        return ('signed_decimal' if dec_len else 'signed_numeric'), length, dec_len
    return ('decimal' if dec_len else 'numeric'), length, dec_len


class COBOLParser:
    """Parse a COBOL source string and produce a ProgramNode AST.

    Usage::

        parser = COBOLParser(source_code)
        program = parser.parse()
    """

    def __init__(self, source: str) -> None:
        lexer = Lexer(source)
        self._tokens: List[Token] = lexer.tokenise()
        self._pos = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        """Entry point — parse the whole program."""
        program = ProgramNode()
        program.program_name = self._parse_identification_division()
        program.data_division = self._parse_data_division()
        program.procedure_division = self._parse_procedure_division()
        return program

    # ------------------------------------------------------------------
    # Token navigation helpers
    # ------------------------------------------------------------------

    @property
    def _current(self) -> Token:
        return self._tokens[self._pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self._pos + offset
        if idx < len(self._tokens):
            return self._tokens[idx]
        return self._tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._current.type in types

    def _match(self, *types: TokenType) -> bool:
        if self._check(*types):
            self._advance()
            return True
        return False

    def _expect(self, *types: TokenType) -> Token:
        if self._check(*types):
            return self._advance()
        raise ParseError(
            f"Line {self._current.line}: expected {[t.name for t in types]}, "
            f"got {self._current.type.name!r} ({self._current.value!r})"
        )

    def _skip_to_dot(self) -> None:
        """Consume tokens until (and including) the next DOT."""
        while not self._check(TokenType.DOT, TokenType.EOF):
            self._advance()
        if self._check(TokenType.DOT):
            self._advance()

    def _skip_division_header(self, *division_keywords: TokenType) -> None:
        """Consume 'KEYWORD DIVISION .'"""
        for kw in division_keywords:
            self._match(kw)
        self._match(TokenType.DIVISION)
        self._match(TokenType.DOT)

    def _at_eof(self) -> bool:
        return self._current.type == TokenType.EOF

    # ------------------------------------------------------------------
    # IDENTIFICATION DIVISION
    # ------------------------------------------------------------------

    def _parse_identification_division(self) -> str:
        """Skip the identification division and return the program name."""
        program_name = "UNKNOWN"
        # Skip until we hit DATA or PROCEDURE (or EOF)
        while not self._at_eof():
            if self._check(TokenType.DATA, TokenType.PROCEDURE):
                break
            if self._check(TokenType.PROGRAM_ID):
                self._advance()
                self._match(TokenType.DOT)
                if self._check(TokenType.IDENTIFIER):
                    program_name = self._current.value
                    self._advance()
                self._skip_to_dot()
            else:
                self._advance()
        return program_name

    # ------------------------------------------------------------------
    # DATA DIVISION
    # ------------------------------------------------------------------

    def _parse_data_division(self) -> DataDivisionNode:
        """Parse DATA DIVISION and all field definitions."""
        node = DataDivisionNode()

        # Locate DATA DIVISION
        while not self._at_eof():
            if self._check(TokenType.DATA):
                self._skip_division_header(TokenType.DATA)
                break
            if self._check(TokenType.PROCEDURE):
                return node  # no DATA DIVISION present
            self._advance()

        # Skip section headers (WORKING-STORAGE SECTION, FILE SECTION …)
        self._skip_section_headers()

        # Parse field definitions until PROCEDURE DIVISION
        current_record: Optional[str] = None
        while not self._at_eof():
            if self._check(TokenType.PROCEDURE):
                break
            if self._check(TokenType.WORKING_STORAGE, TokenType.FILE, TokenType.SECTION):
                self._skip_section_headers()
                continue
            if self._check(TokenType.LEVEL_NUMBER):
                field = self._parse_field_definition(current_record)
                if field:
                    if field.level == 1:
                        current_record = field.name
                    node.fields.append(field)
            else:
                self._advance()

        return node

    def _skip_section_headers(self) -> None:
        while self._check(TokenType.WORKING_STORAGE, TokenType.FILE, TokenType.SECTION):
            self._skip_to_dot()

    def _parse_field_definition(self, current_record: Optional[str]) -> Optional[FieldDefinitionNode]:
        """Parse one field line: level-number name PIC clause."""
        level_tok = self._expect(TokenType.LEVEL_NUMBER)
        level = int(level_tok.value)

        if not self._check(TokenType.IDENTIFIER):
            self._skip_to_dot()
            return None
        name = self._advance().value.upper().replace('-', '_')

        node = FieldDefinitionNode(level=level, name=name)
        if level != 1:
            node.parent = current_record

        # Scan tokens on this line for PIC, OCCURS, VALUE, REDEFINES
        pic_raw = ""
        while not self._check(TokenType.DOT, TokenType.EOF, TokenType.LEVEL_NUMBER):
            if self._check(TokenType.PIC, TokenType.PICTURE):
                self._advance()
                # The PIC clause value follows as one or more tokens (e.g. 9 ( 7 ) V 9 9)
                pic_raw = self._collect_pic_clause()
            elif self._check(TokenType.VALUE):
                self._skip_to_dot()
                return node  # we captured the field; value literal is not needed for schema
            elif self._check(TokenType.OCCURS, TokenType.REDEFINES):
                self._advance()  # skip OCCURS/REDEFINES and its arguments
            else:
                self._advance()

        self._match(TokenType.DOT)

        if pic_raw:
            cobol_type, length, dec = _parse_pic(pic_raw)
            node.pic_clause = pic_raw
            node.cobol_type = cobol_type
            node.length = length
            node.decimal_places = dec

        return node if pic_raw or level == 1 else None

    def _collect_pic_clause(self) -> str:
        """Collect a PIC clause which may be spread over several tokens.

        E.g. 'PIC 9(7)V99' is tokenised as: INTEGER(9) LPAREN INTEGER(7) RPAREN …
        We reassemble into a single string like '9(7)V99'.
        """
        parts: List[str] = []
        while not self._check(TokenType.DOT, TokenType.EOF,
                               TokenType.LEVEL_NUMBER, TokenType.VALUE,
                               TokenType.OCCURS, TokenType.REDEFINES):
            tok = self._current
            if tok.type in (TokenType.INTEGER, TokenType.IDENTIFIER,
                            TokenType.LPAREN, TokenType.RPAREN,
                            TokenType.LEVEL_NUMBER):
                parts.append(tok.value)
                self._advance()
            elif tok.type == TokenType.DECIMAL:
                parts.append(tok.value)
                self._advance()
            else:
                break
        return ''.join(parts)

    # ------------------------------------------------------------------
    # PROCEDURE DIVISION
    # ------------------------------------------------------------------

    def _parse_procedure_division(self) -> ProcedureDivisionNode:
        """Parse PROCEDURE DIVISION and all statements."""
        node = ProcedureDivisionNode()

        while not self._at_eof():
            if self._check(TokenType.PROCEDURE):
                self._skip_division_header(TokenType.PROCEDURE)
                break
            self._advance()

        while not self._at_eof():
            stmt = self._parse_statement()
            if stmt:
                node.statements.append(stmt)

        return node

    def _parse_statement(self) -> Optional[ASTNode]:
        """Dispatch to the appropriate statement parser."""
        tok = self._current

        if tok.type == TokenType.MOVE:
            return self._parse_move()
        if tok.type == TokenType.IF:
            return self._parse_if()
        if tok.type == TokenType.COMPUTE:
            return self._parse_compute()
        if tok.type == TokenType.ADD:
            return self._parse_add()
        if tok.type == TokenType.SUBTRACT:
            return self._parse_subtract()
        if tok.type == TokenType.MULTIPLY:
            return self._parse_multiply()
        if tok.type == TokenType.DIVIDE:
            return self._parse_divide()
        if tok.type == TokenType.READ:
            return self._parse_read()
        if tok.type == TokenType.WRITE:
            return self._parse_write()
        if tok.type == TokenType.PERFORM:
            return self._parse_perform()
        if tok.type == TokenType.STOP:
            return self._parse_stop_run()
        if tok.type == TokenType.IDENTIFIER:
            # Paragraph name — skip the header line
            self._advance()
            self._match(TokenType.DOT)
            return None
        if tok.type in (TokenType.DOT, TokenType.SECTION, TokenType.DIVISION):
            self._advance()
            return None
        if tok.type == TokenType.EOF:
            return None
        # Unrecognised token — skip it
        self._advance()
        return None

    # ------------------------------------------------------------------
    # Statement parsers
    # ------------------------------------------------------------------

    def _parse_move(self) -> MoveStatement:
        """MOVE source TO target"""
        self._advance()  # consume MOVE
        source = self._collect_value()
        self._match(TokenType.TO)
        target = self._collect_identifier()
        self._match(TokenType.DOT)
        return MoveStatement(source=source, target=target.upper().replace('-', '_'))

    def _parse_if(self) -> IfStatement:
        """IF condition statements [ELSE statements] END-IF"""
        self._advance()  # consume IF
        condition = self._collect_condition()
        then_stmts: List[ASTNode] = []
        else_clause: Optional[ElseClause] = None

        while not self._at_eof():
            if self._check(TokenType.END_IF):
                self._advance()
                self._match(TokenType.DOT)
                break
            if self._check(TokenType.ELSE):
                self._advance()
                else_stmts: List[ASTNode] = []
                while not self._check(TokenType.END_IF, TokenType.EOF):
                    s = self._parse_statement()
                    if s:
                        else_stmts.append(s)
                else_clause = ElseClause(statements=else_stmts)
                continue
            s = self._parse_statement()
            if s:
                then_stmts.append(s)

        return IfStatement(condition=condition, then_statements=then_stmts, else_clause=else_clause)

    def _parse_compute(self) -> ComputeStatement:
        """COMPUTE target = expression"""
        self._advance()  # consume COMPUTE
        target = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.EQUALS)
        expr = self._collect_expression()
        self._match(TokenType.DOT)
        return ComputeStatement(target=target, expression=expr)

    def _parse_add(self) -> AddStatement:
        """ADD operands TO target [GIVING result]"""
        self._advance()
        operands: List[str] = []
        while not self._check(TokenType.TO, TokenType.DOT, TokenType.EOF):
            operands.append(self._collect_value())
        self._match(TokenType.TO)
        target = self._collect_identifier().upper().replace('-', '_')
        giving = ""
        if self._match(TokenType.GIVING):
            giving = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.DOT)
        return AddStatement(operands=operands, target=target, giving=giving)

    def _parse_subtract(self) -> SubtractStatement:
        """SUBTRACT operands FROM target [GIVING result]"""
        self._advance()
        operands: List[str] = []
        while not self._check(TokenType.FROM, TokenType.DOT, TokenType.EOF):
            operands.append(self._collect_value())
        self._match(TokenType.FROM)
        target = self._collect_identifier().upper().replace('-', '_')
        giving = ""
        if self._match(TokenType.GIVING):
            giving = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.DOT)
        return SubtractStatement(operands=operands, target=target, giving=giving)

    def _parse_multiply(self) -> MultiplyStatement:
        """MULTIPLY a BY b [GIVING result]"""
        self._advance()
        a = self._collect_value()
        self._match(TokenType.BY)
        b = self._collect_value()
        giving = ""
        if self._match(TokenType.GIVING):
            giving = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.DOT)
        return MultiplyStatement(operand_a=a, operand_b=b, giving=giving)

    def _parse_divide(self) -> DivideStatement:
        """DIVIDE a INTO b [GIVING result] [REMAINDER rem]"""
        self._advance()
        divisor = self._collect_value()
        self._match(TokenType.INTO)
        dividend = self._collect_identifier().upper().replace('-', '_')
        giving = ""
        remainder = ""
        if self._match(TokenType.GIVING):
            giving = self._collect_identifier().upper().replace('-', '_')
        if self._match(TokenType.REMAINDER):
            remainder = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.DOT)
        return DivideStatement(divisor=divisor, dividend=dividend, giving=giving, remainder=remainder)

    def _parse_read(self) -> ReadStatement:
        """READ file-name [INTO field]"""
        self._advance()
        file_name = self._collect_identifier().upper().replace('-', '_')
        into_field = ""
        if self._match(TokenType.INTO):
            into_field = self._collect_identifier().upper().replace('-', '_')
        # Skip AT END clause
        while not self._check(TokenType.DOT, TokenType.EOF,
                               TokenType.MOVE, TokenType.IF, TokenType.COMPUTE,
                               TokenType.ADD, TokenType.SUBTRACT, TokenType.MULTIPLY,
                               TokenType.DIVIDE, TokenType.WRITE, TokenType.PERFORM,
                               TokenType.STOP, TokenType.READ):
            self._advance()
        self._match(TokenType.DOT)
        return ReadStatement(file_name=file_name, into_field=into_field)

    def _parse_write(self) -> WriteStatement:
        """WRITE record-name [FROM field]"""
        self._advance()
        record_name = self._collect_identifier().upper().replace('-', '_')
        from_field = ""
        if self._match(TokenType.FROM):
            from_field = self._collect_identifier().upper().replace('-', '_')
        self._match(TokenType.DOT)
        return WriteStatement(record_name=record_name, from_field=from_field)

    def _parse_perform(self) -> PerformStatement:
        """PERFORM paragraph [UNTIL cond | n TIMES]"""
        self._advance()
        target = self._collect_identifier()
        until_cond = ""
        times = None
        if self._match(TokenType.UNTIL):
            until_cond = self._collect_condition()
        elif self._check(TokenType.INTEGER):
            times = int(self._advance().value)
            self._match(TokenType.TIMES)
        self._match(TokenType.DOT)
        return PerformStatement(target=target.upper().replace('-', '_'),
                                until_condition=until_cond, times=times)

    def _parse_stop_run(self) -> StopRunStatement:
        """STOP RUN"""
        self._advance()  # STOP
        self._match(TokenType.RUN)
        self._match(TokenType.DOT)
        return StopRunStatement()

    # ------------------------------------------------------------------
    # Value / expression collectors
    # ------------------------------------------------------------------

    def _collect_identifier(self) -> str:
        """Return next identifier or number token value."""
        if self._check(TokenType.IDENTIFIER):
            return self._advance().value
        if self._check(TokenType.INTEGER, TokenType.DECIMAL):
            return self._advance().value
        return ""

    def _collect_value(self) -> str:
        """Return a literal or identifier as a string."""
        if self._check(TokenType.STRING_LITERAL):
            return self._advance().value
        if self._check(TokenType.INTEGER, TokenType.DECIMAL):
            return self._advance().value
        if self._check(TokenType.IDENTIFIER):
            return self._advance().value
        return ""

    def _collect_expression(self) -> str:
        """Collect an arithmetic expression until a DOT or statement keyword."""
        _STOP = {
            TokenType.DOT, TokenType.EOF, TokenType.MOVE, TokenType.IF,
            TokenType.COMPUTE, TokenType.ADD, TokenType.SUBTRACT,
            TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.READ,
            TokenType.WRITE, TokenType.PERFORM, TokenType.STOP,
            TokenType.END_IF, TokenType.ELSE,
        }
        parts: List[str] = []
        while self._current.type not in _STOP:
            tok = self._advance()
            if tok.type == TokenType.STAR:
                parts.append(' * ')
            elif tok.type == TokenType.PLUS:
                parts.append(' + ')
            elif tok.type == TokenType.MINUS:
                parts.append(' - ')
            elif tok.type == TokenType.SLASH:
                parts.append(' / ')
            elif tok.type == TokenType.LPAREN:
                parts.append('(')
            elif tok.type == TokenType.RPAREN:
                parts.append(')')
            else:
                parts.append(tok.value)
        return ''.join(parts).strip()

    def _collect_condition(self) -> str:
        """Collect a condition clause until a statement verb or END-IF/ELSE."""
        _STOP = {
            TokenType.EOF, TokenType.MOVE, TokenType.IF, TokenType.COMPUTE,
            TokenType.ADD, TokenType.SUBTRACT, TokenType.MULTIPLY,
            TokenType.DIVIDE, TokenType.READ, TokenType.WRITE,
            TokenType.PERFORM, TokenType.STOP, TokenType.END_IF,
            TokenType.ELSE, TokenType.DOT,
        }
        parts: List[str] = []
        while self._current.type not in _STOP:
            tok = self._advance()
            if tok.type == TokenType.GREATER_THAN:
                parts.append(' > ')
            elif tok.type == TokenType.LESS_THAN:
                parts.append(' < ')
            elif tok.type == TokenType.EQUALS:
                parts.append(' = ')
            elif tok.type in (TokenType.GREATER, TokenType.LESS, TokenType.EQUAL,
                               TokenType.THAN, TokenType.EQUAL_TO, TokenType.GREATER_THAN,
                               TokenType.LESS_THAN):
                parts.append(f' {tok.value} ')
            elif tok.type == TokenType.NOT:
                parts.append('NOT ')
            elif tok.type == TokenType.AND:
                parts.append(' AND ')
            elif tok.type == TokenType.OR:
                parts.append(' OR ')
            else:
                parts.append(tok.value)
        return ' '.join(''.join(parts).split())  # normalise whitespace
