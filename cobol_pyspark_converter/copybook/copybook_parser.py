"""
Copybook Parser
===============
A COBOL *copybook* (COPY member) is a reusable data-layout definition stored
in a library and pulled into programs with the COPY statement.  In mainframe
shops, copybooks define the canonical schema for every record type — they are
the precursors of what we today call schema registries.

What we do here
---------------
We parse a standalone copybook text and produce two things:
  1. A list of FieldDefinitionNode objects (same as the DATA DIVISION parser).
  2. A Spark StructType definition as a *Python source string* ready to paste
     into a PySpark job.

PIC type → Spark type mapping
------------------------------
  PIC X(n)   → StringType()           (variable-length text)
  PIC 9(n)   → LongType()             (integer)
  PIC S9(n)  → LongType()             (signed integer)
  PIC 9(n)V99 → DecimalType(n+2, 2)  (fixed-point decimal)
  PIC S9(n)V99 → DecimalType(n+2, 2) (signed fixed-point decimal)

Why DecimalType instead of DoubleType?
  Financial data must use exact decimal arithmetic.  FloatingPoint types
  (float, double) cannot represent values like 0.1 exactly, causing rounding
  errors in monetary calculations.  Spark's DecimalType maps directly to
  java.math.BigDecimal which is what banks and insurers require.
"""

from __future__ import annotations
import re
from typing import List, Tuple

from ..ast_nodes.nodes import FieldDefinitionNode
from ..parser.cobol_parser import _parse_pic   # reuse the PIC interpreter


class CopybookParser:
    """Parse a COBOL copybook and generate Spark schema code.

    Usage::

        cp = CopybookParser(copybook_text)
        fields = cp.parse()
        schema_code = cp.to_spark_schema_code()
    """

    def __init__(self, source: str) -> None:
        self._source = source
        self._fields: List[FieldDefinitionNode] = []

    def parse(self) -> List[FieldDefinitionNode]:
        """Return a list of FieldDefinitionNode objects."""
        self._fields = []
        current_record: str | None = None

        for line in self._source.splitlines():
            line = line.strip()
            # Skip blank lines and comment lines (* in col 7, or starting with *)
            if not line or line.startswith('*'):
                continue

            # Match: level-number  name  PIC [IS] clause
            match = re.match(
                r'^(\d{1,2})\s+([A-Z0-9][A-Z0-9\-]*)\s+(?:PIC|PICTURE)(?:\s+IS)?\s+(\S+)\s*\.?$',
                line, re.IGNORECASE
            )
            if match:
                level = int(match.group(1))
                name = match.group(2).upper().replace('-', '_')
                pic_raw = match.group(3).rstrip('.')
                cobol_type, length, dec = _parse_pic(pic_raw)
                field = FieldDefinitionNode(
                    level=level, name=name, pic_clause=pic_raw,
                    cobol_type=cobol_type, length=length,
                    decimal_places=dec, parent=current_record if level != 1 else None,
                )
                if level == 1:
                    current_record = name
                self._fields.append(field)
                continue

            # Match group item (no PIC clause): 01 CUSTOMER-REC.
            match2 = re.match(r'^(\d{1,2})\s+([A-Z0-9][A-Z0-9\-]*)\s*\.?$', line, re.IGNORECASE)
            if match2:
                level = int(match2.group(1))
                name = match2.group(2).upper().replace('-', '_')
                if level == 1:
                    current_record = name
                    self._fields.append(FieldDefinitionNode(
                        level=level, name=name, cobol_type='group', parent=None
                    ))

        return self._fields

    # ------------------------------------------------------------------
    # Spark schema code generation
    # ------------------------------------------------------------------

    def to_spark_schema_code(self) -> str:
        """Return a Python string defining a Spark StructType for the copybook."""
        if not self._fields:
            self.parse()

        elementary = [f for f in self._fields if f.level != 1 and f.cobol_type != 'group']
        lines = ["from pyspark.sql.types import StructType, StructField, StringType, LongType, DecimalType, IntegerType",
                 "",
                 "schema = StructType(["]
        for f in elementary:
            spark_type = self._to_spark_type(f)
            lines.append(f"    StructField(\"{f.name}\", {spark_type}, nullable=True),")
        lines.append("])")
        return '\n'.join(lines)

    def to_struct_fields(self) -> List[Tuple[str, str]]:
        """Return list of (field_name, spark_type_string) pairs."""
        if not self._fields:
            self.parse()
        return [
            (f.name, self._to_spark_type(f))
            for f in self._fields
            if f.level != 1 and f.cobol_type != 'group'
        ]

    @staticmethod
    def _to_spark_type(field: FieldDefinitionNode) -> str:
        ct = field.cobol_type
        if ct == 'alphanumeric':
            return 'StringType()'
        if ct in ('decimal', 'signed_decimal'):
            precision = field.length + field.decimal_places
            return f'DecimalType({precision}, {field.decimal_places})'
        if ct in ('numeric', 'signed_numeric'):
            return 'LongType()'
        return 'StringType()'
