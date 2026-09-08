"""
Build the final Ocean Finance Excel workings workbook.

This is the presentation layer only. Analytical logic lives in SQL and in
`src/run_conditional_counterfactual.py`.

Final run order (from repository root)
--------------------------------------
python src/build_database.py
python src/export_analysis_tables.py
python src/run_conditional_counterfactual.py
python src/build_excel_workings.py

The earlier `src/run_counterfactual.py` is retained as exploratory history,
but it is NOT used by this workbook.

Dependencies
------------
pandas
XlsxWriter
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd


FILES = {
    # Observed / SQL outputs
    "panel": "panel_baseline.csv",
    "cards": "card_performance.csv",
    "context": "card29_context.csv",

    # Final conditional-counterfactual outputs
    "intervention": "conditional_intervention_summary.csv",
    "alternatives": "conditional_alternative_distribution.csv",
    "rank1_distribution": "conditional_rank1_distribution.csv",
    "support": "conditional_support_summary.csv",
    "rank1_predictions": "conditional_rank1_predictions.csv",
    "expected_clicks": "conditional_expected_clicks_by_card.csv",
    "economics": "conditional_supported_economics.csv",
    "residual": "conditional_residual_apps.csv",
    "break_even": "conditional_break_even_sensitivity.csv",
    "break_even_matrix": "conditional_break_even_matrix.csv",
}

# This was validated in Notebook 2 from Card-29-absent applications.
# It is a presentation note, not an input to the counterfactual calculation.
HISTORICAL_RANK1_CLICK_SHARE = 0.956198


# ---------------------------------------------------------------------------
# Input / output
# ---------------------------------------------------------------------------

def load_inputs(table_dir: Path) -> dict[str, pd.DataFrame]:
    missing = [
        table_dir / filename
        for filename in FILES.values()
        if not (table_dir / filename).exists()
    ]

    if missing:
        missing_text = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(
            "Missing analysis outputs:\n"
            f"{missing_text}\n\n"
            "Run export_analysis_tables.py and "
            "run_conditional_counterfactual.py first."
        )

    return {
        key: pd.read_csv(table_dir / filename)
        for key, filename in FILES.items()
    }


def get_scalar(df: pd.DataFrame, key_col: str, key: str, value_col: str) -> float:
    row = df.loc[df[key_col].eq(key)]
    if len(row) != 1:
        raise ValueError(f"Expected one row where {key_col}={key!r}; found {len(row)}")
    return float(row.iloc[0][value_col])


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def make_formats(workbook):
    colors = {
        "dark_teal": "#0F5D75",
        "mid_teal": "#2F7E96",
        "light_blue": "#D9EAF2",
        "light_teal": "#EAF4F8",
        "gold": "#E3A008",
        "pale_gold": "#FFF2CC",
        "light_green": "#E8F5E9",
        "light_red": "#FDECEC",
        "light_gray": "#F3F4F6",
        "text": "#1F2937",
        "muted": "#5F6B76",
        "white": "#FFFFFF",
    }

    f: dict[str, object] = {}

    f["title"] = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": colors["white"],
        "bg_color": colors["dark_teal"],
        "valign": "vcenter",
    })

    f["subtitle"] = workbook.add_format({
        "italic": True,
        "font_size": 10,
        "font_color": colors["muted"],
    })

    f["header"] = workbook.add_format({
        "bold": True,
        "font_color": colors["white"],
        "bg_color": colors["dark_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
        "border": 0,
    })

    f["section"] = workbook.add_format({
        "bold": True,
        "font_color": "#163A4A",
        "bg_color": colors["light_blue"],
        "valign": "vcenter",
    })

    f["subheader"] = workbook.add_format({
        "bold": True,
        "font_color": colors["white"],
        "bg_color": colors["mid_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    f["text"] = workbook.add_format({
        "font_size": 10,
        "font_color": colors["text"],
    })

    f["text_wrap"] = workbook.add_format({
        "font_size": 10,
        "font_color": colors["text"],
        "text_wrap": True,
        "valign": "top",
    })

    f["center"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "valign": "vcenter",
    })

    f["int"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "num_format": "#,##0",
    })

    f["decimal"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "num_format": "0.00",
    })

    f["pct"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "num_format": "0.0%",
    })

    f["currency"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "num_format": "£#,##0.00;[Red]-£#,##0.00",
    })

    f["currency_delta"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "align": "center",
        "num_format": "+£#,##0;[Red]-£#,##0;£0",
    })

    f["kpi_label"] = workbook.add_format({
        "bold": True,
        "font_size": 9,
        "font_color": colors["dark_teal"],
        "bg_color": colors["light_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
        "border": 1,
        "border_color": "#D7E3E8",
    })

    f["kpi_int"] = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": colors["text"],
        "align": "center",
        "valign": "vcenter",
        "num_format": "#,##0",
        "border": 1,
        "border_color": "#D7E3E8",
    })

    f["kpi_decimal"] = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": colors["text"],
        "align": "center",
        "valign": "vcenter",
        "num_format": "0.00",
        "border": 1,
        "border_color": "#D7E3E8",
    })

    f["kpi_pct"] = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": colors["text"],
        "align": "center",
        "valign": "vcenter",
        "num_format": "0.0%",
        "border": 1,
        "border_color": "#D7E3E8",
    })

    f["kpi_currency"] = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "font_color": colors["text"],
        "align": "center",
        "valign": "vcenter",
        "num_format": "£#,##0.00;[Red]-£#,##0.00",
        "border": 1,
        "border_color": "#D7E3E8",
    })

    f["note"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "bg_color": colors["light_gray"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["gold_note"] = workbook.add_format({
        "font_size": 9,
        "font_color": "#6B4E00",
        "bg_color": colors["pale_gold"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["green_note"] = workbook.add_format({
        "font_size": 9,
        "font_color": "#176B3A",
        "bg_color": colors["light_green"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["red_note"] = workbook.add_format({
        "font_size": 9,
        "font_color": "#B42318",
        "bg_color": colors["light_red"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["card29"] = workbook.add_format({
        "bold": True,
        "font_color": "#7A4E00",
        "bg_color": colors["pale_gold"],
    })

    f["comparator"] = workbook.add_format({
        "bg_color": colors["light_teal"],
    })

    f["footer"] = workbook.add_format({
        "italic": True,
        "font_size": 8,
        "font_color": colors["muted"],
    })

    return colors, f


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_df(
    worksheet,
    df: pd.DataFrame,
    start_row: int,
    start_col: int,
    header_format,
    column_formats: dict[str, object] | None = None,
):
    column_formats = column_formats or {}

    for col_offset, column in enumerate(df.columns):
        worksheet.write(start_row, start_col + col_offset, column, header_format)

    for row_offset, row in enumerate(df.itertuples(index=False, name=None), start=1):
        for col_offset, value in enumerate(row):
            column_name = df.columns[col_offset]
            cell_format = column_formats.get(column_name)

            if isinstance(value, np.generic):
                value = value.item()

            if pd.isna(value):
                worksheet.write_blank(
                    start_row + row_offset,
                    start_col + col_offset,
                    None,
                    cell_format,
                )
            else:
                worksheet.write(
                    start_row + row_offset,
                    start_col + col_offset,
                    value,
                    cell_format,
                )


def add_sheet_title(ws, title: str, subtitle: str, f, end_col: int = 7):
    ws.merge_range(0, 0, 1, end_col, title, f["title"])
    ws.set_row(0, 26)
    ws.set_row(1, 26)
    ws.merge_range(2, 0, 2, end_col, subtitle, f["subtitle"])


# ---------------------------------------------------------------------------
# 1. Summary placeholder
# ---------------------------------------------------------------------------

def add_summary_placeholder(workbook, f):
    ws = workbook.add_worksheet("1. Summary")
    ws.hide_gridlines(2)
    ws.set_zoom(90)
    ws.set_column("A:A", 3)
    ws.set_column("B:H", 18)

    ws.merge_range("B2:H3", "Credit Card Panel Performance Review", f["title"])
    ws.merge_range(
        "B5:H8",
        "Summary intentionally left as a paste-ready placeholder. "
        "Paste the final executive Summary sheet here after the working sheets are generated.",
        f["note"],
    )


# ---------------------------------------------------------------------------
# 2. Panel Baseline
# ---------------------------------------------------------------------------

def add_panel_baseline(workbook, data, f):
    ws = workbook.add_worksheet("2. Panel Baseline")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 0)
    ws.set_zoom(90)

    formats = {
        "total_applications": f["int"],
        "total_offers": f["int"],
        "applications_with_click": f["int"],
        "total_clicks": f["int"],
        "total_sales": f["int"],
        "total_revenue": f["currency"],
        "application_clickout_rate": f["pct"],
        "offer_click_through_rate": f["pct"],
        "click_to_sale_rate": f["pct"],
        "revenue_per_click": f["currency"],
        "revenue_per_application": f["currency"],
    }

    write_df(ws, data["panel"], 0, 0, f["header"], formats)

    widths = [16, 14, 22, 14, 12, 16, 23, 22, 20, 18, 21, 21]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)
    ws.set_row(0, 38)


# ---------------------------------------------------------------------------
# 3. Card Performance
# ---------------------------------------------------------------------------

def add_card_performance(workbook, data, colors, f):
    ws = workbook.add_worksheet("3. Card Performance")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 1)
    ws.set_zoom(85)

    formats = {
        "offers": f["int"],
        "clicks": f["int"],
        "click_through_rate": f["pct"],
        "sales": f["int"],
        "click_to_sale_rate": f["pct"],
        "revenue": f["currency"],
        "revenue_per_click": f["currency"],
        "revenue_per_offer": f["currency"],
        "revenue_per_sale": f["currency"],
    }

    write_df(ws, data["cards"], 0, 0, f["header"], formats)

    widths = [12, 10, 10, 18, 10, 18, 14, 17, 17, 17, 12, 16, 15, 19]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)
    ws.set_row(0, 34)

    last_row = len(data["cards"])

    # Works whether card_id is stored as "Card 29" or 29 in the CSV.
    ws.conditional_format(
        1, 0, last_row, len(data["cards"].columns) - 1,
        {
            "type": "formula",
            "criteria": '=OR($A2="Card 29",$A2=29)',
            "format": f["card29"],
        },
    )

    ws.conditional_format(
        1, 0, last_row, len(data["cards"].columns) - 1,
        {
            "type": "formula",
            "criteria": '=OR($A2="Card 30",$A2=30,$A2="Card 31",$A2=31)',
            "format": f["comparator"],
        },
    )

    if "clicks" in data["cards"].columns:
        col = data["cards"].columns.get_loc("clicks")
        ws.conditional_format(1, col, last_row, col, {
            "type": "data_bar",
            "bar_color": "#6BAED6",
        })

    if "revenue_per_click" in data["cards"].columns:
        col = data["cards"].columns.get_loc("revenue_per_click")
        ws.conditional_format(1, col, last_row, col, {
            "type": "data_bar",
            "bar_color": "#74C69D",
        })


# ---------------------------------------------------------------------------
# 4. Card29 Context
# ---------------------------------------------------------------------------

def add_card29_context(workbook, data, f):
    ws = workbook.add_worksheet("4. Card29 Context")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 1)
    ws.set_zoom(85)

    multiple_format = workbook.add_format({
        "font_size": 9,
        "font_color": "#1F2937",
        "align": "center",
        "num_format": '0.00"x"',
    })

    formats = {
        "applications_together": f["int"],
        "card29_clicks": f["int"],
        "competitor_clicks": f["int"],
        "card29_click_rate": f["pct"],
        "competitor_click_rate": f["pct"],
        "click_rate_multiple": multiple_format,
        "same_likelihood_rate": f["pct"],
        "card29_higher_likelihood_rate": f["pct"],
        "card29_lower_apr_rate": f["pct"],
    }

    write_df(ws, data["context"], 0, 0, f["header"], formats)

    widths = [16, 20, 16, 18, 19, 20, 18, 21, 25, 21]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)
    ws.set_row(0, 38)

    last_row = len(data["context"])
    ws.conditional_format(
        1, 0, last_row, len(data["context"].columns) - 1,
        {
            "type": "formula",
            "criteria": '=OR($A2="Card 30",$A2=30,$A2="Card 31",$A2=31)',
            "format": f["comparator"],
        },
    )


# ---------------------------------------------------------------------------
# 5. Intervention Population
# ---------------------------------------------------------------------------

def add_intervention_population(workbook, data, f):
    ws = workbook.add_worksheet("5. Intervention Population")
    ws.hide_gridlines(2)
    ws.set_zoom(90)

    add_sheet_title(
        ws,
        "Conditional Card 29 Intervention Population",
        "Card 29 is retained when it is the applicant's only offer and suppressed only where alternatives exist.",
        f,
        end_col=7,
    )

    total = int(get_scalar(data["intervention"], "group", "all_card29_clickers", "applications"))
    suppress = int(get_scalar(data["intervention"], "group", "suppress_card29", "applications"))
    retain = int(get_scalar(data["intervention"], "group", "retain_card29", "applications"))

    ws.write("A5", "CARD 29 CLICKERS", f["kpi_label"])
    ws.write("A6", total, f["kpi_int"])
    ws.write("C5", "SUPPRESS WHEN ALTERNATIVE EXISTS", f["kpi_label"])
    ws.write("C6", suppress, f["kpi_int"])
    ws.write("E5", "SHARE AFFECTED", f["kpi_label"])
    ws.write("E6", suppress / total, f["kpi_pct"])
    ws.write("G5", "RETAIN AS SOLE OFFER", f["kpi_label"])
    ws.write("G6", retain, f["kpi_int"])

    ws.merge_range(
        "A8:H9",
        "Interpretation: 315 of 398 Card 29 clickers (79.1%) had at least one alternative. "
        "The remaining 83 had no alternative, so Card 29 cannot be diverting them from another offer and is retained under the practical intervention.",
        f["gold_note"],
    )

    ws.merge_range("A11:C11", "Alternatives after suppressing Card 29", f["section"])
    alt = data["alternatives"].copy()
    write_df(
        ws,
        alt,
        11,
        0,
        f["subheader"],
        {"alternative_count": f["int"], "applications": f["int"], "share": f["pct"]},
    )

    ws.merge_range("E11:G11", "Number of cards tied at likelihood rank 1", f["section"])
    rank1 = data["rank1_distribution"].copy()
    write_df(
        ws,
        rank1,
        11,
        4,
        f["subheader"],
        {"number_of_rank1_cards": f["int"], "applications": f["int"], "share": f["pct"]},
    )

    multi_rank1 = rank1.loc[rank1["number_of_rank1_cards"] > 1, "applications"].sum()
    ws.merge_range(
        "E18:H20",
        f"{multi_rank1 / suppress:.1%} of affected applicants have more than one card tied at likelihood rank 1 after suppression. "
        "Therefore a deterministic 'next-best card' assumption is not appropriate for most affected customers.",
        f["note"],
    )

    ws.set_column("A:A", 20)
    ws.set_column("B:B", 16)
    ws.set_column("C:C", 18)
    ws.set_column("D:D", 4)
    ws.set_column("E:E", 22)
    ws.set_column("F:F", 16)
    ws.set_column("G:G", 16)
    ws.set_column("H:H", 18)
    ws.set_row(5, 30)


# ---------------------------------------------------------------------------
# 6. Redistribution Model
# ---------------------------------------------------------------------------

def add_redistribution_model(workbook, data, f):
    ws = workbook.add_worksheet("6. Redistribution Model")
    ws.hide_gridlines(2)
    ws.freeze_panes(12, 0)
    ws.set_zoom(85)

    add_sheet_title(
        ws,
        "Empirically Anchored Redistribution Model",
        "Post-suppression likelihood ranks are recomputed and matched to historical Card-29-absent behaviour.",
        f,
        end_col=7,
    )

    supported = int(get_scalar(data["support"], "group", "empirically_supported", "applications"))
    residual = int(get_scalar(data["support"], "group", "residual_sensitivity", "applications"))
    affected = supported + residual

    econ = data["economics"].copy()
    expected_clicks = float(econ["expected_clicks"].sum())
    expected_sales = float(econ["expected_sales"].sum())
    expected_revenue = float(econ["expected_revenue"].sum())

    ws.write("A5", "AFFECTED APPLICANTS", f["kpi_label"])
    ws.write("A6", affected, f["kpi_int"])
    ws.write("C5", "EMPIRICALLY SUPPORTED", f["kpi_label"])
    ws.write("C6", supported, f["kpi_int"])
    ws.write("E5", "SUPPORTED SHARE", f["kpi_label"])
    ws.write("E6", supported / affected, f["kpi_pct"])
    ws.write("G5", "RESIDUAL SENSITIVITY", f["kpi_label"])
    ws.write("G6", residual, f["kpi_int"])

    ws.merge_range(
        "A8:H9",
        f"For {supported} of {affected} affected applicants ({supported / affected:.1%}), the post-suppression rank-1 card set had at least 10 historical Card-29-absent observations. "
        f"Likelihood rank 1 captured {HISTORICAL_RANK1_CLICK_SHARE:.1%} of historical clicks, so redistribution is anchored to observed top-ranked-card behaviour rather than assuming customers always transfer.",
        f["green_note"],
    )

    ws.write("A11", "EXPECTED REPLACEMENT CLICKS", f["kpi_label"])
    ws.write("A12", expected_clicks, f["kpi_decimal"])
    ws.write("C11", "EXPECTED SALES", f["kpi_label"])
    ws.write("C12", expected_sales, f["kpi_decimal"])
    ws.write("E11", "EXPECTED REVENUE", f["kpi_label"])
    ws.write("E12", expected_revenue, f["kpi_currency"])
    ws.write("G11", "MODELED POPULATION", f["kpi_label"])
    ws.write("G12", supported, f["kpi_int"])

    ws.merge_range("A15:F15", "Expected redistribution by destination card", f["section"])

    display = econ[[
        "card_id",
        "expected_clicks",
        "conversion_rate",
        "revenue_per_click",
        "expected_sales",
        "expected_revenue",
    ]].copy()

    display["card_id"] = display["card_id"].apply(lambda x: f"Card {int(x)}")
    display.columns = [
        "card",
        "expected_clicks",
        "observed_conversion",
        "revenue_per_click",
        "expected_sales",
        "expected_revenue",
    ]

    write_df(
        ws,
        display,
        15,
        0,
        f["subheader"],
        {
            "expected_clicks": f["decimal"],
            "observed_conversion": f["pct"],
            "revenue_per_click": f["currency"],
            "expected_sales": f["decimal"],
            "expected_revenue": f["currency"],
        },
    )

    start = 16
    end = start + len(display) - 1
    ws.conditional_format(start, 1, end, 1, {
        "type": "data_bar",
        "bar_color": "#6BAED6",
    })
    ws.conditional_format(start, 5, end, 5, {
        "type": "data_bar",
        "bar_color": "#74C69D",
    })

    ws.merge_range(
        f"A{18 + len(display)}:H{20 + len(display)}",
        "Model scope: the expected click/sales/revenue figures above cover only the 282 empirically supported applicants. "
        "The remaining 33 are excluded from the point estimate and handled through sensitivity analysis. "
        "Lower-ranked clicks are also excluded because lower-card availability differs across otherwise comparable panels; they represented only 4.4% of historical clicks.",
        f["note"],
    )

    ws.set_column("A:A", 18)
    ws.set_column("B:B", 18)
    ws.set_column("C:C", 19)
    ws.set_column("D:D", 18)
    ws.set_column("E:E", 21)
    ws.set_column("F:F", 22)
    ws.set_column("G:H", 19)


# ---------------------------------------------------------------------------
# 7. Break-even Sensitivity
# ---------------------------------------------------------------------------

def add_break_even_sensitivity(workbook, data, colors, f):
    ws = workbook.add_worksheet("7. Break-even Sensitivity")
    ws.hide_gridlines(2)
    ws.freeze_panes(12, 1)
    ws.set_zoom(85)

    add_sheet_title(
        ws,
        "Conditional Suppression Break-even Sensitivity",
        "Break-even depends on the two behaviours that cannot be observed directly from the supplied card-level sales data.",
        f,
        end_col=12,
    )

    econ = data["economics"]
    residual = data["residual"]
    be = data["break_even"].copy()
    matrix = data["break_even_matrix"].copy()

    supported_revenue = float(econ["expected_revenue"].sum())
    residual_full_revenue = float(residual["revenue_per_transfer_click"].sum())
    residual_full_sales = float(residual["sales_per_transfer_click"].sum())

    # Card 29 total revenue can be recovered from the sensitivity baseline at retained_sales=0.
    row0 = be.loc[be["retained_card29_sales"].eq(0)].iloc[0]
    card29_total_revenue = float(row0["affected_card29_baseline_revenue"])

    revenue_per_sale = 44.0  # verified from supplied Card 29 sales/revenue: £2,772 / 63.
    min_retained_achievable = math.ceil(
        (card29_total_revenue - supported_revenue - residual_full_revenue) / revenue_per_sale
    )
    retained_supported_only = math.ceil(
        (card29_total_revenue - supported_revenue) / revenue_per_sale
    )

    illustrative_sales = 13
    illustrative_row = be.loc[be["retained_card29_sales"].eq(illustrative_sales)].iloc[0]
    illustrative_required = float(illustrative_row["required_residual_transfer_rate"])

    ws.write("A5", "SUPPORTED REPLACEMENT REVENUE", f["kpi_label"])
    ws.write("A6", supported_revenue, f["kpi_currency"])
    ws.write("C5", "RESIDUAL 33: 100% TRANSFER REVENUE", f["kpi_label"])
    ws.write("C6", residual_full_revenue, f["kpi_currency"])
    ws.write("E5", "MIN RETAINED SALES FOR BREAK-EVEN TO BE POSSIBLE", f["kpi_label"])
    ws.write("E6", min_retained_achievable, f["kpi_int"])
    ws.write("G5", "RETAINED SALES FOR SUPPORTED 282 ALONE TO BREAK EVEN", f["kpi_label"])
    ws.write("G6", retained_supported_only, f["kpi_int"])

    ws.merge_range(
        "A8:H10",
        f"Illustrative proportional reference: if the 83 retained Card 29 clickers converted at Card 29's overall observed rate, they would account for about 13 sales. "
        f"At 13 retained sales (£572 retained revenue), the residual 33 need approximately {illustrative_required:.1%} transfer to break even. "
        "This is an illustrative assumption for sensitivity context, not an observed subgroup result.",
        f["gold_note"],
    )

    # Small decision-oriented break-even table.
    selected_sales = [0, 5, 6, 10, 13, 14, 15]
    selected = be[be["retained_card29_sales"].isin(selected_sales)].copy()
    selected["required_residual_transfer_pct"] = selected["required_residual_transfer_rate"]
    selected = selected[[
        "retained_card29_sales",
        "retained_card29_revenue",
        "affected_card29_baseline_revenue",
        "required_residual_transfer_pct",
    ]]
    selected.columns = [
        "retained_card29_sales",
        "retained_card29_revenue",
        "affected_revenue_to_replace",
        "required_residual_transfer",
    ]

    ws.merge_range("A12:D12", "Key break-even reference points", f["section"])
    write_df(
        ws,
        selected,
        12,
        0,
        f["subheader"],
        {
            "retained_card29_sales": f["int"],
            "retained_card29_revenue": f["currency"],
            "affected_revenue_to_replace": f["currency"],
            "required_residual_transfer": f["pct"],
        },
    )

    # Full heat-map matrix, 0..63 retained sales x 0..100% residual transfer.
    pivot = matrix.pivot(
        index="retained_card29_sales",
        columns="residual_transfer_rate",
        values="revenue_change",
    ).sort_index()

    pivot.columns = [f"{float(c):.0%}" for c in pivot.columns]
    pivot = pivot.reset_index()
    pivot.rename(columns={"retained_card29_sales": "retained_sales"}, inplace=True)

    matrix_start_row = 37
    ws.merge_range(
        matrix_start_row - 1, 0, matrix_start_row - 1, len(pivot.columns) - 1,
        "Full sensitivity matrix — revenue change vs current affected Card 29 baseline",
        f["section"],
    )

    matrix_formats = {"retained_sales": f["int"]}
    for c in pivot.columns[1:]:
        matrix_formats[c] = f["currency_delta"]

    write_df(ws, pivot, matrix_start_row, 0, f["subheader"], matrix_formats)

    data_start = matrix_start_row + 1
    data_end = data_start + len(pivot) - 1
    first_value_col = 1
    last_value_col = len(pivot.columns) - 1

    ws.conditional_format(
        data_start,
        first_value_col,
        data_end,
        last_value_col,
        {
            "type": "3_color_scale",
            "min_color": "#F4CCCC",
            "mid_color": "#FFF2CC",
            "max_color": "#D9EAD3",
            "min_type": "min",
            "mid_type": "num",
            "mid_value": 0,
            "max_type": "max",
        },
    )

    # Create chart-helper block from the matrix for selected assumptions.
    chart_sales = [0, 10, 13, 15]
    chart_start_col = 14  # O
    chart_start_row = 1

    transfer_rates = sorted(matrix["residual_transfer_rate"].unique())
    ws.write(chart_start_row, chart_start_col, "Residual transfer rate", f["subheader"])
    for j, s in enumerate(chart_sales, start=1):
        ws.write(chart_start_row, chart_start_col + j, f"{s} retained sales", f["subheader"])

    for i, rate in enumerate(transfer_rates, start=1):
        ws.write(chart_start_row + i, chart_start_col, rate, f["pct"])
        for j, s in enumerate(chart_sales, start=1):
            value = float(
                matrix.loc[
                    matrix["retained_card29_sales"].eq(s)
                    & matrix["residual_transfer_rate"].eq(rate),
                    "revenue_change",
                ].iloc[0]
            )
            ws.write(chart_start_row + i, chart_start_col + j, value, f["currency_delta"])

    chart = workbook.add_chart({"type": "line"})
    for j, s in enumerate(chart_sales, start=1):
        chart.add_series({
            "name": [ws.get_name(), chart_start_row, chart_start_col + j],
            "categories": [
                ws.get_name(),
                chart_start_row + 1,
                chart_start_col,
                chart_start_row + len(transfer_rates),
                chart_start_col,
            ],
            "values": [
                ws.get_name(),
                chart_start_row + 1,
                chart_start_col + j,
                chart_start_row + len(transfer_rates),
                chart_start_col + j,
            ],
            "marker": {"type": "circle", "size": 4},
            "line": {"width": 1.5},
        })

    chart.set_title({"name": "Revenue impact by residual transfer rate"})
    chart.set_x_axis({
        "name": "Residual 33 transfer rate",
        "num_format": "0%",
        "major_gridlines": {"visible": False},
    })
    chart.set_y_axis({
        "name": "Revenue change vs current affected baseline (£)",
        "num_format": "£0;[Red]-£0",
        "major_gridlines": {"visible": True, "line": {"color": "#E5E7EB"}},
    })
    chart.set_legend({"position": "bottom"})
    chart.set_chartarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
    chart.set_plotarea({"border": {"none": True}, "fill": {"color": "#FFFFFF"}})
    chart.set_size({"width": 620, "height": 330})
    ws.insert_chart("F12", chart)

    ws.merge_range(
        "F31:M34",
        "How to read the sensitivity: rows represent the unknown number of Card 29 sales generated by the 83 customers who keep Card 29; columns represent the transfer rate among the residual 33 applicants. "
        "Green cells indicate modeled revenue above the current affected Card 29 baseline; red cells indicate below baseline.",
        f["note"],
    )

    footer_start_row = data_end + 3
    ws.merge_range(
        footer_start_row,
        0,
        footer_start_row + 3,
        12,
        f"Residual 33 ceiling: if all 33 transfer once, their modelled destination-card economics imply £{residual_full_revenue:,.2f} revenue and {residual_full_sales:.2f} sales. "
        "The sensitivity analysis does not claim an exact transfer rate for these sparse states.",
        f["footer"],
    )

    ws.set_column("A:A", 20)
    ws.set_column("B:M", 15)
    ws.set_column("N:N", 2)
    ws.set_column("O:S", 16, None, {"hidden": True})


# ---------------------------------------------------------------------------
# 8. Methodology
# ---------------------------------------------------------------------------

def add_methodology(workbook, f):
    ws = workbook.add_worksheet("8. Methodology")
    ws.hide_gridlines(2)
    ws.set_zoom(90)

    ws.set_column("A:A", 5)
    ws.set_column("B:B", 23)
    ws.set_column("C:H", 18)

    ws.merge_range("B2:H3", "Analysis Approach & Assumptions", f["title"])
    ws.merge_range(
        "B4:H4",
        "Observed panel diagnosis followed by a conditional Card 29 counterfactual.",
        f["subtitle"],
    )

    ws.merge_range("B6:H6", "1. Business question", f["section"])
    ws.merge_range(
        "B7:H9",
        "The supplied data were used to assess whether any card appears to harm panel performance. "
        "Card 29 was identified as the strongest intervention candidate because it attracts substantial click volume while monetising weakly downstream. "
        "The final intervention is conditional rather than panel-wide: retain Card 29 when it is the only offer; suppress/deprioritise it when another offer exists.",
        f["text_wrap"],
    )

    ws.merge_range("B11:H11", "2. Observed analysis", f["section"])
    ws.merge_range(
        "B12:H15",
        "Panel and card metrics are calculated directly from the supplied quote and sales data. Same-application comparisons are used to understand Card 29's competitive context. "
        "The observed diagnosis does not assume causality: stronger click attraction combined with weaker downstream conversion creates a plausible diversion risk, not proof that every Card 29 click would move elsewhere if the card were suppressed.",
        f["text_wrap"],
    )

    ws.merge_range("B17:H17", "3. Conditional counterfactual", f["section"])
    steps = [
        ("A", "Identify population", "398 Card 29 clickers → retain for 83 sole-offer applicants; suppress for 315 with ≥1 alternative."),
        ("B", "Recompute ranking", "Remove Card 29 from affected applications and recompute likelihood/APR ranks using the supplied competition/min ranking convention."),
        ("C", "Historical behavioural anchor", "Use applications where Card 29 was absent to observe click/no-click behaviour for the same post-suppression rank-1 card set."),
        ("D", "Support threshold", "Rank-1 states with ≥10 historical applications are treated as empirically supported: 282/315 affected applicants (89.5%)."),
        ("E", "Point estimate", "For supported states, estimate destination-card clicks from historical behaviour, then apply each destination card's observed click→sale conversion and revenue/click."),
        ("F", "Residual uncertainty", "The remaining 33 sparse-state applicants are not point-estimated; their transfer rate is sensitivity-tested."),
        ("G", "Break-even", "Because Card 29 sales are only available at card level, retained Card 29 sales among the 83 sole-offer users are also sensitivity-tested."),
    ]

    row = 18
    for code, label, text in steps:
        ws.write(row, 1, code, f["kpi_label"])
        ws.write(row, 2, label, f["subheader"])
        ws.merge_range(row, 3, row, 7, text, f["text_wrap"])
        ws.set_row(row, 38)
        row += 1

    ws.merge_range("B27:H27", "4. Key assumptions / limitations", f["section"])
    ws.merge_range(
        "B28:H33",
        "• Sales and revenue are supplied only at card level, not application level. Therefore Card 29's 63 sales cannot be directly split between the 83 retained sole-offer clickers and the 315 affected clickers.\n"
        "• A redirected click is assumed to monetise at the destination card's observed overall click→sale conversion and revenue/click.\n"
        "• Historical redistribution is anchored to the post-suppression likelihood-rank-1 card set. Lower-ranked clicks are excluded from the point estimate because lower-card availability differs across otherwise comparable panels; they represented 4.4% of historical clicks.\n"
        "• Counterfactual outputs are modelled estimates, not causal measurements of what will happen after a product change.",
        f["gold_note"],
    )

    ws.merge_range("B35:H35", "5. Decision use", f["section"])
    ws.merge_range(
        "B36:H39",
        "The analysis supports a controlled conditional suppression/deprioritisation test rather than immediate permanent removal. "
        "Primary KPI: revenue per application. Secondary monitoring: sales/application, application clickout rate, click→sale conversion and redistribution across remaining cards. "
        "The break-even matrix shows the range of outcomes consistent with the two behaviours that are not observable directly in the supplied data.",
        f["green_note"],
    )


# ---------------------------------------------------------------------------
# Build workbook
# ---------------------------------------------------------------------------

def build_workbook(table_dir: Path, output_file: Path):
    data = load_inputs(table_dir)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(
        output_file,
        engine="xlsxwriter",
        engine_kwargs={"options": {"nan_inf_to_errors": True}},
    ) as writer:
        workbook = writer.book
        workbook.set_properties({
            "title": "Credit Card Panel Performance Review",
            "subject": "Ocean Finance Analytics Engineer exercise",
            "comments": "Generated from reproducible SQL/Python analysis outputs.",
        })

        colors, f = make_formats(workbook)

        add_summary_placeholder(workbook, f)
        add_panel_baseline(workbook, data, f)
        add_card_performance(workbook, data, colors, f)
        add_card29_context(workbook, data, f)
        add_intervention_population(workbook, data, f)
        add_redistribution_model(workbook, data, f)
        add_break_even_sensitivity(workbook, data, colors, f)
        add_methodology(workbook, f)

    print(f"Workbook written to: {output_file.resolve()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Build the final Ocean Finance Excel workings workbook."
    )
    parser.add_argument(
        "--table-dir",
        type=Path,
        default=Path("outputs/tables"),
        help="Directory containing exported analysis CSV tables.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/final/Credit_Platform_Analysis_Workings.xlsx"),
        help="Output Excel file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_workbook(args.table_dir, args.output)
