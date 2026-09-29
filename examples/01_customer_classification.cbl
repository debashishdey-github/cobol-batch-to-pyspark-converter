      *----------------------------------------------------------------
      * Example 01: Customer Classification
      *
      * Business Rule:
      *   Classify customers as PREMIUM, SILVER, or STANDARD
      *   based on their account balance.
      *
      * Key COBOL concepts demonstrated:
      *   - DATA DIVISION field definitions
      *   - Nested IF/ELSE logic
      *   - MOVE statement for string assignment
      *   - READ/WRITE for file I/O
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTCLASSIFY.
       AUTHOR.     MODERNISATION-TEAM.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 CUSTOMER-REC.
          05 CUSTOMER-ID     PIC X(10).
          05 CUSTOMER-NAME   PIC X(30).
          05 BALANCE         PIC 9(7)V99.
          05 CUSTOMER-TYPE   PIC X(10).
          05 REWARD-POINTS   PIC 9(5).

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ CUSTOMER-FILE.
           IF BALANCE > 10000
              MOVE 'PREMIUM' TO CUSTOMER-TYPE
           ELSE
              IF BALANCE > 1000
                 MOVE 'SILVER' TO CUSTOMER-TYPE
              ELSE
                 MOVE 'STANDARD' TO CUSTOMER-TYPE
              END-IF
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
