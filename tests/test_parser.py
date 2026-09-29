"""
Unit tests for the COBOL Parser.

Learning objective:
  Understand how a recursive-descent parser builds an AST.
  Tests verify node types, field counts, and statement ordering.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.ast_nodes import (
    ProgramNode, DataDivisionNode, FieldDefinitionNode,
    ProcedureDivisionNode, MoveStatement, IfStatement,
    ComputeStatement, ReadStatement, WriteStatement,
    AddStatement, SubtractStatement, MultiplyStatement, DivideStatement,
    StopRunStatement,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_PROGRAM = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. TESTPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CUSTOMER-REC.
   05 CUSTOMER-ID   PIC X(10).
   05 BALANCE       PIC 9(7)V99.
   05 CUST-TYPE     PIC X(10).

PROCEDURE DIVISION.
    READ CUSTOMER-FILE.
    IF BALANCE > 1000
       MOVE 'PREMIUM' TO CUST-TYPE
    ELSE
       MOVE 'STANDARD' TO CUST-TYPE
    END-IF.
    WRITE OUTPUT-RECORD.
    STOP RUN.
"""

COMPUTE_PROGRAM = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. CALCPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CALC-REC.
   05 PRICE      PIC 9(7)V99.
   05 QTY        PIC 9(5).
   05 TOTAL      PIC 9(9)V99.

PROCEDURE DIVISION.
    READ INPUT-FILE.
    COMPUTE TOTAL = PRICE * QTY.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""

ARITHMETIC_PROGRAM = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. ARTHPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 ARITH-REC.
   05 A    PIC 9(5).
   05 B    PIC 9(5).
   05 C    PIC 9(5).

PROCEDURE DIVISION.
    READ INPUT-FILE.
    ADD A TO B.
    SUBTRACT A FROM C.
    MULTIPLY A BY B.
    DIVIDE A INTO C.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""


# ---------------------------------------------------------------------------
# Program structure
# ---------------------------------------------------------------------------

class TestProgramStructure:
    def test_returns_program_node(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        assert isinstance(prog, ProgramNode)

    def test_program_name_extracted(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        assert prog.program_name == "TESTPROG"

    def test_data_division_present(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        assert prog.data_division is not None
        assert isinstance(prog.data_division, DataDivisionNode)

    def test_procedure_division_present(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        assert prog.procedure_division is not None
        assert isinstance(prog.procedure_division, ProcedureDivisionNode)


# ---------------------------------------------------------------------------
# DATA DIVISION parsing
# ---------------------------------------------------------------------------

class TestDataDivision:
    def test_field_count(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        # 01 + three 05-level fields = 4 total
        fields = prog.data_division.fields
        assert len(fields) == 4

    def test_record_field_level(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        record = prog.data_division.fields[0]
        assert record.level == 1

    def test_elementary_field_levels(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        elementary = [f for f in prog.data_division.fields if f.level == 5]
        assert len(elementary) == 3

    def test_field_names_normalised(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        names = [f.name for f in prog.data_division.fields]
        assert "CUSTOMER_ID" in names
        assert "BALANCE" in names
        assert "CUST_TYPE" in names

    def test_alphanumeric_field_type(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        cust_id = next(f for f in prog.data_division.fields if f.name == "CUSTOMER_ID")
        assert cust_id.cobol_type == "alphanumeric"
        assert cust_id.length == 10

    def test_decimal_field_type(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        balance = next(f for f in prog.data_division.fields if f.name == "BALANCE")
        assert "decimal" in balance.cobol_type
        assert balance.decimal_places == 2

    def test_parent_field_set(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        for f in prog.data_division.fields:
            if f.level == 5:
                assert f.parent is not None


# ---------------------------------------------------------------------------
# PROCEDURE DIVISION — statement types
# ---------------------------------------------------------------------------

class TestProcedureDivision:
    def _get_stmts(self, source):
        return COBOLParser(source).parse().procedure_division.statements

    def test_read_statement_parsed(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        reads = [s for s in stmts if isinstance(s, ReadStatement)]
        assert len(reads) == 1

    def test_read_file_name(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        read = next(s for s in stmts if isinstance(s, ReadStatement))
        assert "CUSTOMER" in read.file_name

    def test_if_statement_parsed(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        ifs = [s for s in stmts if isinstance(s, IfStatement)]
        assert len(ifs) == 1

    def test_if_condition(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        if_stmt = next(s for s in stmts if isinstance(s, IfStatement))
        assert "BALANCE" in if_stmt.condition
        assert "1000" in if_stmt.condition

    def test_if_then_branch(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        if_stmt = next(s for s in stmts if isinstance(s, IfStatement))
        assert len(if_stmt.then_statements) == 1
        assert isinstance(if_stmt.then_statements[0], MoveStatement)

    def test_if_else_branch(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        if_stmt = next(s for s in stmts if isinstance(s, IfStatement))
        assert if_stmt.else_clause is not None
        assert len(if_stmt.else_clause.statements) == 1

    def test_move_source_and_target(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        if_stmt = next(s for s in stmts if isinstance(s, IfStatement))
        move = if_stmt.then_statements[0]
        assert isinstance(move, MoveStatement)
        assert move.source == "'PREMIUM'"
        assert move.target == "CUST_TYPE"

    def test_write_statement_parsed(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        writes = [s for s in stmts if isinstance(s, WriteStatement)]
        assert len(writes) == 1

    def test_stop_run_parsed(self):
        stmts = self._get_stmts(SIMPLE_PROGRAM)
        stops = [s for s in stmts if isinstance(s, StopRunStatement)]
        assert len(stops) == 1

    def test_compute_parsed(self):
        stmts = self._get_stmts(COMPUTE_PROGRAM)
        computes = [s for s in stmts if isinstance(s, ComputeStatement)]
        assert len(computes) == 1

    def test_compute_target_and_expression(self):
        stmts = self._get_stmts(COMPUTE_PROGRAM)
        compute = next(s for s in stmts if isinstance(s, ComputeStatement))
        assert compute.target == "TOTAL"
        assert "PRICE" in compute.expression
        assert "QTY" in compute.expression

    def test_add_statement_parsed(self):
        stmts = self._get_stmts(ARITHMETIC_PROGRAM)
        adds = [s for s in stmts if isinstance(s, AddStatement)]
        assert len(adds) == 1

    def test_subtract_statement_parsed(self):
        stmts = self._get_stmts(ARITHMETIC_PROGRAM)
        subs = [s for s in stmts if isinstance(s, SubtractStatement)]
        assert len(subs) == 1

    def test_multiply_statement_parsed(self):
        stmts = self._get_stmts(ARITHMETIC_PROGRAM)
        muls = [s for s in stmts if isinstance(s, MultiplyStatement)]
        assert len(muls) == 1

    def test_divide_statement_parsed(self):
        stmts = self._get_stmts(ARITHMETIC_PROGRAM)
        divs = [s for s in stmts if isinstance(s, DivideStatement)]
        assert len(divs) == 1


# ---------------------------------------------------------------------------
# AST serialisation
# ---------------------------------------------------------------------------

class TestASTSerialisation:
    def test_program_to_dict(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        d = prog.to_dict()
        assert d["node_type"] == "ProgramNode"
        assert "data_division" in d
        assert "procedure_division" in d

    def test_data_division_to_dict(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        d = prog.data_division.to_dict()
        assert d["node_type"] == "DataDivisionNode"
        assert isinstance(d["fields"], list)

    def test_field_to_dict(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        field = prog.data_division.fields[1]  # first elementary field
        d = field.to_dict()
        assert "name" in d
        assert "pic_clause" in d
        assert "cobol_type" in d

    def test_if_statement_to_dict(self):
        prog = COBOLParser(SIMPLE_PROGRAM).parse()
        stmts = prog.procedure_division.statements
        if_stmt = next(s for s in stmts if isinstance(s, IfStatement))
        d = if_stmt.to_dict()
        assert d["node_type"] == "IfStatement"
        assert "condition" in d
        assert "then_statements" in d
        assert "else_clause" in d
