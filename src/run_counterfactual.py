from pathlib import Path  # noqa: I001

import duckdb
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ocean_finance.duckdb"
)

CARD_PERFORMANCE_SQL = (
    PROJECT_ROOT
    / "sql"
    / "02_card_performance.sql"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "outputs"
    / "tables"
)


def load_data():
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        quotes = con.execute(
            "SELECT * FROM quotes"
        ).fetchdf()

        card_performance = con.execute(
            CARD_PERFORMANCE_SQL.read_text()
        ).fetchdf()

    return quotes, card_performance


def build_scenario_a(quotes, card_performance):
    """
    Scenario A:
    Remove Card 29 and assume every applicant with an alternative
    clicks the strongest visible remaining offer.

    Ordering:
    1. best likelihood rank
    2. lowest APR
    3. card ID as deterministic tie-breaker
    """

    card29_clicker_ids = quotes.loc[
        (quotes["card_id"] == "Card 29")
        & (quotes["clicked"] == 1),
        "application_id"
    ].unique()

    card29_clickers = quotes[
        quotes["application_id"].isin(
            card29_clicker_ids
        )
    ].copy()

    alternatives = card29_clickers[
        card29_clickers["card_id"] != "Card 29"
    ].copy()

    top_alternatives = (
        alternatives
        .sort_values(
            [
                "application_id",
                "likelihood_rank",
                "apr",
                "card_id",
            ]
        )
        .drop_duplicates(
            subset="application_id",
            keep="first"
        )
    )

    replacement_performance = (
        top_alternatives[
            ["application_id", "card_id"]
        ]
        .merge(
            card_performance[
                [
                    "card_id",
                    "click_to_sale_rate",
                    "revenue_per_click",
                ]
            ],
            on="card_id",
            how="left"
        )
    )

    replacement_distribution = (
        replacement_performance
        .groupby("card_id")
        .size()
        .reset_index(name="modelled_replacements")
        .sort_values(
            "modelled_replacements",
            ascending=False
        )
    )

    expected_sales = (
        replacement_performance[
            "click_to_sale_rate"
        ].sum()
    )

    expected_revenue = (
        replacement_performance[
            "revenue_per_click"
        ].sum()
    )

    return {
        "card29_clicker_ids": card29_clicker_ids,
        "card29_clickers": card29_clickers,
        "replacement_performance": replacement_performance,
        "replacement_distribution": replacement_distribution,
        "expected_clicks": len(replacement_performance),
        "expected_sales": expected_sales,
        "expected_revenue": expected_revenue,
    }


def build_scenario_b(
    quotes,
    card_performance,
    scenario_a
):
    """
    Scenario B:
    For Card 29 clickers who had both Cards 30 and 31 available,
    use observed behaviour from applications where Cards 30 and 31
    were available but Card 29 was absent.

    For the remaining Card 29 clickers with alternatives, retain
    Scenario A's strongest-visible-alternative rule.
    """

    card29_clicker_ids = scenario_a[
        "card29_clicker_ids"
    ]

    card29_clickers = scenario_a[
        "card29_clickers"
    ]

    application_card_sets = (
        quotes
        .groupby("application_id")["card_id"]
        .agg(set)
    )

    # ----------------------------------------------------------
    # Identify Card 29 clickers with both Card 30 and Card 31
    # ----------------------------------------------------------

    card29_choice_sets = (
        card29_clickers
        .groupby("application_id")["card_id"]
        .agg(set)
    )

    both_30_31_ids = card29_choice_sets[
        card29_choice_sets.apply(
            lambda cards:
                "Card 30" in cards
                and "Card 31" in cards
        )
    ].index

    remaining_card29_ids = [
        app_id
        for app_id in card29_clicker_ids
        if app_id not in set(both_30_31_ids)
    ]

    # ----------------------------------------------------------
    # Empirical reference group:
    # Card 30 + Card 31 present, Card 29 absent
    # ----------------------------------------------------------

    reference_ids = application_card_sets[
        application_card_sets.apply(
            lambda cards:
                "Card 30" in cards
                and "Card 31" in cards
                and "Card 29" not in cards
        )
    ].index

    reference_data = quotes[
        quotes["application_id"].isin(
            reference_ids
        )
    ].copy()

    reference_behaviour = pd.DataFrame(
        index=reference_ids
    )

    reference_behaviour["card30_click"] = (
        reference_data[
            reference_data["card_id"] == "Card 30"
        ]
        .set_index("application_id")["clicked"]
        .reindex(reference_ids, fill_value=0)
    )

    reference_behaviour["card31_click"] = (
        reference_data[
            reference_data["card_id"] == "Card 31"
        ]
        .set_index("application_id")["clicked"]
        .reindex(reference_ids, fill_value=0)
    )

    other_clicks = (
        reference_data[
            ~reference_data["card_id"].isin(
                ["Card 30", "Card 31"]
            )
        ]
        .groupby("application_id")["clicked"]
        .max()
    )

    reference_behaviour["other_card_click"] = (
        other_clicks.reindex(
            reference_ids,
            fill_value=0
        )
    )

    reference_behaviour["any_click"] = (
        reference_data
        .groupby("application_id")["clicked"]
        .max()
        .reindex(reference_ids, fill_value=0)
    )

    # Scenario B assumes mutually exclusive observed outcomes.
    click_categories = (
        reference_behaviour[
            [
                "card30_click",
                "card31_click",
                "other_card_click",
            ]
        ]
        .sum(axis=1)
    )

    if (click_categories > 1).any():
        raise ValueError(
            "Reference group contains overlapping click categories."
        )

    p_card30 = reference_behaviour[
        "card30_click"
    ].mean()

    p_card31 = reference_behaviour[
        "card31_click"
    ].mean()

    p_other = reference_behaviour[
        "other_card_click"
    ].mean()

    p_no_click = (
        1
        - reference_behaviour["any_click"].mean()
    )

    # ----------------------------------------------------------
    # Estimate downstream performance of "other card" clicks
    # ----------------------------------------------------------

    reference_other_card_clicks = (
        reference_data[
            (~reference_data["card_id"].isin(
                ["Card 30", "Card 31"]
            ))
            & (reference_data["clicked"] == 1)
        ]
        .groupby("card_id")
        .agg(
            clicked_applications=(
                "application_id",
                "nunique"
            )
        )
        .reset_index()
    )

    other_performance = (
        reference_other_card_clicks
        .merge(
            card_performance[
                [
                    "card_id",
                    "click_to_sale_rate",
                    "revenue_per_click",
                ]
            ],
            on="card_id",
            how="left"
        )
    )

    total_other_clicks = (
        other_performance[
            "clicked_applications"
        ].sum()
    )

    other_weighted_conversion = (
        (
            other_performance["clicked_applications"]
            * other_performance["click_to_sale_rate"]
        ).sum()
        / total_other_clicks
    )

    other_weighted_rpc = (
        (
            other_performance["clicked_applications"]
            * other_performance["revenue_per_click"]
        ).sum()
        / total_other_clicks
    )

    # ----------------------------------------------------------
    # Expected behaviour for ambiguous Card 29 clickers
    # ----------------------------------------------------------

    card30 = card_performance[
        card_performance["card_id"] == "Card 30"
    ].iloc[0]

    card31 = card_performance[
        card_performance["card_id"] == "Card 31"
    ].iloc[0]

    n_both = len(both_30_31_ids)

    ambiguous_group = pd.DataFrame({
        "outcome": [
            "Card 30",
            "Card 31",
            "Other card",
            "No click",
        ],
        "expected_applicants": [
            n_both * p_card30,
            n_both * p_card31,
            n_both * p_other,
            n_both * p_no_click,
        ],
        "expected_sales": [
            n_both
            * p_card30
            * card30["click_to_sale_rate"],

            n_both
            * p_card31
            * card31["click_to_sale_rate"],

            n_both
            * p_other
            * other_weighted_conversion,

            0,
        ],
        "expected_revenue": [
            n_both
            * p_card30
            * card30["revenue_per_click"],

            n_both
            * p_card31
            * card31["revenue_per_click"],

            n_both
            * p_other
            * other_weighted_rpc,

            0,
        ],
    })

    # ----------------------------------------------------------
    # Remaining Card 29 clickers:
    # retain Scenario A's modelled alternative
    # ----------------------------------------------------------

    remaining_replacements = (
        scenario_a["replacement_performance"][
            scenario_a["replacement_performance"][
                "application_id"
            ].isin(remaining_card29_ids)
        ]
        .copy()
    )

    ambiguous_expected_clicks = (
        ambiguous_group.loc[
            ambiguous_group["outcome"] != "No click",
            "expected_applicants"
        ].sum()
    )

    ambiguous_sales = (
        ambiguous_group[
            "expected_sales"
        ].sum()
    )

    ambiguous_revenue = (
        ambiguous_group[
            "expected_revenue"
        ].sum()
    )

    remaining_sales_opportunity = (
        remaining_replacements[
            "click_to_sale_rate"
        ].sum()
    )

    remaining_revenue_opportunity = (
        remaining_replacements[
            "revenue_per_click"
        ].sum()
    )

    expected_clicks = (
        ambiguous_expected_clicks
        + len(remaining_replacements)
    )

    expected_sales = (
        ambiguous_sales
        + remaining_sales_opportunity
    )

    expected_revenue = (
        ambiguous_revenue
        + remaining_revenue_opportunity
    )

    return {
        "reference_applications": len(reference_ids),
        "p_card30": p_card30,
        "p_card31": p_card31,
        "p_other": p_other,
        "p_no_click": p_no_click,
        "ambiguous_group": ambiguous_group,
        "ambiguous_clickers": n_both,
        "remaining_card29_clickers": len(
            remaining_card29_ids
        ),
        "remaining_replacements": remaining_replacements,
        "ambiguous_sales": ambiguous_sales,
        "ambiguous_revenue": ambiguous_revenue,
        "remaining_sales_opportunity":
            remaining_sales_opportunity,
        "remaining_revenue_opportunity":
            remaining_revenue_opportunity,
        "expected_clicks": expected_clicks,
        "expected_sales": expected_sales,
        "expected_revenue": expected_revenue,
    }


def build_sensitivity(
    scenario_b,
    card29_actual
):
    """
    Hold the empirically modelled ambiguous group fixed and vary
    the transfer rate among the remaining eligible applicants.
    """

    rates = np.arange(0, 1.01, 0.10)

    sensitivity = pd.DataFrame({
        "remaining_transfer_rate": rates
    })

    sensitivity["expected_sales"] = (
        scenario_b["ambiguous_sales"]
        + rates
        * scenario_b[
            "remaining_sales_opportunity"
        ]
    )

    sensitivity["expected_revenue"] = (
        scenario_b["ambiguous_revenue"]
        + rates
        * scenario_b[
            "remaining_revenue_opportunity"
        ]
    )

    sensitivity["sales_vs_card29"] = (
        sensitivity["expected_sales"]
        - card29_actual["sales"]
    )

    sensitivity["revenue_vs_card29"] = (
        sensitivity["expected_revenue"]
        - card29_actual["revenue"]
    )

    sales_break_even = (
        card29_actual["sales"]
        - scenario_b["ambiguous_sales"]
    ) / scenario_b[
        "remaining_sales_opportunity"
    ]

    revenue_break_even = (
        card29_actual["revenue"]
        - scenario_b["ambiguous_revenue"]
    ) / scenario_b[
        "remaining_revenue_opportunity"
    ]

    break_even = pd.DataFrame({
        "metric": [
            "Remaining-group sales break-even transfer",
            "Remaining-group revenue break-even transfer",
        ],
        "value": [
            sales_break_even,
            revenue_break_even,
        ]
    })

    return sensitivity, break_even


def main():
    quotes, card_performance = load_data()

    card29_actual = (
        card_performance[
            card_performance["card_id"] == "Card 29"
        ]
        .iloc[0]
    )

    scenario_a = build_scenario_a(
        quotes,
        card_performance
    )

    scenario_b = build_scenario_b(
        quotes,
        card_performance,
        scenario_a
    )

    sensitivity, break_even = build_sensitivity(
        scenario_b,
        card29_actual
    )

    scenario_comparison = pd.DataFrame({
        "scenario": [
            "Keep Card 29",
            "A - strongest visible alternative",
            "B - empirical redistribution",
        ],
        "clicks_or_expected_clicks": [
            card29_actual["clicks"],
            scenario_a["expected_clicks"],
            scenario_b["expected_clicks"],
        ],
        "sales_or_expected_sales": [
            card29_actual["sales"],
            scenario_a["expected_sales"],
            scenario_b["expected_sales"],
        ],
        "revenue_or_expected_revenue": [
            card29_actual["revenue"],
            scenario_a["expected_revenue"],
            scenario_b["expected_revenue"],
        ],
    })

    # ----------------------------------------------------------
    # Print audit-friendly outputs
    # ----------------------------------------------------------

    print(
        "\nSCENARIO A — STRONGEST VISIBLE ALTERNATIVE"
    )
    print("=" * 55)

    print(
        pd.DataFrame({
            "metric": [
                "Card 29 clickers",
                "Eligible replacement clickers",
                "No alternative",
                "Expected sales",
                "Expected revenue",
            ],
            "value": [
                len(
                    scenario_a[
                        "card29_clicker_ids"
                    ]
                ),
                scenario_a["expected_clicks"],
                len(
                    scenario_a[
                        "card29_clicker_ids"
                    ]
                )
                - scenario_a["expected_clicks"],
                scenario_a["expected_sales"],
                scenario_a["expected_revenue"],
            ]
        }).to_string(index=False)
    )

    print(
        "\nSCENARIO B — EMPIRICAL REDISTRIBUTION"
    )
    print("=" * 55)

    print(
        f"Reference applications: "
        f"{scenario_b['reference_applications']}"
    )

    print(
        f"Card 30 click share: "
        f"{scenario_b['p_card30']:.4f}"
    )
    print(
        f"Card 31 click share: "
        f"{scenario_b['p_card31']:.4f}"
    )
    print(
        f"Other-card click share: "
        f"{scenario_b['p_other']:.4f}"
    )
    print(
        f"No-click share: "
        f"{scenario_b['p_no_click']:.4f}"
    )

    print("\nScenario comparison:")
    print(
        scenario_comparison.to_string(
            index=False
        )
    )

    print("\nBreak-even sensitivity:")
    print(
        break_even.to_string(
            index=False
        )
    )

    print("\nScenario B sensitivity:")
    print(
        sensitivity.to_string(
            index=False
        )
    )

    # ----------------------------------------------------------
    # Save reusable outputs for Excel / presentation work
    # ----------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    scenario_a[
        "replacement_distribution"
    ].to_csv(
        OUTPUT_DIR
        / "scenario_a_replacement_distribution.csv",
        index=False
    )

    scenario_b[
        "ambiguous_group"
    ].to_csv(
        OUTPUT_DIR
        / "scenario_b_ambiguous_group.csv",
        index=False
    )

    scenario_comparison.to_csv(
        OUTPUT_DIR
        / "scenario_comparison.csv",
        index=False
    )

    break_even.to_csv(
        OUTPUT_DIR
        / "scenario_b_break_even.csv",
        index=False
    )

    sensitivity.to_csv(
        OUTPUT_DIR
        / "scenario_b_sensitivity.csv",
        index=False
    )

    print(
        f"\nOutputs saved to: {OUTPUT_DIR}"
    )


if __name__ == "__main__":
    main()