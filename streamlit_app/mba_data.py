"""Data access and calculations for the Market Basket Analysis Streamlit dashboard.

This module only *reads* artefacts that already exist in the repository
(Python pipeline outputs, the Power BI dashboard workbook and the dashboard JSON
bundle). It never re-runs or alters the cleaning / association pipeline, and it
needs neither Oracle, Power BI, a Microsoft login nor the raw UCI workbook.

All paths are resolved relative to the repository root, so the same code works
locally and on Streamlit Community Cloud.

The module is deliberately free of Streamlit imports so it can be unit-tested.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Paths (relative to the repository root, never absolute)
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
REPORTS = ROOT / "reports"
CONFIG_JSON = ROOT / "config" / "analysis_config.json"
WORKBOOK = ROOT / "powerbi" / "market_basket_dashboard_data.xlsx"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "dashboard_data.json"

PAIR_FULL_CSV = OUTPUTS / "python_pair_metrics.csv"
PAIR_TOP_COUNT_CSV = OUTPUTS / "python_top_10_pairs.csv"
PAIR_TOP_LIFT_CSV = OUTPUTS / "python_lift_top_10_pairs.csv"
ITEM_FREQ_CSV = OUTPUTS / "python_item_frequency.csv"
RARE_IMPACT_CSV = OUTPUTS / "rare_item_impact.csv"

PAIR_COLUMNS = [
    "item_a_key", "item_a_name", "item_b_key", "item_b_name",
    "pair_count", "basket_count", "item_a_basket_count", "item_b_basket_count",
    "support", "confidence_a_to_b", "confidence_b_to_a", "lift", "rank",
]
PAIR_DTYPES = {"item_a_key": str, "item_b_key": str}

TIER_ORDER = ["1. Rare (<5)", "2. Low (5-49)", "3. Medium (50-249)", "4. High (250+)"]


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
@dataclass
class Loaded:
    """A loaded table plus a human-readable description of where it came from."""
    data: pd.DataFrame | None
    source: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.data is not None and len(self.data) > 0


def _read_sheet(sheet: str, **kwargs) -> pd.DataFrame | None:
    """Read one sheet of the dashboard workbook; None if workbook/sheet/openpyxl is missing."""
    if not WORKBOOK.exists():
        return None
    try:
        return pd.read_excel(WORKBOOK, sheet_name=sheet, **kwargs)
    except Exception:  # missing sheet, missing openpyxl, corrupt file ...
        return None


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_csv(path: Path, **kwargs) -> pd.DataFrame | None:
    try:
        if path.exists() and path.stat().st_size > 0:
            return pd.read_csv(path, **kwargs)
    except Exception:
        return None
    return None


def pair_label(df: pd.DataFrame) -> pd.Series:
    return df["item_a_name"].astype(str) + " + " + df["item_b_name"].astype(str)


def product_label(key: str, name: str) -> str:
    """Names are not unique across stock codes, so the key is always shown."""
    return f"{name} ({key})"


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    cfg = _read_json(CONFIG_JSON) or (_read_json(DASHBOARD_JSON) or {}).get("thresholds") or {}
    return cfg


def load_kpis() -> Loaded:
    """Headline KPIs. Preference: workbook ExecutiveKPI -> dashboard_data.json."""
    df = _read_sheet("ExecutiveKPI")
    if df is not None and len(df):
        return Loaded(df.iloc[0].to_dict(), "powerbi/market_basket_dashboard_data.xlsx (ExecutiveKPI)")  # type: ignore[arg-type]
    js = _read_json(DASHBOARD_JSON)
    if js and "kpis" in js:
        k = js["kpis"]
        out = {
            "raw_rows": k.get("raw_rows"),
            "retained_clean_lines": k.get("retained_clean_lines"),
            "distinct_baskets": k.get("baskets"),
            "distinct_products": k.get("products"),
            "presence_rows": k.get("presence_rows"),
            "single_item_baskets": k.get("single_item_baskets"),
            "qualifying_pairs": k.get("qualifying_pairs"),
        }
        if out["raw_rows"] and out["retained_clean_lines"]:
            out["removed_rows"] = out["raw_rows"] - out["retained_clean_lines"]
        if out["distinct_baskets"]:
            if out["single_item_baskets"] is not None:
                out["single_item_basket_pct"] = out["single_item_baskets"] / out["distinct_baskets"]
            if out["presence_rows"]:
                out["average_basket_size"] = out["presence_rows"] / out["distinct_baskets"]
        rec = js.get("reconciliation", {})
        out.update(matching_pairs=rec.get("matching_pairs"), failed_pairs=rec.get("failed_pairs"),
                   reconciliation_status=rec.get("status"))
        return Loaded(out, "dashboard/data/dashboard_data.json (fallback)")  # type: ignore[arg-type]
    return Loaded(None, "not found")


def kpi_dict(loaded: Loaded) -> dict:
    return loaded.data if isinstance(loaded.data, dict) else {}


def load_pairs() -> Loaded:
    """Association pairs.

    1. outputs/python_pair_metrics.csv  - the full 347k-row project output (preferred)
    2. workbook PairMetrics sheet        - 200-pair subset (reduced mode)
    3. the two committed top-10 CSVs     - 20 pairs (minimal mode)
    """
    df = _read_csv(PAIR_FULL_CSV, dtype=PAIR_DTYPES)
    if df is not None and set(PAIR_COLUMNS).issubset(df.columns):
        return Loaded(df[PAIR_COLUMNS].copy(), "outputs/python_pair_metrics.csv (full)")

    notes = ["outputs/python_pair_metrics.csv is missing or unreadable - showing a reduced pair set."]
    sheet = _read_sheet("PairMetrics", dtype={"item_a_key": str, "item_b_key": str})
    if sheet is not None and set(PAIR_COLUMNS).issubset(sheet.columns):
        return Loaded(sheet[PAIR_COLUMNS].copy(), "workbook PairMetrics sheet (reduced)", notes)

    parts = [
        _read_csv(p, dtype=PAIR_DTYPES) for p in (PAIR_TOP_COUNT_CSV, PAIR_TOP_LIFT_CSV)
    ]
    parts = [p[PAIR_COLUMNS] for p in parts if p is not None and set(PAIR_COLUMNS).issubset(p.columns)]
    if parts:
        merged = pd.concat(parts).drop_duplicates(["item_a_key", "item_b_key"]).reset_index(drop=True)
        return Loaded(merged, "top-10 CSV files (minimal)", notes)
    return Loaded(None, "not found", notes)


def load_official_top10() -> dict[str, pd.DataFrame | None]:
    """The committed top-10 outputs, used only to cross-check the dashboard."""
    return {
        "count": _read_csv(PAIR_TOP_COUNT_CSV, dtype=PAIR_DTYPES),
        "lift": _read_csv(PAIR_TOP_LIFT_CSV, dtype=PAIR_DTYPES),
    }


def load_products(basket_total: int | None = None, min_item_frequency: int = 5) -> Loaded:
    """One row per product with basket count (+ quantity / revenue / tier when available)."""
    freq = _read_csv(ITEM_FREQ_CSV, dtype={"item_key": str})
    dim = _read_sheet("DimProduct", dtype={"item_key": str})
    notes: list[str] = []

    if freq is not None and {"item_key", "item_name", "basket_count"}.issubset(freq.columns):
        base, source = freq[["item_key", "item_name", "basket_count"]].copy(), "outputs/python_item_frequency.csv"
    elif dim is not None:
        base, source = dim[["item_key", "item_name", "basket_count"]].copy(), "workbook DimProduct"
        notes.append("outputs/python_item_frequency.csv missing - using workbook DimProduct.")
    else:
        js = _read_json(DASHBOARD_JSON)
        if js and js.get("item_frequency"):
            base = pd.DataFrame(js["item_frequency"])
            base["item_key"] = base["item_key"].astype(str)
            source = "dashboard_data.json (top-40 items only)"
            notes.append("Only the 40 most frequent products are available in this fallback.")
        else:
            return Loaded(None, "not found", ["No product data available."])

    if dim is not None:
        extra = [c for c in ("total_quantity", "total_revenue", "frequency_tier", "rare_status") if c in dim.columns]
        base = base.merge(dim[["item_key", *extra]], on="item_key", how="left")
        source += " + workbook DimProduct"
    else:
        notes.append("Quantity / revenue / tier unavailable (workbook missing).")

    base = base.sort_values(["basket_count", "item_name"], ascending=[False, True]).reset_index(drop=True)
    base["product_rank"] = np.arange(1, len(base) + 1)
    if basket_total:
        base["item_support"] = base["basket_count"] / basket_total
    base["is_rare"] = base["basket_count"] < min_item_frequency
    if "frequency_tier" not in base.columns:
        bins = [0, 4, 49, 249, np.inf]
        base["frequency_tier"] = pd.cut(base["basket_count"], bins=bins, labels=TIER_ORDER).astype(str)
    base["label"] = [product_label(k, n) for k, n in zip(base["item_key"], base["item_name"])]
    return Loaded(base, source, notes)


def load_baskets() -> Loaded:
    df = _read_sheet("BasketSummary", dtype={"basket_id": str})
    if df is None or df.empty:
        return Loaded(None, "not found", ["workbook BasketSummary sheet unavailable - basket-level charts are hidden."])
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["month_start"] = pd.to_datetime(df["month_start"])
    return Loaded(df, "workbook BasketSummary")


def load_countries() -> Loaded:
    df = _read_sheet("DimCountry")
    return Loaded(df, "workbook DimCountry") if df is not None else Loaded(None, "not found")


def load_dq() -> Loaded:
    df = _read_sheet("DataQualitySummary")
    return Loaded(df, "workbook DataQualitySummary") if df is not None else Loaded(None, "not found")


def load_audit() -> Loaded:
    df = _read_sheet("CleaningAudit")
    return Loaded(df, "workbook CleaningAudit") if df is not None else Loaded(None, "not found")


def load_rare_impact() -> Loaded:
    df = _read_csv(RARE_IMPACT_CSV)
    if df is not None:
        return Loaded(df, "outputs/rare_item_impact.csv")
    js = _read_json(DASHBOARD_JSON)
    if js and js.get("rare_item_impact"):
        return Loaded(pd.DataFrame(js["rare_item_impact"]), "dashboard_data.json")
    return Loaded(None, "not found")


def load_reconciliation() -> Loaded:
    df = _read_sheet("ReconciliationSummary")
    if df is not None and len(df):
        return Loaded(df.iloc[0].to_dict(), "workbook ReconciliationSummary")  # type: ignore[arg-type]
    js = _read_json(DASHBOARD_JSON)
    if js and "reconciliation" in js:
        r = js["reconciliation"]
        d = {"status": r.get("status"), "matching_pairs": r.get("matching_pairs"),
             "failed_pairs": r.get("failed_pairs")}
        if d["matching_pairs"] is not None and d["failed_pairs"] is not None:
            d["compared_pairs"] = d["matching_pairs"] + d["failed_pairs"]
        return Loaded(d, "dashboard_data.json")  # type: ignore[arg-type]
    return Loaded(None, "not found")


def load_pair_context() -> Loaded:
    """Country/date occurrences. Only exists in the workbook for its 200 pairs."""
    df = _read_sheet("PairContext")
    if df is None or df.empty:
        return Loaded(None, "not found")
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    return Loaded(df, "workbook PairContext (subset of pairs)")


def generated_at() -> str | None:
    return (_read_json(DASHBOARD_JSON) or {}).get("generated_at")


# --------------------------------------------------------------------------- #
# Filtering and ranking
# --------------------------------------------------------------------------- #
def filter_pairs(
    pairs: pd.DataFrame,
    products: Iterable[str] = (),
    both_products: bool = False,
    query: str = "",
    min_pair_count: float = 0,
    min_support: float = 0.0,
    min_lift: float = 0.0,
    min_confidence: float = 0.0,
) -> pd.DataFrame:
    """Apply the sidebar filters. `products` are item keys."""
    if pairs is None or pairs.empty:
        return pairs.iloc[0:0] if pairs is not None else pd.DataFrame(columns=PAIR_COLUMNS)
    m = np.ones(len(pairs), dtype=bool)
    products = list(products)
    if products:
        a = pairs["item_a_key"].isin(products).to_numpy()
        b = pairs["item_b_key"].isin(products).to_numpy()
        m &= (a & b) if both_products else (a | b)
    q = (query or "").strip().lower()
    if q:
        hay = (pairs["item_a_name"].astype(str) + " + " + pairs["item_b_name"].astype(str)).str.lower()
        keys = (pairs["item_a_key"].astype(str) + " " + pairs["item_b_key"].astype(str)).str.lower()
        m &= (hay.str.contains(q, regex=False) | keys.str.contains(q, regex=False)).to_numpy()
    m &= (pairs["pair_count"] >= min_pair_count).to_numpy()
    m &= (pairs["support"] >= min_support).to_numpy()
    m &= (pairs["lift"] >= min_lift).to_numpy()
    if min_confidence > 0:  # same rule as the pipeline: both directions must meet it
        m &= ((pairs["confidence_a_to_b"] >= min_confidence) & (pairs["confidence_b_to_a"] >= min_confidence)).to_numpy()
    return pairs[m]


def top_by_count(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Pipeline ranking: pair_count desc, lift desc, then item names asc (docs/kpi_definitions.md)."""
    out = df.sort_values(["pair_count", "lift", "item_a_name", "item_b_name"],
                         ascending=[False, False, True, True], kind="mergesort").head(n).copy()
    out.insert(0, "display_rank", np.arange(1, len(out) + 1))
    return out


def top_by_lift(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Supplementary ranking: lift desc, pair_count desc, then item names asc."""
    out = df.sort_values(["lift", "pair_count", "item_a_name", "item_b_name"],
                         ascending=[False, False, True, True], kind="mergesort").head(n).copy()
    out.insert(0, "display_rank", np.arange(1, len(out) + 1))
    return out


def anchor_partners(pairs: pd.DataFrame, anchor_key: str) -> pd.DataFrame:
    """All pairs containing `anchor_key`, re-oriented so the anchor is always 'A'.

    Pairs are stored once with item_a_key < item_b_key, so for pairs where the
    anchor is stored as B the two directional confidences are swapped.
    """
    as_a = pairs[pairs["item_a_key"] == anchor_key]
    as_b = pairs[pairs["item_b_key"] == anchor_key]
    left = pd.DataFrame({
        "partner_key": as_a["item_b_key"], "partner_name": as_a["item_b_name"],
        "pair_count": as_a["pair_count"], "anchor_basket_count": as_a["item_a_basket_count"],
        "partner_basket_count": as_a["item_b_basket_count"], "support": as_a["support"],
        "confidence_anchor_to_partner": as_a["confidence_a_to_b"],
        "confidence_partner_to_anchor": as_a["confidence_b_to_a"], "lift": as_a["lift"],
        "basket_count": as_a["basket_count"],
    })
    right = pd.DataFrame({
        "partner_key": as_b["item_a_key"], "partner_name": as_b["item_a_name"],
        "pair_count": as_b["pair_count"], "anchor_basket_count": as_b["item_b_basket_count"],
        "partner_basket_count": as_b["item_a_basket_count"], "support": as_b["support"],
        "confidence_anchor_to_partner": as_b["confidence_b_to_a"],
        "confidence_partner_to_anchor": as_b["confidence_a_to_b"], "lift": as_b["lift"],
        "basket_count": as_b["basket_count"],
    })
    return pd.concat([left, right], ignore_index=True)


def contingency(row: pd.Series) -> dict[str, int]:
    """Basket counts for the four A/B combinations, derived only from stored counts."""
    both = int(row["pair_count"])
    a = int(row["item_a_basket_count"])
    b = int(row["item_b_basket_count"])
    n = int(row["basket_count"])
    return {"both": both, "only_a": a - both, "only_b": b - both, "neither": n - a - b + both}


def expected_pair_count(row: pd.Series) -> float:
    """Pairs expected under independence: count(A) * count(B) / N. observed / expected == lift."""
    return float(row["item_a_basket_count"]) * float(row["item_b_basket_count"]) / float(row["basket_count"])


# --------------------------------------------------------------------------- #
# Integrity checks (computed from the loaded data, not hard-coded)
# --------------------------------------------------------------------------- #
def integrity_checks(pairs: pd.DataFrame, kpis: dict, tol: float = 1e-9) -> pd.DataFrame:
    """Recompute the documented formulas over every loaded pair and compare."""
    rows: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        rows.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

    if pairs is None or pairs.empty:
        return pd.DataFrame(rows, columns=["check", "result", "detail"])

    n = pairs["basket_count"].iloc[0]
    add("Single basket denominator", pairs["basket_count"].nunique() == 1, f"basket_count = {int(n):,} on every pair")
    if kpis.get("distinct_baskets"):
        add("Denominator equals KPI baskets", int(n) == int(kpis["distinct_baskets"]),
            f"pairs: {int(n):,} | KPI: {int(kpis['distinct_baskets']):,}")
    add("Pair key rule item_a_key < item_b_key", bool((pairs["item_a_key"] < pairs["item_b_key"]).all()),
        f"{int((pairs['item_a_key'] >= pairs['item_b_key']).sum()):,} violations")
    add("No duplicated unordered pairs", not pairs.duplicated(["item_a_key", "item_b_key"]).any(),
        f"{int(pairs.duplicated(['item_a_key', 'item_b_key']).sum()):,} duplicates")
    s = (pairs["pair_count"] / pairs["basket_count"] - pairs["support"]).abs().max()
    add("support = pair_count / baskets", s < 1e-9, f"max abs diff {s:.2e}")
    c1 = (pairs["pair_count"] / pairs["item_a_basket_count"] - pairs["confidence_a_to_b"]).abs().max()
    c2 = (pairs["pair_count"] / pairs["item_b_basket_count"] - pairs["confidence_b_to_a"]).abs().max()
    add("confidence A→B and B→A formulas", max(c1, c2) < 1e-9, f"max abs diff {max(c1, c2):.2e}")
    lift = pairs["pair_count"] * pairs["basket_count"] / (pairs["item_a_basket_count"] * pairs["item_b_basket_count"])
    l = (lift - pairs["lift"]).abs().max()
    add("lift = support / (support A × support B)", l < 1e-6, f"max abs diff {l:.2e}")
    if kpis.get("qualifying_pairs"):
        add("Pair rows equal KPI qualifying pairs", len(pairs) == int(kpis["qualifying_pairs"]),
            f"loaded: {len(pairs):,} | KPI: {int(kpis['qualifying_pairs']):,}")
    return pd.DataFrame(rows, columns=["check", "result", "detail"])


def histogram(values: pd.Series, bins: int = 40, log: bool = False) -> pd.DataFrame:
    """Pre-binned histogram so the browser receives a few dozen bars, not 347k points."""
    v = values.dropna().to_numpy(dtype=float)
    if len(v) == 0:
        return pd.DataFrame(columns=["left", "right", "mid", "count"])
    if log:
        v = v[v > 0]
        if len(v) == 0:
            return pd.DataFrame(columns=["left", "right", "mid", "count"])
        edges = np.logspace(np.log10(v.min()), np.log10(v.max()) if v.max() > v.min() else np.log10(v.min()) + 1e-6, bins + 1)
        mid = np.sqrt(edges[:-1] * edges[1:])
    else:
        hi = v.max() if v.max() > v.min() else v.min() + 1e-9
        edges = np.linspace(v.min(), hi, bins + 1)
        mid = (edges[:-1] + edges[1:]) / 2
    counts, _ = np.histogram(v, bins=edges)
    return pd.DataFrame({"left": edges[:-1], "right": edges[1:], "mid": mid, "count": counts})
