# Market Basket Analysis Research Report

*Generated: 2026-11-26 | Sources: 24 | Deep-read sources: UCI dataset record, the VLDB association-rule paper, mlxtend metric documentation, Oracle SQL documentation, and Microsoft Power BI guidance | Overall confidence: High for definitions and platform guidance; medium for dataset-specific cleaning because the source does not prescribe an association-analysis policy.*

## Executive summary

The recommended source is UCI's **Online Retail** dataset, a public workbook containing 541,909 invoice lines for a UK non-store online retailer, with invoice, stock code, description, quantity, timestamp, price, customer, and country fields. The UCI record identifies cancellations through an invoice number beginning with `C`, documents the eight variables, provides a 22.6 MB workbook, and licenses the dataset under CC BY 4.0 ([UCI dataset record](https://archive.ics.uci.edu/dataset/352/online%2Bretail)).

For basket analysis, the safest reproducible unit is a distinct `(basket_id, item_key)` presence row. Quantity and revenue remain separate additive measures, while support, confidence, and lift are calculated from presence. This prevents duplicate invoice lines from inflating pair counts and keeps single-item baskets in the support denominator. Confidence is directional; lift is symmetric and equals 1 under independence in the standard formulation ([mlxtend association-rule metrics](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/)).

The project uses a transparent Python combination algorithm and an Oracle-compatible self-join over the same cleaned presence grain. Oracle's documentation defines joins as combining rows according to join conditions and documents `COUNT(DISTINCT ...)` for exact distinct counts ([Oracle joins](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Joins.html), [Oracle COUNT](https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/COUNT.html)). The Power BI design follows star-schema guidance: dimensions filter/group and facts summarize, with explicit DAX measures, slicers, matrix conditional formatting, and a pair drill-through page ([Power BI star schema](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema), [Power BI slicers](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicer-visual), [Power BI drillthrough](https://learn.microsoft.com/en-us/power-bi/guidance/report-drillthrough)).

## Research questions

1. Which public grocery, retail, or e-commerce basket dataset is most suitable?
2. What are the correct definitions and interpretations of support, confidence, lift, basket, item, and pair?
3. How should cancellations, returns, duplicates, missing values, and rare items be handled?
4. What Oracle SQL design supports distinct basket-item pairs, self-joins, indexes, and repeatable loading?
5. What Power BI model and visual interactions communicate pair relationships without symmetric double-counting?

## Findings by theme

### 1. Dataset selection

**Fact.** UCI describes Online Retail as a transactional dataset covering 2010-12-01 through 2011-12-09 for a UK-based registered non-store retailer whose products are mainly unique all-occasion gifts; it reports 541,909 instances and eight documented variables ([UCI dataset record](https://archive.ics.uci.edu/dataset/352/online%2Bretail)). The record identifies the invoice, stock code, description, quantity, invoice date, unit price, customer ID, and country fields and states that a leading `C` on `InvoiceNo` indicates a cancellation ([UCI variable table](https://archive.ics.uci.edu/dataset/352/online%2Bretail)).

**Comparison.** UCI also publishes Online Retail II, a larger follow-on record ([UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii)). It is a valid alternative, but this build selects Online Retail because the official record provides a direct, manageable workbook and the selected extract is sufficient to produce stable pair counts while keeping the reproducible demo smaller.

**Recommendation.** Use Online Retail, preserve the downloaded workbook under `data/raw/`, and record the download date, source URL, license, and SHA-256 hash. This project does that. The CC BY 4.0 license permits sharing and adaptation with attribution according to the UCI record ([UCI license statement](https://archive.ics.uci.edu/dataset/352/online%2Bretail)).

**Confidence: High** for provenance and fields; **Medium** for the relative suitability judgment because suitability depends on the intended business use.

### 2. Association-rule definitions

The original VLDB paper formalizes association-rule mining over sales transactions and motivates use cases such as cross-marketing, add-on sales, and store layout ([Agrawal and Srikant, VLDB 1994](https://www.vldb.org/dblp/db/conf/vldb/vldb94-487.html); [paper PDF](https://www.macs.hw.ac.uk/~dwcorne/Teaching/agrawal94fast.pdf)). The implementation uses the following definitions:

- A **basket** is one valid transaction identifier, `InvoiceNo` in this dataset.
- An **item** is one normalized merchandise `StockCode`; the description is a label, not the key.
- **Basket-item presence** is binary: one row per basket and item regardless of quantity.
- **Pair count** is the number of distinct baskets containing both items.
- `support(A,B) = pair_count(A,B) / eligible_basket_count`.
- `confidence(A → B) = pair_count(A,B) / basket_count(A)`.
- `confidence(B → A) = pair_count(A,B) / basket_count(B)`.
- `lift(A,B) = support(A,B) / (support(A) × support(B))`.

The mlxtend documentation states the support, confidence, and lift formulas, explains that confidence is not symmetric, and interprets lift of 1 as independence ([mlxtend association rules](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/)). The project therefore stores one unordered pair with deterministic `item_a_key < item_b_key`, but reports both directional confidence values. Lift is symmetric because the joint support and the product of marginal supports are symmetric.

**Confidence: High** for formulas and directional interpretation because the academic and package references agree.

### 3. Cleaning and rare-item policy

The UCI record documents cancellations, quantity, product, date, price, customer, and country fields, but it does not prescribe one universal retail-cleaning policy ([UCI dataset record](https://archive.ics.uci.edu/dataset/352/online%2Bretail)). The project therefore separates source facts from business assumptions:

1. Keep the raw workbook unchanged.
2. Normalize text keys by trimming and upper-casing; parse dates and numbers with coercion and flag failures.
3. Exclude cancellation/return rows, non-positive quantities, invalid prices, missing basket/item/name/date fields, known service or adjustment codes, test rows, and exact duplicate rows from the default merchandise population.
4. Retain missing customer IDs when the basket and item are otherwise valid; customer identity is not part of the basket definition.
5. Remove duplicate source rows once, then aggregate to one presence row per basket-item. Quantity, line count, and revenue remain available in separate columns.
6. Keep single-item baskets in the eligible basket population. They contribute to the support denominator and cannot generate a pair naturally.
7. Do not delete rare products from the cleaned data. The default analysis filter is `basket_count >= 5`, and the default pair threshold is `pair_count >= 20` plus `support >= 0.001`. The impact table reports the number of products, basket-item rows, and pair rows before and after the item-frequency filter.

The pandas implementation relies on documented `read_excel`/`read_csv` ingestion, `drop_duplicates`, and group-by aggregation ([pandas read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html), [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html), [pandas drop_duplicates](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html), [pandas groupby](https://pandas.pydata.org/docs/user_guide/groupby.html)).

**Confidence: Medium-high.** The mechanics are reproducible; the decision to exclude service lines and returns is a documented analytical assumption, not a claim about the retailer's accounting system.

### 4. Oracle design

Use a small star/normalized model with `STG_TRANSACTION_LINE` at source-line grain, `DIM_PRODUCT`, `DIM_CUSTOMER`, and `DIM_DATE` dimensions, `FACT_TRANSACTION` at basket grain, and `FACT_BASKET_ITEM` at distinct basket-item grain. The pair query first selects distinct basket-item keys, derives item counts, self-joins two aliases on the same basket and enforces `item_a < item_b`, then counts distinct baskets. This is the SQL equivalent of the Python combinations algorithm.

Oracle documents that join results are governed by join conditions and that the optimizer considers join conditions, indexes, and statistics ([Oracle joins](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Joins.html)). Oracle documents exact `COUNT(DISTINCT expr)` behavior ([Oracle COUNT](https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/COUNT.html)), inline views/subqueries for staged transformations ([Oracle subqueries](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Using-Subqueries.html)), primary/foreign/check constraints in `CREATE TABLE` ([Oracle CREATE TABLE](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-TABLE.html)), and explicit indexes ([Oracle CREATE INDEX](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-INDEX.html)). Oracle also notes that indexes speed access but add storage and DML overhead, so indexes should target join, filter, and foreign-key columns ([Oracle index concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/indexes-and-index-organized-tables.html)).

**Recommendation.** Load normalized staging text through SQL*Loader, build cleaned facts with `ROW_NUMBER()`/`GROUP BY`, enforce a composite primary key on `(basket_id, item_key)`, and index `(basket_id, item_key)` plus `(item_key, basket_id)`. Use a `MB_CONFIG` table for thresholds so SQL and Python can share explicit parameters.

**Confidence: High** for the Oracle design pattern; **Medium** for performance because actual plans depend on Oracle version, statistics, storage, and data volume.

### 5. Power BI model and visuals

Microsoft recommends dimensions for filtering/grouping and facts for summarization, with a consistent fact grain and one-to-many relationships where possible ([Power BI star schema](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)). Power BI relationships propagate filters, and the one side must contain unique values for a standard one-to-many relationship ([Power BI relationships](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-relationships-understand)).

The dashboard specification therefore uses `DimProduct`, `DimDate`, `DimCustomer`, `FactTransaction`, `FactBasketItem`, `BasketSummary`, and the precomputed unordered `PairMetrics` table. Slicers are appropriate for item, date, country, and customer filters because the Slicer visual filters other visuals and supports text, numeric, and date fields ([Power BI slicer](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicer-visual)). A matrix is appropriate for an Item A × Item B pair grid; Microsoft documents matrix row/column hierarchies and conditional formatting for values, totals, and subtotals ([Power BI matrix](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-matrix-visual), [conditional formatting](https://learn.microsoft.com/en-us/power-bi/desktop-conditional-table-formatting)). A drill-through page should receive the selected pair and expose supporting baskets and transaction detail ([Power BI drill-through guidance](https://learn.microsoft.com/en-us/power-bi/guidance/report-drillthrough)).

Use explicit DAX measures rather than relying on implicit aggregations; Microsoft documents that measures are calculated on demand and respond to report interaction ([Power BI measures](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-measures), [calculation options](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-calculations-options)). The pair table itself is directional only in the confidence columns and has one row per unordered pair, preventing symmetric double-counting.

**Confidence: High** for platform capabilities; **Medium** for visual effectiveness because usability should be validated with actual stakeholders.

## Dataset selection rationale and provenance

| Field | Decision |
|---|---|
| Dataset | UCI Online Retail |
| Source | https://archive.ics.uci.edu/dataset/352/online%2Bretail |
| Citation | Chen, D. (2015). Online Retail. UCI Machine Learning Repository. DOI: https://doi.org/10.24432/C5BW33 |
| License | CC BY 4.0; attribution required |
| Download date | 2026-11-26 |
| Format | `Online Retail.xlsx`, one workbook, 22.6 MB according to the UCI record |
| Original columns | InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country |
| Limitations | One retailer, one historical period, no category hierarchy, missing customer IDs, cancellations/returns mixed with sales, and no guarantee that invoice-level data represents a checkout session |
| Why suitable | It contains a stable transaction identifier, product identifier/description, quantity, timestamp, price, customer, and country—enough to construct presence, revenue, time, and cross-segment outputs |

## Methodology

The research covered five sub-questions across dataset provenance, association-rule methodology, data cleaning, Oracle implementation, and Power BI reporting. Twenty-two unique URLs were reviewed. The most important sources were read in detail: the UCI dataset record; Agrawal and Srikant's VLDB paper; mlxtend's metric definitions; Oracle's join/count/index/constraint guidance; and Microsoft's star-schema, slicer, matrix, measures, and drill-through guidance. External pages were treated as untrusted reference data; no instructions embedded in pages were followed.

## Limitations and unresolved gaps

- Oracle Database and Power BI Desktop were not available in the build environment. Oracle scripts are written for Oracle 19c-compatible syntax and the Power BI design is complete, but direct execution of the database and creation of a `.pbix` remain environment-dependent.
- The UCI dataset is historical and retailer-specific. Observed pairs are descriptive co-occurrences, not causal evidence that one product drives another.
- Returns and service/adjustment lines are excluded by default. A different accounting objective may require a separate net-sales or return-aware analysis.
- Lift-ranked pairs have intentionally low absolute support in some cases; the report shows both count-ranked and lift-ranked tables and retains thresholds to make this trade-off explicit.

## Sources

1. [UCI Online Retail dataset record](https://archive.ics.uci.edu/dataset/352/online%2Bretail) — provenance, fields, instance count, file, license.
2. [UCI Online Retail II dataset record](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii) — alternative public retail extract.
3. [UCI dataset DOI](https://doi.org/10.24432/C5BW33) — persistent citation.
4. [Agrawal and Srikant, VLDB 1994](https://www.vldb.org/dblp/db/conf/vldb/vldb94-487.html) — original association-rule mining paper record.
5. [Agrawal and Srikant paper PDF](https://www.macs.hw.ac.uk/~dwcorne/Teaching/agrawal94fast.pdf) — full paper text.
6. [mlxtend association rules guide](https://rasbt.github.io/mlxtend/user_guide/frequent_patterns/association_rules/) — support, confidence, lift and directionality.
7. [mlxtend association_rules API](https://rasbt.github.io/mlxtend/api_modules/mlxtend.frequent_patterns/association_rules/) — configurable rule-generation API.
8. [pandas read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) — workbook ingestion.
9. [pandas read_csv](https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html) — CSV ingestion.
10. [pandas drop_duplicates](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html) — duplicate handling.
11. [pandas groupby guide](https://pandas.pydata.org/docs/user_guide/groupby.html) — grouped aggregation.
12. [Oracle joins](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Joins.html) — join semantics and optimizer context.
13. [Oracle COUNT](https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/COUNT.html) — exact distinct counting.
14. [Oracle subqueries](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Using-Subqueries.html) — inline-view transformations.
15. [Oracle CREATE TABLE](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-TABLE.html) — keys and integrity constraints.
16. [Oracle CREATE INDEX](https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/CREATE-INDEX.html) — index syntax and purpose.
17. [Oracle index concepts](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/indexes-and-index-organized-tables.html) — index trade-offs.
18. [Power BI star schema](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) — semantic-model design.
19. [Power BI relationships](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-relationships-understand) — filter propagation and cardinality.
20. [Power BI slicer visual](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicer-visual) — interactive filtering.
21. [Power BI matrix conditional formatting](https://learn.microsoft.com/en-us/power-bi/desktop-conditional-table-formatting) — pair heat-map implementation.
22. [Power BI drill-through guidance](https://learn.microsoft.com/en-us/power-bi/guidance/report-drillthrough) — detail navigation.
23. [Power BI measures](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-measures) — responsive DAX calculations.
24. [Power BI Query Overview](https://learn.microsoft.com/power-bi/desktop-query-overview) — Power Query import and transformation workflow.

