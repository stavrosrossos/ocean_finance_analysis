from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


# ============================================================
# Paths / constants
# ============================================================

DB_PATH = Path("data/processed/ocean_finance.duckdb")
OUTPUT_DIR = Path("outputs/tables")

CARD29 = 29
MIN_HISTORICAL_SUPPORT = 10

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Load data
# ============================================================

con = duckdb.connect(str(DB_PATH), read_only=True)

quotes = con.execute("""
    SELECT *
    FROM quotes
""").df()

sales = con.execute("""
    SELECT *
    FROM sales
""").df()

con.close()


# DuckDB stores IDs as strings such as "Card 29"
quotes["card_id"] = (
    quotes["card_id"]
    .astype(str)
    .str.extract(r"(\d+)", expand=False)
    .astype(int)
)

sales["card_id"] = (
    sales["card_id"]
    .astype(str)
    .str.extract(r"(\d+)", expand=False)
    .astype(int)
)


# ============================================================
# 1. Card 29 intervention population
# ============================================================

card29_clicker_ids = (
    quotes.loc[
        (quotes["card_id"] == CARD29) &
        (quotes["clicked"] == 1),
        "application_id"
    ]
    .drop_duplicates()
)

assert len(card29_clicker_ids) == 398


card29_panels = quotes[
    quotes["application_id"].isin(card29_clicker_ids)
].copy()


alternative_sets = (
    card29_panels
    .groupby("application_id")
    .apply(
        lambda g: tuple(
            sorted(
                g.loc[
                    g["card_id"] != CARD29,
                    "card_id"
                ].astype(int).unique()
            )
        ),
        include_groups=False
    )
    .rename("alternative_cards")
    .reset_index()
)

alternative_sets["alternative_count"] = (
    alternative_sets["alternative_cards"].apply(len)
)

alternative_sets["intervention_group"] = np.where(
    alternative_sets["alternative_count"] == 0,
    "retain_card29",
    "suppress_card29"
)


n_total = len(alternative_sets)
n_retain = (alternative_sets["alternative_count"] == 0).sum()
n_suppress = (alternative_sets["alternative_count"] > 0).sum()

assert n_total == 398
assert n_retain == 83
assert n_suppress == 315


intervention_summary = pd.DataFrame({
    "group": [
        "all_card29_clickers",
        "suppress_card29",
        "retain_card29"
    ],
    "applications": [
        n_total,
        n_suppress,
        n_retain
    ]
})

intervention_summary["share"] = (
    intervention_summary["applications"] / n_total
)


alternative_distribution = (
    alternative_sets.loc[
        alternative_sets["intervention_group"] == "suppress_card29",
        "alternative_count"
    ]
    .value_counts()
    .sort_index()
    .rename_axis("alternative_count")
    .reset_index(name="applications")
)

alternative_distribution["share"] = (
    alternative_distribution["applications"] /
    n_suppress
)


# ============================================================
# 2. Remove Card 29 and recompute rankings
# ============================================================

affected_ids = set(
    alternative_sets.loc[
        alternative_sets["intervention_group"] == "suppress_card29",
        "application_id"
    ]
)

post_removal = card29_panels[
    card29_panels["application_id"].isin(affected_ids) &
    (card29_panels["card_id"] != CARD29)
].copy()

assert post_removal["application_id"].nunique() == 315


post_removal["likelihood_rank_after"] = (
    post_removal
    .groupby("application_id")["likelihood"]
    .rank(method="min", ascending=False)
    .astype(int)
)

post_removal["apr_rank_after"] = (
    post_removal
    .groupby("application_id")["apr"]
    .rank(method="min", ascending=True)
    .astype(int)
)


rank1_sets = (
    post_removal[
        post_removal["likelihood_rank_after"] == 1
    ]
    .groupby("application_id")["card_id"]
    .agg(lambda x: tuple(sorted(x.astype(int).unique())))
    .rename("rank1_cards")
    .reset_index()
)


rank1_distribution = (
    rank1_sets["rank1_cards"]
    .apply(len)
    .value_counts()
    .sort_index()
    .rename_axis("number_of_rank1_cards")
    .reset_index(name="applications")
)

rank1_distribution["share"] = (
    rank1_distribution["applications"] /
    n_suppress
)


# ============================================================
# 3. Historical reference population: Card 29 absent
# ============================================================

apps_with_29 = set(
    quotes.loc[
        quotes["card_id"] == CARD29,
        "application_id"
    ]
)

no29 = quotes[
    ~quotes["application_id"].isin(apps_with_29)
].copy()

assert CARD29 not in no29["card_id"].unique()


no29_rank1_sets = (
    no29[
        no29["likelihood_rank"] == 1
    ]
    .groupby("application_id")["card_id"]
    .agg(lambda x: tuple(sorted(x.astype(int).unique())))
    .rename("rank1_cards")
    .reset_index()
)


historical_rank1_counts = (
    no29_rank1_sets["rank1_cards"]
    .value_counts()
    .rename_axis("rank1_cards")
    .reset_index(name="historical_applications")
)


# ============================================================
# 4. Historical support for affected rank-1 states
# ============================================================

affected_rank1_support = (
    rank1_sets
    .merge(
        historical_rank1_counts,
        on="rank1_cards",
        how="left"
    )
)

affected_rank1_support["historical_applications"] = (
    affected_rank1_support["historical_applications"]
    .fillna(0)
    .astype(int)
)

affected_rank1_support["support_group"] = np.where(
    affected_rank1_support["historical_applications"]
    >= MIN_HISTORICAL_SUPPORT,
    "empirically_supported",
    "residual_sensitivity"
)


support_summary = (
    affected_rank1_support["support_group"]
    .value_counts()
    .rename_axis("group")
    .reset_index(name="applications")
)

support_summary["share_of_affected"] = (
    support_summary["applications"] / n_suppress
)


supported_apps = affected_rank1_support[
    affected_rank1_support["support_group"]
    == "empirically_supported"
].copy()

residual_apps = affected_rank1_support[
    affected_rank1_support["support_group"]
    == "residual_sensitivity"
].copy()

assert len(supported_apps) == 282
assert len(residual_apps) == 33


# ============================================================
# 5. Historical click behaviour by rank-1 state
# ============================================================

affected_rank1_counts = (
    supported_apps["rank1_cards"]
    .value_counts()
    .rename_axis("rank1_cards")
    .reset_index(name="affected_applications")
)


prediction_rows = []

for _, affected_row in affected_rank1_counts.iterrows():

    rank1_set = affected_row["rank1_cards"]
    n_affected = int(affected_row["affected_applications"])

    hist_app_ids = set(
        no29_rank1_sets.loc[
            no29_rank1_sets["rank1_cards"] == rank1_set,
            "application_id"
        ]
    )

    hist = no29[
        no29["application_id"].isin(hist_app_ids)
    ]

    n_hist = len(hist_app_ids)

    row = {
        "rank1_cards": rank1_set,
        "affected_applications": n_affected,
        "historical_applications": n_hist
    }

    expected_top_rank_clicks = 0.0

    for card in rank1_set:

        historical_card_clicks = (
            (
                (hist["card_id"] == card) &
                (hist["clicked"] == 1)
            )
            .sum()
        )

        click_probability = (
            historical_card_clicks / n_hist
        )

        expected_clicks = (
            n_affected * click_probability
        )

        row[f"card_{card}_click_probability"] = (
            click_probability
        )

        row[f"card_{card}_expected_clicks"] = (
            expected_clicks
        )

        expected_top_rank_clicks += expected_clicks

    row["expected_top_rank_clicks"] = (
        expected_top_rank_clicks
    )

    row["expected_no_top_rank_click"] = (
        n_affected - expected_top_rank_clicks
    )

    prediction_rows.append(row)


supported_predictions = (
    pd.DataFrame(prediction_rows)
    .sort_values(
        "affected_applications",
        ascending=False
    )
    .reset_index(drop=True)
)


# ============================================================
# 6. Aggregate expected clicks by destination card
# ============================================================

card_expected_clicks = {}

for _, row in supported_predictions.iterrows():

    for card in row["rank1_cards"]:

        col = f"card_{card}_expected_clicks"

        card_expected_clicks[card] = (
            card_expected_clicks.get(card, 0.0)
            + row[col]
        )


expected_clicks_by_card = (
    pd.DataFrame([
        {
            "card_id": card,
            "expected_clicks": clicks
        }
        for card, clicks in card_expected_clicks.items()
    ])
    .sort_values(
        "expected_clicks",
        ascending=False
    )
    .reset_index(drop=True)
)


# ============================================================
# 7. Card-level downstream economics
# ============================================================

clicks_by_card = (
    quotes
    .groupby("card_id")
    .agg(
        clicks=("clicked", "sum")
    )
    .reset_index()
)


card_perf = (
    clicks_by_card
    .merge(
        sales,
        on="card_id",
        how="left"
    )
)

card_perf["conversion_rate"] = (
    card_perf["sales"] /
    card_perf["clicks"]
)

card_perf["revenue_per_click"] = (
    card_perf["revenue"] /
    card_perf["clicks"]
)


supported_economics = (
    expected_clicks_by_card
    .merge(
        card_perf[
            [
                "card_id",
                "conversion_rate",
                "revenue_per_click"
            ]
        ],
        on="card_id",
        how="left"
    )
)

supported_economics["expected_sales"] = (
    supported_economics["expected_clicks"]
    * supported_economics["conversion_rate"]
)

supported_economics["expected_revenue"] = (
    supported_economics["expected_clicks"]
    * supported_economics["revenue_per_click"]
)

supported_economics = (
    supported_economics
    .sort_values(
        "expected_revenue",
        ascending=False
    )
    .reset_index(drop=True)
)


supported_expected_clicks = (
    supported_economics["expected_clicks"].sum()
)

supported_expected_sales = (
    supported_economics["expected_sales"].sum()
)

supported_expected_revenue = (
    supported_economics["expected_revenue"].sum()
)


# ============================================================
# 8. Residual 33: value of one transfer
# ============================================================

rpc_map = (
    card_perf
    .set_index("card_id")["revenue_per_click"]
    .to_dict()
)

conversion_map = (
    card_perf
    .set_index("card_id")["conversion_rate"]
    .to_dict()
)


def mean_metric(cards, metric_map):
    return np.mean(
        [metric_map[card] for card in cards]
    )


residual_apps["revenue_per_transfer_click"] = (
    residual_apps["rank1_cards"]
    .apply(
        lambda cards: mean_metric(cards, rpc_map)
    )
)

residual_apps["sales_per_transfer_click"] = (
    residual_apps["rank1_cards"]
    .apply(
        lambda cards: mean_metric(
            cards,
            conversion_map
        )
    )
)


residual_full_transfer_revenue = (
    residual_apps["revenue_per_transfer_click"]
    .sum()
)

residual_full_transfer_sales = (
    residual_apps["sales_per_transfer_click"]
    .sum()
)


# ============================================================
# 9. Corrected break-even sensitivity
# ============================================================

card29_row = card_perf.loc[
    card_perf["card_id"] == CARD29
].iloc[0]

CARD29_TOTAL_REVENUE = float(
    card29_row["revenue"]
)

CARD29_TOTAL_SALES = int(
    card29_row["sales"]
)

CARD29_REVENUE_PER_SALE = (
    CARD29_TOTAL_REVENUE /
    CARD29_TOTAL_SALES
)


sensitivity_rows = []

for retained_sales in range(
    CARD29_TOTAL_SALES + 1
):

    retained_revenue = (
        retained_sales
        * CARD29_REVENUE_PER_SALE
    )

    affected_card29_baseline = (
        CARD29_TOTAL_REVENUE
        - retained_revenue
    )

    revenue_gap_after_supported = (
        affected_card29_baseline
        - supported_expected_revenue
    )

    required_transfer_rate = (
        revenue_gap_after_supported /
        residual_full_transfer_revenue
    )

    sensitivity_rows.append({
        "retained_card29_sales":
            retained_sales,

        "retained_card29_revenue":
            retained_revenue,

        "affected_card29_baseline_revenue":
            affected_card29_baseline,

        "supported_replacement_revenue":
            supported_expected_revenue,

        "revenue_gap_after_supported":
            revenue_gap_after_supported,

        "required_residual_transfer_rate":
            required_transfer_rate
    })


break_even_sensitivity = pd.DataFrame(
    sensitivity_rows
)


# Full 2D sensitivity matrix:
# retained sales x residual transfer rate

matrix_rows = []

for retained_sales in range(
    CARD29_TOTAL_SALES + 1
):

    retained_revenue = (
        retained_sales
        * CARD29_REVENUE_PER_SALE
    )

    current_affected_revenue = (
        CARD29_TOTAL_REVENUE
        - retained_revenue
    )

    for transfer_rate in np.arange(
        0,
        1.01,
        0.10
    ):

        replacement_revenue = (
            supported_expected_revenue
            + transfer_rate
            * residual_full_transfer_revenue
        )

        revenue_change = (
            replacement_revenue
            - current_affected_revenue
        )

        matrix_rows.append({
            "retained_card29_sales":
                retained_sales,

            "retained_card29_revenue":
                retained_revenue,

            "residual_transfer_rate":
                round(float(transfer_rate), 2),

            "replacement_revenue":
                replacement_revenue,

            "affected_card29_baseline_revenue":
                current_affected_revenue,

            "revenue_change":
                revenue_change
        })


break_even_matrix = pd.DataFrame(matrix_rows)


# ============================================================
# 10. Export
# ============================================================

intervention_summary.to_csv(
    OUTPUT_DIR /
    "conditional_intervention_summary.csv",
    index=False
)

alternative_distribution.to_csv(
    OUTPUT_DIR /
    "conditional_alternative_distribution.csv",
    index=False
)

rank1_distribution.to_csv(
    OUTPUT_DIR /
    "conditional_rank1_distribution.csv",
    index=False
)

support_summary.to_csv(
    OUTPUT_DIR /
    "conditional_support_summary.csv",
    index=False
)

supported_predictions.to_csv(
    OUTPUT_DIR /
    "conditional_rank1_predictions.csv",
    index=False
)

expected_clicks_by_card.to_csv(
    OUTPUT_DIR /
    "conditional_expected_clicks_by_card.csv",
    index=False
)

supported_economics.to_csv(
    OUTPUT_DIR /
    "conditional_supported_economics.csv",
    index=False
)

residual_apps.to_csv(
    OUTPUT_DIR /
    "conditional_residual_apps.csv",
    index=False
)

break_even_sensitivity.to_csv(
    OUTPUT_DIR /
    "conditional_break_even_sensitivity.csv",
    index=False
)

break_even_matrix.to_csv(
    OUTPUT_DIR /
    "conditional_break_even_matrix.csv",
    index=False
)


# ============================================================
# Console summary
# ============================================================

print()
print("=" * 60)
print("CONDITIONAL CARD 29 COUNTERFACTUAL")
print("=" * 60)

print(f"Card 29 clickers:                {n_total}")
print(f"Retain Card 29:                  {n_retain}")
print(f"Suppress Card 29:                {n_suppress}")

print()

print(
    f"Empirically supported:           "
    f"{len(supported_apps)}"
)

print(
    f"Residual sensitivity group:      "
    f"{len(residual_apps)}"
)

print()

print(
    f"Expected replacement clicks:     "
    f"{supported_expected_clicks:.2f}"
)

print(
    f"Expected replacement sales:      "
    f"{supported_expected_sales:.2f}"
)

print(
    f"Expected replacement revenue:    "
    f"£{supported_expected_revenue:,.2f}"
)

print()

print(
    f"Residual 100% transfer revenue:  "
    f"£{residual_full_transfer_revenue:,.2f}"
)

print(
    f"Residual 100% transfer sales:    "
    f"{residual_full_transfer_sales:.2f}"
)

print()

print("Tables exported to:")
print(OUTPUT_DIR.resolve())