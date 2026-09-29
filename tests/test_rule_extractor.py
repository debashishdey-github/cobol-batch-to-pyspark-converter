"""
Unit tests for the Rule Extractor.

Learning objective:
  Understand how business rules are extracted from AST nodes.
  Tests check rule types, conditions, and action descriptions.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.rule_extractor import RuleExtractor
from cobol_pyspark_converter.rule_extractor.extractor import (
    ConditionalRule, AssignmentRule, ComputationRule, IORule, LoopRule,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CLASSIFY_PROG = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. CLASSIFY.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CUST-REC.
   05 BALANCE        PIC 9(7)V99.
   05 CUST-TYPE      PIC X(10).

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

COMPUTE_PROG = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. CALC.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CALC-REC.
   05 PRICE      PIC 9(7)V99.
   05 QTY        PIC 9(5).
   05 TOTAL      PIC 9(9)V99.
   05 TAX        PIC 9(9)V99.

PROCEDURE DIVISION.
    READ INPUT-FILE.
    COMPUTE TOTAL = PRICE * QTY.
    COMPUTE TAX = TOTAL * 0.20.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""

PERFORM_PROG = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. LOOPPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-COUNTER PIC 9(3).

PROCEDURE DIVISION.
    PERFORM PROCESS-RECORDS UNTIL WS-COUNTER > 100.
    STOP RUN.
"""


# ---------------------------------------------------------------------------
# Rule extraction
# ---------------------------------------------------------------------------

class TestRuleExtraction:
    def _extract(self, source):
        prog = COBOLParser(source).parse()
        return RuleExtractor(prog).extract()

    def test_returns_list(self):
        rules = self._extract(CLASSIFY_PROG)
        assert isinstance(rules, list)

    def test_extracts_io_rule_for_read(self):
        rules = self._extract(CLASSIFY_PROG)
        io_rules = [r for r in rules if isinstance(r, IORule)]
        assert any(r.operation == "READ" for r in io_rules)

    def test_extracts_io_rule_for_write(self):
        rules = self._extract(CLASSIFY_PROG)
        io_rules = [r for r in rules if isinstance(r, IORule)]
        assert any(r.operation == "WRITE" for r in io_rules)

    def test_extracts_conditional_rule(self):
        rules = self._extract(CLASSIFY_PROG)
        cond_rules = [r for r in rules if isinstance(r, ConditionalRule)]
        assert len(cond_rules) >= 1

    def test_conditional_rule_has_condition(self):
        rules = self._extract(CLASSIFY_PROG)
        cond = next(r for r in rules if isinstance(r, ConditionalRule))
        assert "BALANCE" in cond.condition
        assert "1000" in cond.condition

    def test_conditional_rule_then_actions(self):
        rules = self._extract(CLASSIFY_PROG)
        cond = next(r for r in rules if isinstance(r, ConditionalRule))
        assert len(cond.then_actions) > 0
        assert any("PREMIUM" in a or "CUST" in a for a in cond.then_actions)

    def test_conditional_rule_else_actions(self):
        rules = self._extract(CLASSIFY_PROG)
        cond = next(r for r in rules if isinstance(r, ConditionalRule))
        assert len(cond.else_actions) > 0

    def test_extracts_computation_rules(self):
        rules = self._extract(COMPUTE_PROG)
        comp_rules = [r for r in rules if isinstance(r, ComputationRule)]
        assert len(comp_rules) == 2

    def test_computation_rule_operator(self):
        rules = self._extract(COMPUTE_PROG)
        comp = next(r for r in rules if isinstance(r, ComputationRule))
        assert comp.operator == "COMPUTE"

    def test_computation_rule_target(self):
        rules = self._extract(COMPUTE_PROG)
        targets = {r.target for r in rules if isinstance(r, ComputationRule)}
        assert "TOTAL" in targets

    def test_loop_rule_extracted(self):
        rules = self._extract(PERFORM_PROG)
        loop_rules = [r for r in rules if isinstance(r, LoopRule)]
        assert len(loop_rules) == 1

    def test_loop_rule_has_condition(self):
        rules = self._extract(PERFORM_PROG)
        loop = next(r for r in rules if isinstance(r, LoopRule))
        assert "COUNTER" in loop.until_condition or "100" in loop.until_condition

    def test_rule_ids_are_unique(self):
        rules = self._extract(CLASSIFY_PROG)
        ids = [r.rule_id for r in rules]
        assert len(ids) == len(set(ids))

    def test_all_rules_have_description(self):
        rules = self._extract(CLASSIFY_PROG)
        for rule in rules:
            assert rule.description  # non-empty string


# ---------------------------------------------------------------------------
# Rule dict serialisation
# ---------------------------------------------------------------------------

class TestRuleDictSerialisation:
    def _extract(self, source):
        prog = COBOLParser(source).parse()
        return RuleExtractor(prog).extract()

    def test_conditional_rule_dict(self):
        rules = self._extract(CLASSIFY_PROG)
        cond = next(r for r in rules if isinstance(r, ConditionalRule))
        d = cond.to_dict()
        assert d["rule_type"] == "ConditionalRule"
        assert "condition" in d
        assert "then_actions" in d
        assert "else_actions" in d

    def test_io_rule_dict(self):
        rules = self._extract(CLASSIFY_PROG)
        io = next(r for r in rules if isinstance(r, IORule))
        d = io.to_dict()
        assert d["rule_type"] == "IORule"
        assert "operation" in d
        assert "file_or_record" in d

    def test_computation_rule_dict(self):
        rules = self._extract(COMPUTE_PROG)
        comp = next(r for r in rules if isinstance(r, ComputationRule))
        d = comp.to_dict()
        assert d["rule_type"] == "ComputationRule"
        assert "target" in d
        assert "expression" in d


# ---------------------------------------------------------------------------
# Documentation generation
# ---------------------------------------------------------------------------

class TestDocumentationGeneration:
    def test_generate_documentation_returns_string(self):
        prog = COBOLParser(CLASSIFY_PROG).parse()
        extractor = RuleExtractor(prog)
        extractor.extract()
        doc = extractor.generate_documentation()
        assert isinstance(doc, str)

    def test_documentation_contains_program_name(self):
        prog = COBOLParser(CLASSIFY_PROG).parse()
        extractor = RuleExtractor(prog)
        extractor.extract()
        doc = extractor.generate_documentation()
        assert "CLASSIFY" in doc

    def test_documentation_contains_rule_details(self):
        prog = COBOLParser(CLASSIFY_PROG).parse()
        extractor = RuleExtractor(prog)
        extractor.extract()
        doc = extractor.generate_documentation()
        assert "Rule #" in doc
        assert "BALANCE" in doc

    def test_documentation_has_total_count(self):
        prog = COBOLParser(CLASSIFY_PROG).parse()
        extractor = RuleExtractor(prog)
        rules = extractor.extract()
        doc = extractor.generate_documentation()
        assert f"Total rules extracted: {len(rules)}" in doc
