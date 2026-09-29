      *----------------------------------------------------------------
      * Example 03: Interest Calculation
      *
      * Business Rule:
      *   Calculate monthly interest earned on savings accounts.
      *   Apply a bonus rate for balances over $50,000.
      *   New balance = old balance + interest earned.
      *
      * Key COBOL concepts demonstrated:
      *   - COMPUTE with compound expressions
      *   - Conditional rate selection
      *   - Decimal arithmetic (V99 fields)
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTERESTCALC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ACCOUNT-REC.
          05 ACCOUNT-ID      PIC X(10).
          05 BALANCE         PIC 9(9)V99.
          05 INTEREST-RATE   PIC 9(2)V4.
          05 INTEREST-AMT    PIC 9(9)V99.
          05 NEW-BALANCE     PIC 9(9)V99.
          05 RATE-TIER       PIC X(10).

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ ACCOUNT-FILE.
           IF BALANCE > 50000
              MOVE 'HIGH' TO RATE-TIER
              MOVE 4 TO INTEREST-RATE
           ELSE
              MOVE 'STANDARD' TO RATE-TIER
              MOVE 2 TO INTEREST-RATE
           END-IF.
           COMPUTE INTEREST-AMT = BALANCE * INTEREST-RATE / 100.
           COMPUTE NEW-BALANCE = BALANCE + INTEREST-AMT.
           WRITE OUTPUT-RECORD.
           STOP RUN.
