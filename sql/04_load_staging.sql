-- Load normalized staging CSV produced by src/clean_data.py.
-- The command below is executed by SQL*Plus/SQLcl through HOST; it is not a
-- SQL statement and requires sqlldr on the client machine.

TRUNCATE TABLE stg_transaction_line;

-- From the project root, after updating the Oracle connect identifier:
-- HOST sqlldr userid=<user>@<service> control=sql/stg_transaction_line.ctl data=data/derived/sql_staging.csv log=oracle_staging_load.log direct=true

-- Verify the load before transforming:
SELECT COUNT(*) AS staging_rows,
       SUM(CASE WHEN is_retained = 1 THEN 1 ELSE 0 END) AS flagged_retained_rows,
       MIN(source_row_number) AS first_source_row,
       MAX(source_row_number) AS last_source_row
FROM stg_transaction_line;

