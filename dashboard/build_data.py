#!/usr/bin/env python3
"""Build the small, browser-friendly data bundle used by the GitHub Pages dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "dashboard" / "data"


def json_records(path: Path, limit: int | None = None) -> list[dict]:
    frame = pd.read_csv(path)
    if limit is not None:
        frame = frame.head(limit)
    return json.loads(frame.to_json(orient="records"))


def quality_metrics() -> dict[str, int | float]:
    path = ROOT / "data" / "cleaned" / "data_quality_summary.csv"
    frame = pd.read_csv(path)
    return {
        str(row.metric): row.value.item() if hasattr(row.value, "item") else row.value
        for row in frame.itertuples(index=False)
    }


def reconciliation_metrics() -> dict[str, int | str]:
    path = ROOT / "reports" / "sql_python_reconciliation.csv"
    if not path.exists():
        return {"status": "PENDING", "matching_pairs": 0, "failed_pairs": 0}
    frame = pd.read_csv(path, low_memory=False)
    statuses = frame["status"].value_counts().to_dict()
    failed = sum(value for key, value in statuses.items() if key != "MATCH")
    matching = int(statuses.get("MATCH", 0))
    return {
        "status": "PASS" if failed == 0 and matching else "FAIL",
        "matching_pairs": matching,
        "failed_pairs": int(failed),
    }


def main() -> None:
    config = json.loads((ROOT / "config" / "analysis_config.json").read_text(encoding="utf-8"))
    quality = quality_metrics()
    pair_rows = json_records(ROOT / "outputs" / "python_pair_metrics.csv")
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "UCI Online Retail",
        "thresholds": config,
        "kpis": {
            "raw_rows": quality.get("raw_rows", 0),
            "retained_clean_lines": quality.get("retained_clean_lines", 0),
            "baskets": quality.get("distinct_baskets", 0),
            "products": quality.get("distinct_products", 0),
            "presence_rows": quality.get("distinct_basket_item_presence_rows", 0),
            "single_item_baskets": quality.get("single_item_baskets", 0),
            "qualifying_pairs": len(pair_rows),
        },
        "reconciliation": reconciliation_metrics(),
        "count_pairs": json_records(ROOT / "outputs" / "python_top_10_pairs.csv"),
        "lift_pairs": json_records(ROOT / "outputs" / "python_lift_top_10_pairs.csv"),
        "item_frequency": json_records(ROOT / "outputs" / "python_item_frequency.csv", limit=40),
        "rare_item_impact": json_records(ROOT / "outputs" / "rare_item_impact.csv"),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "dashboard_data.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {DATA_DIR / 'dashboard_data.json'}")


if __name__ == "__main__":
    main()
