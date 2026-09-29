      *----------------------------------------------------------------
      * Example 06: Employee Payroll Processing
      *
      * Business Rule:
      *   Calculate gross pay including overtime (1.5x rate).
      *   Deduct income tax (20%) and pension (5%).
      *   Net pay = gross pay - tax - pension contribution.
      *   Flag high earners (gross > 10,000) for payroll audit.
      *
      * Key COBOL concepts demonstrated:
      *   - Sequential COMPUTE statements
      *   - ADD and SUBTRACT statements
      *   - PERFORM for sub-paragraphs
      *   - Conditional flagging
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 EMPLOYEE-REC.
          05 EMP-ID          PIC X(10).
          05 EMP-NAME        PIC X(30).
          05 HOURLY-RATE     PIC 9(5)V99.
          05 HOURS-WORKED    PIC 9(3)V99.
          05 OVERTIME-HOURS  PIC 9(3)V99.
          05 GROSS-PAY       PIC 9(7)V99.
          05 TAX-AMOUNT      PIC 9(7)V99.
          05 PENSION-AMOUNT  PIC 9(7)V99.
          05 NET-PAY         PIC 9(7)V99.
          05 AUDIT-FLAG      PIC X(1).

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ EMPLOYEE-FILE.
           COMPUTE GROSS-PAY = HOURLY-RATE * HOURS-WORKED.
           IF OVERTIME-HOURS > 0
              COMPUTE GROSS-PAY = GROSS-PAY + (OVERTIME-HOURS * HOURLY-RATE * 1.5)
           END-IF.
           COMPUTE TAX-AMOUNT = GROSS-PAY * 0.20.
           COMPUTE PENSION-AMOUNT = GROSS-PAY * 0.05.
           COMPUTE NET-PAY = GROSS-PAY - TAX-AMOUNT - PENSION-AMOUNT.
           IF GROSS-PAY > 10000
              MOVE 'Y' TO AUDIT-FLAG
           ELSE
              MOVE 'N' TO AUDIT-FLAG
           END-IF.
           WRITE OUTPUT-RECORD.
           STOP RUN.
