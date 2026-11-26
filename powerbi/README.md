# Power BI dashboard build specification

Power BI Desktop was not available in the build environment, so `market_basket_analysis.pbix` was **not** created or claimed. This folder contains the reproducible import, model, DAX, page, slicer, matrix, and drill-through specification needed to build it in Power BI Desktop.

## Build and refresh sequence

1. Run `python src/clean_data.py` and `python src/market_basket_analysis.py` from the project root.
2. Open Power BI Desktop and create a text parameter named `ProjectRoot` pointing to the project directory.
3. Use `powerbi/power_query.m` in the Advanced Editor, or create one query per table using its `Csv` helper and the listed relative paths.
4. Apply the column types shown in the M file, then Close & Apply.
5. Create the relationships in `model_relationships.md`.
6. Add the measures from `dax_measures.dax`.
7. Build the five pages below and save the report as `powerbi/market_basket_analysis.pbix`.
8. On refresh, rerun the Python pipeline first so the CSV outputs and thresholds are current, then use Refresh in Power BI.

## Required input tables

Import these generated CSVs:

- `data/cleaned/product_summary.csv` as `DimProduct`
- `data/cleaned/basket_summary.csv` as `BasketSummary`
- `data/cleaned/basket_item_presence.csv` as `FactBasketItem`
- `outputs/python_pair_metrics.csv` as `PairMetrics`
- `data/cleaned/data_quality_summary.csv` as `DataQualitySummary`
- `data/cleaned/cleaning_audit.csv` as `CleaningAudit`
- `outputs/python_item_frequency.csv` as `ItemFrequency`

Use `powerbi/power_query.m` as the Advanced Editor starting point. Replace the `ProjectRoot` parameter with the absolute project path or create a text parameter with that name.

## Relationships

Create single-direction, one-to-many relationships:

- `DimProduct[item_key]` 1 → * `FactBasketItem[item_key]`
- `DimProduct[item_key]` 1 → * `PairMetrics[item_a_key]` is **not** recommended as a direct relationship because the pair table contains the same product in two role columns. Keep `PairMetrics` disconnected for pair-specific cards/matrices, or add two role-playing copies of `DimProduct` named `DimItemA` and `DimItemB`.
- `BasketSummary[basket_id]` 1 → * `FactBasketItem[basket_id]`
- `BasketSummary[transaction_date]` * → 1 `DimDate[calendar_date]` if a `DimDate` table is created.

For the simplest import model, use `PairMetrics` as a precomputed analytical table and use its fields directly in the pair table/matrix. The unordered pair key rule is already enforced by `item_a_key < item_b_key`; do not append a reversed copy.

## Pair-matrix performance decision

`PairMetrics` contains 347,481 qualifying rows under the default thresholds. Import the table for filtered detail and drill-through, but do not place all rows and all products into an unrestricted matrix. For the main Pair analysis page, apply a visual-level Top N filter (for example, top 50 pairs by `pair_count`) or filter to a selected Item A/Item B before rendering the matrix. Keep the full table available for search and drill-through. This preserves the complete analytical output while keeping the main report responsive.

## Pages

### Executive overview

Cards: Basket Count, Distinct Item Count, Total Item Lines, Average Basket Size, Single-item Basket %, Top Pair by Count, Top Pair by Lift.

Visuals: monthly basket trend from `BasketSummary[transaction_date]`; bar chart of top item frequencies; a small count-ranked pair table.

### Pair analysis

Add dropdown/search slicers for Item A, Item B, date, country, and customer. Add a matrix with `PairMetrics[item_a_name]` on rows, `PairMetrics[item_b_name]` on columns, and `Pair Count` as values. Add conditional formatting to the value field using a color scale or data bars. Add a table with pair count, support, both confidence values, and lift. Use bookmarks or separate visuals for count-ranked and lift-ranked views.

Use a visual-level Top N filter or selected-item filter on the matrix. Do not create reversed pair rows: `PairMetrics` already guarantees `item_a_key < item_b_key`.

### Item analysis

Add an item-frequency bar chart, basket count by item, support by item (`basket_count / Basket Count`), quantity and revenue trend visuals, and a rare-item table using `ItemFrequency[basket_count] < 5` as a diagnostic filter.

### Data quality

Use cards/table visuals from `DataQualitySummary` and `CleaningAudit`: raw rows, retained rows, removed rows, duplicates, missing customer IDs, invalid quantities/prices, cancellations/returns, single-item baskets, and rare-item impact from `outputs/rare_item_impact.csv`.

### Pair drill-through detail

Create a page named `Pair detail` with drill-through fields `PairMetrics[item_a_key]` and `PairMetrics[item_b_key]`. Add the selected pair, pair metrics, a supporting-basket table, transaction dates, customer/country, and the other items in those baskets. Add the default Back button. If the pair table is disconnected, use the selected keys in DAX/TREATAS or use role-playing item dimensions.

