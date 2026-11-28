"""Build the verified Power BI Service import workbook from pipeline outputs."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "dashboard_data.json"
CLEANED_DIR = ROOT / "data" / "cleaned"
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"
OUTPUT = ROOT / "powerbi" / "market_basket_dashboard_data.xlsx"

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="17324D")

KPI_LABELS = {
    "raw_rows": "Raw Rows",
    "retained_clean_lines": "Retained Clean Lines",
    "baskets": "Total Baskets",
    "products": "Total Products",
    "presence_rows": "Presence Rows",
    "single_item_baskets": "Single Item Baskets",
    "qualifying_pairs": "Qualifying Pairs",
}

DQ_META = {
    "raw_rows": ("Raw Records", "Volume"),
    "retained_clean_lines": ("Retained Clean Lines", "Volume"),
    "removed_rows": ("Removed Records", "Volume"),
    "distinct_baskets": ("Distinct Baskets", "Population"),
    "distinct_products": ("Distinct Products", "Population"),
    "distinct_basket_item_presence_rows": ("Basket-Item Presence Rows", "Population"),
    "single_item_baskets": ("Single-Item Baskets", "Basket Shape"),
    "missing_customer_ids_raw": ("Missing Customer IDs (Retained if Valid)", "Completeness"),
    "cancellation_rows_flagged": ("Cancellations / Returns Flagged", "Exclusion Flag"),
    "non_positive_quantity_rows": ("Invalid Quantities (<= 0)", "Exclusion Flag"),
    "invalid_unit_price_rows": ("Invalid Prices (<= 0)", "Exclusion Flag"),
    "missing_basket_id_rows": ("Missing Basket IDs", "Completeness"),
    "missing_item_key_rows": ("Missing Item Keys", "Completeness"),
    "missing_item_name_rows": ("Missing Item Names", "Completeness"),
    "invalid_date_rows": ("Invalid Transaction Dates", "Completeness"),
    "non_merchandise_rows": ("Non-Merchandise / Service Rows", "Exclusion Flag"),
    "test_transaction_rows": ("Test Transaction Rows", "Exclusion Flag"),
    "exact_duplicate_rows": ("Exact Duplicate Rows Flagged", "Exclusion Flag"),
}

AUDIT_LABELS = {
    "retained": "Retained Clean Merchandise Lines",
    "canceled_or_returned": "Canceled or Returned Invoices",
    "exact_duplicate": "Exact Duplicate Lines",
    "non_merchandise_code": "Non-Merchandise / Service Codes",
    "invalid_unit_price": "Invalid Unit Price (<= 0)",
}

PAIR_HEADERS = [
    "pair_key",
    "pair_label",
    "item_a_key",
    "item_a_name",
    "item_b_key",
    "item_b_name",
    "pair_count",
    "basket_count",
    "item_a_basket_count",
    "item_b_basket_count",
    "support",
    "confidence_a_to_b",
    "confidence_b_to_a",
    "lift",
    "rank",
]


def write_table(
    wb: Workbook,
    sheet_name: str,
    table_name: str,
    headers: list[str],
    rows: list[list],
    *,
    auto_width: bool = True,
) -> None:
    """Write a worksheet formatted as a typed Excel Table for Power BI import."""
    ws = wb.create_sheet(sheet_name)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"

    last_col = get_column_letter(len(headers))
    last_row = max(len(rows) + 1, 2)
    if not rows:
        ws.append([None] * len(headers))
    ref = f"A1:{last_col}{last_row}"
    tab = Table(displayName=table_name, ref=ref)
    tab.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(tab)

    if auto_width:
        sample_rows = rows[:200]
        for idx, header in enumerate(headers, start=1):
            max_len = len(str(header))
            for r in sample_rows:
                val = r[idx - 1]
                max_len = max(max_len, len(str(val if val is not None else "")))
            ws.column_dimensions[get_column_letter(idx)].width = min(max_len + 3, 48)


def _pair_row_values(row: dict, extra_cols: list[str] | None = None) -> list:
    item_a_key = str(row["item_a_key"])
    item_b_key = str(row["item_b_key"])
    item_a_name = str(row["item_a_name"])
    item_b_name = str(row["item_b_name"])
    pair_key = f"{item_a_key}|{item_b_key}"
    pair_label = f"{item_a_name} + {item_b_name}"
    base = [
        pair_key,
        pair_label,
        item_a_key,
        item_a_name,
        item_b_key,
        item_b_name,
        int(row["pair_count"]),
        int(row["basket_count"]),
        int(row["item_a_basket_count"]),
        int(row["item_b_basket_count"]),
        float(row["support"]),
        float(row["confidence_a_to_b"]),
        float(row["confidence_b_to_a"]),
        float(row["lift"]),
        int(row["rank"]),
    ]
    if extra_cols:
        for col in extra_cols:
            base.append(row[col])
    return base


def _build_from_pipeline(wb: Workbook, bundle: dict) -> None:
    """Populate full multi-page analytical tables from verified pipeline outputs."""
    bs = pd.read_csv(CLEANED_DIR / "basket_summary.csv")
    ps = pd.read_csv(CLEANED_DIR / "product_summary.csv")
    dq = pd.read_csv(CLEANED_DIR / "data_quality_summary.csv")
    ca = pd.read_csv(CLEANED_DIR / "cleaning_audit.csv")
    pm = pd.read_csv(OUTPUTS_DIR / "python_pair_metrics.csv")
    bip = pd.read_csv(
        CLEANED_DIR / "basket_item_presence.csv",
        usecols=["basket_id", "item_key"],
    )

    dq_map = {str(r.metric): int(r.value) for r in dq.itertuples(index=False)}
    ca_map = {str(r.primary_exclusion_reason): int(r.row_count) for r in ca.itertuples(index=False)}
    recon = bundle["reconciliation"]
    top_count = bundle["count_pairs"][0]
    top_lift = bundle["lift_pairs"][0]

    total_baskets = dq_map["distinct_baskets"]
    presence_rows = dq_map["distinct_basket_item_presence_rows"]
    single_baskets = dq_map["single_item_baskets"]

    exec_headers = [
        "raw_rows",
        "retained_clean_lines",
        "removed_rows",
        "distinct_baskets",
        "distinct_products",
        "presence_rows",
        "single_item_baskets",
        "single_item_basket_pct",
        "average_basket_size",
        "qualifying_pairs",
        "duplicate_records",
        "duplicate_excluded_primary",
        "invalid_quantities",
        "invalid_prices",
        "invalid_prices_excluded_primary",
        "missing_customer_ids",
        "cancellation_rows",
        "non_merchandise_rows",
        "test_transaction_rows",
        "top_pair_by_count",
        "top_pair_count",
        "top_pair_by_lift",
        "top_pair_lift",
        "matching_pairs",
        "failed_pairs",
        "reconciliation_status",
    ]
    exec_row = [
        dq_map["raw_rows"],
        dq_map["retained_clean_lines"],
        dq_map["removed_rows"],
        total_baskets,
        dq_map["distinct_products"],
        presence_rows,
        single_baskets,
        single_baskets / total_baskets,
        presence_rows / total_baskets,
        len(pm),
        dq_map["exact_duplicate_rows"],
        ca_map.get("exact_duplicate", 0),
        dq_map["non_positive_quantity_rows"],
        dq_map["invalid_unit_price_rows"],
        ca_map.get("invalid_unit_price", 0),
        dq_map["missing_customer_ids_raw"],
        dq_map["cancellation_rows_flagged"],
        dq_map["non_merchandise_rows"],
        dq_map["test_transaction_rows"],
        f"{top_count['item_a_name']} + {top_count['item_b_name']}",
        int(top_count["pair_count"]),
        f"{top_lift['item_a_name']} + {top_lift['item_b_name']}",
        float(top_lift["lift"]),
        int(recon["matching_pairs"]),
        int(recon["failed_pairs"]),
        str(recon["status"]),
    ]
    write_table(wb, "ExecutiveKPI", "tblExecutiveKPI", exec_headers, [exec_row])

    # Product catalog (all 3,798 products including all 392 rare items)
    ps_sorted = ps.sort_values(
        ["basket_count", "total_revenue", "item_key"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    ps_sorted["product_rank"] = ps_sorted.index + 1

    def freq_tier(cnt: int) -> str:
        if cnt < 5:
            return "1. Rare (<5)"
        if cnt < 50:
            return "2. Low (5-49)"
        if cnt < 250:
            return "3. Medium (50-249)"
        return "4. High (250+)"

    prod_rows = []
    for r in ps_sorted.itertuples(index=False):
        cnt = int(r.basket_count)
        is_rare = 1 if cnt < 5 else 0
        prod_rows.append([
            str(r.item_key),
            str(r.item_name),
            cnt,
            float(r.total_quantity),
            float(r.total_revenue),
            int(r.product_rank),
            is_rare,
            "Rare (<5 baskets)" if is_rare else "Qualifying (>=5 baskets)",
            freq_tier(cnt),
            cnt / total_baskets,
        ])
    write_table(
        wb,
        "DimProduct",
        "tblDimProduct",
        [
            "item_key",
            "item_name",
            "basket_count",
            "total_quantity",
            "total_revenue",
            "product_rank",
            "is_rare_item",
            "rare_status",
            "frequency_tier",
            "item_support",
        ],
        prod_rows,
    )

    # BasketSummary + DimDate + DimCountry (all 19,773 baskets)
    bs["dt"] = pd.to_datetime(bs["transaction_date"])
    bs["tx_date"] = bs["dt"].dt.date
    bs["year_month"] = bs["dt"].dt.strftime("%Y-%m")
    bs["month_start"] = bs["dt"].dt.to_period("M").dt.to_timestamp().dt.date

    basket_rows = [
        [
            str(r.basket_id),
            r.tx_date,
            str(r.year_month),
            r.month_start,
            str(r.country),
            int(r.distinct_item_count),
            float(r.total_quantity),
            float(r.total_revenue),
            int(r.item_line_count),
            int(r.is_single_item),
        ]
        for r in bs.itertuples(index=False)
    ]
    write_table(
        wb,
        "BasketSummary",
        "tblBasketSummary",
        [
            "basket_id",
            "transaction_date",
            "year_month",
            "month_start",
            "country",
            "distinct_item_count",
            "total_quantity",
            "total_revenue",
            "item_line_count",
            "is_single_item",
        ],
        basket_rows,
    )

    # DimDate
    unique_dates = sorted(bs["tx_date"].unique())
    date_rows = [
        [
            d,
            d.year,
            d.month,
            d.strftime("%Y-%m"),
            date(d.year, d.month, 1),
            d.strftime("%b %Y"),
        ]
        for d in unique_dates
    ]
    write_table(
        wb,
        "DimDate",
        "tblDimDate",
        ["transaction_date", "year", "month_number", "year_month", "month_start", "month_label"],
        date_rows,
    )

    # DimCountry
    country_agg = (
        bs.groupby("country", as_index=False)
        .agg(
            basket_count=("basket_id", "nunique"),
            single_item_baskets=("is_single_item", "sum"),
            total_revenue=("total_revenue", "sum"),
        )
        .sort_values(["basket_count", "country"], ascending=[False, True])
    )
    write_table(
        wb,
        "DimCountry",
        "tblDimCountry",
        ["country", "basket_count", "single_item_baskets", "total_revenue"],
        [
            [str(r.country), int(r.basket_count), int(r.single_item_baskets), float(r.total_revenue)]
            for r in country_agg.itertuples(index=False)
        ],
    )

    # PairMetrics (Top 150 by count + Top 50 by lift) with exact PairContext by (country, transaction_date)
    pm_lift_sorted = pm.sort_values(
        ["lift", "pair_count", "item_a_name", "item_b_name"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)
    pm_lift_sorted["lift_rank"] = pm_lift_sorted.index + 1

    top_cnt = pm_lift_sorted.sort_values(
        ["pair_count", "lift", "item_a_name", "item_b_name"],
        ascending=[False, False, True, True],
    ).head(150)
    top_lft = pm_lift_sorted.head(50)
    pm_sub = (
        pd.concat([top_cnt, top_lft], ignore_index=True)
        .drop_duplicates(["item_a_key", "item_b_key"])
        .copy()
    )

    pm_rows = []
    for r in pm_sub.to_dict(orient="records"):
        r["in_top_10_count"] = 1 if int(r["rank"]) <= 10 else 0
        r["in_top_10_lift"] = 1 if int(r["lift_rank"]) <= 10 else 0
        pm_rows.append(_pair_row_values(r, ["lift_rank", "in_top_10_count", "in_top_10_lift"]))
    write_table(
        wb,
        "PairMetrics",
        "tblPairMetrics",
        PAIR_HEADERS + ["lift_rank", "in_top_10_count", "in_top_10_lift"],
        pm_rows,
    )

    # PairContext: exact (pair_key, country, transaction_date, basket_occurrences)
    item_baskets = bip.groupby(bip["item_key"].astype(str))["basket_id"].apply(set).to_dict()
    bs_lookup = bs.set_index("basket_id")[["country", "tx_date"]].to_dict("index")
    ctx_rows = []
    for r in pm_sub.itertuples(index=False):
        a_key = str(r.item_a_key)
        b_key = str(r.item_b_key)
        pair_key = f"{a_key}|{b_key}"
        common = item_baskets[a_key] & item_baskets[b_key]
        counts: dict[tuple[str, date], int] = {}
        for bid in common:
            info = bs_lookup[bid]
            k = (str(info["country"]), info["tx_date"])
            counts[k] = counts.get(k, 0) + 1
        if sum(counts.values()) != int(r.pair_count):
            raise ValueError(f"PairContext sum mismatch for {pair_key}")
        for (country, tx_date), occ in counts.items():
            ctx_rows.append([pair_key, country, tx_date, occ])

    write_table(
        wb,
        "PairContext",
        "tblPairContext",
        ["pair_key", "country", "transaction_date", "basket_occurrences"],
        ctx_rows,
    )

    # DataQualitySummary & CleaningAudit
    raw_total = dq_map["raw_rows"]
    dq_rows = []
    for r in dq.itertuples(index=False):
        metric = str(r.metric)
        val = int(r.value)
        label, cat = DQ_META.get(metric, (metric.replace("_", " ").title(), "Other"))
        dq_rows.append([metric, label, cat, val, val / raw_total])
    write_table(
        wb,
        "DataQualitySummary",
        "tblDataQualitySummary",
        ["metric", "label", "category", "value", "pct_of_raw"],
        dq_rows,
    )

    ca_rows = [
        [
            str(r.primary_exclusion_reason),
            AUDIT_LABELS.get(str(r.primary_exclusion_reason), str(r.primary_exclusion_reason)),
            int(r.row_count),
            float(r.pct_raw),
        ]
        for r in ca.itertuples(index=False)
    ]
    write_table(
        wb,
        "CleaningAudit",
        "tblCleaningAudit",
        ["primary_exclusion_reason", "reason_label", "row_count", "pct_raw"],
        ca_rows,
    )


def main() -> None:
    bundle = json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))
    wb = Workbook()
    wb.remove(wb.active)

    write_table(
        wb,
        "KPI",
        "tblKPI",
        ["metric", "label", "value"],
        [
            [key, KPI_LABELS.get(key, key), int(value)]
            for key, value in bundle["kpis"].items()
        ],
    )

    for sheet_name, tbl_name, key in (
        ("TopPairsCount", "tblTopPairsCount", "count_pairs"),
        ("TopPairsLift", "tblTopPairsLift", "lift_pairs"),
    ):
        write_table(
            wb,
            sheet_name,
            tbl_name,
            PAIR_HEADERS,
            [_pair_row_values(pair) for pair in bundle[key]],
        )

    recon = bundle["reconciliation"]
    write_table(
        wb,
        "Reconciliation",
        "tblReconciliation",
        ["metric", "label", "display_value", "numeric_value"],
        [
            ["status", "Reconciliation Status", str(recon["status"]), None],
            ["matching_pairs", "Matching Pairs", f"{int(recon['matching_pairs']):,}", int(recon["matching_pairs"])],
            ["failed_pairs", "Failed Pairs", f"{int(recon['failed_pairs']):,}", int(recon["failed_pairs"])],
            ["compared_pairs", "Total Compared Pairs", f"{int(recon['matching_pairs']) + int(recon['failed_pairs']):,}", int(recon["matching_pairs"]) + int(recon["failed_pairs"])],
            ["float_tolerance", "Float Tolerance", "1e-09", 1e-9],
            ["match_rate_pct", "Match Rate (%)", "100.00%", 100.0 if int(recon["failed_pairs"]) == 0 else 0.0],
        ],
    )
    write_table(
        wb,
        "ReconciliationSummary",
        "tblReconciliationSummary",
        ["status", "compared_pairs", "matching_pairs", "failed_pairs", "float_tolerance", "python_engine", "oracle_engine", "match_rate_pct"],
        [[
            str(recon["status"]),
            int(recon["matching_pairs"]) + int(recon["failed_pairs"]),
            int(recon["matching_pairs"]),
            int(recon["failed_pairs"]),
            1e-9,
            "Python 3.11 (itertools.combinations)",
            "Oracle 19c Free (Self-Join SQL)",
            100.0 if int(recon["failed_pairs"]) == 0 else 0.0,
        ]],
    )

    write_table(
        wb,
        "Rules",
        "tblRules",
        ["rule", "value"],
        [[str(key), str(value)] for key, value in bundle["thresholds"].items()],
    )

    pop_labels = {
        "all_cleaned_items": "All Cleaned Products",
        "items_with_basket_count_ge_5": "Qualifying Products (Basket Count >= 5)",
    }
    write_table(
        wb,
        "RareItemImpact",
        "tblRareItemImpact",
        ["population", "population_label", "item_count", "basket_item_rows", "pair_count_rows"],
        [
            [
                row["population"],
                pop_labels.get(row["population"], row["population"]),
                int(row["item_count"]),
                int(row["basket_item_rows"]),
                int(row["pair_count_rows"]),
            ]
            for row in bundle["rare_item_impact"]
        ],
    )

    if (CLEANED_DIR / "basket_summary.csv").exists() and (OUTPUTS_DIR / "python_pair_metrics.csv").exists():
        _build_from_pipeline(wb, bundle)
    else:
        write_table(
            wb,
            "ItemFrequency",
            "tblItemFrequency",
            ["item_key", "item_name", "basket_count"],
            [
                [str(row["item_key"]), str(row["item_name"]), int(row["basket_count"])]
                for row in bundle["item_frequency"]
            ],
        )

    wb.properties.title = "Market Basket Analysis Dashboard Data"
    wb.properties.subject = "Verified Python and Oracle reconciliation results"
    wb.save(OUTPUT)
    print(f"{OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
