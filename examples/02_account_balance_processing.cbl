      *----------------------------------------------------------------
      * Example 02: Account Balance Processing
      *
      * Business Rule:
      *   Apply monthly service charges to accounts.
      *   Waive the charge for PREMIUM accounts.
      *   Flag accounts with negative balance as OVERDRAWN.
      *
      * Key COBOL concepts demonstrated:
      *   - COMPUTE for arithmetic
      *   - SUBTRACT statement
      *   - Multiple IF conditions
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCTBAL.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ACCOUNT-REC.
          05 ACCOUNT-ID      PIC X(10).
          05 ACCOUNT-TYPE    PIC X(10).
          05 BALANCE         PIC S9(9)V99.
          05 SERVICE-CHARGE  PIC 9(5)V99.
          05 NEW-BALANCE     PIC S9(9)V99.
          05 ACCOUNT-STATUS  PIC X(10).

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ ACCOUNT-FILE.
           IF ACCOUNT-TYPE = 'PREMIUM'
              MOVE 0 TO SERVICE-CHARGE
           ELSE
              MOVE 25 TO SERVICE-CHARGE
           END-IF.
           COMPUTE NEW-BALANCE = BALANCE - SERVICE-CHARGE.
           IF NEW-BALANCE < 0
              MOVE 'OVERDRAWN' TO ACCOUNT-STATUS
           ELSE
              MOVE 'ACTIVE' TO ACCOUNT-STATUS
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
