LOAD DATA
APPEND
INTO TABLE stg_transaction_line
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' TRAILING NULLCOLS
(
  source_row_number    INTEGER EXTERNAL,
  invoice_id           CHAR,
  item_key             CHAR,
  item_name            CHAR,
  quantity             DECIMAL EXTERNAL,
  transaction_date     TIMESTAMP "YYYY-MM-DD HH24:MI:SS",
  unit_price           DECIMAL EXTERNAL,
  customer_id          CHAR,
  country              CHAR,
  line_revenue         DECIMAL EXTERNAL,
  is_cancellation      INTEGER EXTERNAL,
  is_non_merchandise   INTEGER EXTERNAL,
  is_exact_duplicate   INTEGER EXTERNAL,
  is_test_transaction  INTEGER EXTERNAL,
  exclusion_reason     CHAR,
  is_retained          INTEGER EXTERNAL
)
