# SQL/Python reconciliation

**Status: PENDING.** Validation was rechecked on 2026-11-26. No Oracle Database, SQL*Plus, SQLcl, SQL*Loader, `oracledb`/`cx_Oracle` driver, Docker/Podman runtime, Oracle connection configuration, or accessible remote Oracle environment was available. This project does not claim a database execution result, and `outputs/oracle_pair_metrics.csv` was not fabricated.

The Python reference file is `outputs/python_pair_metrics.csv`. Run `sql/06_pair_queries.sql` in the target Oracle schema, export the result with the documented column names, and rerun:

```bash
python src/reconcile_sql_python.py --python outputs/python_pair_metrics.csv --sql path/to/oracle_pair_metrics.csv
```

Acceptance criteria: exact equality for integer counts and absolute difference <= 1e-9 for support, both directional confidences, and lift. Missing, extra, or mismatched pairs cause a non-zero exit code. The reconciler's mismatch behavior is covered by the automated test suite.
