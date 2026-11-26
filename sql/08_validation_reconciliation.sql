-- Validation queries and Oracle-to-Python export instructions.

-- 1. Fact grain and referential checks.
SELECT COUNT(*) AS duplicate_basket_item_keys
FROM (
    SELECT basket_id, item_key, COUNT(*) AS row_count
    FROM fact_basket_item
    GROUP BY basket_id, item_key
    HAVING COUNT(*) > 1
);

SELECT COUNT(*) AS orphan_basket_items
FROM fact_basket_item fbi
LEFT JOIN fact_transaction ft ON ft.basket_id = fbi.basket_id
LEFT JOIN dim_product dp ON dp.item_key = fbi.item_key
WHERE ft.basket_id IS NULL OR dp.item_key IS NULL;

-- 2. Export the exact result set for the Python reconciliation script.
-- In SQLcl/SQL*Plus:
-- SET SQLFORMAT csv
-- SPOOL oracle_exports/oracle_pair_metrics.csv
-- @sql/06_pair_queries.sql
-- SPOOL OFF
-- SET SQLFORMAT ansiconsole

-- 3. After exporting, run from the project root:
-- python src/reconcile_sql_python.py \
--   --python outputs/python_pair_metrics.csv \
--   --sql oracle_exports/oracle_pair_metrics.csv

-- Acceptance criteria:
-- * exact equality for all integer counts;
-- * absolute difference <= 1e-9 for support, both confidences, and lift;
-- * no missing or extra pair keys;
-- * non-zero script exit code for any failure.

