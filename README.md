# Market Basket Analysis for Retail Transactions

This project analyzes retail invoice baskets with transparent Python association metrics, an Oracle SQL self-join implementation, and a Power BI dashboard specification. It is built around the public UCI **Online Retail** dataset and is designed to be rerun from the command line.

Published repository: [github.com/krishporwal011/Bussiness-BI](https://github.com/krishporwal011/Bussiness-BI), branch `main`.

## Business problem

Retail teams want to identify products that co-occur in the same transaction so they can test bundles, merchandising adjacency, and “frequently bought together” recommendations. The project reports the top 10 unordered item pairs by pair count and a supplementary top 10 by lift, including support, confidence A → B, confidence B → A, and lift.

## Current result

The UCI workbook contains 541,909 raw invoice lines. With the default rules, the pipeline retains 522,537 valid merchandise lines, 19,773 baskets, 3,798 products, 517,287 distinct basket-item rows, and 1,500 single-item baskets. The count-ranked top pair is `JUMBO BAG PINK POLKADOT + JUMBO BAG RED RETROSPOT` with 825 baskets, support 0.041724, directional confidence 0.6773 / 0.3949, and lift 6.4112. The lift-ranked top pair is `PINK KNITTED EGG COSY + BLUE KNITTED EGG COSY` with 25 baskets and lift 608.7746; its low pair count is why lift is shown separately from count.

See [reports/insights_summary.md](reports/insights_summary.md) for the full generated tables and observed-fact/recommendation separation.

## Dataset source and license

- Dataset: UCI Online Retail.
- Official source: [UCI dataset record](https://archive.ics.uci.edu/dataset/352/online%2Bretail).
- Citation: Chen, D. (2015). Online Retail. UCI Machine Learning Repository. [DOI 10.24432/C5BW33](https://doi.org/10.24432/C5BW33).
- Download date: 2026-11-26.
- License: CC BY 4.0; retain attribution for redistributed or adapted work.
- Raw file: `data/raw/Online Retail.xlsx`; it is preserved locally and ignored by Git.

The research rationale and citations are in [docs/research_report.md](docs/research_report.md).

## Folder structure

```text
config/       Thresholds and dataset configuration
data/raw/     Unmodified source workbook (local, ignored)
data/cleaned/ Clean transaction, presence, basket, product, and quality tables
data/derived/ Normalized SQL staging CSV (local, ignored)
demo/         Demo script, storyboard, and recording checklist
docs/         Research, KPI definitions, and data-model diagram
notebooks/    Cleaning and association-analysis walkthroughs
outputs/      Python pair metrics, top-10 outputs, frequency and impact tables
powerbi/      Power Query, DAX, model, and dashboard build specification
reports/      Data quality, insights, and SQL/Python reconciliation reports
sql/          Oracle 19c-compatible schema, load, transform, views, and validation
src/          Command-line cleaning, analysis, and reconciliation programs
tests/        Automated unit tests for pair grain and denominator behavior
```

## Environment setup

Python 3.10+ is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The downloaded workbook is already present in this workspace. For a fresh clone, download `Online Retail.xlsx` from the official UCI record into `data/raw/` and keep the raw file unchanged.

## Run the Python pipeline

From the project root:

```bash
python src/clean_data.py
python src/market_basket_analysis.py
python src/reconcile_sql_python.py
```

Outputs:

- `data/cleaned/cleaned_transaction_lines.csv`
- `data/cleaned/basket_item_presence.csv`
- `data/cleaned/basket_summary.csv`
- `data/cleaned/product_summary.csv`
- `data/cleaned/data_quality_summary.csv`
- `data/cleaned/cleaning_audit.csv`
- `reports/data_quality_report.md`
- `outputs/python_pair_metrics.csv`
- `outputs/python_top_10_pairs.csv`
- `outputs/python_lift_top_10_pairs.csv`
- `outputs/python_item_frequency.csv`
- `outputs/rare_item_impact.csv`

The full `outputs/python_pair_metrics.csv` is tracked because it is a required project output; it is approximately 54 MB. Raw, staging, and large cleaned extracts remain ignored and are regenerated from the documented UCI source.

The primary implementation is intentionally transparent: it deduplicates to one row per basket-item, uses `itertools.combinations` to generate unordered pairs inside each basket, counts baskets, and computes the documented formulas. It does not rely on `mlxtend`; the research report links to mlxtend for independent metric definitions.

## Threshold configuration

Edit `config/analysis_config.json` before rerunning both Python and Oracle:

```json
{
  "min_item_frequency": 5,
  "min_pair_count": 20,
  "min_support": 0.001,
  "min_confidence": 0.0,
  "top_n": 10,
  "include_canceled_returns": false
}
```

The cleaned dataset preserves all valid merchandise products. The minimum item frequency affects pair generation only and the impact is written to `outputs/rare_item_impact.csv`. The default count/support thresholds make the full pair CSV manageable and reduce unstable lift-only results; they are not hard-coded in the source.

## Data-cleaning rules

The raw workbook is never edited. The pipeline standardizes column names, trims and upper-cases keys/names, parses numbers and dates safely, flags cancellations/returns, invalid quantities/prices, missing basket/item/name/date values, known service/adjustment codes, test rows, and exact duplicates, and records primary exclusion counts. Missing customer IDs are retained when the basket-item data is valid. Quantity, line count, and revenue are kept separately from binary presence.

Single-item baskets are kept in the basket population and support denominator; they simply create no pair. Exact duplicates are removed once before the clean-line output. Association counts are computed from the unique basket-item presence table, so repeated lines for the same item cannot inflate pair counts.

See [docs/kpi_definitions.md](docs/kpi_definitions.md) and [reports/data_quality_report.md](reports/data_quality_report.md).

## Oracle setup and execution

Oracle Database and `sqlplus`/`sqlcl` were not installed in the build environment, so the SQL scripts are syntactically reviewed and logically aligned with Python but not claimed as executed here.

Run in this order in a target Oracle 19c-compatible schema:

```text
@sql/01_create_schema.sql
@sql/02_create_tables.sql
-- load data/derived/sql_staging.csv with sql/stg_transaction_line.ctl
@sql/04_load_staging.sql
@sql/05_transform_clean.sql
@sql/03_create_constraints_indexes.sql
@sql/07_create_views.sql
@sql/06_pair_queries.sql
@sql/08_validation_reconciliation.sql
```

The pair query uses `SELECT DISTINCT` basket-item keys, item-frequency filtering, a self-join on basket ID, `item_a_key < item_b_key`, exact distinct basket counts, and the `FACT_TRANSACTION` basket denominator. Views include `VW_BASKET_SUMMARY`, `VW_ITEM_FREQUENCY`, `VW_ITEM_PAIR_METRICS`, `VW_TOP_10_ITEM_PAIRS`, and `VW_DATA_QUALITY_SUMMARY`. Full details are in [sql/README.md](sql/README.md).

Validation prerequisites are Oracle 19c/Free/XE (or an approved Oracle service), SQL*Plus or SQLcl, SQL*Loader, schema DDL/view/index privileges, and a regenerated `data/derived/sql_staging.csv`. Use an interactive connection or wallet; never place a password in a command or repository. The exact validation checklist is in [sql/README.md](sql/README.md).

## SQL/Python reconciliation

The reconciler compares pair keys, pair counts, basket counts, both item counts, support, both directional confidences, and lift. Integer counts must match exactly; floating metrics use an absolute tolerance of `1e-9`. Missing and extra pair keys are reported, and any mismatch causes a non-zero exit code.

Current status: **PENDING**, because Oracle was unavailable. The generated [reconciliation report](reports/sql_python_reconciliation.md) deliberately does not claim a database result. After exporting `sql/06_pair_queries.sql` to CSV:

```bash
python src/reconcile_sql_python.py \
  --python outputs/python_pair_metrics.csv \
  --sql oracle_exports/oracle_pair_metrics.csv
```

## Power BI dashboard

Power BI Desktop was not available, so no `.pbix` file was created. The project does not pretend otherwise. The complete build specification is in [powerbi/README.md](powerbi/README.md), with [Power Query M](powerbi/power_query.m), [DAX measures](powerbi/dax_measures.dax), and [relationship guidance](powerbi/model_relationships.md). The intended file name is `market_basket_analysis.pbix`. Because the qualifying pair table has 347,481 rows, the main matrix should use selected-item or Top-N filtering while the full table remains available for detail.

Required pages:

1. Executive overview — KPI cards, trend, frequent items, top pair.
2. Pair analysis — Item A/B/date/customer/country slicers, pair matrix, conditional formatting, count/lift views.
3. Item analysis — item frequency, support, quantity/revenue, rare-item diagnostics.
4. Data quality — raw/retained/removed/duplicate/missing/return/singleton/rare-item metrics.
5. Pair detail — drill-through to supporting baskets, dates, customer/country, and co-purchased items.

## KPI formulas

The full dictionary is in [docs/kpi_definitions.md](docs/kpi_definitions.md). In short:

```text
support(A,B)       = pair_count(A,B) / eligible_basket_count
confidence(A -> B) = pair_count(A,B) / basket_count(A)
confidence(B -> A) = pair_count(A,B) / basket_count(B)
lift(A,B)          = support(A,B) / (support(A) * support(B))
```

Pairs are stored once with `item_a_key < item_b_key`; lift is symmetric, confidence is directional.

## Tests and validation

```bash
python -m pytest -q
python -m json.tool notebooks/01_cleaning_and_quality.ipynb >/dev/null
python -m json.tool notebooks/02_association_rules.ipynb >/dev/null
```

The unit tests verify that duplicate lines do not inflate a pair and that a single-item basket remains in the support denominator. The notebooks are executable walkthroughs of the two Python stages.

The final audit is in [reports/final_submission_checklist.md](reports/final_submission_checklist.md). The current suite has 5 passing tests, including threshold behavior, formula checks, deterministic ordering, no reverse-pair duplication, and visible reconciliation failure behavior.

## Demo

No video-recording capability was available, so no MP4 is claimed. Use [demo/demo_script.md](demo/demo_script.md), [demo/demo_storyboard.md](demo/demo_storyboard.md), and [demo/recording_checklist.md](demo/recording_checklist.md) to record `demo/market_basket_analysis_demo.mp4` in an environment with a screen recorder.

## GitHub publication

The project is published at the repository root on the authorized `main` branch. GitHub accepted the approximately 54 MB `outputs/python_pair_metrics.csv` file with a large-file recommendation warning; raw data and bulk staging/cleaned extracts remain excluded and reproducible.

## Known limitations and remaining user action

- Run the Oracle scripts in an Oracle environment and export the query result to complete reconciliation.
- Build and save `market_basket_analysis.pbix` in Power BI Desktop using the supplied specification.
- Optional: record the demo video.
- The dataset is one historical retailer and should not be treated as causal or universally representative.
- A fresh clone must obtain the public raw workbook separately because the raw file, SQL staging extract, and bulk cleaned CSVs are ignored by Git. The required full pair-metrics CSV is included despite its size; the remaining generated extracts can be regenerated with the Python commands above.
- The local Git repository is initialized on `main`, tracks `origin/main`, and is published at the repository URL shown above.

