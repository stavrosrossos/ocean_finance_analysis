"""
Build the Ocean Finance Excel workings workbook from the reproducible analysis outputs.

Why this file exists
--------------------
The analysis itself lives in SQL/Python. This script is only the presentation
layer: it turns the stable analysis outputs into the Excel workbook delivered
to the stakeholder.

Run order
---------
python src/build_database.py
python src/run_counterfactual.py
python src/export_analysis_tables.py
python src/build_excel_workings.py

Dependencies
------------
pandas
XlsxWriter
"""

from __future__ import annotations  # noqa: I001

import argparse
from pathlib import Path

import pandas as pd


FILES = {
    "panel": "panel_baseline.csv",
    "cards": "card_performance.csv",
    "context": "card29_context.csv",
    "scenario_comparison": "scenario_comparison.csv",
    "scenario_a": "scenario_a_replacement_distribution.csv",
    "scenario_b": "scenario_b_ambiguous_group.csv",
    "break_even": "scenario_b_break_even.csv",
    "sensitivity": "scenario_b_sensitivity.csv",
}


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
            "Run export_analysis_tables.py and run_counterfactual.py first."
        )

    return {
        key: pd.read_csv(table_dir / filename)
        for key, filename in FILES.items()
    }


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def make_formats(workbook):
    colors = {
        "dark_teal": "#0F5D75",
        "mid_teal": "#2F7E96",
        "light_teal": "#EAF4F8",
        "pale_gold": "#FFF2CC",
        "light_green": "#E8F5E9",
        "light_gray": "#F3F4F6",
        "text": "#1F2937",
        "muted": "#5F6B76",
        "white": "#FFFFFF",
    }

    f = {}

    f["header"] = workbook.add_format({
        "bold": True,
        "font_color": colors["white"],
        "bg_color": colors["dark_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    f["section"] = workbook.add_format({
        "bold": True,
        "font_color": "#163A4A",
        "bg_color": "#D9EAF2",
        "valign": "vcenter",
    })

    f["title"] = workbook.add_format({
        "bold": True,
        "font_size": 21,
        "font_color": colors["white"],
        "bg_color": colors["dark_teal"],
        "valign": "vcenter",
    })

    f["subtitle"] = workbook.add_format({
        "italic": True,
        "font_size": 10,
        "font_color": colors["muted"],
    })

    f["conclusion"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": "#6B4E00",
        "bg_color": colors["pale_gold"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["summary_header"] = workbook.add_format({
        "bold": True,
        "font_size": 11,
        "font_color": colors["white"],
        "bg_color": colors["dark_teal"],
    })

    f["summary_col_header"] = workbook.add_format({
        "bold": True,
        "font_size": 9,
        "font_color": colors["white"],
        "bg_color": colors["mid_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    f["kpi_label"] = workbook.add_format({
        "bold": True,
        "font_size": 9,
        "font_color": colors["dark_teal"],
        "bg_color": colors["light_teal"],
        "align": "center",
        "valign": "vcenter",
        "text_wrap": True,
    })

    def kpi(num_format):
        return workbook.add_format({
            "bold": True,
            "font_size": 18,
            "font_color": colors["text"],
            "align": "center",
            "valign": "vcenter",
            "num_format": num_format,
        })

    f["kpi_int"] = kpi("#,##0")
    f["kpi_pct"] = kpi("0.0%")
    f["kpi_currency"] = kpi("£0.00")

    def body(num_format=None, align=None, size=10):
        props = {
            "font_size": size,
            "font_color": colors["text"],
        }
        if num_format:
            props["num_format"] = num_format
        if align:
            props["align"] = align
        return workbook.add_format(props)

    f["text"] = body()
    f["center"] = body(align="center", size=9)
    f["int"] = body("#,##0", "center", 9)
    f["decimal"] = body("0.0", "center", 9)
    f["decimal2"] = body("0.00", "center", 9)
    f["pct"] = body("0.0%", "center", 9)
    f["currency"] = body("£#,##0.00", "center", 9)
    f["currency10"] = body("£#,##0.00", size=10)
    f["int10"] = body("#,##0", size=10)
    f["pct10"] = body("0.0%", size=10)

    f["note"] = workbook.add_format({
        "font_size": 9,
        "font_color": colors["text"],
        "bg_color": colors["light_gray"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["uncertainty_header"] = workbook.add_format({
        "bold": True,
        "font_size": 9,
        "font_color": "#6B4E00",
        "bg_color": colors["pale_gold"],
        "align": "center",
    })

    f["uncertainty"] = workbook.add_format({
        "font_size": 9,
        "font_color": "#6B4E00",
        "bg_color": "#FFF9E6",
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["recommendation"] = workbook.add_format({
        "font_size": 10,
        "font_color": "#176B3A",
        "bg_color": colors["light_green"],
        "text_wrap": True,
        "valign": "vcenter",
    })

    f["footer"] = workbook.add_format({
        "italic": True,
        "font_size": 8,
        "font_color": colors["muted"],
    })

    f["currency_delta"] = workbook.add_format({
        "font_size": 9,
        "align": "center",
        "num_format": "+£#,##0;[Red]-£#,##0",
    })

    f["negative"] = workbook.add_format({
        "bg_color": "#FDECEC",
        "font_color": "#B42318",
    })

    f["positive"] = workbook.add_format({
        "bg_color": "#EAF7EE",
        "font_color": "#176B3A",
    })

    f["card29_cf"] = workbook.add_format({
        "bold": True,
        "font_color": "#7A4E00",
        "bg_color": colors["pale_gold"],
    })

    f["comparator_cf"] = workbook.add_format({
        "bg_color": colors["light_teal"],
    })

    return colors, f


# ---------------------------------------------------------------------------
# Generic dataframe writer
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
        worksheet.write(
            start_row,
            start_col + col_offset,
            column,
            header_format,
        )

    for row_offset, row in enumerate(
        df.itertuples(index=False, name=None),
        start=1,
    ):
        for col_offset, value in enumerate(row):
            column_name = df.columns[col_offset]
            cell_format = column_formats.get(column_name)

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


# ---------------------------------------------------------------------------
# Working sheets
# ---------------------------------------------------------------------------

def add_panel_baseline(workbook, data, f):
    ws = workbook.add_worksheet("2. Panel Baseline")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 0)
    ws.set_zoom(90)

    formats = {
        "total_applications": f["int10"],
        "total_offers": f["int10"],
        "applications_with_click": f["int10"],
        "total_clicks": f["int10"],
        "total_sales": f["int10"],
        "total_revenue": f["currency10"],
        "application_clickout_rate": f["pct10"],
        "offer_click_through_rate": f["pct10"],
        "click_to_sale_rate": f["pct10"],
        "revenue_per_click": f["currency10"],
        "revenue_per_application": f["currency10"],
        "sales_per_100_applications": f["text"],
    }

    write_df(ws, data["panel"], 0, 0, f["header"], formats)

    widths = [16, 14, 22, 14, 12, 16, 23, 22, 20, 18, 21, 21]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)

    ws.set_row(0, 38)


def add_card_performance(workbook, data, colors, f):
    ws = workbook.add_worksheet("3. Card Performance")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 1)
    ws.set_zoom(85)

    formats = {
        "offers": f["int10"],
        "clicks": f["int10"],
        "click_through_rate": f["pct10"],
        "sales": f["int10"],
        "click_to_sale_rate": f["pct10"],
        "revenue": f["currency10"],
        "revenue_per_click": f["currency10"],
        "revenue_per_offer": f["currency10"],
        "revenue_per_sale": f["currency10"],
        "avg_apr": f["text"],
        "avg_likelihood": f["text"],
        "avg_apr_rank": f["text"],
        "avg_likelihood_rank": f["text"],
    }

    write_df(ws, data["cards"], 0, 0, f["header"], formats)

    widths = [12, 10, 10, 18, 10, 18, 14, 17, 17, 17, 12, 16, 15, 19]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)

    ws.set_row(0, 34)

    last_row = len(data["cards"])

    # Highlight by card id rather than hard-coding row numbers.
    ws.conditional_format(
        1, 0, last_row, len(data["cards"].columns) - 1,
        {
            "type": "formula",
            "criteria": '=$A2="Card 29"',
            "format": f["card29_cf"],
        },
    )

    ws.conditional_format(
        1, 0, last_row, len(data["cards"].columns) - 1,
        {
            "type": "formula",
            "criteria": '=OR($A2="Card 30",$A2="Card 31")',
            "format": f["comparator_cf"],
        },
    )

    ws.conditional_format(
        1, data["cards"].columns.get_loc("clicks"),
        last_row, data["cards"].columns.get_loc("clicks"),
        {"type": "data_bar", "bar_color": "#6BAED6"},
    )

    ws.conditional_format(
        1, data["cards"].columns.get_loc("revenue_per_click"),
        last_row, data["cards"].columns.get_loc("revenue_per_click"),
        {"type": "data_bar", "bar_color": "#74C69D"},
    )


def add_card29_context(workbook, data, f):
    ws = workbook.add_worksheet("4. Card 29 context")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 1)
    ws.set_zoom(85)

    formats = {
        "applications_together": f["int10"],
        "card29_clicks": f["int10"],
        "competitor_clicks": f["int10"],
        "card29_click_rate": f["pct10"],
        "competitor_click_rate": f["pct10"],
        "click_rate_multiple": workbook.add_format({
            "font_size": 10,
            "font_color": "#1F2937",
            "num_format": '0.00"x"',
        }),
        "same_likelihood_rate": f["pct10"],
        "card29_higher_likelihood_rate": f["pct10"],
        "card29_lower_apr_rate": f["pct10"],
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
            "criteria": '=OR($A2="Card 30",$A2="Card 31")',
            "format": f["comparator_cf"],
        },
    )


def add_scenario_analysis(workbook, data, f):
    ws = workbook.add_worksheet("5. Scenario Analysis")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 0)
    ws.set_zoom(90)

    comp_formats = {
        "clicks_or_expected_clicks": f["decimal"],
        "sales_or_expected_sales": f["decimal"],
        "revenue_or_expected_revenue": f["currency"],
    }

    write_df(
        ws,
        data["scenario_comparison"],
        0,
        0,
        f["header"],
        comp_formats,
    )

    ws.merge_range(
        "A6:B6",
        "Scenario A — strongest visible alternative",
        f["section"],
    )
    write_df(
        ws,
        data["scenario_a"],
        7,
        0,
        f["header"],
        {"modelled_replacements": f["int"]},
    )

    ws.merge_range(
        "D6:G6",
        "Scenario B — empirical redistribution",
        f["section"],
    )
    write_df(
        ws,
        data["scenario_b"],
        8,
        3,
        f["header"],
        {
            "expected_applicants": f["decimal"],
            "expected_sales": f["decimal"],
            "expected_revenue": f["currency"],
        },
    )

    widths = [34, 28, 25, 30, 22, 20, 20]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)


def add_sensitivity(workbook, data, f):
    ws = workbook.add_worksheet("6. Sensitivity")
    ws.hide_gridlines(2)
    ws.freeze_panes(1, 0)
    ws.set_zoom(90)

    write_df(
        ws,
        data["break_even"],
        0,
        0,
        f["header"],
        {"value": f["pct10"]},
    )

    ws.merge_range(
        "A5:E5",
        "Scenario B sensitivity to remaining-group transfer",
        f["section"],
    )

    write_df(
        ws,
        data["sensitivity"],
        7,
        0,
        f["header"],
        {
            "remaining_transfer_rate": f["pct"],
            "expected_sales": f["decimal"],
            "expected_revenue": f["currency"],
            "sales_vs_card29": f["decimal"],
            "revenue_vs_card29": f["currency"],
        },
    )

    widths = [45, 23, 22, 20, 22]
    for i, width in enumerate(widths):
        ws.set_column(i, i, width)

    start = 8
    end = start + len(data["sensitivity"]) - 1

    for col_name in ["sales_vs_card29", "revenue_vs_card29"]:
        col = data["sensitivity"].columns.get_loc(col_name)

        ws.conditional_format(
            start, col, end, col,
            {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": f["negative"],
            },
        )

        ws.conditional_format(
            start, col, end, col,
            {
                "type": "cell",
                "criteria": ">",
                "value": 0,
                "format": f["positive"],
            },
        )


# ---------------------------------------------------------------------------
# Executive summary
# ---------------------------------------------------------------------------

def excel_row(df: pd.DataFrame, key_column: str, key_value: str) -> int:
    """Return 1-based Excel row where dataframe header occupies row 1."""
    matches = df.index[df[key_column].eq(key_value)]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one {key_column}={key_value!r}; found {len(matches)}."
        )

    return int(matches[0]) + 2


def add_summary(workbook, data, colors, f):
    ws = workbook.add_worksheet("1. Summary")
    ws.hide_gridlines(2)
    ws.freeze_panes(3, 0)
    ws.set_zoom(90)

    ws.set_column("A:A", 34)
    ws.set_column("B:E", 16)
    ws.set_column("F:H", 18)

    # Title
    ws.merge_range(
        "A1:H2",
        "Credit Card Panel Performance Review",
        f["title"],
    )
    ws.set_row(0, 28)
    ws.set_row(1, 28)

    ws.merge_range(
        "A3:H3",
        "Assessment of whether any individual card is materially harming marketplace performance",
        f["subtitle"],
    )

    # Executive conclusion
    ws.merge_range(
        "A5:H7",
        "Card 29 is the clearest intervention candidate, but the evidence does not justify immediate permanent removal.\n"
        "It attracts the highest click volume in the panel while monetising materially worse than its main alternatives. "
        "Removal could improve performance, but the result depends on how customers redistribute after Card 29 disappears.",
        f["conclusion"],
    )

    # KPI block
    ws.merge_range("A9:H9", "Key diagnostics", f["summary_header"])

    card29 = data["cards"].loc[
        data["cards"]["card_id"].eq("Card 29")
    ].iloc[0]

    card29_row = excel_row(data["cards"], "card_id", "Card 29")
    panel = data["panel"].iloc[0]

    kpis = [
        (
            "A10:B10", "A11:B12", "Card 29 clicks",
            f"='3. Card Performance'!C{card29_row}",
            card29["clicks"], f["kpi_int"],
        ),
        (
            "C10:D10", "C11:D12", "Card 29 conversion",
            f"='3. Card Performance'!F{card29_row}",
            card29["click_to_sale_rate"], f["kpi_pct"],
        ),
        (
            "E10:F10", "E11:F12", "Card 29 revenue / click",
            f"='3. Card Performance'!H{card29_row}",
            card29["revenue_per_click"], f["kpi_currency"],
        ),
        (
            "G10:H10", "G11:H12", "Panel revenue / click",
            "='2. Panel Baseline'!J2",
            panel["revenue_per_click"], f["kpi_currency"],
        ),
    ]

    for label_range, value_range, label, formula, cached_value, value_format in kpis:
        ws.merge_range(label_range, label, f["kpi_label"])
        ws.merge_range(value_range, "", value_format)
        first_cell = value_range.split(":")[0]
        ws.write_formula(first_cell, formula, value_format, cached_value)

    # Card comparison
    ws.merge_range(
        "A14:H14",
        "Why Card 29 stands out",
        f["summary_header"],
    )

    headers = [
        "Card",
        "Clicks",
        "Click rate",
        "Conversion",
        "Revenue / click",
        "APR",
        "Revenue / sale",
    ]

    for col, header in enumerate(headers):
        ws.write(14, col, header, f["summary_col_header"])

    cards_to_show = ["Card 29", "Card 30", "Card 31"]

    summary_formats = [
        f["center"],
        f["int"],
        f["pct"],
        f["pct"],
        f["currency"],
        f["decimal"],
        f["currency"],
    ]

    source_columns = [
        "card_id",
        "clicks",
        "click_through_rate",
        "click_to_sale_rate",
        "revenue_per_click",
        "avg_apr",
        "revenue_per_sale",
    ]

    source_excel_cols = ["A", "C", "D", "F", "H", "K", "J"]

    for target_row, card in enumerate(cards_to_show, start=15):
        source_row = excel_row(data["cards"], "card_id", card)
        card_data = data["cards"].loc[
            data["cards"]["card_id"].eq(card)
        ].iloc[0]

        for col, (
            source_col,
            source_excel_col,
            cell_format,
        ) in enumerate(
            zip(
                source_columns,
                source_excel_cols,
                summary_formats,
            )
        ):
            ws.write_formula(
                target_row,
                col,
                f"='3. Card Performance'!{source_excel_col}{source_row}",
                cell_format,
                card_data[source_col],
            )

    # Fill/highlight without destroying number formats.
    ws.conditional_format(
        "A16:G18",
        {
            "type": "formula",
            "criteria": '=$A16="Card 29"',
            "format": f["card29_cf"],
        },
    )

    ws.merge_range(
        "A20:H21",
        "When co-offered, Card 29 receives 2.38× Card 30's click rate and 4.81× Card 31's click rate, "
        "despite materially weaker downstream conversion. All three cards generate £44 per completed sale.",
        f["note"],
    )

    # Scenario comparison
    ws.merge_range(
        "A23:H23",
        "Does removing Card 29 improve the panel?",
        f["summary_header"],
    )

    headers = [
        "Scenario",
        "Expected clicks",
        "Expected sales",
        "Expected revenue",
        "Revenue vs keep",
    ]
    for col, header in enumerate(headers):
        ws.write(23, col, header, f["summary_col_header"])

    scenarios = data["scenario_comparison"].reset_index(drop=True)
    keep_revenue = float(
        scenarios.loc[
            scenarios["scenario"].eq("Keep Card 29"),
            "revenue_or_expected_revenue",
        ].iloc[0]
    )

    for i, row in scenarios.iterrows():
        target_row = 24 + i
        source_row = 2 + i

        ws.write_formula(
            target_row, 0,
            f"='5. Scenario Analysis'!A{source_row}",
            f["center"],
            row["scenario"],
        )
        ws.write_formula(
            target_row, 1,
            f"='5. Scenario Analysis'!B{source_row}",
            f["decimal"],
            row["clicks_or_expected_clicks"],
        )
        ws.write_formula(
            target_row, 2,
            f"='5. Scenario Analysis'!C{source_row}",
            f["decimal"],
            row["sales_or_expected_sales"],
        )
        ws.write_formula(
            target_row, 3,
            f"='5. Scenario Analysis'!D{source_row}",
            f["currency"],
            row["revenue_or_expected_revenue"],
        )

        if row["scenario"] == "Keep Card 29":
            ws.write(target_row, 4, "—", f["center"])
        else:
            delta = float(row["revenue_or_expected_revenue"]) - keep_revenue
            ws.write_formula(
                target_row, 4,
                f"=D{target_row + 1}-$D$25",
                f["currency_delta"],
                delta,
            )

    # Scenario B row
    ws.conditional_format(
        "A25:E27",
        {
            "type": "formula",
            "criteria": '=$A25="B - empirical redistribution"',
            "format": f["positive"],
        },
    )

    # Uncertainty box
    ws.merge_range(
        "F24:H24",
        "Key uncertainty",
        f["uncertainty_header"],
    )

    revenue_break_even = float(
        data["break_even"].loc[
            data["break_even"]["metric"].eq(
                "Remaining-group revenue break-even transfer"
            ),
            "value",
        ].iloc[0]
    )

    ws.merge_range(
        "F25:H27",
        f"Under the empirically anchored scenario, the remaining eligible group requires "
        f"{revenue_break_even:.1%} transfer for revenue to break even. "
        "This behaviour cannot be observed directly in the supplied data.",
        f["uncertainty"],
    )

    # Recommendation
    ws.merge_range(
        "A29:H32",
        "Recommended action: controlled test of Card 29 removal or deprioritisation\n\n"
        "Primary KPI: revenue per application.\n"
        "Secondary metrics: sales per application, application clickout rate, "
        "click-to-sale conversion and click redistribution toward Cards 30/31.\n"
        "Permanent removal should follow only if treatment produces a commercially "
        "meaningful improvement without materially reducing clickout.",
        f["recommendation"],
    )

    ws.merge_range(
        "A34:H34",
        "All figures are linked to the underlying working sheets; scenario outputs are modelled, not observed causal outcomes.",
        f["footer"],
    )


def add_methodology(workbook):
    ws = workbook.add_worksheet("7. Methodology")
    ws.hide_gridlines(2)
    # Intentionally blank for now. The analytical method is already documented
    # in the notebook and source code; this can be populated later if required.


# ---------------------------------------------------------------------------
# Workbook assembly
# ---------------------------------------------------------------------------

def build_workbook(
    project_root: Path,
    output_path: Path,
):
    table_dir = project_root / "outputs" / "tables"
    data = load_inputs(table_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(
        output_path,
        engine="xlsxwriter",
        engine_kwargs={
            "options": {
                "strings_to_urls": False,
                "nan_inf_to_errors": True,
            }
        },
    ) as writer:
        workbook = writer.book
        colors, f = make_formats(workbook)

        # Sheet creation order controls workbook tab order.
        add_summary(workbook, data, colors, f)
        add_panel_baseline(workbook, data, f)
        add_card_performance(workbook, data, colors, f)
        add_card29_context(workbook, data, f)
        add_scenario_analysis(workbook, data, f)
        add_sensitivity(workbook, data, f)
        add_methodology(workbook)

    print(f"Workbook created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Build the Ocean Finance Excel workings workbook."
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root. Defaults to the parent of src/.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional .xlsx output path.",
    )

    args = parser.parse_args()

    project_root = args.project_root.resolve()

    output_path = (
        args.output.resolve()
        if args.output
        else project_root
        / "outputs"
        / "final"
        / "Credit_Platform_Analysis_Workings.xlsx"
    )

    build_workbook(
        project_root=project_root,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
