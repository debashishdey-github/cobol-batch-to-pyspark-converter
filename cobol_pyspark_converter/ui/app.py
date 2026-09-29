"""
Streamlit UI — COBOL Batch → PySpark Converter
================================================
Run with:
    streamlit run cobol_pyspark_converter/ui/app.py
"""

import json
import sys
import os

import streamlit as st

# Make imports work whether run from project root or ui/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from cobol_pyspark_converter.parser import COBOLParser
from cobol_pyspark_converter.rule_extractor import RuleExtractor
from cobol_pyspark_converter.code_generator import PySparkGenerator
from cobol_pyspark_converter.copybook import CopybookParser


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="COBOL → PySpark Converter",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Sample COBOL programs (loaded from examples/ folder when available)
# ---------------------------------------------------------------------------

SAMPLES = {
    "1. Customer Classification": """\
IDENTIFICATION DIVISION.
PROGRAM-ID. CUSTCLASSIFY.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 CUSTOMER-REC.
   05 CUSTOMER-ID     PIC X(10).
   05 CUSTOMER-NAME   PIC X(30).
   05 BALANCE         PIC 9(7)V99.
   05 CUSTOMER-TYPE   PIC X(10).

PROCEDURE DIVISION.
    READ CUSTOMER-FILE.
    IF BALANCE > 1000
       MOVE 'PREMIUM' TO CUSTOMER-TYPE
    ELSE
       MOVE 'STANDARD' TO CUSTOMER-TYPE
    END-IF.
    WRITE OUTPUT-RECORD.
    STOP RUN.
""",
    "2. Interest Calculation": """\
IDENTIFICATION DIVISION.
PROGRAM-ID. INTERESTCALC.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 ACCOUNT-REC.
   05 ACCOUNT-ID      PIC X(10).
   05 BALANCE         PIC 9(9)V99.
   05 INTEREST-RATE   PIC 9(2)V99.
   05 INTEREST-AMT    PIC 9(9)V99.
   05 NEW-BALANCE     PIC 9(9)V99.

PROCEDURE DIVISION.
    READ ACCOUNT-FILE.
    COMPUTE INTEREST-AMT = BALANCE * INTEREST-RATE / 100.
    COMPUTE NEW-BALANCE = BALANCE + INTEREST-AMT.
    WRITE OUTPUT-RECORD.
    STOP RUN.
""",
    "3. Loan Eligibility": """\
IDENTIFICATION DIVISION.
PROGRAM-ID. LOANCHECK.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 APPLICANT-REC.
   05 APPLICANT-ID    PIC X(10).
   05 CREDIT-SCORE    PIC 9(3).
   05 ANNUAL-INCOME   PIC 9(9)V99.
   05 LOAN-STATUS     PIC X(10).
   05 LOAN-LIMIT      PIC 9(9)V99.

PROCEDURE DIVISION.
    READ APPLICANT-FILE.
    IF CREDIT-SCORE > 700
       MOVE 'APPROVED' TO LOAN-STATUS
       COMPUTE LOAN-LIMIT = ANNUAL-INCOME * 5
    ELSE
       MOVE 'REJECTED' TO LOAN-STATUS
       MOVE 0 TO LOAN-LIMIT
    END-IF.
    WRITE OUTPUT-RECORD.
    STOP RUN.
""",
    "4. Employee Payroll": """\
IDENTIFICATION DIVISION.
PROGRAM-ID. PAYROLL.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 EMPLOYEE-REC.
   05 EMP-ID          PIC X(10).
   05 HOURLY-RATE     PIC 9(5)V99.
   05 HOURS-WORKED    PIC 9(3)V99.
   05 OVERTIME-HOURS  PIC 9(3)V99.
   05 GROSS-PAY       PIC 9(7)V99.
   05 TAX-AMOUNT      PIC 9(7)V99.
   05 NET-PAY         PIC 9(7)V99.

PROCEDURE DIVISION.
    READ EMPLOYEE-FILE.
    COMPUTE GROSS-PAY = HOURLY-RATE * HOURS-WORKED.
    IF OVERTIME-HOURS > 0
       COMPUTE GROSS-PAY = GROSS-PAY + (OVERTIME-HOURS * HOURLY-RATE * 1.5)
    END-IF.
    COMPUTE TAX-AMOUNT = GROSS-PAY * 0.20.
    COMPUTE NET-PAY = GROSS-PAY - TAX-AMOUNT.
    WRITE OUTPUT-RECORD.
    STOP RUN.
""",
    "5. Product Discount": """\
IDENTIFICATION DIVISION.
PROGRAM-ID. DISCOUNT.

DATA DIVISION.
WORKING-STORAGE SECTION.
01 PRODUCT-REC.
   05 PRODUCT-ID      PIC X(10).
   05 UNIT-PRICE      PIC 9(7)V99.
   05 QUANTITY        PIC 9(5).
   05 DISCOUNT-RATE   PIC 9(2)V99.
   05 TOTAL-PRICE     PIC 9(9)V99.
   05 FINAL-PRICE     PIC 9(9)V99.

PROCEDURE DIVISION.
    READ PRODUCT-FILE.
    COMPUTE TOTAL-PRICE = UNIT-PRICE * QUANTITY.
    IF QUANTITY > 100
       MOVE 15 TO DISCOUNT-RATE
    ELSE
       IF QUANTITY > 50
          MOVE 10 TO DISCOUNT-RATE
       ELSE
          MOVE 5 TO DISCOUNT-RATE
       END-IF
    END-IF.
    COMPUTE FINAL-PRICE = TOTAL-PRICE - (TOTAL-PRICE * DISCOUNT-RATE / 100).
    WRITE OUTPUT-RECORD.
    STOP RUN.
""",
}


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(source: str) -> dict:
    """Run the full conversion pipeline and return results dict."""
    result = {"error": None, "fields": [], "ast": {}, "rules": [], "pyspark": "", "docs": ""}
    try:
        parser = COBOLParser(source)
        program = parser.parse()

        # Fields
        if program.data_division:
            result["fields"] = [f.to_dict() for f in program.data_division.fields]

        # AST
        result["ast"] = program.to_dict()

        # Rules
        extractor = RuleExtractor(program)
        rules = extractor.extract()
        result["rules"] = [r.to_dict() for r in rules]
        result["docs"] = extractor.generate_documentation()

        # PySpark code
        gen = PySparkGenerator(program)
        result["pyspark"] = gen.generate()

    except Exception as exc:
        result["error"] = str(exc)

    return result


def run_copybook_pipeline(source: str) -> dict:
    result = {"error": None, "fields": [], "schema_code": ""}
    try:
        cp = CopybookParser(source)
        fields = cp.parse()
        result["fields"] = [f.to_dict() for f in fields]
        result["schema_code"] = cp.to_spark_schema_code()
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    st.sidebar.title("⚙️ COBOL → PySpark")
    st.sidebar.caption("A learning-focused modernisation tool")
    st.sidebar.markdown("---")

    mode = st.sidebar.radio(
        "Mode",
        ["COBOL Program Converter", "Copybook → Schema"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Pipeline")
    st.sidebar.markdown("""
```
COBOL Source
    ↓
  Lexer
    ↓
  Parser
    ↓
   AST
    ↓
Rule Extractor
    ↓
PySpark Generator
    ↓
Generated Code
```
""")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Learning Objectives")
    st.sidebar.markdown("""
1. COBOL batch processing
2. Copybook schema definitions
3. Business rule extraction
4. Spark DataFrame transformations
5. Compiler / AST concepts
6. Code generation patterns
7. Mainframe modernisation
""")
    return mode


# ---------------------------------------------------------------------------
# Main converter tab content
# ---------------------------------------------------------------------------

def render_converter():
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("COBOL Source")

        sample_key = st.selectbox(
            "Load a sample program",
            ["— paste your own —"] + list(SAMPLES.keys()),
        )
        if sample_key != "— paste your own —":
            default_code = SAMPLES[sample_key]
        else:
            default_code = ""

        cobol_source = st.text_area(
            "Paste or edit COBOL code",
            value=default_code,
            height=420,
            placeholder="Paste COBOL source here…",
        )

        convert_btn = st.button("Convert →", type="primary", use_container_width=True)

    with col_right:
        if convert_btn and cobol_source.strip():
            result = run_pipeline(cobol_source)

            if result["error"]:
                st.error(f"Parse error: {result['error']}")
                return

            tab1, tab2, tab3, tab4 = st.tabs(["📋 Fields", "🌲 AST", "📜 Rules", "⚡ PySpark"])

            with tab1:
                st.subheader("Parsed Fields (DATA DIVISION)")
                st.caption("These become Spark StructType columns.")
                if result["fields"]:
                    display = []
                    for f in result["fields"]:
                        if f["level"] == 1 or f["cobol_type"] == "group":
                            continue
                        display.append({
                            "Level": f["level"],
                            "Field Name": f["name"],
                            "PIC Clause": f["pic_clause"],
                            "Type": f["cobol_type"],
                            "Length": f["length"],
                            "Decimals": f["decimal_places"],
                            "Parent Record": f["parent"] or "",
                        })
                    if display:
                        st.dataframe(display, use_container_width=True)
                    else:
                        st.info("No elementary fields found.")
                else:
                    st.info("No DATA DIVISION parsed.")

            with tab2:
                st.subheader("Abstract Syntax Tree")
                st.caption("JSON representation of the parsed program structure.")
                st.json(result["ast"], expanded=2)

            with tab3:
                st.subheader("Extracted Business Rules")
                st.caption("Auto-documented rules extracted from the PROCEDURE DIVISION.")

                if result["rules"]:
                    for rule in result["rules"]:
                        rule_type = rule.get("rule_type", "Rule")
                        icon = {
                            "ConditionalRule": "🔀",
                            "AssignmentRule": "📌",
                            "ComputationRule": "🧮",
                            "IORule": "📂",
                            "LoopRule": "🔁",
                        }.get(rule_type, "📎")

                        with st.expander(f"{icon} Rule #{rule['rule_id']}  [{rule_type}] — {rule['description'][:60]}"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Description:** {rule['description']}")
                                st.markdown(f"**COBOL source:** `{rule['source_statement']}`")
                            with col_b:
                                if rule_type == "ConditionalRule":
                                    st.markdown(f"**Condition:** `{rule.get('condition','')}`")
                                    if rule.get("then_actions"):
                                        st.markdown(f"**THEN:** {'; '.join(rule['then_actions'])}")
                                    if rule.get("else_actions"):
                                        st.markdown(f"**ELSE:** {'; '.join(rule['else_actions'])}")
                                elif rule_type == "ComputationRule":
                                    st.markdown(f"**Target:** `{rule.get('target','')}`")
                                    st.markdown(f"**Expression:** `{rule.get('expression','')}`")
                                elif rule_type == "AssignmentRule":
                                    st.markdown(f"**Target:** `{rule.get('target','')}`")
                                    st.markdown(f"**Value:** `{rule.get('value','')}`")
                                elif rule_type == "IORule":
                                    st.markdown(f"**Operation:** `{rule.get('operation','')}`")
                                    st.markdown(f"**File/Record:** `{rule.get('file_or_record','')}`")

                    st.markdown("---")
                    st.subheader("Rule Documentation")
                    st.code(result["docs"], language="text")
                else:
                    st.info("No business rules extracted.")

            with tab4:
                st.subheader("Generated PySpark Code")
                st.caption("Ready-to-use PySpark DataFrame job equivalent.")
                st.code(result["pyspark"], language="python")

                st.download_button(
                    "⬇️ Download .py",
                    data=result["pyspark"],
                    file_name="converted_pyspark.py",
                    mime="text/x-python",
                    use_container_width=True,
                )

        elif convert_btn:
            st.warning("Please paste some COBOL code first.")
        else:
            st.info("← Select a sample or paste COBOL code, then click **Convert →**")
            render_pipeline_diagram()


def render_pipeline_diagram():
    st.markdown("### Conversion Pipeline")
    st.markdown("""
| Stage | Input | Output |
|---|---|---|
| **Lexer** | COBOL source text | Token stream |
| **Parser** | Token stream | Abstract Syntax Tree |
| **Rule Extractor** | AST | Business rule objects |
| **Code Generator** | AST + Rules | PySpark Python code |
""")

    st.markdown("### COBOL → PySpark Mapping")
    st.markdown("""
| COBOL Statement | PySpark Equivalent |
|---|---|
| `MOVE value TO field` | `df.withColumn("field", lit(value))` |
| `IF cond MOVE val TO field END-IF` | `df.withColumn("field", when(cond, val))` |
| `COMPUTE target = expr` | `df.withColumn("target", expr)` |
| `ADD a TO b` | `df.withColumn("b", col("b") + col("a"))` |
| `SUBTRACT a FROM b` | `df.withColumn("b", col("b") - col("a"))` |
| `MULTIPLY a BY b` | `df.withColumn("b", col("a") * col("b"))` |
| `DIVIDE a INTO b` | `df.withColumn("b", col("b") / col("a"))` |
| `READ file-name` | `spark.read.csv("file-name.csv", schema=schema)` |
| `WRITE record` | `df.write.csv("output/record")` |
| `STOP RUN` | `spark.stop()` |
""")


# ---------------------------------------------------------------------------
# Copybook tab
# ---------------------------------------------------------------------------

def render_copybook():
    st.subheader("Copybook → Spark Schema")
    st.markdown("""
A **copybook** is a reusable COBOL data definition — the mainframe equivalent
of a shared schema registry.  Paste a copybook below to generate the
equivalent PySpark `StructType`.
""")

    sample_copybook = """\
01 CUSTOMER.
   05 CUSTOMER-ID     PIC X(10).
   05 CUSTOMER-NAME   PIC X(30).
   05 BALANCE         PIC 9(7)V99.
   05 CREDIT-SCORE    PIC 9(3).
   05 CUSTOMER-TYPE   PIC X(10).
"""
    copybook_source = st.text_area(
        "Paste copybook",
        value=sample_copybook,
        height=200,
    )

    if st.button("Generate Schema →", type="primary"):
        result = run_copybook_pipeline(copybook_source)
        if result["error"]:
            st.error(result["error"])
            return

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Parsed Fields")
            display = [
                {
                    "Level": f["level"],
                    "Name": f["name"],
                    "PIC": f["pic_clause"],
                    "Type": f["cobol_type"],
                    "Length": f["length"],
                    "Decimals": f["decimal_places"],
                }
                for f in result["fields"]
                if f["level"] != 1 and f["cobol_type"] != "group"
            ]
            st.dataframe(display, use_container_width=True)

        with col2:
            st.subheader("PySpark StructType")
            st.code(result["schema_code"], language="python")


# ---------------------------------------------------------------------------
# Learning guide tab
# ---------------------------------------------------------------------------

def render_learning_guide():
    st.subheader("COBOL → PySpark Learning Guide")

    st.markdown("""
### 1. How COBOL Batch Processing Works

COBOL batch programs process records **one at a time** from sequential files:

```cobol
PERFORM UNTIL END-OF-FILE
    READ INPUT-FILE
    PROCESS-RECORD
    WRITE OUTPUT-FILE
END-PERFORM
```

PySpark processes **all records simultaneously** using distributed DataFrames:

```python
df = spark.read.csv("input.csv")
df = df.withColumn(...)   # applied to every row at once
df.write.csv("output")
```

---

### 2. How Copybooks Define Schemas

A COBOL copybook is like a struct definition — it describes the layout of a
data record that multiple programs share:

```cobol
01 CUSTOMER-REC.
   05 CUSTOMER-ID     PIC X(10).   ← 10-char string
   05 BALANCE         PIC 9(7)V99. ← 7-digit number, 2 decimal places
```

PySpark StructType is the equivalent:

```python
schema = StructType([
    StructField("CUSTOMER_ID", StringType()),
    StructField("BALANCE",     DecimalType(9, 2)),
])
```

---

### 3. PIC Clause Quick Reference

| PIC Clause | COBOL Type | Spark Type |
|---|---|---|
| `PIC X(n)` | Alphanumeric string | `StringType()` |
| `PIC 9(n)` | Integer | `LongType()` |
| `PIC 9(n)V99` | Decimal (2 d.p.) | `DecimalType(n+2, 2)` |
| `PIC S9(n)V99` | Signed decimal | `DecimalType(n+2, 2)` |

---

### 4. How the AST Works

The parser converts source text into a tree:

```
ProgramNode
├── DataDivisionNode
│   ├── FieldDefinitionNode(CUSTOMER-ID, PIC X(10))
│   └── FieldDefinitionNode(BALANCE, PIC 9(7)V99)
└── ProcedureDivisionNode
    ├── ReadStatement(CUSTOMER-FILE)
    ├── IfStatement(BALANCE > 1000)
    │   └── MoveStatement('PREMIUM' → CUSTOMER-TYPE)
    └── WriteStatement(OUTPUT-RECORD)
```

Each node type maps directly to a PySpark transformation.

---

### 5. Code Generation Patterns

| Pattern | COBOL | PySpark |
|---|---|---|
| Conditional assignment | `IF x > 0 MOVE 'Y' TO FLAG` | `when(col("x") > 0, lit("Y"))` |
| Arithmetic | `COMPUTE TAX = INCOME * 0.2` | `col("INCOME") * lit(0.2)` |
| Chained conditions | `IF A AND B MOVE …` | `when((col("A")) & (col("B")), …)` |
| Default value | `ELSE MOVE 'N' TO FLAG` | `.otherwise(lit("N"))` |
""")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    st.title("COBOL Batch → PySpark Converter")
    st.caption("A learning-focused mainframe modernisation tool")

    mode = render_sidebar()

    if mode == "COBOL Program Converter":
        page_tab1, page_tab2 = st.tabs(["🔄 Converter", "📚 Learning Guide"])
        with page_tab1:
            render_converter()
        with page_tab2:
            render_learning_guide()
    else:
        render_copybook()


if __name__ == "__main__":
    main()
