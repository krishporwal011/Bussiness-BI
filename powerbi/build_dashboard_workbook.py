"""Build a small Power BI Service import workbook from the verified dashboard bundle."""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "dashboard" / "data" / "dashboard_data.json"
OUTPUT = ROOT / "powerbi" / "market_basket_dashboard_data.xlsx"


def write_table(ws, headers, rows):
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17324D")
    for row in rows:
        ws.append(row)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for column in ws.columns:
        width = min(max(len(str(cell.value or "")) for cell in column) + 2, 48)
        ws.column_dimensions[column[0].column_letter].width = width


def main():
    bundle = json.loads(SOURCE.read_text(encoding="utf-8"))
    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("KPI")
    write_table(ws, ["metric", "value"], [[key, value] for key, value in bundle["kpis"].items()])

    pair_headers = [
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
    for sheet_name, key in (("TopPairsCount", "count_pairs"), ("TopPairsLift", "lift_pairs")):
        ws = wb.create_sheet(sheet_name)
        write_table(ws, pair_headers, [[pair.get(header) for header in pair_headers] for pair in bundle[key]])

    ws = wb.create_sheet("ItemFrequency")
    write_table(ws, ["item_key", "item_name", "basket_count"], [
        [row["item_key"], row["item_name"], row["basket_count"]]
        for row in bundle["item_frequency"]
    ])

    ws = wb.create_sheet("Reconciliation")
    write_table(ws, ["metric", "value"], [[key, value] for key, value in bundle["reconciliation"].items()])

    ws = wb.create_sheet("Rules")
    write_table(ws, ["rule", "value"], [[key, value] for key, value in bundle["thresholds"].items()])

    ws = wb.create_sheet("RareItemImpact")
    rare = bundle["rare_item_impact"]
    write_table(ws, ["population", "item_count", "basket_item_rows", "pair_count_rows"], [
        [row["population"], row["item_count"], row["basket_item_rows"], row["pair_count_rows"]]
        for row in rare
    ])

    wb.properties.title = "Market Basket Analysis Dashboard Data"
    wb.properties.subject = "Verified Python and Oracle reconciliation results"
    wb.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
