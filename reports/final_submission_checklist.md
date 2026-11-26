# Final submission checklist

Generated after the baseline rerun and final QA pass.

| Requirement | Status | Evidence |
|---|---|---|
| Problem statement | Complete | [`README.md`](../README.md) |
| KPI definitions and formulas | Complete | [`docs/kpi_definitions.md`](../docs/kpi_definitions.md) |
| Research report with citations | Complete | [`docs/research_report.md`](../docs/research_report.md) |
| Dataset citation, license, and provenance | Complete | [`data/README.md`](../data/README.md) |
| Editable ER/star-schema diagram | Complete | [`docs/data_model.mmd`](../docs/data_model.mmd) |
| Rendered SVG diagram | Complete | [`docs/data_model.svg`](../docs/data_model.svg) |
| Rendered PNG diagram | Complete | [`docs/data_model.png`](../docs/data_model.png) |
| Python cleaning script | Complete | [`src/clean_data.py`](../src/clean_data.py) |
| Cleaning notebook | Complete | [`notebooks/01_cleaning_and_quality.ipynb`](../notebooks/01_cleaning_and_quality.ipynb) |
| Python association analysis | Complete | [`src/market_basket_analysis.py`](../src/market_basket_analysis.py) |
| Python pair outputs | Complete | [`outputs/python_pair_metrics.csv`](../outputs/python_pair_metrics.csv), [`outputs/python_top_10_pairs.csv`](../outputs/python_top_10_pairs.csv), [`outputs/python_lift_top_10_pairs.csv`](../outputs/python_lift_top_10_pairs.csv) |
| Association-analysis notebook | Complete | [`notebooks/02_association_rules.ipynb`](../notebooks/02_association_rules.ipynb) |
| Oracle DDL and constraints | Complete | [`sql/02_create_tables.sql`](../sql/02_create_tables.sql), [`sql/03_create_constraints_indexes.sql`](../sql/03_create_constraints_indexes.sql) |
| Oracle staging load | Complete | [`sql/04_load_staging.sql`](../sql/04_load_staging.sql), [`sql/stg_transaction_line.ctl`](../sql/stg_transaction_line.ctl) |
| Oracle transform and pair query | Complete | [`sql/05_transform_clean.sql`](../sql/05_transform_clean.sql), [`sql/06_pair_queries.sql`](../sql/06_pair_queries.sql) |
| Oracle analytical views | Complete | [`sql/07_create_views.sql`](../sql/07_create_views.sql) |
| SQL/Python reconciliation execution | Pending | [`reports/sql_python_reconciliation.md`](sql_python_reconciliation.md); Oracle client/database unavailable |
| Power BI `.pbix` | Pending | [`powerbi/market_basket_analysis.pbix.NOT_CREATED.md`](../powerbi/market_basket_analysis.pbix.NOT_CREATED.md) |
| Power BI implementation package | Complete | [`powerbi/README.md`](../powerbi/README.md), [`powerbi/dax_measures.dax`](../powerbi/dax_measures.dax) |
| Data-quality report | Complete | [`reports/data_quality_report.md`](../reports/data_quality_report.md) |
| Insights summary | Complete | [`reports/insights_summary.md`](../reports/insights_summary.md) |
| Automated QA | Complete | `python -m pytest -q` → 5 passed |
| Demo MP4 | Pending | Recording package exists; no recorder available |
| Demo recording package | Complete | [`demo/demo_script.md`](../demo/demo_script.md), [`demo/demo_storyboard.md`](../demo/demo_storyboard.md), [`demo/recording_checklist.md`](../demo/recording_checklist.md) |
| Git repository initialized | Complete | Local `.git/`, branch `main`, no remote |
| Initial Git commit | Complete | Current `HEAD` — `Complete reproducible market basket analysis project` |
| GitHub remote/push | Not applicable | No remote URL or push authorization was provided |

## Verified facts

- Python cleaning rerun: 541,909 raw rows, 522,537 retained lines, 19,773 baskets, 3,798 products, 517,287 presence rows.
- Python analysis rerun: 347,481 qualifying pairs.
- Unit tests: 5 passed.
- Formula/grain checks: passed; no duplicate basket-item presence rows or symmetric pair keys.

## Remaining manual steps

1. Provide an Oracle 19c/Free/XE environment and SQL*Plus/SQLcl plus SQL*Loader; execute the documented runbook and rerun reconciliation.
2. Build/save `powerbi/market_basket_analysis.pbix` in Power BI Desktop using the supplied M/DAX/model package.
3. Record `demo/market_basket_analysis_demo.mp4` using the supplied script and checklist.
4. If desired, add a GitHub remote and push the local `main` branch; no remote URL or push authorization was supplied.
