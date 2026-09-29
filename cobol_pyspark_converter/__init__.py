# COBOL Batch → PySpark Converter
# A learning-focused tool that transforms COBOL batch programs into PySpark DataFrame jobs.
#
# Pipeline:
#   COBOL source
#     → Lexer (tokenisation)
#     → Parser (AST)
#     → Rule Extractor (business logic)
#     → Code Generator (PySpark)
