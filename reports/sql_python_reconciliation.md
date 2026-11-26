# SQL/Python reconciliation

**Status: PENDING.** No Oracle export was available in the build environment, so this project does not claim a database execution result.

The Python reference file is `outputs/python_pair_metrics.csv`. Run `sql/06_pair_queries.sql` in the target Oracle schema, export the result with the documented column names, and rerun:

```bash
python src/reconcile_sql_python.py --python outputs/python_pair_metrics.csv --sql path/to/oracle_pair_metrics.csv
```

Acceptance criteria: exact equality for integer counts and absolute difference <= 1e-9 for support, both directional confidences, and lift. Missing, extra, or mismatched pairs cause a non-zero exit code.
