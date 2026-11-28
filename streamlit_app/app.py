"""Market Basket Analysis - Streamlit dashboard.

Run from the repository root:   streamlit run streamlit_app/app.py

Reads only files that are committed to the repository (Python outputs, the
dashboard workbook, the dashboard JSON). No Oracle, Power BI, Microsoft login or
raw UCI workbook is needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `mba_data` importable on any host
import mba_data as md  # noqa: E402

st.set_page_config(
    page_title="Market Basket Analysis",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette: readable on both light and dark Streamlit themes.
TEAL, INDIGO, AMBER, ROSE, SLATE = "#0D9488", "#6366F1", "#F59E0B", "#E11D48", "#94A3B8"
LIFT_SCALE = [[0.0, "#A5B4FC"], [0.5, "#6366F1"], [1.0, "#3730A3"]]
COUNT_SCALE = [[0.0, "#99F6E4"], [0.5, "#14B8A6"], [1.0, "#0F766E"]]

PAGES = [
    "Executive Overview",
    "Transaction & Basket KPIs",
    "Product Analysis",
    "Top 10 Frequent Item Pairs",
    "Top 10 Pairs by Lift",
    "Support & Confidence",
    "Interactive Pair Analysis",
    "Data Quality Overview",
]

st.markdown(
    """
<style>
/* Theme-neutral polish: only spacing and type; colours come from the active Streamlit theme. */
.block-container {padding-top: 2.2rem; max-width: 1400px;}
[data-testid="stMetricValue"] {font-size: 1.65rem; font-weight: 650; letter-spacing: -0.01em;}
[data-testid="stMetricLabel"] p {font-size: 0.85rem; opacity: 0.75;}
h1 {letter-spacing: -0.02em; font-weight: 700; padding-bottom: 0.2rem;}
h2, h3 {letter-spacing: -0.01em;}
.mba-sub {opacity: 0.72; font-size: 0.98rem; margin-top: -0.4rem; margin-bottom: 1rem; max-width: 80ch;}
.mba-pill {display:inline-block; padding: 0.1rem 0.6rem; border-radius: 999px; font-size: 0.8rem;
           border: 1px solid rgba(128,128,128,.45);}
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Data loading (cached once per server process; frames are never mutated)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner="Loading market basket outputs…")
def load_all() -> dict:
    kpis_l = md.load_kpis()
    kpis = md.kpi_dict(kpis_l)
    pairs_l = md.load_pairs()
    cfg = md.load_config()
    n_baskets = kpis.get("distinct_baskets")
    if not n_baskets and pairs_l.ok:
        n_baskets = int(pairs_l.data["basket_count"].iloc[0])
        kpis["distinct_baskets"] = n_baskets
    return {
        "kpis_l": kpis_l,
        "kpis": kpis,
        "cfg": cfg,
        "pairs": pairs_l,
        "products": md.load_products(n_baskets, int(cfg.get("min_item_frequency", 5))),
        "baskets": md.load_baskets(),
        "countries": md.load_countries(),
        "dq": md.load_dq(),
        "audit": md.load_audit(),
        "rare": md.load_rare_impact(),
        "recon": md.load_reconciliation(),
        "context": md.load_pair_context(),
        "official": md.load_official_top10(),
        "generated_at": md.generated_at(),
    }


D = load_all()
K: dict = D["kpis"]
PAIRS_L: md.Loaded = D["pairs"]

if not PAIRS_L.ok:
    st.title("Market Basket Analysis")
    st.error(
        "No association-pair data could be found. Expected `outputs/python_pair_metrics.csv` "
        "(or `outputs/python_top_10_pairs.csv`) in the repository. Run `python src/market_basket_analysis.py` "
        "after downloading the UCI workbook, or restore the committed output files."
    )
    st.stop()

PAIRS: pd.DataFrame = PAIRS_L.data  # type: ignore[assignment]
PRODUCTS: pd.DataFrame | None = D["products"].data
N_BASKETS = int(K.get("distinct_baskets") or PAIRS["basket_count"].iloc[0])


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def n(v, fmt="{:,.0f}") -> str:
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "n/a"
        return fmt.format(v)
    except (TypeError, ValueError):
        return "n/a"


def pct(v, d=1) -> str:
    return n(v, "{:." + str(d) + "%}")


def wrap(a: str, b: str, width: int = 34) -> str:
    """Two-line axis label for a pair."""
    def cut(s):
        s = str(s)
        return s if len(s) <= width else s[: width - 1] + "…"
    return f"{cut(a)}<br>+ {cut(b)}"


def kpi_cards(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, help_) in zip(cols, items):
        with col, st.container(border=True):
            st.metric(label, value, help=help_)


def style(fig: go.Figure, height: int = 380, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=40, b=8),
        showlegend=legend,
        hoverlabel=dict(font_size=13),
        title=dict(font=dict(size=15), x=0.0, xanchor="left"),
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def show(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", theme="streamlit", key=key, config={"displaylogo": False})


def page_header(title: str, sub: str) -> None:
    st.title(title)
    st.markdown(f'<div class="mba-sub">{sub}</div>', unsafe_allow_html=True)


def empty_state(msg: str = "No pairs match the current sidebar filters.") -> None:
    st.warning(f"{msg} Loosen the thresholds or press **Reset filters** in the sidebar.")


PAIR_TABLE_CFG = {
    "display_rank": st.column_config.NumberColumn("#", width="small"),
    "item_a_name": st.column_config.TextColumn("Item A", width="medium"),
    "item_b_name": st.column_config.TextColumn("Item B", width="medium"),
    "item_a_key": st.column_config.TextColumn("Key A", width="small"),
    "item_b_key": st.column_config.TextColumn("Key B", width="small"),
    "pair_count": st.column_config.NumberColumn("Pair count", format="%d", help="Distinct baskets containing both items"),
    "item_a_basket_count": st.column_config.NumberColumn("Baskets A", format="%d"),
    "item_b_basket_count": st.column_config.NumberColumn("Baskets B", format="%d"),
    "support": st.column_config.NumberColumn("Support", format="%.4f", help="pair_count / total baskets"),
    "confidence_a_to_b": st.column_config.NumberColumn("Conf A→B", format="%.4f"),
    "confidence_b_to_a": st.column_config.NumberColumn("Conf B→A", format="%.4f"),
    "lift": st.column_config.NumberColumn("Lift", format="%.2f", help="support(A,B) / (support(A) × support(B))"),
}
PAIR_TABLE_COLS = ["display_rank", "item_a_name", "item_b_name", "pair_count", "support",
                   "confidence_a_to_b", "confidence_b_to_a", "lift", "item_a_basket_count", "item_b_basket_count"]


def pair_table(df: pd.DataFrame, cols: list[str] | None = None, height: int | None = None) -> None:
    cols = cols or PAIR_TABLE_COLS
    extra = {"height": height} if height else {}
    st.dataframe(df[[c for c in cols if c in df.columns]], hide_index=True, width="stretch",
                 column_config=PAIR_TABLE_CFG, **extra)


# --------------------------------------------------------------------------- #
# Sidebar: navigation + filters
# --------------------------------------------------------------------------- #
P_MIN_COUNT = int(PAIRS["pair_count"].min())
P_MAX_COUNT = int(PAIRS["pair_count"].max())
P_MIN_SUP, P_MAX_SUP = float(PAIRS["support"].min()), float(PAIRS["support"].max())
P_MIN_LIFT, P_MAX_LIFT = float(PAIRS["lift"].min()), float(PAIRS["lift"].max())

DEFAULTS = {
    "f_products": [], "f_mode": "Either item", "f_query": "",
    "f_count": P_MIN_COUNT, "f_support": P_MIN_SUP, "f_lift": P_MIN_LIFT, "f_conf": 0.0,
}
for k_, v_ in DEFAULTS.items():
    st.session_state.setdefault(k_, v_)


def reset_filters() -> None:
    for k_, v_ in DEFAULTS.items():
        st.session_state[k_] = v_


with st.sidebar:
    st.markdown("### 🧺 Market Basket Analysis")
    page = st.radio("Section", PAGES, label_visibility="collapsed", key="page")
    st.divider()
    st.markdown("**Filters** · pair-based sections")

    if PRODUCTS is not None:
        prod_opts = dict(zip(PRODUCTS["item_key"], PRODUCTS["label"]))
        st.multiselect("Product", options=list(prod_opts), format_func=prod_opts.get, key="f_products",
                       placeholder="Any product · type to search",
                       help="Keep pairs that contain the selected product(s). Products are sorted by basket frequency.")
    else:
        st.caption("Product list unavailable.")
    st.radio("Product match", ["Either item", "Both items"], key="f_mode", horizontal=True,
             disabled=len(st.session_state.f_products) < 2,
             help="With two or more products selected: keep pairs with either item in the selection, or only pairs where both items are selected.")
    st.text_input("Pair search", key="f_query", placeholder="e.g. jumbo bag, 85099B",
                  help="Case-insensitive match on either item name or stock code.")

    if P_MAX_COUNT > P_MIN_COUNT:
        st.slider("Minimum pair count", P_MIN_COUNT, P_MAX_COUNT, key="f_count", step=1,
                  help=f"Pipeline threshold is {md.load_config().get('min_pair_count', P_MIN_COUNT)}; this slider can only raise it.")
    if P_MAX_SUP > P_MIN_SUP:
        st.slider("Minimum support", P_MIN_SUP, P_MAX_SUP, key="f_support", step=0.0001, format="%.4f")
    if P_MAX_LIFT > P_MIN_LIFT:
        st.slider("Minimum lift", float(np.floor(P_MIN_LIFT * 10) / 10), float(np.ceil(P_MAX_LIFT)), key="f_lift",
                  step=0.1, format="%.1f", help="Lift above 1 means the items co-occur more than expected by chance.")
    st.slider("Minimum confidence (both directions)", 0.0, 1.0, key="f_conf", step=0.05,
              help="Same rule as the pipeline: both A→B and B→A must meet the value.")
    st.button("Reset filters", on_click=reset_filters, width="stretch")

    FILTERED = md.filter_pairs(
        PAIRS, st.session_state.f_products, st.session_state.f_mode == "Both items", st.session_state.f_query,
        st.session_state.f_count, st.session_state.f_support, st.session_state.f_lift, st.session_state.f_conf,
    )
    st.caption(f"**{len(FILTERED):,}** of {len(PAIRS):,} pairs match")

    st.divider()
    st.caption(f"Pair data: {PAIRS_L.source}")
    for note in PAIRS_L.notes:
        st.warning(note)
    if D["generated_at"]:
        st.caption(f"Outputs generated {D['generated_at'][:10]}")
    st.caption("Historical / optional: [GitHub Pages dashboard](https://krishporwal011.github.io/Bussiness-BI/) "
               "and Power BI report (sign-in required).")

filters_active = len(FILTERED) != len(PAIRS)


# --------------------------------------------------------------------------- #
# 1. Executive Overview
# --------------------------------------------------------------------------- #
def page_overview() -> None:
    page_header("Executive Overview",
                "Which products are bought together in the same UK online-retail invoice, and how strong is each association? "
                "Figures on this page cover the full cleaned dataset; sidebar filters apply to the pair sections.")
    rec = md.kpi_dict(D["recon"]) if D["recon"].ok else {}
    status = K.get("reconciliation_status") or rec.get("status")
    kpi_cards([
        ("Raw invoice lines", n(K.get("raw_rows")), "Rows in the UCI Online Retail workbook"),
        ("Retained lines", n(K.get("retained_clean_lines")),
         f"{pct(K['retained_clean_lines'] / K['raw_rows'])} of raw rows kept after cleaning" if K.get("raw_rows") and K.get("retained_clean_lines") else None),
        ("Baskets (invoices)", n(K.get("distinct_baskets")), "Distinct valid InvoiceNo values; includes single-item baskets"),
        ("Products", n(K.get("distinct_products")), "Distinct normalised StockCode values"),
        ("Qualifying pairs", n(K.get("qualifying_pairs")), "Pairs meeting the item-frequency, pair-count and support thresholds"),
        ("Oracle ↔ Python", status or "n/a", f"{n(K.get('matching_pairs'))} matching · {n(K.get('failed_pairs'))} failed pairs" if K.get("matching_pairs") is not None else None),
    ])

    top_c = md.top_by_count(PAIRS, 1).iloc[0]
    top_l = md.top_by_lift(PAIRS, 1).iloc[0]
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown("**Most frequent pair**")
        st.markdown(f"#### {top_c.item_a_name}  +  {top_c.item_b_name}")
        st.caption(f"{int(top_c.pair_count):,} baskets · support {top_c.support:.4f} · "
                   f"confidence {top_c.confidence_a_to_b:.3f} / {top_c.confidence_b_to_a:.3f} · lift {top_c.lift:.2f}")
    with c2, st.container(border=True):
        st.markdown("**Strongest pair by lift**")
        st.markdown(f"#### {top_l.item_a_name}  +  {top_l.item_b_name}")
        st.caption(f"Lift {top_l.lift:.1f} on only {int(top_l.pair_count):,} baskets (support {top_l.support:.4f}). "
                   "High lift on small counts is less stable, so read it alongside pair count.")

    base = D["baskets"].data
    left, right = st.columns(2)
    if base is not None:
        m = base.groupby("month_start").agg(baskets=("basket_id", "nunique"), revenue=("total_revenue", "sum")).reset_index()
        fig = go.Figure(go.Bar(x=m["month_start"], y=m["baskets"], marker_color=TEAL,
                               hovertemplate="%{x|%b %Y}<br>%{y:,} baskets<extra></extra>"))
        fig.update_layout(title="Baskets per month")
        with left:
            show(style(fig, 340), "ov_month")
        fig = go.Figure(go.Scatter(x=m["month_start"], y=m["revenue"], mode="lines+markers", line=dict(color=INDIGO, width=3),
                                   hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>"))
        fig.update_layout(title="Revenue per month (GBP, retained lines)", yaxis_tickprefix="£")
        with right:
            show(style(fig, 340), "ov_rev")
        last = base["transaction_date"].max()
        if last.day < last.days_in_month:
            st.caption(f"Data runs {base['transaction_date'].min():%d %b %Y} – {last:%d %b %Y}; the final month is partial.")
    else:
        st.info("Monthly trend charts need the Power BI workbook (`powerbi/market_basket_dashboard_data.xlsx`), which was not found.")

    left, right = st.columns(2)
    if PRODUCTS is not None:
        t = PRODUCTS.head(12).iloc[::-1]
        fig = go.Figure(go.Bar(x=t["basket_count"], y=t["item_name"], orientation="h", marker_color=TEAL,
                               hovertemplate="%{y}<br>%{x:,} baskets<extra></extra>"))
        fig.update_layout(title="Most frequent products (baskets containing the item)")
        with left:
            show(style(fig, 420), "ov_prod")
    ctry = D["countries"].data
    if ctry is not None:
        t = ctry.sort_values("basket_count", ascending=False).head(10).iloc[::-1]
        fig = go.Figure(go.Bar(x=t["basket_count"], y=t["country"], orientation="h", marker_color=AMBER,
                               hovertemplate="%{y}<br>%{x:,} baskets<extra></extra>"))
        fig.update_layout(title="Baskets by country (top 10)")
        with right:
            show(style(fig, 420), "ov_ctry")
        uk = ctry.loc[ctry["country"] == "United Kingdom", "basket_count"]
        if len(uk) and ctry["basket_count"].sum():
            st.caption(f"United Kingdom accounts for {uk.iloc[0] / ctry['basket_count'].sum():.1%} of baskets, so findings mainly describe UK shopping behaviour.")


# --------------------------------------------------------------------------- #
# 2. Transaction & Basket KPIs
# --------------------------------------------------------------------------- #
def page_baskets() -> None:
    page_header("Transaction & Basket KPIs",
                "Basket size is the number of distinct products on an invoice (presence-based, not units). "
                "Single-item baskets stay in the denominator for support but create no pairs.")
    b = D["baskets"].data
    if b is None:
        st.info("Basket-level detail comes from the Power BI workbook, which is not available. Showing headline KPIs only.")
        kpi_cards([("Baskets", n(K.get("distinct_baskets")), None),
                   ("Average basket size", n(K.get("average_basket_size"), "{:.2f}"), "Presence rows / baskets"),
                   ("Single-item baskets", n(K.get("single_item_baskets")), None),
                   ("Single-item share", pct(K.get("single_item_basket_pct"), 2), None)])
        return

    with st.container(border=True):
        f1, f2 = st.columns([2, 3])
        countries = sorted(b["country"].dropna().unique())
        sel = f1.multiselect("Country", countries, placeholder="All countries")
        dmin, dmax = b["transaction_date"].min().date(), b["transaction_date"].max().date()
        rng = f2.slider("Invoice date range", dmin, dmax, (dmin, dmax), format="DD MMM YYYY")
    v = b[(b["transaction_date"].dt.date >= rng[0]) & (b["transaction_date"].dt.date <= rng[1])]
    if sel:
        v = v[v["country"].isin(sel)]
    if v.empty:
        st.warning("No baskets match the selected country / date range.")
        return

    kpi_cards([
        ("Baskets", n(len(v)), None),
        ("Avg. basket size", n(v["distinct_item_count"].mean(), "{:.2f}"), "Mean distinct items per basket"),
        ("Median basket size", n(v["distinct_item_count"].median(), "{:.0f}"), None),
        ("Single-item share", pct(v["is_single_item"].mean(), 2), f"{int(v['is_single_item'].sum()):,} baskets"),
        ("Avg. basket value", "£" + n(v["total_revenue"].mean(), "{:,.2f}"), "GBP, retained lines"),
        ("Total revenue", "£" + n(v["total_revenue"].sum(), "{:,.0f}"), "GBP, retained lines"),
    ])
    if not sel and rng == (dmin, dmax) and K.get("average_basket_size"):
        st.caption(f"Cross-check: unfiltered average basket size {v['distinct_item_count'].mean():.4f} vs KPI file {K['average_basket_size']:.4f}.")

    left, right = st.columns(2)
    cap = 60
    sizes = v["distinct_item_count"].clip(upper=cap)
    vc = sizes.value_counts().sort_index()
    labels = [str(int(i)) if i < cap else f"{cap}+" for i in vc.index]
    fig = go.Figure(go.Bar(x=labels, y=vc.values, marker_color=TEAL, hovertemplate="%{x} items<br>%{y:,} baskets<extra></extra>"))
    fig.update_layout(title=f"Basket size distribution (sizes ≥ {cap} grouped)", xaxis_title="Distinct items in basket",
                      yaxis_title="Baskets", xaxis=dict(type="category", dtick=5))
    with left:
        show(style(fig, 360), "bk_dist")
    m = v.groupby("month_start").agg(baskets=("basket_id", "nunique"), avg_size=("distinct_item_count", "mean"),
                                     single=("is_single_item", "mean")).reset_index()
    fig = go.Figure()
    fig.add_bar(x=m["month_start"], y=m["baskets"], name="Baskets", marker_color=TEAL, opacity=0.55,
                hovertemplate="%{x|%b %Y}<br>%{y:,} baskets<extra></extra>")
    fig.add_scatter(x=m["month_start"], y=m["avg_size"], name="Avg. basket size", yaxis="y2", mode="lines+markers",
                    line=dict(color=INDIGO, width=3), hovertemplate="%{x|%b %Y}<br>%{y:.1f} items<extra></extra>")
    fig.update_layout(title="Monthly baskets and average basket size", yaxis=dict(title="Baskets"),
                      yaxis2=dict(title="Avg. items", overlaying="y", side="right", showgrid=False),
                      legend=dict(orientation="h", y=1.12, x=0))
    with right:
        show(style(fig, 360, legend=True), "bk_month")

    g = (v.groupby("country").agg(baskets=("basket_id", "nunique"), avg_items=("distinct_item_count", "mean"),
                                  single_item=("is_single_item", "sum"), revenue=("total_revenue", "sum"))
           .reset_index().sort_values("baskets", ascending=False))
    g["single_share"] = g["single_item"] / g["baskets"]
    st.markdown("##### By country")
    st.dataframe(g, hide_index=True, width="stretch", height=300, column_config={
        "country": "Country", "baskets": st.column_config.NumberColumn("Baskets", format="%d"),
        "avg_items": st.column_config.NumberColumn("Avg. items", format="%.1f"),
        "single_item": st.column_config.NumberColumn("Single-item baskets", format="%d"),
        "single_share": st.column_config.ProgressColumn("Single-item share", format="percent", min_value=0, max_value=1),
        "revenue": st.column_config.NumberColumn("Revenue (£)", format="%.0f")})


# --------------------------------------------------------------------------- #
# 3. Product Analysis
# --------------------------------------------------------------------------- #
def page_products() -> None:
    page_header("Product Analysis",
                "Frequency is the number of baskets containing a product. Rare products (fewer than "
                f"{D['cfg'].get('min_item_frequency', 5)} baskets) are kept in the data but excluded from pair generation.")
    if PRODUCTS is None:
        st.warning("No product data available.")
        return
    for note in D["products"].notes:
        st.info(note)
    p = PRODUCTS
    sel = st.session_state.f_products
    if sel:
        p = p[p["item_key"].isin(sel)]
        st.caption(f"Showing {len(p)} product(s) chosen in the sidebar.")
    hide_rare = st.toggle("Hide rare products", value=False)
    if hide_rare:
        p = p[~p["is_rare"]]
    if p.empty:
        empty_state("No products match.")
        return

    kpi_cards([
        ("Products shown", n(len(p)), None),
        ("Qualifying (≥ min frequency)", n(int((~p["is_rare"]).sum())), None),
        ("Rare products", n(int(p["is_rare"].sum())), "Below the minimum item frequency"),
        ("Median baskets / product", n(p["basket_count"].median(), "{:.0f}"), None),
        ("Top product", str(p.iloc[0]["item_name"])[:28], f"{int(p.iloc[0]['basket_count']):,} baskets"),
    ])

    metrics = {"Baskets containing item": "basket_count"}
    if "total_quantity" in p.columns and p["total_quantity"].notna().any():
        metrics["Units sold"] = "total_quantity"
    if "total_revenue" in p.columns and p["total_revenue"].notna().any():
        metrics["Revenue (£)"] = "total_revenue"
    c1, c2 = st.columns([2, 1])
    metric_label = c1.radio("Rank products by", list(metrics), horizontal=True)
    top_n = c2.slider("Products to show", 5, min(50, len(p)) if len(p) > 5 else 5, min(15, len(p)))
    mcol = metrics[metric_label]
    t = p.sort_values(mcol, ascending=False).head(top_n).iloc[::-1]
    fig = go.Figure(go.Bar(x=t[mcol], y=t["label"], orientation="h", marker_color=TEAL,
                           hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>"))
    fig.update_layout(title=f"Top {len(t)} products by {metric_label.lower()}")
    show(style(fig, max(320, 22 * len(t) + 80)), "pr_top")

    left, right = st.columns(2)
    if "frequency_tier" in p.columns:
        tc = p["frequency_tier"].value_counts().reindex(md.TIER_ORDER).dropna()
        fig = go.Figure(go.Bar(x=[s[3:] for s in tc.index], y=tc.values, marker_color=[SLATE, AMBER, TEAL, INDIGO][: len(tc)],
                               hovertemplate="%{x}<br>%{y:,} products<extra></extra>"))
        fig.update_layout(title="Products by frequency tier (baskets)", yaxis_title="Products")
        with left:
            show(style(fig, 360), "pr_tier")
    if "total_revenue" in p.columns and p["total_revenue"].notna().any():
        q = p[(p["total_revenue"] > 0) & (p["basket_count"] > 0)]
        fig = go.Figure(go.Scattergl(
            x=q["basket_count"], y=q["total_revenue"], mode="markers", text=q["label"],
            marker=dict(color=INDIGO, size=6, opacity=0.5),
            hovertemplate="%{text}<br>%{x:,} baskets<br>£%{y:,.0f}<extra></extra>"))
        fig.update_layout(title="Frequency vs revenue (log scales)", xaxis=dict(type="log", title="Baskets"),
                          yaxis=dict(type="log", title="Revenue (£)"))
        with right:
            show(style(fig, 360), "pr_scatter")
        st.caption("Products with non-positive revenue are omitted from the log chart only.")

    st.markdown("##### Product table")
    q = st.text_input("Search products", placeholder="name or stock code", key="prod_search")
    tbl = p
    if q.strip():
        ql = q.strip().lower()
        tbl = p[p["item_name"].str.lower().str.contains(ql, regex=False) | p["item_key"].str.lower().str.contains(ql, regex=False)]
    cols = [c for c in ["product_rank", "item_key", "item_name", "basket_count", "item_support", "total_quantity", "total_revenue", "frequency_tier"] if c in tbl.columns]
    st.dataframe(tbl[cols], hide_index=True, width="stretch", height=380, column_config={
        "product_rank": st.column_config.NumberColumn("Rank", width="small"), "item_key": "Stock code", "item_name": "Product",
        "basket_count": st.column_config.NumberColumn("Baskets", format="%d"),
        "item_support": st.column_config.NumberColumn("Item support", format="%.4f"),
        "total_quantity": st.column_config.NumberColumn("Units", format="%d"),
        "total_revenue": st.column_config.NumberColumn("Revenue (£)", format="%.2f"), "frequency_tier": "Tier"})
    if tbl.empty:
        st.caption("No products match that search.")


# --------------------------------------------------------------------------- #
# 4 & 5. Top-10 pages
# --------------------------------------------------------------------------- #
def official_match(top: pd.DataFrame, kind: str) -> None:
    ref = D["official"].get(kind)
    if ref is None or top.empty:
        return
    same = (len(ref) == len(top)
            and list(ref["item_a_key"]) == list(top["item_a_key"])
            and list(ref["item_b_key"]) == list(top["item_b_key"])
            and list(ref["pair_count"]) == list(top["pair_count"]))
    fname = "python_top_10_pairs.csv" if kind == "count" else "python_lift_top_10_pairs.csv"
    if same:
        st.success(f"Matches the committed pipeline output `outputs/{fname}` row for row.", icon="✅")
    else:
        st.info(f"Filtered view - differs from the official `outputs/{fname}` because sidebar filters are active.", icon="🔎")


def page_top_count() -> None:
    page_header("Top 10 Frequent Item Pairs",
                "Ranked by the number of baskets containing both items (ties: higher lift, then item name). "
                "Each unordered pair appears once.")
    if FILTERED.empty:
        return empty_state()
    top = md.top_by_count(FILTERED, 10)
    kpi_cards([("Pairs in view", n(len(FILTERED)), None),
               ("Highest pair count", n(top["pair_count"].max()), "Baskets containing both items"),
               ("Highest support", f"{top['support'].max():.4f}", None),
               ("Median lift (top 10)", f"{top['lift'].median():.2f}", None)])
    official_match(top, "count")
    t = top.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=t["pair_count"], y=[wrap(a, b) for a, b in zip(t["item_a_name"], t["item_b_name"])], orientation="h",
        marker=dict(color=t["lift"], colorscale=LIFT_SCALE, colorbar=dict(title="Lift", thickness=12)),
        customdata=np.stack([t["support"], t["confidence_a_to_b"], t["confidence_b_to_a"], t["lift"]], axis=-1),
        hovertemplate="%{y}<br>Pair count %{x:,}<br>Support %{customdata[0]:.4f}<br>"
                      "Conf A→B %{customdata[1]:.3f} · B→A %{customdata[2]:.3f}<br>Lift %{customdata[3]:.2f}<extra></extra>"))
    fig.update_layout(title="Pair count (bar colour = lift)", xaxis_title="Baskets containing both items")
    show(style(fig, 520), "tc_bar")
    pair_table(top)
    st.download_button("Download this table (CSV)", top.drop(columns=["rank"], errors="ignore").to_csv(index=False),
                       "top_10_pairs_by_count.csv", "text/csv")


def page_top_lift() -> None:
    page_header("Top 10 Pairs by Lift",
                "Lift compares how often two items co-occur against what independence would predict. "
                "It is ranked separately because it favours rarer items; always read it alongside pair count.")
    if FILTERED.empty:
        return empty_state()
    top = md.top_by_lift(FILTERED, 10)
    kpi_cards([("Highest lift", f"{top['lift'].max():.1f}", None),
               ("Pair count range (top 10)", f"{int(top['pair_count'].min())}–{int(top['pair_count'].max())}", "Baskets containing both items"),
               ("Max confidence in view", f"{max(top['confidence_a_to_b'].max(), top['confidence_b_to_a'].max()):.3f}", "Either direction"),
               ("Pairs in view", n(len(FILTERED)), None)])
    official_match(top, "lift")
    t = top.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=t["lift"], y=[wrap(a, b) for a, b in zip(t["item_a_name"], t["item_b_name"])], orientation="h",
        marker=dict(color=t["pair_count"], colorscale=COUNT_SCALE, colorbar=dict(title="Pair<br>count", thickness=12)),
        customdata=np.stack([t["pair_count"], t["support"], t["confidence_a_to_b"], t["confidence_b_to_a"]], axis=-1),
        hovertemplate="%{y}<br>Lift %{x:.1f}<br>Pair count %{customdata[0]:,}<br>Support %{customdata[1]:.4f}<br>"
                      "Conf A→B %{customdata[2]:.3f} · B→A %{customdata[3]:.3f}<extra></extra>"))
    fig.update_layout(title="Lift (bar colour = pair count)", xaxis_title="Lift")
    show(style(fig, 520), "tl_bar")
    st.caption(f"These pairs rest on {int(top['pair_count'].min())}–{int(top['pair_count'].max())} baskets out of {N_BASKETS:,}. "
               "Treat them as targeted cross-sell candidates to test, not broad promotions.")
    pair_table(top)
    st.download_button("Download this table (CSV)", top.drop(columns=["rank"], errors="ignore").to_csv(index=False),
                       "top_10_pairs_by_lift.csv", "text/csv")


# --------------------------------------------------------------------------- #
# 6. Support & Confidence
# --------------------------------------------------------------------------- #
def page_support_conf() -> None:
    page_header("Support & Confidence Analysis",
                "Support is how common a pair is across all baskets; confidence is directional: the share of baskets with "
                "one item that also contain the other. Charts use every pair that passes the sidebar filters.")
    if FILTERED.empty:
        return empty_state()
    f = FILTERED
    asym = (f["confidence_a_to_b"] - f["confidence_b_to_a"]).abs()
    kpi_cards([
        ("Pairs in view", n(len(f)), None),
        ("Median support", f"{f['support'].median():.4f}", None),
        ("Median lift", f"{f['lift'].median():.2f}", None),
        ("Lift > 1", pct((f["lift"] > 1).mean()), "Share of pairs co-occurring more than chance"),
        ("Max confidence", f"{max(f['confidence_a_to_b'].max(), f['confidence_b_to_a'].max()):.3f}", "Either direction"),
        ("Median |A→B − B→A|", f"{asym.median():.3f}", "How asymmetric the directional confidences are"),
    ])

    left, right = st.columns(2)
    h = md.histogram(f["support"], 40, log=True)
    fig = go.Figure(go.Bar(x=h["mid"], y=h["count"], marker_color=TEAL, customdata=np.stack([h["left"], h["right"]], axis=-1),
                           hovertemplate="Support %{customdata[0]:.4f}–%{customdata[1]:.4f}<br>%{y:,} pairs<extra></extra>"))
    fig.update_layout(title="Support distribution", xaxis=dict(type="log", title="Support (log scale)"), yaxis_title="Pairs")
    with left:
        show(style(fig, 340), "sc_sup")
    h = md.histogram(f["lift"], 40, log=True)
    fig = go.Figure(go.Bar(x=h["mid"], y=h["count"], marker_color=INDIGO, customdata=np.stack([h["left"], h["right"]], axis=-1),
                           hovertemplate="Lift %{customdata[0]:.2f}–%{customdata[1]:.2f}<br>%{y:,} pairs<extra></extra>"))
    fig.update_layout(title="Lift distribution", xaxis=dict(type="log", title="Lift (log scale)"), yaxis_title="Pairs")
    fig.add_vline(x=1, line_dash="dash", line_color=ROSE, annotation_text="lift = 1")
    with right:
        show(style(fig, 340), "sc_lift")

    cap = 3000
    s = md.top_by_count(f, cap)
    fig = go.Figure(go.Scattergl(
        x=s["confidence_a_to_b"], y=s["confidence_b_to_a"], mode="markers",
        marker=dict(color=s["lift"], colorscale=LIFT_SCALE, cmin=0, cmax=float(s["lift"].quantile(0.98)) or 1, size=6, opacity=0.7,
                    colorbar=dict(title="Lift", thickness=12)),
        text=[f"{a} + {b}" for a, b in zip(s["item_a_name"], s["item_b_name"])],
        customdata=np.stack([s["pair_count"], s["support"], s["lift"]], axis=-1),
        hovertemplate="%{text}<br>Conf A→B %{x:.3f} · B→A %{y:.3f}<br>Pair count %{customdata[0]:,}<br>"
                      "Support %{customdata[1]:.4f} · Lift %{customdata[2]:.2f}<extra></extra>"))
    fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dot", color=SLATE))
    fig.update_layout(title=f"Directional confidence: A→B vs B→A ({len(s):,} most frequent pairs in view)",
                      xaxis=dict(title="Confidence A→B", range=[0, 1.02]), yaxis=dict(title="Confidence B→A", range=[0, 1.02]))
    show(style(fig, 480), "sc_conf")
    st.caption("Points far from the dotted diagonal are one-way relationships: buyers of one item usually take the other, but not vice versa.")

    st.markdown("##### Directional rules (antecedent → consequent)")
    a = pd.DataFrame({"antecedent": f["item_a_name"], "consequent": f["item_b_name"], "confidence": f["confidence_a_to_b"],
                      "pair_count": f["pair_count"], "support": f["support"], "lift": f["lift"]})
    b = pd.DataFrame({"antecedent": f["item_b_name"], "consequent": f["item_a_name"], "confidence": f["confidence_b_to_a"],
                      "pair_count": f["pair_count"], "support": f["support"], "lift": f["lift"]})
    rules = pd.concat([a, b], ignore_index=True).sort_values(["confidence", "pair_count"], ascending=False).head(300)
    st.dataframe(rules, hide_index=True, width="stretch", height=340, column_config={
        "antecedent": "If basket has…", "consequent": "…it also has",
        "confidence": st.column_config.ProgressColumn("Confidence", format="%.3f", min_value=0, max_value=1),
        "pair_count": st.column_config.NumberColumn("Pair count", format="%d"),
        "support": st.column_config.NumberColumn("Support", format="%.4f"),
        "lift": st.column_config.NumberColumn("Lift", format="%.2f")})
    st.caption("Top 300 rules by confidence among the filtered pairs.")


# --------------------------------------------------------------------------- #
# 7. Interactive Pair Analysis
# --------------------------------------------------------------------------- #
def page_pair() -> None:
    page_header("Interactive Pair Analysis",
                "Choose an anchor product to see everything it is bought with, then open one pair for its full breakdown. "
                "Sidebar thresholds apply.")
    if FILTERED.empty:
        return empty_state()
    f = FILTERED
    counts = pd.concat([
        f[["item_a_key", "item_a_name", "item_a_basket_count"]].set_axis(["key", "name", "baskets"], axis=1),
        f[["item_b_key", "item_b_name", "item_b_basket_count"]].set_axis(["key", "name", "baskets"], axis=1),
    ]).drop_duplicates("key").sort_values("baskets", ascending=False)
    labels = {k: md.product_label(k, nm) for k, nm in zip(counts["key"], counts["name"])}
    anchor = st.selectbox("Anchor product", list(labels), format_func=labels.get, index=0,
                          help="Products appearing in at least one pair that passes the sidebar filters, most frequent first.")
    partners = md.anchor_partners(f, anchor)
    if partners.empty:
        return empty_state("This product has no pairs under the current filters.")

    sort_opts = {"Pair count": "pair_count", "Lift": "lift", "Confidence anchor → partner": "confidence_anchor_to_partner",
                 "Confidence partner → anchor": "confidence_partner_to_anchor", "Support": "support"}
    c1, c2 = st.columns([2, 1])
    sort_label = c1.radio("Rank partners by", list(sort_opts), horizontal=True)
    n_show = c2.slider("Partners to chart", 5, 50, 20)
    pr = partners.sort_values([sort_opts[sort_label], "pair_count"], ascending=False).reset_index(drop=True)
    anchor_n = int(pr["anchor_basket_count"].iloc[0])
    kpi_cards([("Anchor baskets", n(anchor_n), f"{anchor_n / N_BASKETS:.2%} of all baskets"),
               ("Partners in view", n(len(pr)), None),
               ("Best partner by count", str(partners.sort_values("pair_count", ascending=False).iloc[0]["partner_name"])[:26], None),
               ("Best partner by lift", str(partners.sort_values("lift", ascending=False).iloc[0]["partner_name"])[:26], None)])

    t = pr.head(n_show)
    fig = go.Figure(go.Scatter(
        x=t["support"], y=t["confidence_anchor_to_partner"], mode="markers", text=t["partner_name"],
        marker=dict(size=np.clip(np.sqrt(t["pair_count"]) * 2.4, 8, 46), color=t["lift"], colorscale=LIFT_SCALE,
                    colorbar=dict(title="Lift", thickness=12), line=dict(width=1, color="rgba(255,255,255,.6)")),
        customdata=np.stack([t["pair_count"], t["lift"], t["confidence_partner_to_anchor"]], axis=-1),
        hovertemplate="%{text}<br>Support %{x:.4f}<br>Conf anchor→partner %{y:.3f}<br>Pair count %{customdata[0]:,}"
                      "<br>Lift %{customdata[1]:.2f}<br>Conf partner→anchor %{customdata[2]:.3f}<extra></extra>"))
    fig.update_layout(title=f"Partners of {md.product_label(anchor, labels[anchor].rsplit(' (', 1)[0])}: support vs confidence (bubble = pair count)",
                      xaxis_title="Support", yaxis=dict(title="Confidence anchor → partner", range=[0, 1.02]))
    show(style(fig, 440), "pa_bubble")

    tbl = pr.head(300).copy()
    tbl.insert(0, "#", np.arange(1, len(tbl) + 1))
    st.dataframe(tbl[["#", "partner_name", "partner_key", "pair_count", "support", "confidence_anchor_to_partner",
                      "confidence_partner_to_anchor", "lift", "partner_basket_count"]],
                 hide_index=True, width="stretch", height=320, column_config={
        "partner_name": "Partner", "partner_key": "Key",
        "pair_count": st.column_config.NumberColumn("Pair count", format="%d"),
        "support": st.column_config.NumberColumn("Support", format="%.4f"),
        "confidence_anchor_to_partner": st.column_config.NumberColumn("Conf anchor→partner", format="%.3f"),
        "confidence_partner_to_anchor": st.column_config.NumberColumn("Conf partner→anchor", format="%.3f"),
        "lift": st.column_config.NumberColumn("Lift", format="%.2f"),
        "partner_basket_count": st.column_config.NumberColumn("Partner baskets", format="%d")})

    st.divider()
    st.subheader("Pair detail")
    plabels = {k: md.product_label(k, nm) for k, nm in zip(pr["partner_key"].head(300), pr["partner_name"].head(300))}
    partner = st.selectbox("Partner product", list(plabels), format_func=plabels.get,
                           help="The 300 highest-ranked partners under the ranking chosen above.")
    row = pr[pr["partner_key"] == partner].iloc[0]
    nb = N_BASKETS
    both = int(row["pair_count"])
    only_anchor = int(row["anchor_basket_count"]) - both
    only_partner = int(row["partner_basket_count"]) - both
    neither = nb - int(row["anchor_basket_count"]) - int(row["partner_basket_count"]) + both
    expected = row["anchor_basket_count"] * row["partner_basket_count"] / nb
    kpi_cards([("Pair count", n(both), "Baskets containing both items"),
               ("Support", f"{row['support']:.4f}", "pair count / all baskets"),
               ("Conf anchor→partner", f"{row['confidence_anchor_to_partner']:.3f}", f"Of anchor baskets, share also containing the partner"),
               ("Conf partner→anchor", f"{row['confidence_partner_to_anchor']:.3f}", None),
               ("Lift", f"{row['lift']:.2f}", "Observed ÷ expected co-occurrence"),
               ("Expected if independent", f"{expected:,.1f}", "anchor baskets × partner baskets ÷ all baskets")])

    left, right = st.columns(2)
    an, pn = labels[anchor].rsplit(" (", 1)[0], plabels[partner].rsplit(" (", 1)[0]
    cats = [("Both items", both, TEAL), (f"Only {an[:22]}", only_anchor, INDIGO), (f"Only {pn[:22]}", only_partner, AMBER)]
    fig = go.Figure(go.Bar(x=[c[0] for c in cats], y=[c[1] for c in cats], marker_color=[c[2] for c in cats],
                           text=[f"{c[1]:,}" for c in cats], textposition="outside",
                           hovertemplate="%{x}<br>%{y:,} baskets<extra></extra>"))
    fig.update_layout(title=f"Baskets by combination (+ {neither:,} with neither item)", yaxis_title="Baskets")
    with left:
        show(style(fig, 340), "pa_cont")
    fig = go.Figure(go.Bar(x=["Expected if independent", "Observed"], y=[expected, both], marker_color=[SLATE, TEAL],
                           text=[f"{expected:,.1f}", f"{both:,}"], textposition="outside"))
    fig.update_layout(title=f"Observed vs expected co-occurrence (lift {row['lift']:.2f})", yaxis_title="Baskets containing both")
    with right:
        show(style(fig, 340), "pa_exp")

    ctx = D["context"].data
    key = "|".join(sorted([anchor, partner]))
    if ctx is not None and (ctx["pair_key"] == key).any():
        c = ctx[ctx["pair_key"] == key]
        st.markdown("##### Where and when this pair was bought")
        l2, r2 = st.columns(2)
        by_c = c.groupby("country")["basket_occurrences"].sum().sort_values(ascending=False).head(10).iloc[::-1]
        fig = go.Figure(go.Bar(x=by_c.values, y=by_c.index, orientation="h", marker_color=AMBER))
        fig.update_layout(title="Baskets by country")
        with l2:
            show(style(fig, 300), "pa_ctry")
        by_m = c.groupby(c["transaction_date"].dt.to_period("M").dt.to_timestamp())["basket_occurrences"].sum()
        fig = go.Figure(go.Bar(x=by_m.index, y=by_m.values, marker_color=TEAL))
        fig.update_layout(title="Baskets by month")
        with r2:
            show(style(fig, 300), "pa_month")
    else:
        st.caption("Country and date detail is only packaged for the project's top-ranked pairs (Power BI workbook); "
                   "it is not available for this pair, and no values are estimated.")


# --------------------------------------------------------------------------- #
# 8. Data Quality Overview
# --------------------------------------------------------------------------- #
def page_quality() -> None:
    page_header("Data Quality Overview",
                "How the raw UCI Online Retail workbook became the cleaned basket population, what was removed and why, "
                "and how the Python results were checked against Oracle SQL.")
    raw, kept = K.get("raw_rows"), K.get("retained_clean_lines")
    dq = D["dq"].data
    miss = None
    if dq is not None and (dq["metric"] == "missing_customer_ids_raw").any():
        miss = float(dq.loc[dq["metric"] == "missing_customer_ids_raw", "value"].iloc[0])
    kpi_cards([
        ("Raw rows", n(raw), None),
        ("Retained lines", n(kept), pct(kept / raw, 2) + " of raw" if raw and kept else None),
        ("Removed rows", n(K.get("removed_rows")), pct(K["removed_rows"] / raw, 2) + " of raw" if raw and K.get("removed_rows") else None),
        ("Missing customer IDs", n(miss), (pct(miss / raw, 1) + " of raw · kept when item and basket are valid") if miss and raw else "Kept when item and basket are valid"),
        ("Single-item baskets", n(K.get("single_item_baskets")), pct(K.get("single_item_basket_pct"), 2) + " of baskets" if K.get("single_item_basket_pct") else None),
    ])

    audit = D["audit"].data
    left, right = st.columns(2)
    if audit is not None:
        a = audit.sort_values("row_count", ascending=False)
        ex = a[a["primary_exclusion_reason"] != "retained"].sort_values("row_count")
        fig = go.Figure(go.Bar(x=ex["row_count"], y=ex["reason_label"], orientation="h", marker_color=ROSE,
                               customdata=ex["pct_raw"], hovertemplate="%{y}<br>%{x:,} rows (%{customdata:.2f}% of raw)<extra></extra>"))
        fig.update_layout(title="Rows removed by primary reason")
        with left:
            show(style(fig, 340), "dq_excl")
        ret = a[a["primary_exclusion_reason"] == "retained"]["row_count"].sum()
        fig = go.Figure(go.Waterfall(
            x=["Raw rows"] + list(ex.sort_values("row_count", ascending=False)["reason_label"]) + ["Retained"],
            measure=["absolute"] + ["relative"] * len(ex) + ["total"],
            y=[raw or (ret + ex["row_count"].sum())] + list(-ex.sort_values("row_count", ascending=False)["row_count"]) + [None],
            increasing_marker_color=TEAL, decreasing_marker_color=ROSE, totals_marker_color=INDIGO,
            hovertemplate="%{x}<br>%{y:,}<extra></extra>"))
        fig.update_layout(title="Raw → retained bridge", xaxis=dict(tickangle=-20))
        with right:
            show(style(fig, 340), "dq_bridge")
        st.caption("Primary reasons are mutually exclusive (each removed row is counted once), so they sum exactly to the removed-row total.")
    else:
        st.info("Cleaning audit table not available (needs the Power BI workbook).")

    if dq is not None:
        st.markdown("##### Quality metrics")
        d2 = dq.copy()
        d2["pct_of_raw"] = d2["pct_of_raw"] * 100
        cat_filter = st.multiselect("Category", sorted(d2["category"].unique()), placeholder="All categories")
        if cat_filter:
            d2 = d2[d2["category"].isin(cat_filter)]
        st.dataframe(d2[["label", "category", "value", "pct_of_raw"]], hide_index=True, width="stretch", height=360, column_config={
            "label": "Metric", "category": "Category", "value": st.column_config.NumberColumn("Rows", format="%d"),
            "pct_of_raw": st.column_config.NumberColumn("% of raw rows", format="%.3f")})
        st.caption("Flag counts overlap (one row can carry several flags), e.g. 2,517 invalid-price rows are flagged but only 1,181 are "
                   "removed under that primary reason; the rest were already removed for an earlier-priority reason. "
                   "Only the primary-reason table above sums to the removed total.")

    left, right = st.columns(2)
    rare = D["rare"].data
    with left:
        st.markdown("##### Rare-item impact")
        if rare is not None:
            r = rare.copy()
            st.dataframe(r, hide_index=True, width="stretch", column_config={
                "population": "Population", "item_count": st.column_config.NumberColumn("Products", format="%d"),
                "basket_item_rows": st.column_config.NumberColumn("Basket-item rows", format="%d"),
                "pair_count_rows": st.column_config.NumberColumn("Candidate pair rows", format="%d")})
            st.caption(f"Excluding products below {D['cfg'].get('min_item_frequency', 5)} baskets from pair generation removes few "
                       "basket-item rows but sharply reduces candidate pairs.")
        else:
            st.info("rare_item_impact.csv not found.")
    with right:
        st.markdown("##### SQL ↔ Python reconciliation")
        rec = md.kpi_dict(D["recon"]) if D["recon"].ok else {}
        if rec:
            with st.container(border=True):
                st.metric("Status", str(rec.get("status", "n/a")))
                st.write(f"{n(rec.get('matching_pairs'))} of {n(rec.get('compared_pairs'))} pairs matched; {n(rec.get('failed_pairs'))} failed.")
                if rec.get("float_tolerance") is not None:
                    st.caption(f"Integer counts must match exactly; floating-point tolerance {rec['float_tolerance']}. "
                               "Result recorded from the committed Oracle run (GitHub Actions); it is not re-executed here.")
        else:
            st.info("Reconciliation summary not available.")

    st.markdown("##### Live integrity checks on the loaded pair table")
    chk = md.integrity_checks(PAIRS, K)
    st.dataframe(chk, hide_index=True, width="stretch", column_config={"check": "Check", "result": "Result", "detail": "Detail"})
    if (chk["result"] == "FAIL").any():
        st.error("One or more integrity checks failed - the loaded files are inconsistent with the documented formulas.")

    with st.expander("Methodology, thresholds and source"):
        cfg = D["cfg"]
        st.markdown(
            "**Formulas** (see `docs/kpi_definitions.md`)\n\n"
            "- `support(A,B) = pair_count(A,B) / eligible_basket_count`\n"
            "- `confidence(A→B) = pair_count(A,B) / basket_count(A)`; `confidence(B→A) = pair_count(A,B) / basket_count(B)`\n"
            "- `lift(A,B) = support(A,B) / (support(A) × support(B))`\n"
            "- Pairs are unordered and stored once with `item_a_key < item_b_key`."
        )
        st.json({k: cfg[k] for k in ("min_item_frequency", "min_pair_count", "min_support", "min_confidence", "top_n",
                                      "include_canceled_returns", "currency") if k in cfg})
        st.markdown("Dataset: UCI Online Retail (Chen, 2015), CC BY 4.0, "
                    "[DOI 10.24432/C5BW33](https://doi.org/10.24432/C5BW33). Observed co-occurrence is not evidence of causation.")


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
ROUTES = {
    "Executive Overview": page_overview,
    "Transaction & Basket KPIs": page_baskets,
    "Product Analysis": page_products,
    "Top 10 Frequent Item Pairs": page_top_count,
    "Top 10 Pairs by Lift": page_top_lift,
    "Support & Confidence": page_support_conf,
    "Interactive Pair Analysis": page_pair,
    "Data Quality Overview": page_quality,
}
if filters_active and page not in ("Executive Overview", "Transaction & Basket KPIs", "Data Quality Overview", "Product Analysis"):
    st.markdown(f'<span class="mba-pill">Filters active · {len(FILTERED):,} of {len(PAIRS):,} pairs</span>', unsafe_allow_html=True)
ROUTES[page]()
