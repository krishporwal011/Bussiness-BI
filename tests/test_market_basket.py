import pandas as pd

from src.market_basket_analysis import compute_pair_metrics
from src.reconcile_sql_python import reconcile


def test_pair_counts_deduplicate_items_within_a_basket():
    presence = pd.DataFrame(
        [
            {"basket_id": "1", "item_key": "A", "item_name": "A"},
            {"basket_id": "1", "item_key": "A", "item_name": "A"},
            {"basket_id": "1", "item_key": "B", "item_name": "B"},
            {"basket_id": "2", "item_key": "A", "item_name": "A"},
            {"basket_id": "2", "item_key": "B", "item_name": "B"},
            {"basket_id": "3", "item_key": "A", "item_name": "A"},
        ]
    ).drop_duplicates(["basket_id", "item_key"])
    config = {"min_item_frequency": 1, "min_pair_count": 1, "min_support": 0, "min_confidence": 0, "top_n": 10}
    pairs, _, _ = compute_pair_metrics(presence, basket_count=3, config=config)
    row = pairs.iloc[0]
    assert row["item_a_key"] == "A"
    assert row["item_b_key"] == "B"
    assert row["pair_count"] == 2
    assert abs(row["support"] - (2 / 3)) < 1e-12
    assert abs(row["confidence_a_to_b"] - (2 / 3)) < 1e-12
    assert abs(row["confidence_b_to_a"] - 1.0) < 1e-12
    assert abs(row["lift"] - 1.0) < 1e-12


def test_single_item_basket_stays_in_support_denominator():
    presence = pd.DataFrame(
        [
            {"basket_id": "1", "item_key": "A", "item_name": "A"},
            {"basket_id": "2", "item_key": "A", "item_name": "A"},
            {"basket_id": "2", "item_key": "B", "item_name": "B"},
        ]
    )
    config = {"min_item_frequency": 1, "min_pair_count": 1, "min_support": 0, "min_confidence": 0, "top_n": 10}
    pairs, _, _ = compute_pair_metrics(presence, basket_count=2, config=config)
    assert pairs.iloc[0]["pair_count"] == 1
    assert abs(pairs.iloc[0]["support"] - 0.5) < 1e-12


def test_pair_ordering_and_threshold_filters_are_deterministic():
    presence = pd.DataFrame(
        [
            {"basket_id": "1", "item_key": "B", "item_name": "B"},
            {"basket_id": "1", "item_key": "A", "item_name": "A"},
            {"basket_id": "1", "item_key": "C", "item_name": "C"},
            {"basket_id": "2", "item_key": "B", "item_name": "B"},
            {"basket_id": "2", "item_key": "A", "item_name": "A"},
            {"basket_id": "3", "item_key": "A", "item_name": "A"},
        ]
    )
    config = {"min_item_frequency": 2, "min_pair_count": 1, "min_support": 0, "min_confidence": 0, "top_n": 10}
    pairs, _, impact = compute_pair_metrics(presence, basket_count=3, config=config)
    assert set(zip(pairs["item_a_key"], pairs["item_b_key"])) == {("A", "B")}
    assert (pairs["item_a_key"] < pairs["item_b_key"]).all()
    assert int(impact.loc[impact["population"] == "items_with_basket_count_ge_2", "item_count"].iloc[0]) == 2


def test_output_pairs_are_nonnegative_integer_counts_without_reverse_duplicates():
    presence = pd.DataFrame(
        [
            {"basket_id": "1", "item_key": "A", "item_name": "A"},
            {"basket_id": "1", "item_key": "B", "item_name": "B"},
            {"basket_id": "1", "item_key": "C", "item_name": "C"},
            {"basket_id": "2", "item_key": "A", "item_name": "A"},
            {"basket_id": "2", "item_key": "C", "item_name": "C"},
        ]
    )
    config = {"min_item_frequency": 1, "min_pair_count": 1, "min_support": 0, "min_confidence": 0, "top_n": 10}
    pairs, _, _ = compute_pair_metrics(presence, basket_count=2, config=config)
    assert (pairs["pair_count"] >= 0).all()
    assert (pairs["pair_count"] == pairs["pair_count"].astype(int)).all()
    keys = set(zip(pairs["item_a_key"], pairs["item_b_key"]))
    assert keys.isdisjoint({(b, a) for a, b in keys})


def test_reconciliation_fails_on_a_metric_mismatch(tmp_path):
    columns = [
        "item_a_key", "item_a_name", "item_b_key", "item_b_name", "pair_count",
        "basket_count", "item_a_basket_count", "item_b_basket_count", "support",
        "confidence_a_to_b", "confidence_b_to_a", "lift", "rank",
    ]
    row = ["A", "A", "B", "B", 2, 3, 3, 2, 2 / 3, 2 / 3, 1.0, 1.0, 1]
    py_path = tmp_path / "python.csv"
    sql_path = tmp_path / "sql.csv"
    report_csv = tmp_path / "reconciliation.csv"
    report_md = tmp_path / "reconciliation.md"
    pd.DataFrame([row], columns=columns).to_csv(py_path, index=False)
    mismatched = row.copy()
    mismatched[4] = 1
    pd.DataFrame([mismatched], columns=columns).to_csv(sql_path, index=False)
    exit_code = reconcile(py_path, sql_path, report_csv, report_md)
    assert exit_code == 1
    assert pd.read_csv(report_csv).iloc[0]["status"] == "MISMATCH"

