# Data

The raw source is the UCI Online Retail workbook:

- Source: <https://archive.ics.uci.edu/dataset/352/online%2Bretail>
- Citation: Chen, D. (2015), UCI Machine Learning Repository, DOI <https://doi.org/10.24432/C5BW33>
- License: CC BY 4.0; retain attribution when sharing derived work.
- Downloaded: 2026-11-26.
- File: `raw/Online Retail.xlsx` (never modified by the pipeline).
- SHA-256: `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`.

Run `python src/clean_data.py` to create:

- `cleaned/cleaned_transaction_lines.csv` — retained source-line grain.
- `cleaned/basket_item_presence.csv` — one row per distinct basket-item.
- `cleaned/basket_summary.csv` — one row per eligible basket.
- `cleaned/product_summary.csv` — one row per item.
- `cleaned/data_quality_summary.csv` and `cleaned/cleaning_audit.csv` — quantified checks.
- `derived/sql_staging.csv` — normalized staging extract for Oracle loading; generated locally and ignored by Git.

The raw workbook, staging CSV, and bulk cleaned extracts are intentionally not published to GitHub. They are reproducible from the official source and the cleaning script. The required full pair-metrics output is published under `outputs/` despite its approximately 54 MB size.

The raw workbook is intentionally not committed. The cleaning rules and all exclusions are documented in `docs/kpi_definitions.md` and `reports/data_quality_report.md`.

