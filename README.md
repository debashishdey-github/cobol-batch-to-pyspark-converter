# COBOL Batch → PySpark Converter

A **learning-focused** mainframe modernisation tool that converts COBOL batch
programs into equivalent PySpark DataFrame jobs.

---

## What This Project Teaches

| Topic | Where You See It |
|---|---|
| How COBOL batch processing works | `examples/*.cbl` sample programs |
| How copybooks define schemas | `copybook/copybook_parser.py` |
| How lexers tokenise source code | `parser/lexer.py` |
| How parsers build ASTs | `parser/cobol_parser.py` |
| How ASTs represent programs | `ast_nodes/nodes.py` |
| How business rules are extracted | `rule_extractor/extractor.py` |
| How code generators work | `code_generator/pyspark_generator.py` |
| How Spark DataFrames transform data | Generated `.py` files |

---

## Project Structure

```
cobol_pyspark_converter/
├── parser/
│   ├── lexer.py            ← Stage 1: tokenise COBOL source
│   └── cobol_parser.py     ← Stage 2: build AST from tokens
├── ast_nodes/
│   └── nodes.py            ← AST node dataclasses
├── rule_extractor/
│   └── extractor.py        ← Extract business rules from AST
├── code_generator/
│   └── pyspark_generator.py ← Generate PySpark code from AST
├── copybook/
│   └── copybook_parser.py  ← Parse COBOL copybooks → StructType
├── ui/
│   └── app.py              ← Streamlit web application
examples/
├── 01_customer_classification.cbl
├── 02_account_balance_processing.cbl
├── 03_interest_calculation.cbl
├── 04_insurance_premium.cbl
├── 05_loan_eligibility.cbl
├── 06_employee_payroll.cbl
├── 07_invoice_processing.cbl
├── 08_product_discount.cbl
├── 09_claims_processing.cbl
└── 10_banking_transaction_validation.cbl
tests/
├── test_lexer.py
├── test_parser.py
├── test_rule_extractor.py
└── test_code_generator.py
docs/
└── architecture.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Streamlit UI

```bash
streamlit run cobol_pyspark_converter/ui/app.py
```

Open http://localhost:8501 in your browser.

### 3. Run the tests

```bash
pytest tests/ -v
```

### 4. Use the converter directly from Python

```python
from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.rule_extractor import RuleExtractor
from cobol_pyspark_converter.code_generator import PySparkGenerator

cobol_source = """
IDENTIFICATION DIVISION.
PROGRAM-ID. DEMO.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CUST-REC.
   05 BALANCE      PIC 9(7)V99.
   05 CUST-TYPE    PIC X(10).

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

# Parse
parser = COBOLParser(cobol_source)
program = parser.parse()

# Extract business rules
extractor = RuleExtractor(program)
rules = extractor.extract()
print(extractor.generate_documentation())

# Generate PySpark
gen = PySparkGenerator(program)
print(gen.generate())
```

---

## Conversion Pipeline

```
COBOL Source
    │
    ▼
 Lexer              tokenise() → List[Token]
    │
    ▼
 Parser             parse() → ProgramNode (AST)
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
Rule Extractor                  Code Generator
extract() → List[Rule]          generate() → str (PySpark)
generate_documentation()
```

---

## COBOL → PySpark Mapping

| COBOL | PySpark |
|---|---|
| `MOVE 'X' TO FIELD` | `df.withColumn("FIELD", lit("X"))` |
| `IF BALANCE > 1000 MOVE 'PREMIUM' TO TYPE END-IF` | `df.withColumn("TYPE", when(col("BALANCE") > 1000, lit("PREMIUM")))` |
| `COMPUTE TOTAL = PRICE * QTY` | `df.withColumn("TOTAL", col("PRICE") * col("QTY"))` |
| `ADD A TO B` | `df.withColumn("B", col("B") + col("A"))` |
| `SUBTRACT A FROM B` | `df.withColumn("B", col("B") - col("A"))` |
| `MULTIPLY A BY B GIVING C` | `df.withColumn("C", col("A") * col("B"))` |
| `DIVIDE A INTO B` | `df.withColumn("B", col("B") / col("A"))` |
| `READ CUSTOMER-FILE` | `df = spark.read.csv("customer-file.csv", schema=schema)` |
| `WRITE OUTPUT-RECORD` | `df.write.mode("overwrite").csv("output/output-record")` |
| `STOP RUN` | `spark.stop()` |

---

## PIC Clause → Spark Type Mapping

| COBOL PIC | Example | Spark Type |
|---|---|---|
| `PIC X(n)` | `PIC X(10)` | `StringType()` |
| `PIC 9(n)` | `PIC 9(5)` | `LongType()` |
| `PIC 9(n)V99` | `PIC 9(7)V99` | `DecimalType(9, 2)` |
| `PIC S9(n)` | `PIC S9(9)` | `LongType()` |
| `PIC S9(n)V99` | `PIC S9(9)V99` | `DecimalType(11, 2)` |

> **Why DecimalType?**
> Monetary values must never use floating-point types (float/double).
> `DecimalType` maps to `java.math.BigDecimal`, providing exact decimal arithmetic.

---

## Sample Programs

| # | Program | Business Domain | Key Concepts |
|---|---|---|---|
| 1 | Customer Classification | Retail Banking | Nested IF/ELSE, MOVE |
| 2 | Account Balance Processing | Banking | COMPUTE, SUBTRACT, MOVE |
| 3 | Interest Calculation | Savings | COMPUTE with decimals |
| 4 | Insurance Premium | Insurance | MULTIPLY, loading factors |
| 5 | Loan Eligibility | Lending | Multi-tier IF, COMPUTE |
| 6 | Employee Payroll | HR/Payroll | Overtime, tax, pension |
| 7 | Invoice Processing | Procurement | VAT, discount, penalty |
| 8 | Product Discount | Retail | Tiered discount logic |
| 9 | Claims Processing | Insurance | Status routing |
| 10 | Transaction Validation | Banking | AML, velocity checks |

---

## Key Learning Concepts

### COBOL Batch vs Spark
```
COBOL batch:                    PySpark:
─────────────                   ────────
for each record in file:        df = spark.read.csv(...)
    read one record             df = df.withColumn(...)  ← all rows at once
    apply business logic        df.write.csv(...)
    write one record
```

### How the AST Works
```
ProgramNode
├── DataDivisionNode
│   ├── FieldDefinitionNode(BALANCE, PIC 9(7)V99, decimal)
│   └── FieldDefinitionNode(CUST_TYPE, PIC X(10), alphanumeric)
└── ProcedureDivisionNode
    ├── ReadStatement(file=CUSTOMER_FILE)
    ├── IfStatement(condition="BALANCE > 1000")
    │   ├── then: MoveStatement('PREMIUM' → CUST_TYPE)
    │   └── else: MoveStatement('STANDARD' → CUST_TYPE)
    └── WriteStatement(record=OUTPUT_RECORD)
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for full component diagrams.

---

## Limitations (by design)

This is an **educational** tool, not a production migration factory.
Deliberately unsupported:
- COBOL COPY statements (inline copybook expansion)
- OCCURS DEPENDING ON (variable-length arrays)
- Packed decimal (COMP-3)
- Indexed/relative file organisations
- CALL statements (sub-programs)
- Complex PERFORM VARYING with nested indexes

These exclusions keep the code readable and learnable.
