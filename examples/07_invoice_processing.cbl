      *----------------------------------------------------------------
      * Example 07: Invoice Processing
      *
      * Business Rule:
      *   Calculate invoice totals with tax and discount.
      *   Apply 20% VAT to all items.
      *   Bulk discount: orders > 1000 units → 5% off subtotal.
      *   Late payment flag: days overdue > 30 → add 2% penalty.
      *
      * Key COBOL concepts demonstrated:
      *   - Chained COMPUTE expressions
      *   - Multiple conditional checks
      *   - MULTIPLY for quantity × price
      *   - Business rule documentation pattern
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. INVOICEPROC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 INVOICE-REC.
          05 INVOICE-ID      PIC X(10).
          05 CUSTOMER-ID     PIC X(10).
          05 UNIT-PRICE      PIC 9(7)V99.
          05 QUANTITY        PIC 9(5).
          05 DAYS-OVERDUE    PIC 9(3).
          05 SUBTOTAL        PIC 9(9)V99.
          05 DISCOUNT-AMT    PIC 9(9)V99.
          05 VAT-AMOUNT      PIC 9(9)V99.
          05 PENALTY-AMT     PIC 9(9)V99.
          05 TOTAL-AMOUNT    PIC 9(9)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ INVOICE-FILE.
           COMPUTE SUBTOTAL = UNIT-PRICE * QUANTITY.
           MOVE 0 TO DISCOUNT-AMT.
           IF QUANTITY > 1000
              COMPUTE DISCOUNT-AMT = SUBTOTAL * 0.05
           END-IF.
           COMPUTE SUBTOTAL = SUBTOTAL - DISCOUNT-AMT.
           COMPUTE VAT-AMOUNT = SUBTOTAL * 0.20.
           MOVE 0 TO PENALTY-AMT.
           IF DAYS-OVERDUE > 30
              COMPUTE PENALTY-AMT = SUBTOTAL * 0.02
           END-IF.
           COMPUTE TOTAL-AMOUNT = SUBTOTAL + VAT-AMOUNT + PENALTY-AMT.
           WRITE OUTPUT-RECORD.
           STOP RUN.
