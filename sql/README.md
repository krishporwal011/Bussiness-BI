# Oracle SQL implementation

## Version assumptions

The scripts target Oracle Database 19c-compatible SQL and use identity columns, `VARCHAR2`, `TIMESTAMP`, common table expressions, analytic `ROW_NUMBER()`, `COUNT(DISTINCT ...)`, and `CREATE OR REPLACE VIEW`. Run them in a dedicated analytical schema or a disposable development schema. The scripts do not create users or credentials.

Required environment for validation:

- Oracle Database 19c, Oracle XE/Free with compatible SQL, or an approved Oracle service.
- A schema with `CREATE TABLE`, `CREATE VIEW`, `CREATE SEQUENCE`, and index privileges.
- SQL*Plus or SQLcl plus `sqlldr` on the client machine.
- The project raw workbook and the regenerated `data/derived/sql_staging.csv`.
- A writable local `oracle_exports/` directory for the query export; this directory is ignored by Git.

Safe availability checks are `sqlplus -V`, `sqlldr -version`, and an Oracle connection test. Supply credentials interactively or through an Oracle wallet; never place passwords in the repository or command history.

## Execution order

From SQL*Plus or SQLcl, in the target schema:

1. `@sql/01_create_schema.sql`
2. `@sql/02_create_tables.sql`
3. Load `data/derived/sql_staging.csv` using `@sql/04_load_staging.sql` and `sql/stg_transaction_line.ctl`.
4. `@sql/05_transform_clean.sql`
5. `@sql/03_create_constraints_indexes.sql` (for large loads, create non-constraint indexes after loading).
6. `@sql/07_create_views.sql`
7. `@sql/06_pair_queries.sql`
8. `@sql/08_validation_reconciliation.sql`

The default configuration is `MIN_ITEM_FREQUENCY=5`, `MIN_PAIR_COUNT=20`, `MIN_SUPPORT=0.001`, `MIN_CONFIDENCE=0`, and `TOP_N=10`. Update `MB_CONFIG` and `config/analysis_config.json` together when changing thresholds.

## Loading

The Python cleaning step creates a normalized CSV with explicit flags and a source-row number. `sqlldr` loads it as text/numeric staging data. Example:

```bash
sqlldr userid=<user>/<password>@<service> \
  control=sql/stg_transaction_line.ctl \
  data=data/derived/sql_staging.csv \
  log=oracle_staging_load.log direct=true
```

Do not commit credentials. Use an Oracle wallet, environment-managed secret, or a local SQL*Loader parameter file outside Git.

## Pair query design

`FACT_BASKET_ITEM` has a composite primary key, but `06_pair_queries.sql` still begins with `SELECT DISTINCT` to make the pair logic robust to a future source or view change. The self-join matches basket IDs and applies `a.item_key < b.item_key`, which produces one unordered pair. Pair counts use distinct baskets. Thresholds are applied after metrics are calculated, and the basket denominator comes from `FACT_TRANSACTION`, so single-item baskets remain eligible.

## Validation checklist

1. Confirm `sqlplus`/SQLcl and `sqlldr` versions and connect to a disposable Oracle schema.
2. Run the Python cleaning and analysis commands from the root so staging and reference outputs are current.
3. Run `@sql/01_create_schema.sql` and `@sql/02_create_tables.sql` in a fresh schema.
4. Run `@sql/04_load_staging.sql`; confirm the staging row count is 541,909 for the current UCI workbook.
5. Run `@sql/05_transform_clean.sql`; confirm the fact basket and basket-item counts against `data/cleaned/data_quality_summary.csv`.
6. Run `@sql/03_create_constraints_indexes.sql` and `@sql/07_create_views.sql`.
7. Run `@sql/06_pair_queries.sql` and export the CSV with SQLcl `SET SQLFORMAT csv` or equivalent.
8. Run `@sql/08_validation_reconciliation.sql` and `python src/reconcile_sql_python.py --python outputs/python_pair_metrics.csv --sql oracle_exports/oracle_pair_metrics.csv`.
9. Accept only a report with zero missing/extra/mismatched pairs, exact integer equality, and floating differences no greater than `1e-9`.

## Reconciliation

Oracle export is intentionally a separate step because no Oracle client/database was available in the build environment. `reports/sql_python_reconciliation.md` is therefore marked **PENDING**, not PASS. After exporting the Oracle query result, run the reconciliation command in `08_validation_reconciliation.sql`; it compares pair keys, all integer counts, support, both directional confidences, and lift with a documented `1e-9` floating-point tolerance.

