"""
Unit tests for the PySpark Code Generator.

Learning objective:
  Verify that COBOL statements produce correct PySpark equivalents.
  Tests check for key PySpark patterns: withColumn, when, spark.read, etc.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.code_generator import PySparkGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate(source: str) -> str:
    prog = COBOLParser(source).parse()
    return PySparkGenerator(prog).generate()


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

PROCEDURE DIVISION.
    READ INPUT-FILE.
    COMPUTE TOTAL = PRICE * QTY.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""

ADD_PROG = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. ADDPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 ARITH-REC.
   05 A    PIC 9(5).
   05 B    PIC 9(5).

PROCEDURE DIVISION.
    READ INPUT-FILE.
    ADD A TO B.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""

MULTIPLY_PROG = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. MULPROG.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 ARITH-REC.
   05 RATE      PIC 9(5)V99.
   05 PRINCIPAL PIC 9(9)V99.
   05 INTEREST  PIC 9(9)V99.

PROCEDURE DIVISION.
    READ INPUT-FILE.
    MULTIPLY RATE BY PRINCIPAL GIVING INTEREST.
    WRITE OUTPUT-FILE.
    STOP RUN.
"""


# ---------------------------------------------------------------------------
# Generated code structure
# ---------------------------------------------------------------------------

class TestCodeStructure:
    def test_generates_string(self):
        code = generate(CLASSIFY_PROG)
        assert isinstance(code, str)
        assert len(code) > 0

    def test_imports_pyspark(self):
        code = generate(CLASSIFY_PROG)
        assert "from pyspark.sql import SparkSession" in code

    def test_imports_functions(self):
        code = generate(CLASSIFY_PROG)
        assert "from pyspark.sql.functions import" in code
        assert "col" in code
        assert "when" in code

    def test_spark_session_created(self):
        code = generate(CLASSIFY_PROG)
        assert "SparkSession.builder" in code
        assert "getOrCreate()" in code

    def test_program_name_in_app(self):
        code = generate(CLASSIFY_PROG)
        assert "CLASSIFY" in code

    def test_spark_stop_at_end(self):
        code = generate(CLASSIFY_PROG)
        assert "spark.stop()" in code


# ---------------------------------------------------------------------------
# Schema generation
# ---------------------------------------------------------------------------

class TestSchemaGeneration:
    def test_schema_generated_from_data_division(self):
        code = generate(CLASSIFY_PROG)
        assert "StructType" in code
        assert "StructField" in code

    def test_alphanumeric_field_maps_to_string_type(self):
        code = generate(CLASSIFY_PROG)
        assert "StringType()" in code

    def test_decimal_field_maps_to_decimal_type(self):
        code = generate(CLASSIFY_PROG)
        assert "DecimalType" in code

    def test_schema_contains_field_names(self):
        code = generate(CLASSIFY_PROG)
        assert "BALANCE" in code
        assert "CUST_TYPE" in code


# ---------------------------------------------------------------------------
# READ → spark.read
# ---------------------------------------------------------------------------

class TestReadGeneration:
    def test_read_generates_spark_read(self):
        code = generate(CLASSIFY_PROG)
        assert "spark.read.csv" in code

    def test_read_includes_schema_arg(self):
        code = generate(CLASSIFY_PROG)
        assert "schema=schema" in code

    def test_read_file_name_in_csv_call(self):
        code = generate(CLASSIFY_PROG)
        assert "customer-file.csv" in code or "customer_file.csv" in code.lower()


# ---------------------------------------------------------------------------
# IF → withColumn(when(…))
# ---------------------------------------------------------------------------

class TestIfGeneration:
    def test_if_generates_with_column(self):
        code = generate(CLASSIFY_PROG)
        assert "withColumn" in code

    def test_if_generates_when(self):
        code = generate(CLASSIFY_PROG)
        assert "when(" in code

    def test_else_generates_otherwise(self):
        code = generate(CLASSIFY_PROG)
        assert ".otherwise(" in code

    def test_when_contains_condition(self):
        code = generate(CLASSIFY_PROG)
        assert "BALANCE" in code
        assert "1000" in code

    def test_string_value_in_lit(self):
        code = generate(CLASSIFY_PROG)
        assert 'lit("PREMIUM")' in code or "PREMIUM" in code

    def test_target_column_name_in_with_column(self):
        code = generate(CLASSIFY_PROG)
        assert '"CUST_TYPE"' in code


# ---------------------------------------------------------------------------
# COMPUTE → withColumn(expr)
# ---------------------------------------------------------------------------

class TestComputeGeneration:
    def test_compute_generates_with_column(self):
        code = generate(COMPUTE_PROG)
        assert "withColumn" in code

    def test_compute_target_column(self):
        code = generate(COMPUTE_PROG)
        assert '"TOTAL"' in code

    def test_compute_uses_col_references(self):
        code = generate(COMPUTE_PROG)
        assert 'col("PRICE")' in code or "PRICE" in code

    def test_compute_multiplication_operator(self):
        code = generate(COMPUTE_PROG)
        assert "*" in code


# ---------------------------------------------------------------------------
# ADD → withColumn
# ---------------------------------------------------------------------------

class TestAddGeneration:
    def test_add_generates_with_column(self):
        code = generate(ADD_PROG)
        assert "withColumn" in code

    def test_add_uses_plus_operator(self):
        code = generate(ADD_PROG)
        assert "+" in code


# ---------------------------------------------------------------------------
# MULTIPLY GIVING → withColumn
# ---------------------------------------------------------------------------

class TestMultiplyGeneration:
    def test_multiply_generates_with_column(self):
        code = generate(MULTIPLY_PROG)
        assert "withColumn" in code

    def test_multiply_uses_star_operator(self):
        code = generate(MULTIPLY_PROG)
        assert "*" in code

    def test_multiply_giving_uses_result_column(self):
        code = generate(MULTIPLY_PROG)
        assert "INTEREST" in code


# ---------------------------------------------------------------------------
# WRITE → df.write
# ---------------------------------------------------------------------------

class TestWriteGeneration:
    def test_write_generates_df_write(self):
        code = generate(CLASSIFY_PROG)
        assert ".write." in code

    def test_write_uses_csv(self):
        code = generate(CLASSIFY_PROG)
        assert ".csv(" in code

    def test_write_uses_overwrite_mode(self):
        code = generate(CLASSIFY_PROG)
        assert "overwrite" in code


# ---------------------------------------------------------------------------
# Copybook parser
# ---------------------------------------------------------------------------

class TestCopybookParser:
    COPYBOOK = """\
01 CUSTOMER.
   05 CUSTOMER-ID     PIC X(10).
   05 NAME            PIC X(30).
   05 BALANCE         PIC 9(7)V99.
   05 CREDIT-SCORE    PIC 9(3).
"""

    def test_parse_returns_fields(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        fields = cp.parse()
        assert len(fields) > 0

    def test_alphanumeric_field_parsed(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        fields = cp.parse()
        cust_id = next((f for f in fields if f.name == "CUSTOMER_ID"), None)
        assert cust_id is not None
        assert cust_id.cobol_type == "alphanumeric"
        assert cust_id.length == 10

    def test_decimal_field_parsed(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        fields = cp.parse()
        balance = next((f for f in fields if f.name == "BALANCE"), None)
        assert balance is not None
        assert "decimal" in balance.cobol_type
        assert balance.decimal_places == 2

    def test_schema_code_generated(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        code = cp.to_spark_schema_code()
        assert "StructType" in code
        assert "StructField" in code
        assert "StringType" in code
        assert "DecimalType" in code

    def test_schema_code_has_all_fields(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        code = cp.to_spark_schema_code()
        assert "CUSTOMER_ID" in code
        assert "NAME" in code
        assert "BALANCE" in code
        assert "CREDIT_SCORE" in code

    def test_to_struct_fields(self):
        from cobol_pyspark_converter.copybook import CopybookParser
        cp = CopybookParser(self.COPYBOOK)
        pairs = cp.to_struct_fields()
        names = [p[0] for p in pairs]
        assert "CUSTOMER_ID" in names
        assert "BALANCE" in names
