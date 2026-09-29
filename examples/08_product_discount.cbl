      *----------------------------------------------------------------
      * Example 08: Product Discount Logic
      *
      * Business Rule:
      *   Tiered discount based on quantity ordered:
      *     >  200 units → 20% discount
      *     >  100 units → 15% discount
      *     >   50 units → 10% discount
      *     Otherwise   →  5% discount
      *   VIP customers receive an additional 5% off.
      *
      * Key COBOL concepts demonstrated:
      *   - Multi-tier nested IF/ELSE
      *   - Cumulative discount computation
      *   - ADD to accumulate values
      *----------------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. DISCOUNT.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 ORDER-REC.
          05 ORDER-ID        PIC X(10).
          05 CUSTOMER-TYPE   PIC X(10).
          05 UNIT-PRICE      PIC 9(7)V99.
          05 QUANTITY        PIC 9(5).
          05 DISCOUNT-RATE   PIC 9(2)V99.
          05 VIP-DISCOUNT    PIC 9(2)V99.
          05 TOTAL-DISCOUNT  PIC 9(2)V99.
          05 LIST-PRICE      PIC 9(9)V99.
          05 FINAL-PRICE     PIC 9(9)V99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           READ ORDER-FILE.
           COMPUTE LIST-PRICE = UNIT-PRICE * QUANTITY.
           IF QUANTITY > 200
              MOVE 20 TO DISCOUNT-RATE
           ELSE
              IF QUANTITY > 100
                 MOVE 15 TO DISCOUNT-RATE
              ELSE
                 IF QUANTITY > 50
                    MOVE 10 TO DISCOUNT-RATE
                 ELSE
                    MOVE 5 TO DISCOUNT-RATE
                 END-IF
              END-IF
           END-IF.
           MOVE 0 TO VIP-DISCOUNT.
           IF CUSTOMER-TYPE = 'VIP'
              MOVE 5 TO VIP-DISCOUNT
           END-IF.
           COMPUTE TOTAL-DISCOUNT = DISCOUNT-RATE + VIP-DISCOUNT.
           COMPUTE FINAL-PRICE = LIST-PRICE - (LIST-PRICE * TOTAL-DISCOUNT / 100).
           WRITE OUTPUT-RECORD.
           STOP RUN.
