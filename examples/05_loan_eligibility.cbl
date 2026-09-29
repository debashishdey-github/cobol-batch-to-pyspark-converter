      *----------------------------------------------------------------
      * Example 05: Loan Eligibility Check
      *
      * Business Rule:
      *   Determine loan eligibility and credit limit.
      *   Credit score >= 750 → EXCELLENT → limit = income * 8
      *   Credit score >= 650 → GOOD      → limit = income * 5
      *   Credit score <  650 → POOR      → REJECTED, limit = 0
      *   Debt-to-income ratio > 0.4 → reduce limit by 25%
      *
      * Key COBOL concepts demonstrated:
      *   - Nested IF/ELSE chains
      *   - COMPUTE with conditional logic
      *   - Multiple output fields set in one pass
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. LOANCHECK.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 APPLICANT-REC.
          05 APPLICANT-ID    PIC X(10).
          05 CREDIT-SCORE    PIC 9(3).
          05 ANNUAL-INCOME   PIC 9(9)V99.
          05 EXISTING-DEBT   PIC 9(9)V99.
          05 DEBT-RATIO      PIC 9(1)V4.
          05 LOAN-STATUS     PIC X(10).
          05 CREDIT-GRADE    PIC X(10).
          05 LOAN-LIMIT      PIC 9(9)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ APPLICANT-FILE.
           COMPUTE DEBT-RATIO = EXISTING-DEBT / ANNUAL-INCOME.
           IF CREDIT-SCORE > 750
              MOVE 'EXCELLENT' TO CREDIT-GRADE
              MOVE 'APPROVED' TO LOAN-STATUS
              COMPUTE LOAN-LIMIT = ANNUAL-INCOME * 8
           ELSE
              IF CREDIT-SCORE > 650
                 MOVE 'GOOD' TO CREDIT-GRADE
                 MOVE 'APPROVED' TO LOAN-STATUS
                 COMPUTE LOAN-LIMIT = ANNUAL-INCOME * 5
              ELSE
                 MOVE 'POOR' TO CREDIT-GRADE
                 MOVE 'REJECTED' TO LOAN-STATUS
                 MOVE 0 TO LOAN-LIMIT
              END-IF
           END-IF.
           IF LOAN-STATUS = 'APPROVED'
              IF DEBT-RATIO > 0.4
                 COMPUTE LOAN-LIMIT = LOAN-LIMIT * 0.75
              END-IF
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
