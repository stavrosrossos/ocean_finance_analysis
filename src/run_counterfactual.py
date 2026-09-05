from pathlib import Path

import duckdb
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
    # Applicants who actually clicked Card 29
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

    # Remove Card 29 and retain the alternatives
    alternatives = card29_clickers[
        card29_clickers["card_id"] != "Card 29"
    ].copy()

    # Transparent strongest-visible-alternative rule:
    # best likelihood rank, then lowest APR,
    # then card ID as deterministic tie-breaker.
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

    scenario_a_sales = (
        replacement_performance[
            "click_to_sale_rate"
        ].sum()
    )

    scenario_a_revenue = (
        replacement_performance[
            "revenue_per_click"
        ].sum()
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

    summary = pd.DataFrame({
        "metric": [
            "Card 29 clickers",
            "Eligible replacement clickers",
            "No alternative",
            "Expected sales",
            "Expected revenue",
        ],
        "value": [
            len(card29_clicker_ids),
            len(replacement_performance),
            len(card29_clicker_ids)
            - len(replacement_performance),
            scenario_a_sales,
            scenario_a_revenue,
        ]
    })

    return (
        summary,
        replacement_distribution,
        replacement_performance,
    )


def main():
    quotes, card_performance = load_data()

    (
        scenario_a_summary,
        replacement_distribution,
        _
    ) = build_scenario_a(
        quotes,
        card_performance
    )

    print("\nSCENARIO A — STRONGEST VISIBLE ALTERNATIVE")
    print("=" * 50)
    print(
        scenario_a_summary.to_string(
            index=False
        )
    )

    print("\nTOP MODELLED REPLACEMENTS")
    print("=" * 50)
    print(
        replacement_distribution
        .head(15)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()