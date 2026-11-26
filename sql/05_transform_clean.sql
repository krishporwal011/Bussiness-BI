-- Build dimensions and facts from normalized staging.
-- The valid_lines CTE repeats the Python business rules and uses ROW_NUMBER
-- to make exact source duplicates harmless before basket-item aggregation.

INSERT INTO dim_customer (customer_key)
SELECT DISTINCT TRIM(customer_id)
FROM stg_transaction_line
WHERE customer_id IS NOT NULL
  AND is_retained = 1;

INSERT INTO dim_product (item_key, item_name)
SELECT item_key, MIN(item_name) AS item_name
FROM stg_transaction_line
WHERE is_retained = 1
  AND item_key IS NOT NULL
  AND item_name IS NOT NULL
GROUP BY item_key;

INSERT INTO dim_date (date_key, calendar_date, calendar_year, calendar_month, month_name, week_of_year, day_of_month)
SELECT TO_NUMBER(TO_CHAR(calendar_date, 'YYYYMMDD')),
       calendar_date,
       EXTRACT(YEAR FROM calendar_date),
       EXTRACT(MONTH FROM calendar_date),
       TO_CHAR(calendar_date, 'MONTH'),
       TO_NUMBER(TO_CHAR(calendar_date, 'IW')),
       EXTRACT(DAY FROM calendar_date)
FROM (
    SELECT min_date + LEVEL - 1 AS calendar_date
    FROM (
        SELECT TRUNC(MIN(transaction_date)) AS min_date,
               TRUNC(MAX(transaction_date)) AS max_date
        FROM stg_transaction_line
        WHERE is_retained = 1
    )
    CONNECT BY LEVEL <= (max_date - min_date + 1)
);

INSERT INTO fact_transaction (basket_id, transaction_date, customer_key, country)
WITH valid_lines AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY invoice_id, item_key, item_name, quantity,
                            transaction_date, unit_price, customer_id, country
               ORDER BY stg_row_id
           ) AS duplicate_sequence
    FROM stg_transaction_line s
    WHERE s.is_retained = 1
      AND s.invoice_id IS NOT NULL
      AND s.item_key IS NOT NULL
      AND s.item_name IS NOT NULL
      AND s.transaction_date IS NOT NULL
      AND s.quantity > 0
      AND s.unit_price > 0
)
SELECT invoice_id,
       MIN(transaction_date),
       MIN(customer_id),
       MIN(country)
FROM valid_lines
WHERE duplicate_sequence = 1
GROUP BY invoice_id;

INSERT INTO fact_basket_item (basket_id, item_key, quantity, revenue, line_count)
WITH valid_lines AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY invoice_id, item_key, item_name, quantity,
                            transaction_date, unit_price, customer_id, country
               ORDER BY stg_row_id
           ) AS duplicate_sequence
    FROM stg_transaction_line s
    WHERE s.is_retained = 1
      AND s.invoice_id IS NOT NULL
      AND s.item_key IS NOT NULL
      AND s.item_name IS NOT NULL
      AND s.transaction_date IS NOT NULL
      AND s.quantity > 0
      AND s.unit_price > 0
)
SELECT v.invoice_id,
       v.item_key,
       SUM(v.quantity),
       SUM(v.quantity * v.unit_price),
       COUNT(*)
FROM valid_lines v
JOIN dim_product p ON p.item_key = v.item_key
WHERE v.duplicate_sequence = 1
GROUP BY v.invoice_id, v.item_key;

COMMIT;

