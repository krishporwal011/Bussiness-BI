#!/usr/bin/env python3
"""Clean the UCI Online Retail workbook into reproducible basket tables.

The raw workbook is never modified. The script writes normalized staging data,
clean transaction lines, one-row-per-basket-item presence, basket summaries,
product summaries, and a quantified data-quality report.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


EXCLUDED_MERCHANDISE_CODES = {
    "AMAZONFEE",
    "BANK CHARGES",
    "B",
    "C2",
    "CRUK",
    "D",
    "M",
    "PADS",
    "POST",
    "S",
    "DOT",
}


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalize_customer_id(values: pd.Series) -> pd.Series:
    normalized = values.astype("string").str.strip()
    normalized = normalized.str.replace(r"\.0$", "", regex=True)
    normalized = normalized.mask(
        normalized.str.upper().isin(["", "NAN", "NONE", "<NA>"]), pd.NA
    )
    return normalized


def _standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        "InvoiceNo": "invoice_id",
        "StockCode": "item_key",
        "Description": "item_name",
        "Quantity": "quantity",
        "InvoiceDate": "transaction_date",
        "UnitPrice": "unit_price",
        "CustomerID": "customer_id",
        "Country": "country",
    }
    missing = sorted(set(mapping) - set(frame.columns))
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")
    frame = frame.rename(columns=mapping).copy()
    frame.insert(0, "source_row_number", np.arange(1, len(frame) + 1))
    frame["invoice_id"] = frame["invoice_id"].astype("string").str.strip().str.upper()
    frame["item_key"] = frame["item_key"].astype("string").str.strip().str.upper()
    frame["item_name"] = frame["item_name"].astype("string").str.strip().str.upper()
    frame["item_name"] = frame["item_name"].mask(frame["item_name"].isin(["", "NAN", "NONE"]), pd.NA)
    frame["customer_id"] = normalize_customer_id(frame["customer_id"])
    frame["country"] = frame["country"].astype("string").str.strip()
    frame["country"] = frame["country"].mask(frame["country"].isin(["", "NAN", "NONE"]), pd.NA)
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
    frame["transaction_date"] = pd.to_datetime(frame["transaction_date"], errors="coerce")
    frame["line_revenue"] = frame["quantity"] * frame["unit_price"]
    return frame


def read_source(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
        raw = pd.read_excel(
            path,
            engine="openpyxl" if path.suffix.lower() != ".xls" else None,
            dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string"},
        )
    elif path.suffix.lower() == ".csv":
        raw = pd.read_csv(path, dtype={"InvoiceNo": "string", "StockCode": "string", "CustomerID": "string"})
    else:
        raise ValueError(f"Unsupported input format: {path.suffix}")
    return _standardize_columns(raw)


def build_quality_flags(frame: pd.DataFrame, include_canceled_returns: bool) -> pd.DataFrame:
    flags = pd.DataFrame(index=frame.index)
    flags["is_cancellation"] = frame["invoice_id"].fillna("").str.startswith("C")
    flags["is_test_transaction"] = (
        frame["invoice_id"].fillna("").str.contains("TEST", case=False, regex=False)
        | frame["item_name"].fillna("").str.contains(r"\bTEST\b", case=False, regex=True)
    )
    duplicate_columns = [column for column in frame.columns if column != "source_row_number"]
    flags["is_exact_duplicate"] = frame[duplicate_columns].duplicated(keep="first")
    flags["is_non_merchandise"] = (
        frame["item_key"].isin(EXCLUDED_MERCHANDISE_CODES)
        | frame["item_key"].fillna("").str.startswith("GIFT_")
    )
    flags["missing_basket_id"] = frame["invoice_id"].isna() | frame["invoice_id"].eq("")
    flags["missing_item_key"] = frame["item_key"].isna() | frame["item_key"].eq("")
    flags["missing_item_name"] = frame["item_name"].isna() | frame["item_name"].eq("")
    flags["missing_customer_id"] = frame["customer_id"].isna() | frame["customer_id"].eq("")
    flags["invalid_date"] = frame["transaction_date"].isna()
    flags["invalid_quantity"] = frame["quantity"].isna()
    flags["non_positive_quantity"] = frame["quantity"].notna() & frame["quantity"].le(0)
    flags["invalid_unit_price"] = frame["unit_price"].isna() | frame["unit_price"].le(0)

    # This is deliberately configurable. The default is the conservative
    # merchandise-basket interpretation: cancellations and returns do not add
    # product presence. If enabled, they are retained after other validation.
    if not include_canceled_returns:
        flags["exclude_canceled_returns"] = flags["is_cancellation"] | flags["non_positive_quantity"]
    else:
        flags["exclude_canceled_returns"] = False
    return flags


def assign_exclusion_reason(flags: pd.DataFrame) -> pd.Series:
    priority: Iterable[tuple[str, str]] = (
        ("exclude_canceled_returns", "canceled_or_returned"),
        ("invalid_quantity", "invalid_quantity"),
        ("invalid_unit_price", "invalid_unit_price"),
        ("missing_basket_id", "missing_basket_id"),
        ("missing_item_key", "missing_item_key"),
        ("missing_item_name", "missing_item_name"),
        ("invalid_date", "invalid_date"),
        ("is_non_merchandise", "non_merchandise_code"),
        ("is_test_transaction", "test_transaction"),
        ("is_exact_duplicate", "exact_duplicate"),
    )
    reason = pd.Series(pd.NA, index=flags.index, dtype="string")
    for flag, label in priority:
        reason = reason.mask(reason.isna() & flags[flag], label)
    return reason.fillna("retained")


def _markdown_table(rows: list[tuple[str, int, float, str]]) -> str:
    lines = ["| Metric | Rows | % of raw | Treatment |", "|---|---:|---:|---|"]
    lines.extend(f"| {label} | {count:,} | {pct:.2f}% | {treatment} |" for label, count, pct, treatment in rows)
    return "\n".join(lines)


def write_quality_report(
    report_path: Path,
    raw_rows: int,
    retained_rows: int,
    flags: pd.DataFrame,
    reasons: pd.Series,
    presence: pd.DataFrame,
    baskets: pd.DataFrame,
    config: dict,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, int, float, str]] = []
    for label, count, treatment in [
        ("Raw rows", raw_rows, "Source count; workbook preserved unchanged"),
        ("Retained cleaned lines", retained_rows, "Used for merchandise analysis"),
        ("Removed rows", raw_rows - retained_rows, "Sum of mutually exclusive exclusion reasons"),
        ("Cancellations/returns flagged", int(flags["is_cancellation"].sum()), "Excluded by default"),
        ("Non-positive quantity flagged", int(flags["non_positive_quantity"].sum()), "Excluded by default"),
        ("Exact duplicate rows flagged", int(flags["is_exact_duplicate"].sum()), "First row retained"),
        ("Missing customer IDs", int(flags["missing_customer_id"].sum()), "Retained when other fields are valid"),
        ("Single-item baskets", int(baskets["is_single_item"].sum()), "Kept in basket population and support denominator"),
    ]:
        rows.append((label, count, (count / raw_rows * 100) if raw_rows else 0, treatment))

    reason_counts = reasons.value_counts().to_dict()
    for reason, count in sorted(reason_counts.items()):
        if reason == "retained":
            continue
        rows.append((f"Exclusion: {reason}", int(count), float(count / raw_rows * 100), "Primary reason assigned"))

    missing_customer_count = 0
    # The source count is passed indirectly through the normalized flags index;
    # this is overwritten by the caller's generated summary below when present.
    report = f"""# Data quality report

Generated by `src/clean_data.py` from the UCI Online Retail workbook.

## Cleaning decision summary

The raw workbook is never modified. Rows are normalized, flagged, and assigned one primary exclusion reason using a deterministic priority. The default association-analysis population excludes cancellation/return invoices, non-positive quantities, invalid prices, missing basket/item/name/date fields, known service or adjustment codes, test rows, and exact duplicate rows. Missing customer IDs are not an exclusion because customer identity is not required to define basket-item presence.

Configuration: `min_item_frequency={config['min_item_frequency']}`, `include_canceled_returns={config['include_canceled_returns']}`.

{_markdown_table(rows)}

## Primary exclusion counts

| Primary reason | Rows |
|---|---:|
"""
    report += "\n".join(f"| {reason} | {int(count):,} |" for reason, count in sorted(reason_counts.items()))
    report += f"""

## Output grains

- Clean transaction lines: one retained source line per row after validation and deduplication.
- Basket-item presence: one row per `(basket_id, item_key)`; quantity and revenue are aggregated separately.
- Basket summary: one row per valid basket. Single-item baskets are retained and counted in the support denominator.
- Product summary: one row per normalized product key with basket count, quantity, and revenue.

The cleaned output contains {len(presence):,} distinct basket-item presence rows across {len(baskets):,} baskets and {presence['item_key'].nunique():,} products.

## Data-quality interpretation

Counts are generated from the current workbook and may change if UCI republishes the file. Overlapping flags are available in `data/derived/sql_staging.csv`; the primary reason table is mutually exclusive and is the basis for the removed-row total. The SQL implementation repeats the same business filters and deduplicates before self-joining so duplicate source lines cannot inflate pair counts.
"""
    report_path.write_text(report, encoding="utf-8")


def run(input_path: Path, output_dir: Path, derived_dir: Path, report_path: Path, config_path: Path) -> dict:
    config = load_config(config_path)
    frame = read_source(input_path)
    raw_rows = len(frame)
    flags = build_quality_flags(frame, bool(config.get("include_canceled_returns", False)))
    reasons = assign_exclusion_reason(flags)
    frame = frame.join(flags)
    frame["exclusion_reason"] = reasons
    frame["is_retained"] = reasons.eq("retained")

    output_dir.mkdir(parents=True, exist_ok=True)
    derived_dir.mkdir(parents=True, exist_ok=True)

    # Normalized staging is derived data for SQL loading; it is not the raw file.
    staging_columns = [
        "source_row_number", "invoice_id", "item_key", "item_name", "quantity",
        "transaction_date", "unit_price", "customer_id", "country", "line_revenue",
        "is_cancellation", "is_non_merchandise", "is_exact_duplicate", "is_test_transaction",
        "exclusion_reason", "is_retained",
    ]
    staging = frame[staging_columns].copy()
    for flag_column in [
        "is_cancellation", "is_non_merchandise", "is_exact_duplicate",
        "is_test_transaction", "is_retained",
    ]:
        staging[flag_column] = staging[flag_column].astype(int)
    staging.to_csv(derived_dir / "sql_staging.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

    clean = frame.loc[frame["is_retained"], [
        "source_row_number", "invoice_id", "item_key", "item_name", "quantity",
        "transaction_date", "unit_price", "line_revenue", "customer_id", "country",
    ]].rename(columns={"invoice_id": "basket_id"})
    clean.to_csv(output_dir / "cleaned_transaction_lines.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

    presence = (
        clean.groupby(["basket_id", "item_key"], as_index=False, dropna=False)
        .agg(
            item_name=("item_name", "first"),
            transaction_date=("transaction_date", "min"),
            customer_id=("customer_id", "first"),
            country=("country", "first"),
            quantity=("quantity", "sum"),
            revenue=("line_revenue", "sum"),
            line_count=("item_key", "size"),
        )
    )
    presence["presence"] = 1
    presence.to_csv(output_dir / "basket_item_presence.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

    baskets = (
        presence.groupby("basket_id", as_index=False)
        .agg(
            transaction_date=("transaction_date", "min"),
            customer_id=("customer_id", "first"),
            country=("country", "first"),
            distinct_item_count=("item_key", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
            item_line_count=("line_count", "sum"),
        )
    )
    baskets["is_single_item"] = baskets["distinct_item_count"].eq(1).astype(int)
    baskets.to_csv(output_dir / "basket_summary.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

    products = (
        presence.groupby("item_key", as_index=False)
        .agg(
            item_name=("item_name", "first"),
            basket_count=("basket_id", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .sort_values(["basket_count", "item_key"], ascending=[False, True])
    )
    products.to_csv(output_dir / "product_summary.csv", index=False)

    summary_rows = [
        ("raw_rows", raw_rows),
        ("retained_clean_lines", int(len(clean))),
        ("removed_rows", int(raw_rows - len(clean))),
        ("distinct_baskets", int(len(baskets))),
        ("distinct_products", int(len(products))),
        ("distinct_basket_item_presence_rows", int(len(presence))),
        ("single_item_baskets", int(baskets["is_single_item"].sum())),
        ("missing_customer_ids_raw", int(frame["customer_id"].isna().sum())),
        ("cancellation_rows_flagged", int(flags["is_cancellation"].sum())),
        ("non_positive_quantity_rows", int(flags["non_positive_quantity"].sum())),
        ("invalid_unit_price_rows", int(flags["invalid_unit_price"].sum())),
        ("missing_basket_id_rows", int(flags["missing_basket_id"].sum())),
        ("missing_item_key_rows", int(flags["missing_item_key"].sum())),
        ("missing_item_name_rows", int(flags["missing_item_name"].sum())),
        ("invalid_date_rows", int(flags["invalid_date"].sum())),
        ("non_merchandise_rows", int(flags["is_non_merchandise"].sum())),
        ("test_transaction_rows", int(flags["is_test_transaction"].sum())),
        ("exact_duplicate_rows", int(flags["is_exact_duplicate"].sum())),
    ]
    pd.DataFrame(summary_rows, columns=["metric", "value"]).to_csv(output_dir / "data_quality_summary.csv", index=False)
    pd.DataFrame(
        [(reason, int(count), float(count / raw_rows * 100)) for reason, count in reasons.value_counts().items()],
        columns=["primary_exclusion_reason", "row_count", "pct_raw"],
    ).to_csv(output_dir / "cleaning_audit.csv", index=False)
    (output_dir / "cleaning_config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    write_quality_report(report_path, raw_rows, len(clean), flags, reasons, presence, baskets, config)
    return {
        "raw_rows": raw_rows,
        "clean_rows": len(clean),
        "baskets": len(baskets),
        "products": len(products),
        "presence_rows": len(presence),
        "single_item_baskets": int(baskets["is_single_item"].sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/Online Retail.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/cleaned"))
    parser.add_argument("--derived-dir", type=Path, default=Path("data/derived"))
    parser.add_argument("--report", type=Path, default=Path("reports/data_quality_report.md"))
    parser.add_argument("--config", type=Path, default=Path("config/analysis_config.json"))
    args = parser.parse_args()
    result = run(args.input, args.output_dir, args.derived_dir, args.report, args.config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
