"""
PySpark Code Generator
======================
This is the final stage of the pipeline.  We walk the AST and the extracted
business rules and produce readable PySpark DataFrame code.

Code generation strategy
-------------------------
We use a *visitor-like* pattern: each AST node type maps to a method that
returns one or more lines of PySpark code.  The generated code is assembled
into a complete, runnable Python script.

Mapping philosophy
------------------
COBOL batch programs process one record at a time in a sequential loop.
PySpark DataFrames represent *all* records simultaneously and apply
transformations column-by-column.

The key conceptual shift is:
  COBOL:   for each record → apply IF/COMPUTE/MOVE → write record
  PySpark: load ALL records → apply withColumn(when(…)) chains → write ALL

This means:
  IF … MOVE   → withColumn("field", when(condition, value))
  COMPUTE     → withColumn("field", expression)
  ADD/SUBTRACT/etc → withColumn("field", col(a) ± col(b))
  READ        → spark.read.csv(…)
  WRITE       → df.write.csv(…)

Condition translation
---------------------
COBOL conditions use field names in HYPHEN-CASE.  We normalise them to
UNDERSCORE_CASE (matching the column names in our DataFrame) and translate
COBOL comparison operators to PySpark equivalents:
  =    → ==
  >    → >
  <    → <
  NOT  → ~
"""

from __future__ import annotations
import re
from typing import List, Optional

from ..ast_nodes.nodes import (
    ProgramNode, ASTNode, MoveStatement, IfStatement, ElseClause,
    PerformStatement, ReadStatement, WriteStatement, ComputeStatement,
    AddStatement, SubtractStatement, MultiplyStatement, DivideStatement,
    StopRunStatement, FieldDefinitionNode,
)
from ..rule_extractor.extractor import BusinessRule, ConditionalRule


class PySparkGenerator:
    """Generate a complete PySpark script from a parsed COBOL program.

    Usage::

        gen = PySparkGenerator(program_ast)
        code = gen.generate()
    """

    def __init__(self, program: ProgramNode) -> None:
        self._program = program
        self._lines: List[str] = []
        self._indent = 0
        self._df_var = "df"
        self._when_chains: List[str] = []   # pending when() chains
        self._field_names: set = set()      # known field names from DATA DIVISION

        # Collect field names for context-aware code gen
        if program.data_division:
            for f in program.data_division.fields:
                self._field_names.add(f.name.upper())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """Return a complete PySpark Python script as a string."""
        self._lines = []
        self._emit_header()
        self._emit_schema_from_data_division()
        self._emit_procedure()
        self._emit_footer()
        return '\n'.join(self._lines)

    # ------------------------------------------------------------------
    # Header / footer
    # ------------------------------------------------------------------

    def _emit_header(self) -> None:
        prog = self._program.program_name or "cobol_program"
        self._lines += [
            f"# Generated PySpark job — converted from COBOL program: {prog}",
            "# Conversion tool: COBOL Batch → PySpark Converter (learning project)",
            "",
            "from pyspark.sql import SparkSession",
            "from pyspark.sql.functions import col, lit, when, expr",
            "from pyspark.sql.types import StructType, StructField, StringType, LongType, DecimalType",
            "",
            "spark = SparkSession.builder \\",
            f'    .appName("{prog}") \\',
            "    .getOrCreate()",
            "",
        ]

    def _emit_footer(self) -> None:
        self._lines += [
            "",
            "spark.stop()",
        ]

    # ------------------------------------------------------------------
    # Schema from DATA DIVISION
    # ------------------------------------------------------------------

    def _emit_schema_from_data_division(self) -> None:
        if not self._program.data_division:
            return
        elementary = [
            f for f in self._program.data_division.fields
            if f.level != 1 and f.cobol_type not in ('', 'group')
        ]
        if not elementary:
            return

        self._lines.append("# Schema derived from COBOL DATA DIVISION")
        self._lines.append("schema = StructType([")
        for f in elementary:
            spark_type = self._field_to_spark_type(f)
            self._lines.append(f'    StructField("{f.name}", {spark_type}, nullable=True),')
        self._lines.append("])")
        self._lines.append("")

    @staticmethod
    def _field_to_spark_type(f: FieldDefinitionNode) -> str:
        ct = f.cobol_type
        if ct == 'alphanumeric':
            return 'StringType()'
        if ct in ('decimal', 'signed_decimal'):
            precision = f.length + f.decimal_places
            return f'DecimalType({precision}, {f.decimal_places})'
        return 'LongType()'

    # ------------------------------------------------------------------
    # PROCEDURE DIVISION
    # ------------------------------------------------------------------

    def _emit_procedure(self) -> None:
        if not self._program.procedure_division:
            return

        # Group consecutive READ → DataFrame load
        # Group consecutive IF/MOVE/COMPUTE → withColumn chains
        # Group consecutive WRITE → DataFrame write

        stmts = self._program.procedure_division.statements
        i = 0
        while i < len(stmts):
            stmt = stmts[i]
            if isinstance(stmt, ReadStatement):
                self._emit_read(stmt)
            elif isinstance(stmt, WriteStatement):
                self._emit_write(stmt)
            elif isinstance(stmt, IfStatement):
                self._emit_if(stmt)
            elif isinstance(stmt, MoveStatement):
                self._emit_move(stmt)
            elif isinstance(stmt, ComputeStatement):
                self._emit_compute(stmt)
            elif isinstance(stmt, AddStatement):
                self._emit_add(stmt)
            elif isinstance(stmt, SubtractStatement):
                self._emit_subtract(stmt)
            elif isinstance(stmt, MultiplyStatement):
                self._emit_multiply(stmt)
            elif isinstance(stmt, DivideStatement):
                self._emit_divide(stmt)
            elif isinstance(stmt, PerformStatement):
                self._emit_perform(stmt)
            elif isinstance(stmt, StopRunStatement):
                self._lines.append("# STOP RUN → spark.stop() is called at the end")
            i += 1

    # ------------------------------------------------------------------
    # I/O statements
    # ------------------------------------------------------------------

    def _emit_read(self, stmt: ReadStatement) -> None:
        name = stmt.file_name.lower().replace('_', '-')
        var = stmt.file_name.lower()
        has_schema = bool(self._program.data_division and
                          any(f.level != 1 and f.cobol_type != 'group'
                              for f in self._program.data_division.fields))
        schema_arg = ", schema=schema" if has_schema else ""
        self._lines += [
            f"# READ {name} — load input file into a DataFrame",
            f'{self._df_var} = spark.read.csv("{name}.csv"{schema_arg}, header=True)',
            "",
        ]

    def _emit_write(self, stmt: WriteStatement) -> None:
        name = stmt.record_name.lower().replace('_', '-')
        self._lines += [
            f"# WRITE {name} — persist transformed DataFrame",
            f'{self._df_var}.write.mode("overwrite").csv("output/{name}", header=True)',
            "",
        ]

    # ------------------------------------------------------------------
    # Transformation statements → withColumn
    # ------------------------------------------------------------------

    def _emit_if(self, stmt: IfStatement) -> None:
        """Convert IF … MOVE … END-IF to withColumn(when(…))."""
        condition_expr = self._translate_condition(stmt.condition)

        # Find the MOVE / COMPUTE inside then-branch
        for sub in stmt.then_statements:
            if isinstance(sub, MoveStatement):
                value_expr = self._translate_value(sub.source)
                col_name = sub.target

                else_expr: Optional[str] = None
                if stmt.else_clause:
                    for esub in stmt.else_clause.statements:
                        if isinstance(esub, MoveStatement):
                            else_expr = self._translate_value(esub.source)

                if else_expr:
                    spark_expr = f"when({condition_expr}, {value_expr}).otherwise({else_expr})"
                else:
                    spark_expr = f"when({condition_expr}, {value_expr})"

                self._lines += [
                    f"# IF {stmt.condition.replace('_','-')} → set {col_name.replace('_','-')}",
                    f'{self._df_var} = {self._df_var}.withColumn(',
                    f'    "{col_name}",',
                    f'    {spark_expr}',
                    ")",
                    "",
                ]

            elif isinstance(sub, ComputeStatement):
                expr_str = self._translate_expression(sub.expression)
                self._lines += [
                    f"# IF {stmt.condition.replace('_','-')} → compute {sub.target.replace('_','-')}",
                    f'{self._df_var} = {self._df_var}.withColumn(',
                    f'    "{sub.target}",',
                    f'    when({condition_expr}, {expr_str})',
                    ")",
                    "",
                ]

    def _emit_move(self, stmt: MoveStatement) -> None:
        """MOVE literal TO field → withColumn("field", lit(value))"""
        value_expr = self._translate_value(stmt.source)
        self._lines += [
            f"# MOVE {stmt.source} TO {stmt.target.replace('_','-')}",
            f'{self._df_var} = {self._df_var}.withColumn("{stmt.target}", {value_expr})',
            "",
        ]

    def _emit_compute(self, stmt: ComputeStatement) -> None:
        """COMPUTE target = expr → withColumn("target", expr)"""
        expr_str = self._translate_expression(stmt.expression)
        self._lines += [
            f"# COMPUTE {stmt.target.replace('_','-')} = {stmt.expression}",
            f'{self._df_var} = {self._df_var}.withColumn(',
            f'    "{stmt.target}",',
            f'    {expr_str}',
            ")",
            "",
        ]

    def _emit_add(self, stmt: AddStatement) -> None:
        result = stmt.giving or stmt.target
        parts = [self._translate_value(o) for o in stmt.operands]
        expr_str = f"col(\"{stmt.target}\") + {' + '.join(parts)}"
        self._lines += [
            f"# ADD {' + '.join(stmt.operands)} TO {stmt.target.replace('_','-')}",
            f'{self._df_var} = {self._df_var}.withColumn("{result}", {expr_str})',
            "",
        ]

    def _emit_subtract(self, stmt: SubtractStatement) -> None:
        result = stmt.giving or stmt.target
        parts = [self._translate_value(o) for o in stmt.operands]
        expr_str = f"col(\"{stmt.target}\") - {' - '.join(parts)}"
        self._lines += [
            f"# SUBTRACT {' - '.join(stmt.operands)} FROM {stmt.target.replace('_','-')}",
            f'{self._df_var} = {self._df_var}.withColumn("{result}", {expr_str})',
            "",
        ]

    def _emit_multiply(self, stmt: MultiplyStatement) -> None:
        result = stmt.giving or stmt.operand_b
        a = self._translate_value(stmt.operand_a)
        b = self._translate_value(stmt.operand_b)
        self._lines += [
            f"# MULTIPLY {stmt.operand_a} BY {stmt.operand_b}",
            f'{self._df_var} = {self._df_var}.withColumn("{result}", {a} * {b})',
            "",
        ]

    def _emit_divide(self, stmt: DivideStatement) -> None:
        result = stmt.giving or stmt.dividend
        num = self._translate_value(stmt.dividend)
        den = self._translate_value(stmt.divisor)
        self._lines += [
            f"# DIVIDE {stmt.divisor} INTO {stmt.dividend}",
            f'{self._df_var} = {self._df_var}.withColumn("{result}", {num} / {den})',
            "",
        ]

    def _emit_perform(self, stmt: PerformStatement) -> None:
        para = stmt.target.replace('_', '-')
        if stmt.until_condition:
            cond = self._translate_condition(stmt.until_condition)
            self._lines += [
                f"# PERFORM {para} UNTIL {stmt.until_condition}",
                f"# → In Spark, loop logic becomes a single transformation pass.",
                f"# → The paragraph '{para}' should be inlined as withColumn chains above.",
                "",
            ]
        elif stmt.times:
            self._lines += [
                f"# PERFORM {para} {stmt.times} TIMES",
                f"# → In Spark, this is typically a chain of {stmt.times} transformations.",
                "",
            ]
        else:
            self._lines += [
                f"# PERFORM {para}",
                f"# → Inline the logic from paragraph '{para}' here.",
                "",
            ]

    # ------------------------------------------------------------------
    # Expression / condition translators
    # ------------------------------------------------------------------

    def _translate_condition(self, condition: str) -> str:
        """Convert a COBOL condition string to a PySpark expression string."""
        cond = condition.strip()

        # Replace COBOL field names (UPPER-CASE with hyphens) with col() calls
        # We match identifiers that contain letters and hyphens
        def replace_field(m: re.Match) -> str:
            name = m.group(0)
            normalised = name.upper().replace('-', '_')
            # If it looks like a known field or a COBOL-style name, wrap in col()
            if name.upper() == name and re.match(r'^[A-Z][A-Z0-9\-_]+$', name):
                return f'col("{normalised}")'
            return name

        # Translate comparison operators
        cond = re.sub(r'\bGREATER\s+THAN\s+OR\s+EQUAL\s+TO\b', '>=', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bLESS\s+THAN\s+OR\s+EQUAL\s+TO\b', '<=', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bGREATER\s+THAN\b', '>', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bLESS\s+THAN\b', '<', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bEQUAL\s+TO\b', '==', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bNOT\s+EQUAL\b', '!=', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bNOT\b', '~', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bAND\b', '&', cond, flags=re.IGNORECASE)
        cond = re.sub(r'\bOR\b', '|', cond, flags=re.IGNORECASE)
        cond = cond.replace(' = ', ' == ')

        # Replace COBOL identifiers with col() calls
        cond = re.sub(r'\b([A-Z][A-Z0-9\-_]{2,})\b', replace_field, cond)

        # Single-quoted COBOL literals → Python strings
        cond = re.sub(r"'([^']*)'", r'"\1"', cond)

        return cond

    def _translate_value(self, value: str) -> str:
        """Translate a COBOL value (literal or field ref) to PySpark."""
        v = value.strip()
        if v.startswith("'") and v.endswith("'"):
            # String literal
            inner = v[1:-1]
            return f'lit("{inner}")'
        if re.match(r'^-?\d+(\.\d+)?$', v):
            # Numeric literal
            return f'lit({v})'
        # Field reference
        normalised = v.upper().replace('-', '_')
        return f'col("{normalised}")'

    def _translate_expression(self, expr: str) -> str:
        """Translate a COBOL arithmetic expression to PySpark."""
        result = expr.strip()

        def replace_token(m: re.Match) -> str:
            token = m.group(0)
            if re.match(r'^-?\d+(\.\d+)?$', token):
                return f'lit({token})'
            if re.match(r"^'.*'$", token):
                return f'lit("{token[1:-1]}")'
            normalised = token.upper().replace('-', '_')
            return f'col("{normalised}")'

        # Replace identifiers and literals
        result = re.sub(
            r"'[^']*'|-?\d+(?:\.\d+)?|[A-Za-z][A-Za-z0-9\-_]*",
            replace_token,
            result,
        )
        return result
