      *----------------------------------------------------------------
      * Example 04: Insurance Premium Calculation
      *
      * Business Rule:
      *   Calculate insurance premium based on age and risk score.
      *   High-risk (score > 70) customers pay a 50% loading.
      *   Senior customers (age > 65) get a loyalty discount of 10%.
      *
      * Key COBOL concepts demonstrated:
      *   - Multiple condition checks
      *   - Sequential COMPUTE statements
      *   - MULTIPLY statement
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INSPREMIUM.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 POLICY-REC.
          05 POLICY-ID       PIC X(10).
          05 CUSTOMER-AGE    PIC 9(3).
          05 RISK-SCORE      PIC 9(3).
          05 BASE-PREMIUM    PIC 9(7)V99.
          05 LOADING-FACTOR  PIC 9(1)V2.
          05 DISCOUNT-RATE   PIC 9(2)V99.
          05 FINAL-PREMIUM   PIC 9(7)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ POLICY-FILE.
           MOVE 0 TO DISCOUNT-RATE.
           MOVE 1 TO LOADING-FACTOR.
           IF RISK-SCORE > 70
              MOVE 1.5 TO LOADING-FACTOR
           END-IF.
           IF CUSTOMER-AGE > 65
              MOVE 10 TO DISCOUNT-RATE
           END-IF.
           COMPUTE FINAL-PREMIUM = BASE-PREMIUM * LOADING-FACTOR.
           COMPUTE FINAL-PREMIUM = FINAL-PREMIUM - (FINAL-PREMIUM * DISCOUNT-RATE / 100).
           WRITE OUTPUT-RECORD.
           STOP RUN.
