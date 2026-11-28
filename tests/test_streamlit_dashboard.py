"""Tests for the Streamlit dashboard (streamlit_app/).

Data-layer tests need only pandas/openpyxl. UI tests use Streamlit's AppTest and are
skipped automatically if streamlit/plotly are not installed (install
streamlit_app/requirements.txt to run them).
"""
import importlib
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "streamlit_app"
sys.path.insert(0, str(APP_DIR))
md = importlib.import_module("mba_data")

needs_full_pairs = pytest.mark.skipif(not md.PAIR_FULL_CSV.exists(), reason="full pair CSV not present")
needs_workbook = pytest.mark.skipif(not md.WORKBOOK.exists(), reason="dashboard workbook not present")

PAGES = [
    "Executive Overview", "Transaction & Basket KPIs", "Product Analysis", "Top 10 Frequent Item Pairs",
    "Top 10 Pairs by Lift", "Support & Confidence", "Interactive Pair Analysis", "Data Quality Overview",
]


@pytest.fixture(scope="module")
def pairs():
    loaded = md.load_pairs()
    assert loaded.ok
    return loaded.data


# ----------------------------- data layer ---------------------------------- #
@needs_full_pairs
def test_full_pair_table_matches_documented_counts(pairs):
    assert len(pairs) == 347_481
    assert pairs["basket_count"].eq(19_773).all()


@needs_full_pairs
def test_top10_by_count_matches_official_output(pairs):
    official = pd.read_csv(md.PAIR_TOP_COUNT_CSV, dtype=md.PAIR_DTYPES)
    top = md.top_by_count(pairs, 10)
    assert list(top["item_a_key"]) == list(official["item_a_key"])
    assert list(top["item_b_key"]) == list(official["item_b_key"])
    assert list(top["pair_count"]) == list(official["pair_count"])
    assert top["lift"].to_numpy() == pytest.approx(official["lift"].to_numpy(), abs=1e-9)


@needs_full_pairs
def test_top10_by_lift_matches_official_output(pairs):
    official = pd.read_csv(md.PAIR_TOP_LIFT_CSV, dtype=md.PAIR_DTYPES)
    top = md.top_by_lift(pairs, 10)
    assert list(top["item_a_key"]) == list(official["item_a_key"])
    assert list(top["item_b_key"]) == list(official["item_b_key"])
    assert top["lift"].to_numpy() == pytest.approx(official["lift"].to_numpy(), abs=1e-9)


@needs_full_pairs
def test_integrity_checks_all_pass(pairs):
    chk = md.integrity_checks(pairs, md.kpi_dict(md.load_kpis()))
    assert len(chk) >= 7
    assert (chk["result"] == "PASS").all(), chk[chk["result"] != "PASS"]


@needs_workbook
def test_kpis_match_report_and_json():
    k = md.kpi_dict(md.load_kpis())
    assert (k["raw_rows"], k["retained_clean_lines"], k["distinct_baskets"], k["distinct_products"]) == (541_909, 522_537, 19_773, 3_798)
    assert (k["presence_rows"], k["single_item_baskets"], k["qualifying_pairs"]) == (517_287, 1_500, 347_481)
    js = md._read_json(md.DASHBOARD_JSON)["kpis"]
    assert js["baskets"] == k["distinct_baskets"] and js["qualifying_pairs"] == k["qualifying_pairs"]
    assert k["average_basket_size"] == pytest.approx(k["presence_rows"] / k["distinct_baskets"])
    assert k["single_item_basket_pct"] == pytest.approx(1500 / 19773)


@needs_workbook
def test_basket_summary_reconciles_with_kpis():
    b = md.load_baskets().data
    k = md.kpi_dict(md.load_kpis())
    assert len(b) == k["distinct_baskets"]
    assert b["distinct_item_count"].sum() == k["presence_rows"]
    assert int(b["is_single_item"].sum()) == k["single_item_baskets"]
    assert b["distinct_item_count"].mean() == pytest.approx(k["average_basket_size"])


@needs_full_pairs
def test_product_frequencies_agree_with_pairs(pairs):
    prod = md.load_products(19_773).data
    assert len(prod) == 3_798
    freq = dict(zip(prod["item_key"], prod["basket_count"]))
    sample = pairs.head(2000)
    assert all(freq[k] == c for k, c in zip(sample["item_a_key"], sample["item_a_basket_count"]))
    assert all(freq[k] == c for k, c in zip(sample["item_b_key"], sample["item_b_basket_count"]))
    assert int((~prod["is_rare"]).sum()) == 3_406


def test_filters_threshold_product_query_and_empty(pairs):
    assert len(md.filter_pairs(pairs)) == len(pairs)
    hi = md.filter_pairs(pairs, min_pair_count=300)
    assert len(hi) and (hi["pair_count"] >= 300).all()
    assert (md.filter_pairs(pairs, min_lift=50)["lift"] >= 50).all()
    assert (md.filter_pairs(pairs, min_support=0.02)["support"] >= 0.02).all()
    both = md.filter_pairs(pairs, min_confidence=0.5)
    assert ((both["confidence_a_to_b"] >= 0.5) & (both["confidence_b_to_a"] >= 0.5)).all()
    prod = md.filter_pairs(pairs, products=["85099B"])
    assert len(prod) and ((prod["item_a_key"] == "85099B") | (prod["item_b_key"] == "85099B")).all()
    q = md.filter_pairs(pairs, query="jumbo bag red retrospot")
    assert len(q) and q.apply(lambda r: "jumbo bag red retrospot" in f"{r.item_a_name} + {r.item_b_name}".lower(), axis=1).all()
    assert md.filter_pairs(pairs, min_pair_count=10**9).empty            # empty result is handled
    assert md.filter_pairs(pairs, query="zzz-no-such-product").empty
    assert md.filter_pairs(pairs.iloc[0:0]).empty                         # empty input is handled
    two = md.filter_pairs(pairs, products=["22386", "85099B"], both_products=True)
    assert len(two) == 1


def test_anchor_partners_swaps_directional_confidence(pairs):
    row = pairs[(pairs["item_a_key"] == "22386") & (pairs["item_b_key"] == "85099B")].iloc[0]
    as_a = md.anchor_partners(pairs, "22386").set_index("partner_key").loc["85099B"]
    as_b = md.anchor_partners(pairs, "85099B").set_index("partner_key").loc["22386"]
    assert as_a["confidence_anchor_to_partner"] == pytest.approx(row["confidence_a_to_b"])
    assert as_b["confidence_anchor_to_partner"] == pytest.approx(row["confidence_b_to_a"])
    assert as_a["pair_count"] == as_b["pair_count"] == row["pair_count"]


def test_contingency_and_expected_count_identities(pairs):
    row = pairs.iloc[0]
    c = md.contingency(row)
    assert sum(c.values()) == row["basket_count"] and min(c.values()) >= 0
    assert row["pair_count"] / md.expected_pair_count(row) == pytest.approx(row["lift"], rel=1e-9)


def test_histogram_handles_edge_cases():
    assert md.histogram(pd.Series([], dtype=float)).empty
    assert md.histogram(pd.Series([2.0, 2.0, 2.0]), log=True)["count"].sum() == 3
    assert md.histogram(pd.Series([0.1, 1, 10, 100]), 4, log=True)["count"].sum() == 4


# ----------------------- missing / ignored generated files ----------------- #
def _patch(monkeypatch, **paths):
    for name, value in paths.items():
        monkeypatch.setattr(md, name, value)


@needs_workbook
def test_falls_back_to_workbook_when_full_csv_missing(monkeypatch, tmp_path):
    _patch(monkeypatch, PAIR_FULL_CSV=tmp_path / "nope.csv")
    loaded = md.load_pairs()
    assert loaded.ok and len(loaded.data) == 200 and loaded.notes


def test_falls_back_to_top10_csvs_when_workbook_and_full_csv_missing(monkeypatch, tmp_path):
    _patch(monkeypatch, PAIR_FULL_CSV=tmp_path / "a.csv", WORKBOOK=tmp_path / "b.xlsx")
    loaded = md.load_pairs()
    assert loaded.ok and 10 < len(loaded.data) <= 20


def test_everything_missing_is_reported_not_raised(monkeypatch, tmp_path):
    _patch(monkeypatch, PAIR_FULL_CSV=tmp_path / "a.csv", WORKBOOK=tmp_path / "b.xlsx",
           PAIR_TOP_COUNT_CSV=tmp_path / "c.csv", PAIR_TOP_LIFT_CSV=tmp_path / "d.csv",
           ITEM_FREQ_CSV=tmp_path / "e.csv", DASHBOARD_JSON=tmp_path / "f.json", RARE_IMPACT_CSV=tmp_path / "g.csv")
    assert not md.load_pairs().ok
    assert not md.load_products().ok
    assert not md.load_baskets().ok
    assert md.kpi_dict(md.load_kpis()) == {}
    assert not md.load_rare_impact().ok and not md.load_reconciliation().ok


def test_kpis_fall_back_to_dashboard_json(monkeypatch, tmp_path):
    _patch(monkeypatch, WORKBOOK=tmp_path / "missing.xlsx")
    k = md.kpi_dict(md.load_kpis())
    assert k["distinct_baskets"] == 19_773 and k["reconciliation_status"] == "PASS"


# ------------------------------ deployment safety -------------------------- #
def test_no_absolute_or_oracle_powerbi_dependencies_in_app_code():
    for f in APP_DIR.glob("*.py"):
        src = f.read_text(encoding="utf-8")
        assert not re.search(r"""["'](/Users/|/home/|[A-Za-z]:\\)""", src), f"absolute path in {f.name}"
        assert not re.search(r"^\s*(import|from)\s+(cx_Oracle|oracledb|msal|powerbi)", src, re.M), f.name
        assert "powerbi.com" not in src


def test_dedicated_requirements_are_minimal():
    req = "\n".join(l for l in (APP_DIR / "requirements.txt").read_text().lower().splitlines() if not l.strip().startswith("#"))
    for needed in ("streamlit", "plotly", "pandas", "openpyxl", "numpy"):
        assert needed in req
    for forbidden in ("jupyter", "pytest", "oracle", "nbformat"):
        assert forbidden not in req


def test_tracked_data_needed_by_app_is_not_git_ignored():
    """Every file the app reads must be committable: python_pair_metrics.csv / item_frequency are matched by
    .gitignore rules but are force-tracked; make sure the other inputs are not ignored at all."""
    ignore = (ROOT / ".gitignore").read_text()
    for must_not_be_ignored in ("powerbi/market_basket_dashboard_data.xlsx", "outputs/python_top_10_pairs.csv",
                                "outputs/rare_item_impact.csv", "dashboard/data/dashboard_data.json"):
        assert must_not_be_ignored not in ignore


# --------------------------------- UI (AppTest) ---------------------------- #
@pytest.fixture(scope="module")
def apptest():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=180)
    at.run()
    return at


def _goto(at, page):
    at.sidebar.radio(key="page").set_value(page)
    at.run()
    return at


@needs_full_pairs
def test_app_first_load_has_no_exception(apptest):
    assert not apptest.exception


@needs_full_pairs
@pytest.mark.parametrize("page", PAGES)
def test_each_page_renders_without_error(apptest, page):
    _goto(apptest, page)
    assert not apptest.exception, [e.value for e in apptest.exception]
    assert not apptest.error
    expected = {"Support & Confidence": "Support & Confidence Analysis"}.get(page, page)
    assert len(apptest.title) == 1 and apptest.title[0].value == expected


@needs_full_pairs
def test_overview_kpi_cards_match_files(apptest):
    _goto(apptest, "Executive Overview")
    vals = {m.label: m.value for m in apptest.metric}
    assert vals["Raw invoice lines"] == "541,909"
    assert vals["Retained lines"] == "522,537"
    assert vals["Baskets (invoices)"] == "19,773"
    assert vals["Products"] == "3,798"
    assert vals["Qualifying pairs"] == "347,481"
    assert vals["Oracle ↔ Python"] == "PASS"


@needs_full_pairs
def test_top10_pages_confirm_official_match_when_unfiltered(apptest):
    apptest.sidebar.button[0].click().run()   # Reset filters
    for page in ("Top 10 Frequent Item Pairs", "Top 10 Pairs by Lift"):
        _goto(apptest, page)
        assert any("Matches the committed pipeline output" in s.value for s in apptest.success)


@needs_full_pairs
def test_filters_change_results_and_empty_state_is_graceful(apptest):
    _goto(apptest, "Top 10 Frequent Item Pairs")
    apptest.session_state["f_count"] = 500
    apptest.run()
    assert not apptest.exception
    pairs_in_view = {m.label: m.value for m in apptest.metric}["Pairs in view"]
    assert int(pairs_in_view.replace(",", "")) < 347_481           # the slider really narrowed the data
    assert int(pairs_in_view.replace(",", "")) == int((md.load_pairs().data["pair_count"] >= 500).sum())
    # impossible filter combination -> warning, not a crash, on every pair page
    apptest.session_state["f_query"] = "zzz-no-such-product"
    for page in ("Top 10 Frequent Item Pairs", "Top 10 Pairs by Lift", "Support & Confidence", "Interactive Pair Analysis"):
        _goto(apptest, page)
        assert not apptest.exception, page
        assert any("No pairs match" in w.value for w in apptest.warning), page
    apptest.sidebar.button[0].click().run()
    assert not apptest.exception


@needs_full_pairs
def test_product_filter_applies_to_pair_pages(apptest):
    apptest.sidebar.button[0].click().run()
    apptest.session_state["f_products"] = ["85099B"]
    _goto(apptest, "Top 10 Frequent Item Pairs")
    assert not apptest.exception
    assert any("Filtered view" in i.value for i in apptest.info)
    apptest.sidebar.button[0].click().run()
