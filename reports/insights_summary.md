# Market Basket Analysis insights

This summary is generated from `outputs/python_top_10_pairs.csv`, `outputs/python_lift_top_10_pairs.csv`, `outputs/python_item_frequency.csv`, and `data/cleaned/data_quality_summary.csv`. It describes observed co-occurrences; recommendations are explicitly labeled as inferences.

## Observed facts

The cleaned population contains 19,773 eligible baskets, 3,798 distinct products, 517,287 distinct basket-item presence rows, and 1,500 single-item baskets. The full raw workbook has 541,909 rows; 522,537 lines are retained after the default cleaning rules. See [data quality report](data_quality_report.md) and [cleaning summary CSV](../data/cleaned/data_quality_summary.csv).

The rare-item filter keeps 3,406 of 3,798 products (basket frequency at least 5), while the full cleaned presence table remains available. The pair threshold is at least 20 baskets and support at least 0.001. See [rare-item impact](../outputs/rare_item_impact.csv) and [KPI dictionary](../docs/kpi_definitions.md).

## Top 10 pairs by count

| Rank | Item A | Item B | Pair count | Support | A → B | B → A | Lift |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | JUMBO BAG PINK POLKADOT | JUMBO BAG RED RETROSPOT | 825 | 0.041724 | 0.6773 | 0.3949 | 6.4112 |
| 2 | GREEN REGENCY TEACUP AND SAUCER | ROSES REGENCY TEACUP AND SAUCER | 767 | 0.038790 | 0.7572 | 0.7202 | 14.0575 |
| 3 | JUMBO STORAGE BAG SUKI | JUMBO BAG RED RETROSPOT | 724 | 0.036616 | 0.6115 | 0.3466 | 5.7879 |
| 4 | JUMBO SHOPPER VINTAGE RED PAISLEY | JUMBO BAG RED RETROSPOT | 680 | 0.034390 | 0.5787 | 0.3255 | 5.4778 |
| 5 | LUNCH BAG RED RETROSPOT | LUNCH BAG SUKI DESIGN | 655 | 0.033126 | 0.4185 | 0.5101 | 6.4452 |
| 6 | LUNCH BAG RED RETROSPOT | LUNCH BAG BLACK SKULL | 641 | 0.032418 | 0.4096 | 0.5035 | 6.3619 |
| 7 | ALARM CLOCK BAKELIKE GREEN | ALARM CLOCK BAKELIKE RED | 640 | 0.032367 | 0.6531 | 0.6089 | 12.2864 |
| 8 | GREEN REGENCY TEACUP AND SAUCER | PINK REGENCY TEACUP AND SAUCER | 632 | 0.031962 | 0.6239 | 0.8261 | 16.1257 |
| 9 | LUNCH BAG RED RETROSPOT | LUNCH BAG PINK POLKADOT | 606 | 0.030648 | 0.3872 | 0.5560 | 7.0243 |
| 10 | PINK REGENCY TEACUP AND SAUCER | ROSES REGENCY TEACUP AND SAUCER | 598 | 0.030243 | 0.7817 | 0.5615 | 14.5132 |

Source: [Python count-ranked output](../outputs/python_top_10_pairs.csv).

## Top 10 pairs by lift

| Rank | Item A | Item B | Pair count | Support | A → B | B → A | Lift |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | PINK KNITTED EGG COSY | BLUE KNITTED EGG COSY | 25 | 0.001264 | 0.8621 | 0.8929 | 608.7746 |
| 2 | PANTRY HOOK TEA STRAINER | PANTRY HOOK SPATULA | 25 | 0.001264 | 0.7813 | 0.7576 | 468.1108 |
| 3 | YELLOW FELT HANGING HEART W FLOWER | BLUE FELT HANGING HEART W FLOWER | 20 | 0.001011 | 0.6897 | 0.6250 | 426.1422 |
| 4 | MIRRORED WALL ART GENTS | MIRRORED WALL ART LADIES | 27 | 0.001365 | 0.6279 | 0.8182 | 376.2304 |
| 5 | PANTRY HOOK SPATULA | PANTRY HOOK BALLOON WHISK | 29 | 0.001467 | 0.8788 | 0.6170 | 369.7079 |
| 6 | PANTRY HOOK TEA STRAINER | PANTRY HOOK BALLOON WHISK | 28 | 0.001417 | 0.8750 | 0.5957 | 368.1144 |
| 7 | CAT AND BIRD WALL ART | DOG AND BALL WALL ART | 25 | 0.001264 | 0.5682 | 0.7813 | 351.0831 |
| 8 | SMALL PARLOUR PICTURE FRAME | MEDIUM PARLOUR PICTURE FRAME | 22 | 0.001113 | 0.6286 | 0.6111 | 345.2429 |
| 9 | SNACK TRAY PAISLEY PARK | SNACK TRAY RED VINTAGE DOILY | 20 | 0.001011 | 0.6250 | 0.5405 | 334.0034 |
| 10 | SILVER FABRIC MIRROR | GOLD FABRIC MIRROR | 21 | 0.001062 | 0.4565 | 0.7241 | 311.2691 |

Source: [Python lift-ranked output](../outputs/python_lift_top_10_pairs.csv).

## Directional confidence

The strongest directional signals in the lift table are `PANTRY HOOK SPATULA → PANTRY HOOK BALLOON WHISK` at 0.8788, `PANTRY HOOK TEA STRAINER → PANTRY HOOK BALLOON WHISK` at 0.8750, and `PINK KNITTED EGG COSY → BLUE KNITTED EGG COSY` at 0.8621. Confidence is directional, so these should not be rephrased as symmetric probabilities. The count-ranked Regency teacup pairs also show asymmetric confidence, including `PINK REGENCY TEACUP AND SAUCER → ROSES REGENCY TEACUP AND SAUCER` at 0.7817 versus the reverse direction at 0.5615.

## Frequently purchased items

The most frequent products by basket count are WHITE HANGING HEART T-LIGHT HOLDER (2,265), JUMBO BAG RED RETROSPOT (2,089), REGENCY CAKESTAND 3 TIER (1,988), PARTY BUNTING (1,685), and LUNCH BAG RED RETROSPOT (1,565). See [item frequency output](../outputs/python_item_frequency.csv).

## High-frequency items with weaker relative associations

High frequency is not equivalent to strong association. For example, JUMBO BAG RED RETROSPOT and WHITE HANGING HEART T-LIGHT HOLDER co-occur in 448 baskets with lift 1.8722, much lower than the count-ranked bag pair's lift 6.4112 and far below the lift-ranked rare pairs. This is a descriptive comparison from the generated pair table, not a causal finding.

## Inferred business recommendations

- Use the count-ranked bag, lunch-bag, alarm-clock, and Regency teacup pairs as candidates for bundle placement or “frequently bought together” modules because they combine high observed pair counts with non-trivial lift.
- Use the Regency teacup and pantry-hook clusters for merchandising adjacency or curated bundle tests; the directional confidence values suggest that recommendations may differ depending on the anchor item.
- Treat lift-ranked pairs as targeted cross-sell candidates rather than broad promotions. Their pair counts are only 20–29 baskets under this configuration, so test with holdouts and monitor conversion before scaling.
- Keep single-item baskets and rare-item diagnostics visible in the dashboard so commercial users do not mistake broad catalog frequency for product affinity.

These are recommendations inferred from the generated metrics. They are not externally sourced facts and should be validated with margin, inventory, seasonality, and controlled promotion data.

## Limitations and biases

- The data represents one retailer and historical period; patterns may not generalize.
- Invoice-level co-occurrence is not proof of causal complementarity.
- Returns, cancellations, service codes, missing descriptions, and exact duplicates are handled by explicit project rules; a different accounting purpose may choose different rules.
- High lift can be unstable for rare products. Pair count and support must be read alongside lift.
- Customer IDs are missing on a material share of raw lines, so customer-level segmentation is incomplete even though basket presence can still be analyzed.

