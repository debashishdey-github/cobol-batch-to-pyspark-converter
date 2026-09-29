"""
AST Node Definitions
====================
An Abstract Syntax Tree (AST) is the backbone of any compiler or code-analysis
tool.  After the lexer breaks raw source text into tokens, the parser assembles
those tokens into a *tree* whose nodes correspond to language constructs.

Every node below represents one COBOL construct.  The tree structure lets us:
  1. Walk the program in a structured way (rather than line by line).
  2. Extract business rules without caring about textual formatting.
  3. Generate target code by visiting each node type.

This is deliberately kept simple so the structure is easy to read and extend.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------

@dataclass
class ASTNode:
    """Every AST node inherits from this base class.

    The `node_type` string lets us identify nodes without isinstance() checks,
    which makes serialisation (e.g. to JSON) straightforward.
    """
    node_type: str = field(init=False)

    def __post_init__(self):
        self.node_type = self.__class__.__name__

    def to_dict(self) -> dict:
        """Return a plain-dict representation (useful for the Streamlit UI)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Program root
# ---------------------------------------------------------------------------

@dataclass
class ProgramNode(ASTNode):
    """Root of every parsed COBOL program.

    A COBOL program has several *divisions* (IDENTIFICATION, ENVIRONMENT,
    DATA, PROCEDURE).  We only model the two that carry business logic:
    DATA DIVISION  → field/schema definitions
    PROCEDURE DIVISION → executable statements
    """
    program_name: str = ""
    data_division: Optional[DataDivisionNode] = None
    procedure_division: Optional[ProcedureDivisionNode] = None

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "program_name": self.program_name,
            "data_division": self.data_division.to_dict() if self.data_division else None,
            "procedure_division": self.procedure_division.to_dict() if self.procedure_division else None,
        }


# ---------------------------------------------------------------------------
# DATA DIVISION
# ---------------------------------------------------------------------------

@dataclass
class DataDivisionNode(ASTNode):
    """Holds all field definitions found in the DATA DIVISION.

    In COBOL, the DATA DIVISION defines the *schema* — every variable,
    record layout, and file structure.  This maps directly to a Spark
    StructType schema.
    """
    fields: List[FieldDefinitionNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "fields": [f.to_dict() for f in self.fields],
        }


@dataclass
class FieldDefinitionNode(ASTNode):
    """One COBOL field definition, e.g.  05 BALANCE PIC 9(7)V99.

    Level numbers in COBOL indicate hierarchy:
      01  = record (group item)
      05  = elementary field inside a record
      77  = standalone field (no record parent)

    The PIC clause defines the data type and size:
      PIC X(n)   → alphanumeric string of length n
      PIC 9(n)   → numeric integer of n digits
      PIC 9(n)V99 → numeric with 2 decimal places
      PIC S9(n)  → signed numeric
    """
    level: int = 0
    name: str = ""
    pic_clause: str = ""           # raw PIC string, e.g. "X(10)" or "9(7)V99"
    cobol_type: str = ""           # "alphanumeric" | "numeric" | "decimal" | "signed_numeric"
    length: int = 0
    decimal_places: int = 0
    parent: Optional[str] = None   # parent record name if this is a group member

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "level": self.level,
            "name": self.name,
            "pic_clause": self.pic_clause,
            "cobol_type": self.cobol_type,
            "length": self.length,
            "decimal_places": self.decimal_places,
            "parent": self.parent,
        }


# ---------------------------------------------------------------------------
# PROCEDURE DIVISION
# ---------------------------------------------------------------------------

@dataclass
class ProcedureDivisionNode(ASTNode):
    """Holds the ordered list of executable statements.

    In a real COBOL program these are organised into *sections* and
    *paragraphs*.  For our educational purposes we flatten them into a
    single list, which is enough to demonstrate the conversion pipeline.
    """
    statements: List[ASTNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "statements": [s.to_dict() for s in self.statements],
        }


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class MoveStatement(ASTNode):
    """MOVE source TO target

    In COBOL, MOVE copies a value (literal or field) into a target field.
    PySpark equivalent: df.withColumn("TARGET", lit(value)) or col("SOURCE")
    """
    source: str = ""   # literal value (e.g. "'PREMIUM'") or field name
    target: str = ""   # destination field name

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "source": self.source, "target": self.target}


@dataclass
class IfStatement(ASTNode):
    """IF condition … [ELSE …] END-IF

    COBOL's conditional construct.  Conditions compare fields to literals or
    other fields using =, >, <, >=, <=, NOT.
    PySpark equivalent: when(condition, value).otherwise(other_value)
    """
    condition: str = ""                       # raw condition text, e.g. "BALANCE > 1000"
    then_statements: List[ASTNode] = field(default_factory=list)
    else_clause: Optional[ElseClause] = None

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "condition": self.condition,
            "then_statements": [s.to_dict() for s in self.then_statements],
            "else_clause": self.else_clause.to_dict() if self.else_clause else None,
        }


@dataclass
class ElseClause(ASTNode):
    """The ELSE branch of an IF statement."""
    statements: List[ASTNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "statements": [s.to_dict() for s in self.statements]}


@dataclass
class PerformStatement(ASTNode):
    """PERFORM paragraph-name [UNTIL condition] [VARYING …]

    PERFORM is COBOL's loop/subroutine-call mechanism.
    PySpark equivalent: often a UDF, a separate transformation, or a loop
    that builds a chain of withColumn calls.
    """
    target: str = ""         # paragraph or section name
    until_condition: str = ""  # UNTIL condition, if present
    times: Optional[int] = None  # PERFORM X TIMES

    def to_dict(self) -> dict:
        return {
            "node_type": self.node_type,
            "target": self.target,
            "until_condition": self.until_condition,
            "times": self.times,
        }


@dataclass
class ReadStatement(ASTNode):
    """READ file-name [INTO record] [AT END …]

    In batch COBOL, READ fetches one record at a time from a sequential file.
    PySpark equivalent: spark.read.csv() / spark.read.parquet() etc.
    """
    file_name: str = ""
    into_field: str = ""

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "file_name": self.file_name, "into_field": self.into_field}


@dataclass
class WriteStatement(ASTNode):
    """WRITE record [FROM field]

    Writes one record to an output file.
    PySpark equivalent: df.write.csv() / df.write.parquet() etc.
    """
    record_name: str = ""
    from_field: str = ""

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "record_name": self.record_name, "from_field": self.from_field}


@dataclass
class ComputeStatement(ASTNode):
    """COMPUTE target = arithmetic-expression

    COBOL's general-purpose arithmetic assignment.
    PySpark equivalent: df.withColumn("TARGET", expr)
    """
    target: str = ""
    expression: str = ""   # e.g. "PRICE * QTY" or "BALANCE * 1.05"

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "target": self.target, "expression": self.expression}


@dataclass
class AddStatement(ASTNode):
    """ADD source TO target [GIVING result]

    PySpark: col("TARGET") + col("SOURCE")  or  col("A") + col("B")
    """
    operands: List[str] = field(default_factory=list)
    target: str = ""
    giving: str = ""   # optional GIVING field

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "operands": self.operands, "target": self.target, "giving": self.giving}


@dataclass
class SubtractStatement(ASTNode):
    """SUBTRACT source FROM target [GIVING result]"""
    operands: List[str] = field(default_factory=list)
    target: str = ""
    giving: str = ""

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "operands": self.operands, "target": self.target, "giving": self.giving}


@dataclass
class MultiplyStatement(ASTNode):
    """MULTIPLY a BY b [GIVING result]"""
    operand_a: str = ""
    operand_b: str = ""
    giving: str = ""

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "operand_a": self.operand_a,
                "operand_b": self.operand_b, "giving": self.giving}


@dataclass
class DivideStatement(ASTNode):
    """DIVIDE a INTO b [GIVING result] [REMAINDER rem]"""
    divisor: str = ""
    dividend: str = ""
    giving: str = ""
    remainder: str = ""

    def to_dict(self) -> dict:
        return {"node_type": self.node_type, "divisor": self.divisor,
                "dividend": self.dividend, "giving": self.giving, "remainder": self.remainder}


@dataclass
class StopRunStatement(ASTNode):
    """STOP RUN — terminates the batch job.

    PySpark equivalent: spark.stop()
    """
    def to_dict(self) -> dict:
        return {"node_type": self.node_type}
