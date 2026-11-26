#!/usr/bin/env python3
"""Compute transparent unordered pair metrics from basket-item presence."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

import pandas as pd


PAIR_COLUMNS = [
    "item_a_key", "item_a_name", "item_b_key", "item_b_name", "pair_count",
    "basket_count", "item_a_basket_count", "item_b_basket_count", "support",
    "confidence_a_to_b", "confidence_b_to_a", "lift", "rank",
]


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def compute_pair_metrics(presence: pd.DataFrame, basket_count: int, config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    item_counts = presence.groupby("item_key")["basket_id"].nunique().rename("item_basket_count")
    min_item_frequency = int(config.get("min_item_frequency", 1))
    eligible_items = set(item_counts[item_counts >= min_item_frequency].index)
    filtered = presence[presence["item_key"].isin(eligible_items)].copy()
    names = presence.drop_duplicates("item_key").set_index("item_key")["item_name"].to_dict()

    pair_counts: Counter[tuple[str, str]] = Counter()
    for _, group in filtered.groupby("basket_id", sort=False):
        items = sorted(set(group["item_key"].dropna()))
        pair_counts.update(itertools.combinations(items, 2))

    rows = []
    for (item_a, item_b), pair_count in pair_counts.items():
        a_count = int(item_counts[item_a])
        b_count = int(item_counts[item_b])
        support = pair_count / basket_count if basket_count else 0.0
        confidence_a_to_b = pair_count / a_count if a_count else 0.0
        confidence_b_to_a = pair_count / b_count if b_count else 0.0
        lift = support / ((a_count / basket_count) * (b_count / basket_count)) if basket_count and a_count and b_count else 0.0
        rows.append({
            "item_a_key": item_a,
            "item_a_name": names.get(item_a, item_a),
            "item_b_key": item_b,
            "item_b_name": names.get(item_b, item_b),
            "pair_count": int(pair_count),
            "basket_count": int(basket_count),
            "item_a_basket_count": a_count,
            "item_b_basket_count": b_count,
            "support": support,
            "confidence_a_to_b": confidence_a_to_b,
            "confidence_b_to_a": confidence_b_to_a,
            "lift": lift,
        })

    if not rows:
        empty = pd.DataFrame(columns=PAIR_COLUMNS)
        return empty, pd.DataFrame(columns=["item_key", "item_name", "basket_count"]), pd.DataFrame()

    all_pairs = pd.DataFrame(rows)
    min_pair_count = int(config.get("min_pair_count", 1))
    min_support = float(config.get("min_support", 0.0))
    min_confidence = float(config.get("min_confidence", 0.0))
    qualifying = all_pairs[
        (all_pairs["pair_count"] >= min_pair_count)
        & (all_pairs["support"] >= min_support)
        & (all_pairs["confidence_a_to_b"] >= min_confidence)
        & (all_pairs["confidence_b_to_a"] >= min_confidence)
    ].copy()
    qualifying = qualifying.sort_values(
        ["pair_count", "lift", "item_a_name", "item_b_name"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    qualifying["rank"] = qualifying.index + 1

    lift_ranked = qualifying.sort_values(
        ["lift", "pair_count", "item_a_name", "item_b_name"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    lift_ranked["rank"] = lift_ranked.index + 1

    item_frequency = (
        presence.groupby("item_key", as_index=False)
        .agg(item_name=("item_name", "first"), basket_count=("basket_id", "nunique"))
        .sort_values(["basket_count", "item_key"], ascending=[False, True])
    )
    impact = pd.DataFrame([
        {"population": "all_cleaned_items", "item_count": int(item_counts.size), "basket_item_rows": int(len(presence)), "pair_count_rows": int(len(all_pairs))},
        {"population": f"items_with_basket_count_ge_{min_item_frequency}", "item_count": int(len(eligible_items)), "basket_item_rows": int(len(filtered)), "pair_count_rows": int(len(qualifying))},
    ])
    return qualifying[PAIR_COLUMNS], item_frequency, impact


def run(presence_path: Path, basket_path: Path, output_dir: Path, config_path: Path) -> dict:
    config = load_config(config_path)
    presence = pd.read_csv(presence_path, parse_dates=["transaction_date"])
    baskets = pd.read_csv(basket_path, parse_dates=["transaction_date"])
    metrics, item_frequency, impact = compute_pair_metrics(presence, len(baskets), config)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Keep enough precision for the documented 1e-9 SQL/Python reconciliation
    # tolerance, especially for high-lift rare pairs.
    metrics.to_csv(output_dir / "python_pair_metrics.csv", index=False, float_format="%.15g")
    top_n = int(config.get("top_n", 10))
    metrics.head(top_n).to_csv(output_dir / "python_top_10_pairs.csv", index=False, float_format="%.15g")
    metrics.sort_values(["lift", "pair_count", "item_a_name", "item_b_name"], ascending=[False, False, True, True], kind="mergesort").head(top_n).assign(rank=lambda df: range(1, len(df) + 1)).to_csv(output_dir / "python_lift_top_10_pairs.csv", index=False, float_format="%.15g")
    item_frequency.to_csv(output_dir / "python_item_frequency.csv", index=False)
    impact.to_csv(output_dir / "rare_item_impact.csv", index=False)
    (output_dir / "python_analysis_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    result = {
        "basket_count": int(len(baskets)),
        "pair_rows": int(len(metrics)),
        "top_n": int(min(top_n, len(metrics))),
        "min_item_frequency": int(config.get("min_item_frequency", 1)),
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--presence", type=Path, default=Path("data/cleaned/basket_item_presence.csv"))
    parser.add_argument("--baskets", type=Path, default=Path("data/cleaned/basket_summary.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--config", type=Path, default=Path("config/analysis_config.json"))
    args = parser.parse_args()
    run(args.presence, args.baskets, args.output_dir, args.config)


if __name__ == "__main__":
    main()
