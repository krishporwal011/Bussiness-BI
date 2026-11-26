# Demo script: Market Basket Analysis

Target length: 4–6 minutes.

1. **Objective (20 seconds)** — Explain that the project compares transparent Python pair counts with an Oracle self-join and surfaces count-ranked and lift-ranked item pairs for Power BI.
2. **Dataset and provenance (30 seconds)** — Show `data/README.md`, the UCI source, license, download date, and the unchanged raw workbook.
3. **Cleaning (45 seconds)** — Run `python src/clean_data.py`; open `reports/data_quality_report.md`; point out retained rows, exclusions, single-item baskets, and the presence-table grain.
4. **Python analysis (45 seconds)** — Run `python src/market_basket_analysis.py`; open `outputs/python_top_10_pairs.csv` and `outputs/python_lift_top_10_pairs.csv`; explain directional confidence and symmetric lift.
5. **Oracle SQL (45 seconds)** — Open `sql/06_pair_queries.sql`; highlight `SELECT DISTINCT`, self-join on basket ID, `item_a < item_b`, distinct counts, and the configurable denominator.
6. **Reconciliation (30 seconds)** — Open `reports/sql_python_reconciliation.md`; state that it is pending because Oracle was unavailable in this environment, and show the exact command for completing validation.
7. **Power BI dashboard (60 seconds)** — Open `powerbi/README.md`, `powerbi/dax_measures.dax`, and the model diagram; explain the five pages, matrix, slicers, conditional formatting, and pair drill-through.
8. **Insights (30 seconds)** — Open `reports/insights_summary.md`; contrast count-ranked bag/teacup/lunch-bag pairs with high-lift but rare pantry-hook and egg-cosy pairs.

