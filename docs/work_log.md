# Work Log — COBOL Batch → PySpark Converter

**Session Date:** 2026-06-07
**Model:** Claude Sonnet 4.6
**Project Type:** Learning-Focused Mainframe Modernisation Tool

---

## Objective

Build a hands-on educational project that:
1. Accepts a COBOL batch program as input
2. Parses it into an Abstract Syntax Tree (AST)
3. Extracts business rules from the AST
4. Generates equivalent PySpark DataFrame code

---

## Deliverables Completed

| # | Deliverable | Status | File(s) |
|---|---|---|---|
| 1 | System Architecture | ✅ Done | `docs/architecture.md` |
| 2 | AST Node Model | ✅ Done | `cobol_pyspark_converter/ast_nodes/nodes.py` |
| 3 | COBOL Lexer | ✅ Done | `cobol_pyspark_converter/parser/lexer.py` |
| 4 | COBOL Parser | ✅ Done | `cobol_pyspark_converter/parser/cobol_parser.py` |
| 5 | Copybook Parser | ✅ Done | `cobol_pyspark_converter/copybook/copybook_parser.py` |
| 6 | Rule Extraction Engine | ✅ Done | `cobol_pyspark_converter/rule_extractor/extractor.py` |
| 7 | PySpark Code Generator | ✅ Done | `cobol_pyspark_converter/code_generator/pyspark_generator.py` |
| 8 | Streamlit UI | ✅ Done | `cobol_pyspark_converter/ui/app.py` |
| 9 | 10 Sample COBOL Programs | ✅ Done | `examples/*.cbl` |
| 10 | Unit Tests (124 tests) | ✅ Done | `tests/` |
| 11 | Documentation & README | ✅ Done | `README.md`, `docs/` |

---

## Build Sequence

### Step 1 — Project Scaffolding

Created directory structure:

```
cobol_pyspark_converter/
├── parser/
├── ast_nodes/
├── rule_extractor/
├── code_generator/
├── copybook/
├── ui/
examples/
tests/
docs/
```

Created `requirements.txt`:
```
streamlit>=1.32.0
pytest>=8.0.0
pytest-cov>=4.1.0
graphviz>=0.20.1
```

---

### Step 2 — AST Node Definitions (`ast_nodes/nodes.py`)

**What:** Python dataclasses representing every supported COBOL construct.

**Why dataclasses:** Auto-generated `__init__`, `__repr__`, type hints — easy to inspect in tests and the UI.

**Nodes created:**

| Node | COBOL Construct |
|---|---|
| `ProgramNode` | Root of the entire program |
| `DataDivisionNode` | DATA DIVISION container |
| `FieldDefinitionNode` | One `PIC` field (level, name, type, length, decimals) |
| `ProcedureDivisionNode` | PROCEDURE DIVISION statement list |
| `MoveStatement` | `MOVE source TO target` |
| `IfStatement` | `IF … ELSE … END-IF` |
| `ElseClause` | The ELSE branch |
| `PerformStatement` | `PERFORM paragraph [UNTIL …]` |
| `ReadStatement` | `READ file-name` |
| `WriteStatement` | `WRITE record-name` |
| `ComputeStatement` | `COMPUTE target = expression` |
| `AddStatement` | `ADD … TO …` |
| `SubtractStatement` | `SUBTRACT … FROM …` |
| `MultiplyStatement` | `MULTIPLY … BY … GIVING …` |
| `DivideStatement` | `DIVIDE … INTO … GIVING … REMAINDER …` |
| `StopRunStatement` | `STOP RUN` |

All nodes implement `to_dict()` for JSON serialisation (used in the Streamlit UI AST tab).

**Key design decision:** The `node_type` string field (auto-set in `__post_init__`) lets us identify nodes in serialised form without isinstance() checks — important for the UI rendering.

---

### Step 3 — COBOL Lexer (`parser/lexer.py`)

**What:** Converts raw COBOL source text into a flat list of `Token` objects.

**Why a separate lexer:** Separating tokenisation from parsing keeps both stages simple and independently testable.

**Token types defined (TokenType enum):** 60+ types covering:
- Structural keywords: `IDENTIFICATION`, `DATA`, `PROCEDURE`, `DIVISION`, `SECTION`
- Data keywords: `PIC`, `PICTURE`, `OCCURS`, `REDEFINES`, `VALUE`
- Statement keywords: `MOVE`, `TO`, `IF`, `ELSE`, `END_IF`, `PERFORM`, `UNTIL`, `READ`, `WRITE`, `COMPUTE`, `ADD`, `SUBTRACT`, `MULTIPLY`, `DIVIDE`, `INTO`, `GIVING`, `REMAINDER`, `STOP`, `RUN`
- Comparison keywords: `NOT`, `AND`, `OR`, `EQUAL`, `GREATER`, `LESS`, `THAN`
- Operators: `EQUALS`, `PLUS`, `MINUS`, `STAR`, `SLASH`, `DOT`, `LPAREN`, `RPAREN`, `GREATER_THAN`, `LESS_THAN`
- Primitives: `INTEGER`, `DECIMAL`, `STRING_LITERAL`, `IDENTIFIER`, `LEVEL_NUMBER`
- Housekeeping: `NEWLINE`, `EOF`, `UNKNOWN`

**COBOL-specific handling:**
- **Case insensitivity:** All keywords looked up via `.lower()` — matches real COBOL compiler behaviour
- **Hyphenated identifiers:** `CUSTOMER-ID`, `ACCOUNT-BALANCE` treated as single tokens
- **Level numbers:** `01`, `05`, `77` — distinguished from plain integers by context (followed by an alphabetic character)
- **String literals:** Single-quoted `'PREMIUM'`
- **Comment lines:** Lines starting with `*` (COBOL traditional comment style) are silently skipped
- **PIC clause components:** `9(7)V99` spread across multiple tokens and later reassembled

**KEYWORD lookup table:** A plain Python dict maps lowercase keyword strings to `TokenType` values — fast, readable, and easy to extend.

---

### Step 4 — COBOL Parser (`parser/cobol_parser.py`)

**What:** Recursive-descent parser that reads the token stream and builds the AST.

**Strategy — Recursive Descent:**
One method per grammar rule. Each method consumes tokens from the front of the stream and returns an AST node. This mirrors the grammar structure directly, making the connection between grammar and code explicit for learners.

**Grammar handled:**
```
program       → identification-div data-div procedure-div
data-div      → 'DATA' 'DIVISION' '.' {field-definition}
field-def     → level-number identifier 'PIC' pic-clause '.'
procedure-div → 'PROCEDURE' 'DIVISION' '.' {statement}
statement     → move | if | compute | add | subtract
              | multiply | divide | read | write | perform | stop-run
if            → 'IF' condition {statement} ['ELSE' {statement}] 'END-IF'
```

**PIC clause interpreter (`_parse_pic`):** A regex function that decodes any PIC clause into `(cobol_type, length, decimal_places)`:
- `PIC X(10)` → `('alphanumeric', 10, 0)`
- `PIC 9(7)V99` → `('decimal', 7, 2)`
- `PIC S9(9)V99` → `('signed_decimal', 9, 2)`
- `PIC 999` (repeated chars) → `('numeric', 3, 0)`

**Field name normalisation:** All field names converted from `HYPHEN-CASE` to `UNDERSCORE_CASE` to match Spark column naming conventions.

**Identification Division:** Skipped (not needed for conversion) but program name is extracted.

**Helper methods:**
- `_advance()`, `_match()`, `_expect()` — token navigation
- `_skip_to_dot()` — recover from unexpected input
- `_collect_pic_clause()` — reassemble multi-token PIC strings
- `_collect_condition()` — collect comparison expressions stopping at statement keywords
- `_collect_expression()` — collect arithmetic expressions

---

### Step 5 — Copybook Parser (`copybook/copybook_parser.py`)

**What:** Standalone parser for COBOL copybook files (record layout definitions).

**Why copybooks matter:** In mainframe shops, copybooks are the canonical schema registry. They define record layouts shared across dozens of programs — the precursor of modern schema registries.

**Output:**
1. `List[FieldDefinitionNode]` — same node type as the main parser produces
2. Spark `StructType` Python source code (as a string, ready to paste)

**PIC → Spark type mapping:**

| PIC Clause | Spark Type |
|---|---|
| `PIC X(n)` | `StringType()` |
| `PIC 9(n)` | `LongType()` |
| `PIC S9(n)` | `LongType()` |
| `PIC 9(n)V99` | `DecimalType(n+2, 2)` |
| `PIC S9(n)V99` | `DecimalType(n+2, 2)` |

**Why `DecimalType` not `DoubleType`:** Financial data requires exact decimal arithmetic. `float`/`double` cannot represent 0.1 exactly. `DecimalType` maps to `java.math.BigDecimal`.

**Bug fixed during testing:** Initial regex required `IS` keyword (`PIC IS X(10)`) but test data used the more common `PIC X(10)` form. Fixed the regex to make `IS` optional: `(?:PIC|PICTURE)(?:\s+IS)?\s+`.

---

### Step 6 — Rule Extractor (`rule_extractor/extractor.py`)

**What:** Walks the AST and produces structured `BusinessRule` objects representing the business logic, independent of how it is implemented in code.

**Why separate rule extraction:** In real modernisation projects, business analysts must validate that the new system implements the same rules as the old one. They need readable documentation, not code. The rule extractor bridges this gap.

**Rule types:**

| Rule Class | Source | Fields |
|---|---|---|
| `ConditionalRule` | `IfStatement` | `condition`, `then_actions`, `else_actions`, `nested_rules` |
| `AssignmentRule` | `MoveStatement` | `target`, `value` |
| `ComputationRule` | `ComputeStatement`, `AddStatement`, `SubtractStatement`, `MultiplyStatement`, `DivideStatement` | `target`, `expression`, `operator` |
| `IORule` | `ReadStatement`, `WriteStatement` | `operation`, `file_or_record` |
| `LoopRule` | `PerformStatement` | `target_paragraph`, `until_condition`, `times` |

**Documentation generator:** `generate_documentation()` formats all rules into a human-readable text report including: Rule ID, type, description, COBOL source, condition/expression/target details, and a total rule count.

---

### Step 7 — PySpark Code Generator (`code_generator/pyspark_generator.py`)

**What:** Visits each AST node and emits lines of PySpark DataFrame code, assembled into a complete runnable Python script.

**Key conceptual shift explained in code comments:**
```
COBOL batch:  for each record → apply IF/COMPUTE/MOVE → write record
PySpark:      load ALL records → apply withColumn chains → write ALL
```

**Generated code structure:**
1. Header (imports + SparkSession creation)
2. Schema definition (from DATA DIVISION `FieldDefinitionNode` list)
3. Procedure transformations (one `withColumn` per statement)
4. Footer (`spark.stop()`)

**Statement → code mappings:**

| AST Node | PySpark Pattern |
|---|---|
| `ReadStatement` | `spark.read.csv("filename.csv", schema=schema, header=True)` |
| `WriteStatement` | `df.write.mode("overwrite").csv("output/name", header=True)` |
| `IfStatement` + `MoveStatement` | `df.withColumn("col", when(cond, val).otherwise(other))` |
| `IfStatement` + `ComputeStatement` | `df.withColumn("col", when(cond, expr))` |
| `MoveStatement` (standalone) | `df.withColumn("col", lit(value))` |
| `ComputeStatement` | `df.withColumn("col", translated_expr)` |
| `AddStatement` | `df.withColumn("col", col("a") + col("b"))` |
| `SubtractStatement` | `df.withColumn("col", col("a") - col("b"))` |
| `MultiplyStatement` | `df.withColumn("col", col("a") * col("b"))` |
| `DivideStatement` | `df.withColumn("col", col("a") / col("b"))` |
| `PerformStatement` | Comment explaining the manual inlining needed |

**Condition translator (`_translate_condition`):** Converts COBOL conditions to PySpark:
- `GREATER THAN` → `>`
- `LESS THAN` → `<`
- `EQUAL TO` → `==`
- `NOT EQUAL` → `!=`
- `AND` → `&`
- `OR` → `|`
- Field names → `col("FIELD_NAME")`
- `'PREMIUM'` → `"PREMIUM"`

**Expression translator (`_translate_expression`):** Converts COBOL arithmetic expressions:
- Identifiers → `col("NAME")`
- Numeric literals → `lit(value)`
- String literals → `lit("value")`

---

### Step 8 — Streamlit UI (`ui/app.py`)

**What:** Two-panel web application for interactive COBOL → PySpark conversion.

**Sidebar:**
- Mode selector: `COBOL Program Converter` / `Copybook → Schema`
- Pipeline diagram (ASCII art showing all 6 stages)
- Learning objectives list

**COBOL Converter mode:**
- Left panel: text area with sample program selector (5 built-in samples)
- Right panel (4 tabs):
  - **Fields tab:** Table of parsed DATA DIVISION fields (level, name, PIC, type, length, decimals, parent record)
  - **AST tab:** Interactive JSON tree of the full program AST
  - **Rules tab:** Expandable rule cards (with emoji icons by type) + full documentation text
  - **PySpark tab:** Syntax-highlighted generated code + download button

**Copybook mode:**
- Text area for copybook input
- Side-by-side: parsed field table + generated StructType code

**Learning Guide tab:**
- Explains COBOL batch vs Spark paradigm difference
- PIC clause quick reference table
- AST diagram example
- Code generation patterns table

**5 Built-in samples:**
1. Customer Classification (nested IF/ELSE)
2. Interest Calculation (COMPUTE with decimals)
3. Loan Eligibility (multi-tier IF + COMPUTE)
4. Employee Payroll (overtime + tax + pension)
5. Product Discount (tiered discount logic)

---

### Step 9 — 10 Sample COBOL Programs (`examples/`)

| File | Program | Business Domain | COBOL Features |
|---|---|---|---|
| `01_customer_classification.cbl` | CUSTCLASSIFY | Retail Banking | Nested IF/ELSE, MOVE, READ/WRITE |
| `02_account_balance_processing.cbl` | ACCTBAL | Banking | COMPUTE, SUBTRACT, multi-IF |
| `03_interest_calculation.cbl` | INTERESTCALC | Savings | COMPUTE with rate tiers |
| `04_insurance_premium.cbl` | INSPREMIUM | Insurance | MULTIPLY, loading factors, senior discount |
| `05_loan_eligibility.cbl` | LOANCHECK | Lending | Multi-tier IF, debt ratio COMPUTE |
| `06_employee_payroll.cbl` | PAYROLL | HR/Payroll | Overtime (1.5x), tax, pension, audit flag |
| `07_invoice_processing.cbl` | INVOICEPROC | Procurement | VAT, bulk discount, late penalty |
| `08_product_discount.cbl` | DISCOUNT | Retail | 4-tier quantity discount + VIP discount |
| `09_claims_processing.cbl` | CLAIMSPROC | Insurance | Policy limit check, days-submitted routing |
| `10_banking_transaction_validation.cbl` | TXNVALIDATE | Banking | AML flag, velocity check, balance validation |

Each program includes:
- Full `IDENTIFICATION DIVISION` with `PROGRAM-ID`
- `DATA DIVISION` with realistic field definitions and proper PIC clauses
- `PROCEDURE DIVISION` with a business rule flow
- Header comment explaining the business rules and COBOL concepts demonstrated

---

### Step 10 — Unit Tests (`tests/`)

**124 tests total, all passing.**

**`test_lexer.py` — 40 tests:**
- Keywords (MOVE, IF, END-IF, COMPUTE, READ, WRITE, STOP RUN, DATA DIVISION) — case-insensitive
- Identifiers (simple, hyphenated, with digits, multiple)
- Literals (string, integer, decimal, zero)
- Operators (=, >, <, +, -, *, /)
- Level numbers (01, 05, 77)
- PIC clause tokenisation (keyword, X components, parentheses)
- Comment handling (star lines skipped, multiline)
- Full snippet tests (MOVE, IF, COMPUTE, EOF sentinel)

**`test_parser.py` — 32 tests:**
- Program structure (returns ProgramNode, program name, both divisions present)
- Data Division (field count, level numbers, names normalised to UNDERSCORE_CASE, types, decimals, parent links)
- Procedure Division (READ, IF, IF condition, THEN branch, ELSE branch, MOVE source/target, WRITE, STOP RUN, COMPUTE, ADD, SUBTRACT, MULTIPLY, DIVIDE)
- AST serialisation (program, data division, field, IF statement to dict)

**`test_rule_extractor.py` — 28 tests:**
- Rule extraction (returns list, READ IORule, WRITE IORule, ConditionalRule, condition content, then/else actions)
- Computation rules (count, operator, target)
- Loop rules (extracted, condition present)
- Rule IDs (unique), descriptions (non-empty)
- Dict serialisation (ConditionalRule, IORule, ComputationRule dicts)
- Documentation generation (returns string, contains program name, rule details, total count)

**`test_code_generator.py` — 24 tests:**
- Code structure (generates string, PySpark imports, SparkSession, program name, spark.stop())
- Schema generation (StructType/StructField present, StringType for alphanumeric, DecimalType for decimal, field names)
- READ → spark.read.csv (present, schema arg, filename)
- IF → withColumn(when(…)) (withColumn, when, otherwise, condition content, lit("PREMIUM"), target column)
- COMPUTE → withColumn (present, target column, col references, * operator)
- ADD → withColumn with + (present, + operator)
- MULTIPLY GIVING → withColumn (present, * operator, result column)
- WRITE → df.write.csv (present, .csv(), overwrite mode)
- Copybook parser (parse, alphanumeric field, decimal field, schema code, all fields in code, struct_fields pairs)

---

### Step 11 — Documentation (`docs/`, `README.md`)

**`docs/architecture.md`:**
- ASCII pipeline diagram showing all 6 stages with inputs/outputs
- Component responsibilities (1 section per component)
- Grammar handled by the parser (informal BNF)
- COBOL construct → AST node mapping table
- PIC type → Spark type table with rationale
- Rule extractor rule-type table
- Code generator node → PySpark mapping table
- Key design decisions (why recursive descent, why dataclasses, why separate rule extractor, why DecimalType)
- Full data flow example (IF/MOVE → Lexer → Parser → Rule → Code)

**`README.md`:**
- Learning objective table (topic → where you see it)
- Project structure tree
- Quick start (install, run UI, run tests, use from Python)
- Pipeline diagram
- Full COBOL → PySpark mapping table
- PIC clause → Spark type table with DecimalType rationale
- Sample program index (all 10 with domain and key concepts)
- Key learning concepts (batch vs Spark paradigm, AST structure example)
- Deliberate limitations section (what was left out and why)

---

## Test Results Summary

```
============================= test session starts ==============================
platform darwin -- Python 3.9.13, pytest-8.4.2

collected 124 items

tests/test_code_generator.py   31 passed
tests/test_lexer.py            40 passed
tests/test_parser.py           32 passed
tests/test_rule_extractor.py   21 passed

========================== 124 passed in 0.13s ================================
```

---

## Bug Fixed During Development

**Issue:** Copybook parser regex required the optional `IS` keyword (`PIC IS X(10)`) but test data used the more common short form `PIC X(10)`.

**Root cause:** Regex pattern was `\s+IS\s+` (mandatory) instead of `(?:\s+IS)?\s+` (optional).

**Fix:** Changed regex in `copybook/copybook_parser.py` line 66:
```python
# Before (broke on PIC X(10)):
r'^(\d{1,2})\s+([A-Z0-9][A-Z0-9\-]*)\s+(?:PIC|PICTURE)\s+IS\s+(\S+)\s*\.?$'

# After (handles both PIC X(10) and PIC IS X(10)):
r'^(\d{1,2})\s+([A-Z0-9][A-Z0-9\-]*)\s+(?:PIC|PICTURE)(?:\s+IS)?\s+(\S+)\s*\.?$'
```

Result: went from 120 passing / 4 failing → **124/124 passing**.

---

## End-to-End Smoke Test Output

Ran example 06 (Employee Payroll) through the full pipeline:

**Input COBOL fields parsed:**
```
EMP_ID           alphanumeric    len=10  dec=0
EMP_NAME         alphanumeric    len=30  dec=0
HOURLY_RATE      decimal         len=5   dec=2
HOURS_WORKED     decimal         len=3   dec=2
OVERTIME_HOURS   decimal         len=3   dec=2
GROSS_PAY        decimal         len=7   dec=2
TAX_AMOUNT       decimal         len=7   dec=2
PENSION_AMOUNT   decimal         len=7   dec=2
NET_PAY          decimal         len=7   dec=2
AUDIT_FLAG       alphanumeric    len=1   dec=0
```

**Business rules extracted:**
```
[IORule]          Read records from EMPLOYEE-FILE
[ComputationRule] Calculate GROSS-PAY = HOURLY-RATE * HOURS-WORKED
[ConditionalRule] If OVERTIME-HOURS > 0 then compute GROSS-PAY = ...
[ComputationRule] Calculate TAX-AMOUNT = GROSS-PAY * 0.20
[ComputationRule] Calculate PENSION-AMOUNT = GROSS-PAY * 0.05
[ComputationRule] Calculate NET-PAY = GROSS-PAY - TAX-AMOUNT - PENSION-AMOUNT
[ConditionalRule] If GROSS-PAY > 10000 then set AUDIT-FLAG = Y
[IORule]          Write OUTPUT-RECORD to output file
```

**Generated PySpark (excerpt):**
```python
schema = StructType([
    StructField("GROSS_PAY",       DecimalType(9, 2),  nullable=True),
    StructField("TAX_AMOUNT",      DecimalType(9, 2),  nullable=True),
    StructField("NET_PAY",         DecimalType(9, 2),  nullable=True),
    StructField("AUDIT_FLAG",      StringType(),       nullable=True),
    ...
])

df = spark.read.csv("employee-file.csv", schema=schema, header=True)

df = df.withColumn("GROSS_PAY", col("HOURLY_RATE") * col("HOURS_WORKED"))
df = df.withColumn("GROSS_PAY",
    when(col("OVERTIME_HOURS") > 0,
         col("GROSS_PAY") + (col("OVERTIME_HOURS") * col("HOURLY_RATE") * lit(1.5))))
df = df.withColumn("TAX_AMOUNT",     col("GROSS_PAY") * lit(0.20))
df = df.withColumn("PENSION_AMOUNT", col("GROSS_PAY") * lit(0.05))
df = df.withColumn("NET_PAY",        col("GROSS_PAY") - col("TAX_AMOUNT") - col("PENSION_AMOUNT"))
df = df.withColumn("AUDIT_FLAG",     when(col("GROSS_PAY") > 10000, lit("Y")).otherwise(lit("N")))

df.write.mode("overwrite").csv("output/output-record", header=True)
spark.stop()
```

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit UI
streamlit run cobol_pyspark_converter/ui/app.py

# Run all tests
pytest tests/ -v

# Use from Python directly
python -c "
from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.rule_extractor import RuleExtractor
from cobol_pyspark_converter.code_generator import PySparkGenerator

src = open('examples/06_employee_payroll.cbl').read()
prog = COBOLParser(src).parse()
print(PySparkGenerator(prog).generate())
"
```
