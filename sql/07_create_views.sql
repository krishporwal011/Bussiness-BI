-- Analytical views for Power BI and ad-hoc analysis.

CREATE OR REPLACE VIEW vw_basket_summary AS
SELECT f.basket_id,
       f.transaction_date,
       f.customer_key,
       f.country,
       COUNT(*) AS distinct_item_count,
       SUM(fbi.quantity) AS total_quantity,
       SUM(fbi.revenue) AS total_revenue,
       CASE WHEN COUNT(*) = 1 THEN 1 ELSE 0 END AS is_single_item
FROM fact_transaction f
JOIN fact_basket_item fbi ON fbi.basket_id = f.basket_id
GROUP BY f.basket_id, f.transaction_date, f.customer_key, f.country;

CREATE OR REPLACE VIEW vw_item_frequency AS
SELECT fbi.item_key,
       p.item_name,
       COUNT(DISTINCT fbi.basket_id) AS basket_count,
       SUM(fbi.quantity) AS total_quantity,
       SUM(fbi.revenue) AS total_revenue
FROM fact_basket_item fbi
JOIN dim_product p ON p.item_key = fbi.item_key
GROUP BY fbi.item_key, p.item_name;

CREATE OR REPLACE VIEW vw_item_pair_metrics AS
WITH
params AS (
    SELECT
        MAX(CASE WHEN param_name = 'MIN_ITEM_FREQUENCY' THEN num_value END) AS min_item_frequency,
        MAX(CASE WHEN param_name = 'MIN_PAIR_COUNT' THEN num_value END) AS min_pair_count,
        MAX(CASE WHEN param_name = 'MIN_SUPPORT' THEN num_value END) AS min_support,
        MAX(CASE WHEN param_name = 'MIN_CONFIDENCE' THEN num_value END) AS min_confidence
    FROM mb_config
),
distinct_basket_items AS (
    SELECT DISTINCT basket_id, item_key FROM fact_basket_item
),
item_counts AS (
    SELECT item_key, COUNT(DISTINCT basket_id) AS item_basket_count
    FROM distinct_basket_items GROUP BY item_key
),
eligible_items AS (
    SELECT i.* FROM item_counts i CROSS JOIN params p
    WHERE i.item_basket_count >= p.min_item_frequency
),
pair_counts AS (
    SELECT a.item_key AS item_a_key, b.item_key AS item_b_key,
           COUNT(DISTINCT a.basket_id) AS pair_count
    FROM distinct_basket_items a
    JOIN distinct_basket_items b ON b.basket_id = a.basket_id AND a.item_key < b.item_key
    JOIN eligible_items ea ON ea.item_key = a.item_key
    JOIN eligible_items eb ON eb.item_key = b.item_key
    GROUP BY a.item_key, b.item_key
),
basket_total AS (
    SELECT COUNT(DISTINCT basket_id) AS basket_count FROM fact_transaction
),
metrics AS (
    SELECT pc.item_a_key, pa.item_name AS item_a_name,
           pc.item_b_key, pb.item_name AS item_b_name,
           pc.pair_count, bt.basket_count,
           ia.item_basket_count AS item_a_basket_count,
           ib.item_basket_count AS item_b_basket_count,
           pc.pair_count / NULLIF(bt.basket_count, 0) AS support,
           pc.pair_count / NULLIF(ia.item_basket_count, 0) AS confidence_a_to_b,
           pc.pair_count / NULLIF(ib.item_basket_count, 0) AS confidence_b_to_a,
           (pc.pair_count / NULLIF(bt.basket_count, 0)) /
           NULLIF((ia.item_basket_count / NULLIF(bt.basket_count, 0)) *
                  (ib.item_basket_count / NULLIF(bt.basket_count, 0)), 0) AS lift
    FROM pair_counts pc
    JOIN eligible_items ia ON ia.item_key = pc.item_a_key
    JOIN eligible_items ib ON ib.item_key = pc.item_b_key
    JOIN dim_product pa ON pa.item_key = pc.item_a_key
    JOIN dim_product pb ON pb.item_key = pc.item_b_key
    CROSS JOIN basket_total bt
)
SELECT m.*,
       ROW_NUMBER() OVER (ORDER BY m.pair_count DESC, m.lift DESC, m.item_a_name, m.item_b_name) AS rank
FROM metrics m
CROSS JOIN params p
WHERE m.pair_count >= p.min_pair_count
  AND m.support >= p.min_support
  AND m.confidence_a_to_b >= p.min_confidence
  AND m.confidence_b_to_a >= p.min_confidence;

CREATE OR REPLACE VIEW vw_top_10_item_pairs AS
SELECT *
FROM (
    SELECT m.*,
           ROW_NUMBER() OVER (ORDER BY m.pair_count DESC, m.lift DESC, m.item_a_name, m.item_b_name) AS top_rank
    FROM vw_item_pair_metrics m
)
WHERE top_rank <= (SELECT num_value FROM mb_config WHERE param_name = 'TOP_N');

CREATE OR REPLACE VIEW vw_data_quality_summary AS
SELECT 'RAW_STAGING_ROWS' AS metric, COUNT(*) AS value FROM stg_transaction_line
UNION ALL SELECT 'RETAINED_STAGING_ROWS', COUNT(*) FROM stg_transaction_line WHERE is_retained = 1
UNION ALL SELECT 'CANCELLATION_ROWS_FLAGGED', COUNT(*) FROM stg_transaction_line WHERE is_cancellation = 1
UNION ALL SELECT 'NON_POSITIVE_QUANTITY_ROWS', COUNT(*) FROM stg_transaction_line WHERE quantity <= 0
UNION ALL SELECT 'EXACT_DUPLICATE_ROWS_FLAGGED', COUNT(*) FROM stg_transaction_line WHERE is_exact_duplicate = 1
UNION ALL SELECT 'VALID_BASKETS', COUNT(*) FROM fact_transaction
UNION ALL SELECT 'DISTINCT_PRODUCTS', COUNT(*) FROM dim_product
UNION ALL SELECT 'BASKET_ITEM_PRESENCE_ROWS', COUNT(*) FROM fact_basket_item
UNION ALL SELECT 'SINGLE_ITEM_BASKETS', COUNT(*) FROM vw_basket_summary WHERE is_single_item = 1;

