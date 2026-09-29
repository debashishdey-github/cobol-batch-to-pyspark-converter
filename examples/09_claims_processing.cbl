      *----------------------------------------------------------------
      * Example 09: Insurance Claims Processing
      *
      * Business Rule:
      *   Process insurance claims and determine approval/rejection.
      *   Claim > policy limit → REJECTED (OVER-LIMIT)
      *   Claim submitted within 30 days → APPROVED
      *   Claim submitted 31-90 days → PENDING REVIEW
      *   Claim submitted > 90 days → REJECTED (EXPIRED)
      *   Approved claims: payout = min(claim-amount, policy-limit)
      *
      * Key COBOL concepts demonstrated:
      *   - Business rule chains
      *   - Multiple outcome fields
      *   - COMPUTE for payout calculation
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CLAIMSPROC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 CLAIM-REC.
          05 CLAIM-ID        PIC X(10).
          05 POLICY-ID       PIC X(10).
          05 CLAIM-AMOUNT    PIC 9(9)V99.
          05 POLICY-LIMIT    PIC 9(9)V99.
          05 DAYS-SUBMITTED  PIC 9(3).
          05 CLAIM-STATUS    PIC X(20).
          05 REJECTION-CODE  PIC X(15).
          05 PAYOUT-AMOUNT   PIC 9(9)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ CLAIMS-FILE.
           MOVE 0 TO PAYOUT-AMOUNT.
           MOVE 'NONE' TO REJECTION-CODE.
           IF CLAIM-AMOUNT > POLICY-LIMIT
              MOVE 'REJECTED' TO CLAIM-STATUS
              MOVE 'OVER-LIMIT' TO REJECTION-CODE
           ELSE
              IF DAYS-SUBMITTED < 31
                 MOVE 'APPROVED' TO CLAIM-STATUS
                 COMPUTE PAYOUT-AMOUNT = CLAIM-AMOUNT
              ELSE
                 IF DAYS-SUBMITTED < 91
                    MOVE 'PENDING' TO CLAIM-STATUS
                 ELSE
                    MOVE 'REJECTED' TO CLAIM-STATUS
                    MOVE 'EXPIRED' TO REJECTION-CODE
                 END-IF
              END-IF
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
