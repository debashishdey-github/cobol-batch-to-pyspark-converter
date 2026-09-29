"""
Business Rule Extractor
=======================
After the parser produces an AST, this module walks the tree and extracts
*business rules* — the decision logic that describes what the program does,
independent of how it does it.

Why extract rules separately?
------------------------------
In mainframe modernisation projects, one of the hardest challenges is
*understanding* what the legacy system does before trying to rewrite it.
Business analysts need readable documentation; they cannot read COBOL.

By walking the AST and producing structured rule objects we can:
  1. Generate human-readable documentation automatically.
  2. Validate the generated PySpark against the original intent.
  3. Build a "rule inventory" for the target system.

Rule types extracted
--------------------
  ConditionalRule    IF … THEN … ELSE …
  AssignmentRule     MOVE value TO field
  ComputationRule    COMPUTE / ADD / SUBTRACT / MULTIPLY / DIVIDE
  IORule             READ / WRITE (data sources & sinks)
  LoopRule           PERFORM … UNTIL …
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any

from ..ast_nodes.nodes import (
    ProgramNode, ProcedureDivisionNode, ASTNode,
    MoveStatement, IfStatement, ElseClause,
    PerformStatement, ReadStatement, WriteStatement,
    ComputeStatement, AddStatement, SubtractStatement,
    MultiplyStatement, DivideStatement, StopRunStatement,
)


# ---------------------------------------------------------------------------
# Rule data classes
# ---------------------------------------------------------------------------

@dataclass
class BusinessRule:
    """Base class for all extracted rules."""
    rule_id: int = 0
    rule_type: str = ""
    description: str = ""
    source_statement: str = ""   # human-readable COBOL equivalent

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "description": self.description,
            "source_statement": self.source_statement,
        }


@dataclass
class ConditionalRule(BusinessRule):
    """IF condition → THEN action(s) [ELSE action(s)]"""
    condition: str = ""
    then_actions: List[str] = field(default_factory=list)
    else_actions: List[str] = field(default_factory=list)
    nested_rules: List["BusinessRule"] = field(default_factory=list)

    def __post_init__(self):
        self.rule_type = "ConditionalRule"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "condition": self.condition,
            "then_actions": self.then_actions,
            "else_actions": self.else_actions,
            "nested_rules": [r.to_dict() for r in self.nested_rules],
        })
        return d


@dataclass
class AssignmentRule(BusinessRule):
    """MOVE source TO target"""
    target: str = ""
    value: str = ""

    def __post_init__(self):
        self.rule_type = "AssignmentRule"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"target": self.target, "value": self.value})
        return d


@dataclass
class ComputationRule(BusinessRule):
    """Arithmetic operation (COMPUTE / ADD / SUBTRACT / MULTIPLY / DIVIDE)"""
    target: str = ""
    expression: str = ""
    operator: str = ""

    def __post_init__(self):
        self.rule_type = "ComputationRule"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"target": self.target, "expression": self.expression, "operator": self.operator})
        return d


@dataclass
class IORule(BusinessRule):
    """READ or WRITE operation"""
    operation: str = ""   # "READ" or "WRITE"
    file_or_record: str = ""
    format_hint: str = ""  # guessed format (CSV, fixed-width, etc.)

    def __post_init__(self):
        self.rule_type = "IORule"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({"operation": self.operation, "file_or_record": self.file_or_record})
        return d


@dataclass
class LoopRule(BusinessRule):
    """PERFORM … UNTIL or PERFORM n TIMES"""
    target_paragraph: str = ""
    until_condition: str = ""
    times: Optional[int] = None

    def __post_init__(self):
        self.rule_type = "LoopRule"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update({
            "target_paragraph": self.target_paragraph,
            "until_condition": self.until_condition,
            "times": self.times,
        })
        return d


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class RuleExtractor:
    """Walk an AST and produce a list of BusinessRule objects.

    Usage::

        extractor = RuleExtractor(program_ast)
        rules = extractor.extract()
        docs  = extractor.generate_documentation()
    """

    def __init__(self, program: ProgramNode) -> None:
        self._program = program
        self._rules: List[BusinessRule] = []
        self._counter = 0

    def extract(self) -> List[BusinessRule]:
        """Walk the procedure division and extract all rules."""
        self._rules = []
        self._counter = 0
        if self._program.procedure_division:
            for stmt in self._program.procedure_division.statements:
                rules = self._extract_from_statement(stmt)
                self._rules.extend(rules)
        return self._rules

    # ------------------------------------------------------------------
    # Statement dispatchers
    # ------------------------------------------------------------------

    def _extract_from_statement(self, stmt: ASTNode) -> List[BusinessRule]:
        if isinstance(stmt, IfStatement):
            return [self._from_if(stmt)]
        if isinstance(stmt, MoveStatement):
            return [self._from_move(stmt)]
        if isinstance(stmt, ComputeStatement):
            return [self._from_compute(stmt)]
        if isinstance(stmt, AddStatement):
            return [self._from_add(stmt)]
        if isinstance(stmt, SubtractStatement):
            return [self._from_subtract(stmt)]
        if isinstance(stmt, MultiplyStatement):
            return [self._from_multiply(stmt)]
        if isinstance(stmt, DivideStatement):
            return [self._from_divide(stmt)]
        if isinstance(stmt, ReadStatement):
            return [self._from_read(stmt)]
        if isinstance(stmt, WriteStatement):
            return [self._from_write(stmt)]
        if isinstance(stmt, PerformStatement):
            return [self._from_perform(stmt)]
        return []

    def _next_id(self) -> int:
        self._counter += 1
        return self._counter

    # ------------------------------------------------------------------
    # Rule builders
    # ------------------------------------------------------------------

    def _from_if(self, stmt: IfStatement) -> ConditionalRule:
        then_actions = self._summarise_statements(stmt.then_statements)
        else_actions = self._summarise_statements(stmt.else_clause.statements) if stmt.else_clause else []
        nested = []
        for s in stmt.then_statements:
            nested.extend(self._extract_from_statement(s))
        if stmt.else_clause:
            for s in stmt.else_clause.statements:
                nested.extend(self._extract_from_statement(s))

        condition_clean = stmt.condition.replace('_', '-')
        rule = ConditionalRule(
            rule_id=self._next_id(),
            description=f"If {condition_clean} then {'; '.join(then_actions)}",
            source_statement=f"IF {condition_clean}",
            condition=stmt.condition,
            then_actions=then_actions,
            else_actions=else_actions,
            nested_rules=nested,
        )
        return rule

    def _from_move(self, stmt: MoveStatement) -> AssignmentRule:
        src = stmt.source.strip("'")
        tgt = stmt.target.replace('_', '-')
        return AssignmentRule(
            rule_id=self._next_id(),
            description=f"Set {tgt} = {src}",
            source_statement=f"MOVE {stmt.source} TO {stmt.target}",
            target=stmt.target,
            value=stmt.source,
        )

    def _from_compute(self, stmt: ComputeStatement) -> ComputationRule:
        expr = stmt.expression.replace('_', '-')
        tgt = stmt.target.replace('_', '-')
        return ComputationRule(
            rule_id=self._next_id(),
            description=f"Calculate {tgt} = {expr}",
            source_statement=f"COMPUTE {stmt.target} = {stmt.expression}",
            target=stmt.target,
            expression=stmt.expression,
            operator="COMPUTE",
        )

    def _from_add(self, stmt: AddStatement) -> ComputationRule:
        parts = ' + '.join(stmt.operands)
        result = stmt.giving or stmt.target
        tgt = result.replace('_', '-')
        return ComputationRule(
            rule_id=self._next_id(),
            description=f"Add {parts} to {tgt}",
            source_statement=f"ADD {parts} TO {stmt.target}",
            target=result,
            expression=f"{stmt.target} + {parts}",
            operator="ADD",
        )

    def _from_subtract(self, stmt: SubtractStatement) -> ComputationRule:
        parts = ' - '.join(stmt.operands)
        result = stmt.giving or stmt.target
        tgt = result.replace('_', '-')
        return ComputationRule(
            rule_id=self._next_id(),
            description=f"Subtract {parts} from {tgt}",
            source_statement=f"SUBTRACT {parts} FROM {stmt.target}",
            target=result,
            expression=f"{stmt.target} - {parts}",
            operator="SUBTRACT",
        )

    def _from_multiply(self, stmt: MultiplyStatement) -> ComputationRule:
        result = stmt.giving or stmt.operand_b
        tgt = result.replace('_', '-')
        return ComputationRule(
            rule_id=self._next_id(),
            description=f"Multiply {stmt.operand_a} by {stmt.operand_b} → {tgt}",
            source_statement=f"MULTIPLY {stmt.operand_a} BY {stmt.operand_b}",
            target=result,
            expression=f"{stmt.operand_a} * {stmt.operand_b}",
            operator="MULTIPLY",
        )

    def _from_divide(self, stmt: DivideStatement) -> ComputationRule:
        result = stmt.giving or stmt.dividend
        tgt = result.replace('_', '-')
        expr = f"{stmt.dividend} / {stmt.divisor}"
        return ComputationRule(
            rule_id=self._next_id(),
            description=f"Divide {stmt.dividend} by {stmt.divisor} → {tgt}",
            source_statement=f"DIVIDE {stmt.divisor} INTO {stmt.dividend}",
            target=result,
            expression=expr,
            operator="DIVIDE",
        )

    def _from_read(self, stmt: ReadStatement) -> IORule:
        fn = stmt.file_name.replace('_', '-')
        return IORule(
            rule_id=self._next_id(),
            description=f"Read records from {fn}",
            source_statement=f"READ {fn}",
            operation="READ",
            file_or_record=stmt.file_name,
        )

    def _from_write(self, stmt: WriteStatement) -> IORule:
        rn = stmt.record_name.replace('_', '-')
        return IORule(
            rule_id=self._next_id(),
            description=f"Write {rn} to output file",
            source_statement=f"WRITE {rn}",
            operation="WRITE",
            file_or_record=stmt.record_name,
        )

    def _from_perform(self, stmt: PerformStatement) -> LoopRule:
        tgt = stmt.target.replace('_', '-')
        desc = f"Execute paragraph {tgt}"
        if stmt.until_condition:
            desc += f" until {stmt.until_condition}"
        elif stmt.times:
            desc += f" {stmt.times} times"
        return LoopRule(
            rule_id=self._next_id(),
            description=desc,
            source_statement=f"PERFORM {tgt}",
            target_paragraph=stmt.target,
            until_condition=stmt.until_condition,
            times=stmt.times,
        )

    # ------------------------------------------------------------------
    # Documentation generator
    # ------------------------------------------------------------------

    def generate_documentation(self) -> str:
        """Produce a human-readable business rule document."""
        if not self._rules:
            self.extract()

        lines = [
            "=" * 60,
            "  BUSINESS RULE DOCUMENTATION",
            "  Auto-generated from COBOL source",
            "=" * 60,
            "",
        ]

        program_name = self._program.program_name or "UNKNOWN"
        lines.append(f"Program: {program_name}")
        lines.append("")

        for rule in self._rules:
            self._format_rule(rule, lines, indent=0)

        lines.append("=" * 60)
        lines.append(f"Total rules extracted: {len(self._rules)}")
        return '\n'.join(lines)

    def _format_rule(self, rule: BusinessRule, lines: List[str], indent: int) -> None:
        prefix = "  " * indent
        lines.append(f"{prefix}Rule #{rule.rule_id}  [{rule.rule_type}]")
        lines.append(f"{prefix}  Description : {rule.description}")
        lines.append(f"{prefix}  COBOL source: {rule.source_statement}")

        if isinstance(rule, ConditionalRule):
            lines.append(f"{prefix}  Condition   : {rule.condition}")
            if rule.then_actions:
                lines.append(f"{prefix}  THEN        : {'; '.join(rule.then_actions)}")
            if rule.else_actions:
                lines.append(f"{prefix}  ELSE        : {'; '.join(rule.else_actions)}")

        elif isinstance(rule, ComputationRule):
            lines.append(f"{prefix}  Target      : {rule.target}")
            lines.append(f"{prefix}  Expression  : {rule.expression}")

        elif isinstance(rule, AssignmentRule):
            lines.append(f"{prefix}  Target      : {rule.target}")
            lines.append(f"{prefix}  Value       : {rule.value}")

        elif isinstance(rule, IORule):
            lines.append(f"{prefix}  Operation   : {rule.operation}")
            lines.append(f"{prefix}  File/Record : {rule.file_or_record}")

        elif isinstance(rule, LoopRule):
            lines.append(f"{prefix}  Paragraph   : {rule.target_paragraph}")
            if rule.until_condition:
                lines.append(f"{prefix}  Until       : {rule.until_condition}")
            if rule.times:
                lines.append(f"{prefix}  Times       : {rule.times}")

        lines.append("")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _summarise_statements(self, stmts: List[ASTNode]) -> List[str]:
        summaries = []
        for s in stmts:
            if isinstance(s, MoveStatement):
                summaries.append(f"set {s.target.replace('_','-')} = {s.source.strip(chr(39))}")
            elif isinstance(s, ComputeStatement):
                summaries.append(f"compute {s.target.replace('_','-')} = {s.expression}")
            elif isinstance(s, AddStatement):
                summaries.append(f"add to {s.target.replace('_','-')}")
            elif isinstance(s, SubtractStatement):
                summaries.append(f"subtract from {s.target.replace('_','-')}")
            elif isinstance(s, MultiplyStatement):
                summaries.append(f"multiply {s.operand_a} × {s.operand_b}")
            elif isinstance(s, DivideStatement):
                summaries.append(f"divide {s.dividend} ÷ {s.divisor}")
            elif isinstance(s, PerformStatement):
                summaries.append(f"perform {s.target.replace('_','-')}")
        return summaries
