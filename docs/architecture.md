# COBOL Batch → PySpark Converter — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│   ┌─────────────┐              ┌────────────────────┐   │
│   │ COBOL Input │              │   Results Panel    │   │
│   │  (text area)│──────────────│ Fields / AST /     │   │
│   │             │              │ Rules / PySpark    │   │
│   └─────────────┘              └────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
                        │ source string
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   Lexer  (parser/lexer.py)              │
│  Input: raw COBOL text                                  │
│  Output: List[Token]                                    │
│  Converts: keywords, identifiers, literals, operators   │
└───────────────────────┬─────────────────────────────────┘
                        │ token stream
                        ▼
┌─────────────────────────────────────────────────────────┐
│                 Parser  (parser/cobol_parser.py)        │
│  Input: List[Token]                                     │
│  Output: ProgramNode (AST root)                         │
│  Builds: hierarchical tree of ASTNode objects           │
└──────────────┬────────────────────────┬─────────────────┘
               │ ProgramNode            │ ProgramNode
               ▼                        ▼
┌──────────────────────┐    ┌─────────────────────────────┐
│   Rule Extractor     │    │     Code Generator          │
│  (rule_extractor/)   │    │   (code_generator/)         │
│                      │    │                             │
│  Input:  ProgramNode │    │  Input:  ProgramNode        │
│  Output: List[Rule]  │    │  Output: Python string      │
│                      │    │                             │
│  Produces:           │    │  Produces:                  │
│  - ConditionalRule   │    │  - PySpark DataFrame code   │
│  - AssignmentRule    │    │  - Spark StructType schema  │
│  - ComputationRule   │    │  - withColumn chains        │
│  - IORule            │    │  - when() expressions       │
│  - LoopRule          │    │  - spark.read/write calls   │
└──────────────────────┘    └─────────────────────────────┘
```

## Component Responsibilities

### 1. Lexer (`parser/lexer.py`)

The lexer is responsible for **tokenisation** — the process of breaking raw source
text into a flat stream of labelled tokens.

It handles:
- COBOL keywords (case-insensitive): MOVE, IF, COMPUTE, READ, WRITE, etc.
- Identifiers with hyphens: CUSTOMER-ID, ACCOUNT-BALANCE
- String literals: 'PREMIUM', 'Y'
- Numeric literals: 1000, 0.05
- PIC clause components: X, 9, V, parentheses
- Comment lines (skipped)
- Operators: =, >, <, +, -, *, /

**Key design decision:** The lexer normalises all keywords to lower-case for
lookup, making tokenisation case-insensitive — matching how real COBOL compilers work.

### 2. Parser (`parser/cobol_parser.py`)

The parser uses **recursive descent** — one method per COBOL construct — to
build the AST from the token stream.

Grammar handled:
```
program       → identification-div data-div procedure-div
data-div      → 'DATA' 'DIVISION' '.' {field-definition}
field-def     → level-number identifier 'PIC' pic-clause '.'
procedure-div → 'PROCEDURE' 'DIVISION' '.' {statement}
statement     → move | if | compute | add | subtract
              | multiply | divide | read | write | perform | stop-run
if            → 'IF' condition {statement} ['ELSE' {statement}] 'END-IF'
```

### 3. AST Nodes (`ast_nodes/nodes.py`)

Every COBOL construct maps to a Python dataclass:

| COBOL Construct | AST Node |
|---|---|
| Whole program | `ProgramNode` |
| DATA DIVISION | `DataDivisionNode` |
| Field definition | `FieldDefinitionNode` |
| PROCEDURE DIVISION | `ProcedureDivisionNode` |
| MOVE … TO … | `MoveStatement` |
| IF … ELSE … END-IF | `IfStatement`, `ElseClause` |
| COMPUTE … = … | `ComputeStatement` |
| ADD … TO … | `AddStatement` |
| SUBTRACT … FROM … | `SubtractStatement` |
| MULTIPLY … BY … | `MultiplyStatement` |
| DIVIDE … INTO … | `DivideStatement` |
| READ file | `ReadStatement` |
| WRITE record | `WriteStatement` |
| PERFORM paragraph | `PerformStatement` |
| STOP RUN | `StopRunStatement` |

### 4. Copybook Parser (`copybook/copybook_parser.py`)

Parses standalone copybook files (record layout definitions) and produces:
- `FieldDefinitionNode` list
- Spark `StructType` Python code

PIC type mapping:
```
PIC X(n)      → StringType()
PIC 9(n)      → LongType()
PIC 9(n)V99   → DecimalType(n+2, 2)
PIC S9(n)     → LongType()
PIC S9(n)V99  → DecimalType(n+2, 2)
```

### 5. Rule Extractor (`rule_extractor/extractor.py`)

Walks the AST and extracts structured `BusinessRule` objects:

| Rule Type | Source Statement |
|---|---|
| `ConditionalRule` | IF … ELSE … END-IF |
| `AssignmentRule` | MOVE … TO … |
| `ComputationRule` | COMPUTE / ADD / SUBTRACT / MULTIPLY / DIVIDE |
| `IORule` | READ / WRITE |
| `LoopRule` | PERFORM … UNTIL … |

Also generates a human-readable documentation string for business analysts.

### 6. Code Generator (`code_generator/pyspark_generator.py`)

Visits each AST node and emits PySpark code:

| AST Node | PySpark Output |
|---|---|
| `DataDivisionNode` | `StructType([StructField(…), …])` |
| `ReadStatement` | `spark.read.csv(…, schema=schema)` |
| `WriteStatement` | `df.write.mode("overwrite").csv(…)` |
| `IfStatement` + `MoveStatement` | `df.withColumn(…, when(cond, val).otherwise(…))` |
| `ComputeStatement` | `df.withColumn(…, expr)` |
| `AddStatement` | `df.withColumn(…, col(a) + col(b))` |
| `SubtractStatement` | `df.withColumn(…, col(a) - col(b))` |
| `MultiplyStatement` | `df.withColumn(…, col(a) * col(b))` |
| `DivideStatement` | `df.withColumn(…, col(a) / col(b))` |

## Key Design Decisions

### Why recursive descent?
Recursive descent is the most readable parser style for a learning project.
Each method corresponds to one grammar rule, making the connection between
grammar and code explicit.

### Why dataclasses for AST nodes?
Python dataclasses give us `__init__`, `__repr__`, and type hints for free,
making nodes easy to inspect in tests and the Streamlit UI.

### Why separate Rule Extractor?
Separating rule extraction from code generation reflects real modernisation
practice: business analysts need the rules in a format they can validate,
independent of the generated code.

### Why DecimalType for monetary fields?
Floating-point arithmetic (float, double) cannot represent values like 0.1
exactly. Financial systems must use exact decimal arithmetic to avoid
cumulative rounding errors in balance calculations.

## Data Flow Example

```
COBOL input:
    IF BALANCE > 1000
       MOVE 'PREMIUM' TO CUSTOMER-TYPE
    END-IF

↓ Lexer
    [IF] [IDENTIFIER:BALANCE] [GREATER_THAN] [INTEGER:1000]
    [MOVE] [STRING:'PREMIUM'] [TO] [IDENTIFIER:CUSTOMER-TYPE]
    [END_IF]

↓ Parser
    IfStatement(
        condition = "BALANCE > 1000",
        then_statements = [
            MoveStatement(source="'PREMIUM'", target="CUSTOMER_TYPE")
        ]
    )

↓ Rule Extractor
    ConditionalRule(
        condition  = "BALANCE > 1000",
        then_actions = ["set CUSTOMER-TYPE = PREMIUM"]
    )

↓ Code Generator
    df = df.withColumn(
        "CUSTOMER_TYPE",
        when(col("BALANCE") > 1000, lit("PREMIUM"))
    )
```
