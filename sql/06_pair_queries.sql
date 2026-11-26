-- Reference Oracle pair query. It returns one unordered row per pair.
-- Thresholds are read from MB_CONFIG and must match config/analysis_config.json.

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
    SELECT DISTINCT basket_id, item_key
    FROM fact_basket_item
),
item_counts AS (
    SELECT item_key, COUNT(DISTINCT basket_id) AS item_basket_count
    FROM distinct_basket_items
    GROUP BY item_key
),
eligible_items AS (
    SELECT i.item_key, i.item_basket_count
    FROM item_counts i
    CROSS JOIN params p
    WHERE i.item_basket_count >= p.min_item_frequency
),
pair_counts AS (
    SELECT a.item_key AS item_a_key,
           b.item_key AS item_b_key,
           COUNT(DISTINCT a.basket_id) AS pair_count
    FROM distinct_basket_items a
    JOIN distinct_basket_items b
      ON b.basket_id = a.basket_id
     AND a.item_key < b.item_key
    JOIN eligible_items ea ON ea.item_key = a.item_key
    JOIN eligible_items eb ON eb.item_key = b.item_key
    GROUP BY a.item_key, b.item_key
),
basket_total AS (
    SELECT COUNT(DISTINCT basket_id) AS basket_count
    FROM fact_transaction
),
metrics AS (
    SELECT pc.item_a_key,
           pa.item_name AS item_a_name,
           pc.item_b_key,
           pb.item_name AS item_b_name,
           pc.pair_count,
           bt.basket_count,
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
),
qualified AS (
    SELECT m.*
    FROM metrics m
    CROSS JOIN params p
    WHERE m.pair_count >= p.min_pair_count
      AND m.support >= p.min_support
      AND m.confidence_a_to_b >= p.min_confidence
      AND m.confidence_b_to_a >= p.min_confidence
)
SELECT q.*,
       ROW_NUMBER() OVER (
           ORDER BY q.pair_count DESC, q.lift DESC, q.item_a_name, q.item_b_name
       ) AS rank
FROM qualified q
ORDER BY rank;

