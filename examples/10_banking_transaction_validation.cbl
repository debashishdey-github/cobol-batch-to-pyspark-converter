      *----------------------------------------------------------------
      * Example 10: Banking Transaction Validation
      *
      * Business Rule:
      *   Validate banking transactions and flag suspicious activity.
      *   Amount > 10,000  → LARGE-TRANSACTION flag (AML reporting)
      *   Amount > balance → INSUFFICIENT-FUNDS, DECLINED
      *   Velocity > 5 transactions today → SUSPICIOUS, flag for review
      *   Valid transactions: deduct from balance, log APPROVED
      *
      * Key COBOL concepts demonstrated:
      *   - Complex multi-condition validation
      *   - SUBTRACT for balance update
      *   - Multiple output status fields
      *   - Real-world compliance rules (AML = Anti-Money Laundering)
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TXNVALIDATE.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 TRANSACTION-REC.
          05 TXN-ID          PIC X(15).
          05 ACCOUNT-ID      PIC X(10).
          05 TXN-AMOUNT      PIC 9(9)V99.
          05 CURRENT-BALANCE PIC 9(9)V99.
          05 TXN-COUNT-TODAY PIC 9(3).
          05 TXN-STATUS      PIC X(20).
          05 DECLINE-REASON  PIC X(25).
          05 AML-FLAG        PIC X(1).
          05 VELOCITY-FLAG   PIC X(1).
          05 NEW-BALANCE     PIC 9(9)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ TRANSACTION-FILE.
           MOVE 'N' TO AML-FLAG.
           MOVE 'N' TO VELOCITY-FLAG.
           MOVE 'NONE' TO DECLINE-REASON.
           IF TXN-AMOUNT > 10000
              MOVE 'Y' TO AML-FLAG
           END-IF.
           IF TXN-COUNT-TODAY > 5
              MOVE 'Y' TO VELOCITY-FLAG
           END-IF.
           IF TXN-AMOUNT > CURRENT-BALANCE
              MOVE 'DECLINED' TO TXN-STATUS
              MOVE 'INSUFFICIENT-FUNDS' TO DECLINE-REASON
              COMPUTE NEW-BALANCE = CURRENT-BALANCE
           ELSE
              IF VELOCITY-FLAG = 'Y'
                 MOVE 'REVIEW' TO TXN-STATUS
                 COMPUTE NEW-BALANCE = CURRENT-BALANCE - TXN-AMOUNT
              ELSE
                 MOVE 'APPROVED' TO TXN-STATUS
                 COMPUTE NEW-BALANCE = CURRENT-BALANCE - TXN-AMOUNT
              END-IF
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
