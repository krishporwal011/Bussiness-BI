#!/usr/bin/env python3
"""Compare Oracle-exported pair metrics with the transparent Python output."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


KEY_COLUMNS = ["item_a_key", "item_b_key"]
COMPARE_COLUMNS = [
    "pair_count", "basket_count", "item_a_basket_count", "item_b_basket_count",
    "support", "confidence_a_to_b", "confidence_b_to_a", "lift",
]
FLOAT_COLUMNS = {"support", "confidence_a_to_b", "confidence_b_to_a", "lift"}


def _read(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    for col in KEY_COLUMNS:
        frame[col] = frame[col].astype("string").str.strip().str.upper()
    return frame.set_index(KEY_COLUMNS, drop=False)


def reconcile(python_path: Path, sql_path: Path | None, report_csv: Path, report_md: Path, tolerance: float = 1e-9) -> int:
    report_csv.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    if sql_path is None or not sql_path.exists():
        pending = pd.DataFrame([{
            "status": "PENDING",
            "reason": "Oracle export not supplied; sqlplus/sqlcl was not available in the build environment.",
            "python_file": str(python_path),
            "sql_file": str(sql_path) if sql_path else "",
        }])
        pending.to_csv(report_csv, index=False)
        report_md.write_text(
            "# SQL/Python reconciliation\n\n"
            "**Status: PENDING.** No Oracle export was available in the build environment, so this project does not claim a database execution result.\n\n"
            f"The Python reference file is `{python_path}`. Run `sql/06_pair_queries.sql` in the target Oracle schema, export the result with the documented column names, and rerun:\n\n"
            f"```bash\npython src/reconcile_sql_python.py --python {python_path} --sql path/to/oracle_pair_metrics.csv\n```\n\n"
            "Acceptance criteria: exact equality for integer counts and absolute difference <= 1e-9 for support, both directional confidences, and lift. Missing, extra, or mismatched pairs cause a non-zero exit code.\n",
            encoding="utf-8",
        )
        return 0

    py = _read(python_path)
    sql = _read(sql_path)
    rows = []
    for key in sorted(set(py.index) | set(sql.index)):
        py_row = py.loc[key] if key in py.index else None
        sql_row = sql.loc[key] if key in sql.index else None
        if py_row is None:
            rows.append({"item_a_key": key[0], "item_b_key": key[1], "status": "EXTRA_IN_SQL"})
            continue
        if sql_row is None:
            rows.append({"item_a_key": key[0], "item_b_key": key[1], "status": "MISSING_IN_SQL"})
            continue
        result = {"item_a_key": key[0], "item_b_key": key[1], "status": "MATCH"}
        for col in COMPARE_COLUMNS:
            left = float(py_row[col])
            right = float(sql_row[col])
            result[f"python_{col}"] = left
            result[f"sql_{col}"] = right
            if col in FLOAT_COLUMNS:
                equal = abs(left - right) <= tolerance
            else:
                equal = int(left) == int(right)
            if not equal:
                result["status"] = "MISMATCH"
        rows.append(result)
    report = pd.DataFrame(rows)
    report.to_csv(report_csv, index=False)
    failed = int((report["status"] != "MATCH").sum())
    report_md.write_text(
        "# SQL/Python reconciliation\n\n"
        f"Compared `{len(report)}` pair keys with float tolerance `{tolerance}`.\n\n"
        f"- Matching pairs: `{len(report) - failed}`\n"
        f"- Failed pairs: `{failed}`\n"
        f"- Acceptance: {'PASS' if failed == 0 else 'FAIL'}\n\n"
        "See `sql_python_reconciliation.csv` for per-pair values and missing/extra keys.\n",
        encoding="utf-8",
    )
    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", dest="python_path", type=Path, default=Path("outputs/python_pair_metrics.csv"))
    parser.add_argument("--sql", dest="sql_path", type=Path)
    parser.add_argument("--report-csv", type=Path, default=Path("reports/sql_python_reconciliation.csv"))
    parser.add_argument("--report-md", type=Path, default=Path("reports/sql_python_reconciliation.md"))
    parser.add_argument("--tolerance", type=float, default=1e-9)
    args = parser.parse_args()
    raise SystemExit(reconcile(args.python_path, args.sql_path, args.report_csv, args.report_md, args.tolerance))


if __name__ == "__main__":
    main()
