# Ocean Finance – Credit Card Panel Performance Review

## Overview
This repository contains my analysis for the Ocean Finance Analytics Engineer exercise.

The objective was to evaluate credit card panel performance, identify the strongest intervention opportunity, and assess whether Card 29 should remain in the panel or be conditionally suppressed when alternative offers are available.

The project combines:
- SQL-style analytical logic
- Python-based data preparation and counterfactual modelling
- Excel workings for transparent review and traceability
- A final 2-slide PowerPoint report

## Business Question
Which card is the strongest candidate for intervention, and should Card 29 be removed, deprioritised, or retained?

The analysis focuses on:
1. how cards perform in terms of clicks, sales and revenue
2. whether Card 29 attracts clicks disproportionately
3. whether those clicks monetise efficiently
4. what may happen if Card 29 is conditionally suppressed for applicants who already have alternative offers

## Key Conclusion
Card 29 is the clearest intervention candidate.

It attracts a large share of clicks, but converts those clicks into sales less efficiently than both the panel baseline and key alternative cards.

However, a full panel-wide removal is not supported by the structure of the data, because some Card 29 clickers had no alternative offer.

The recommended action is therefore:

> **Run a controlled conditional suppression / deprioritisation test for applicants who have at least one alternative offer, while retaining Card 29 for applicants for whom it is the only available offer.**

## Repository Structure

```text
ocean_finance_analysis/
├── data/
│   ├── raw/
│   │   └── Credit Platform_Analytics Engineer_exercise.xlsx
│   └── processed/
│       └── ocean_finance.duckdb
├── notebooks/
│   ├── 01_panel_analysis.ipynb
│   └── 02_conditional_counterfactual.ipynb
├── outputs/
│   ├── tables/
│   └── final/
├── sql/
│   ├── 01_panel_baseline.sql
│   ├── 02_card_performance.sql
│   └── 03_card29_context.sql
├── src/
│   ├── build_database.py
│   ├── export_analysis_tables.py
│   ├── run_counterfactual.py
│   ├── run_conditional_counterfactual.py
│   └── build_excel_workings.py
├── README.md
└── requirements.txt
```

## Data Used
The source workbook contains quote-level offer data and card-level sales/revenue data for the same panel and time period.

### Quote data
Offer-level records contain fields including:
- application ID
- card ID
- click flag
- APR
- APR rank
- likelihood score
- likelihood rank

### Sales data
Card-level outcomes contain:
- card ID
- sales
- revenue

## Analytical Workflow

### 1. Data validation and setup
The raw workbook was inspected and validated before analysis.

Key checks included:
- row counts
- field types
- missing values
- duplicate application-card rows
- card coverage across quote and sales data

Observed data size:
- 9,945 quote rows
- 3,684 unique applications
- 34 cards
- no duplicate application-card rows
- no missing values in the core analytical fields

### 2. Panel baseline
Whole-panel KPIs were calculated to create benchmarks for card-level comparison.

Key baseline metrics:
- Applications: 3,684
- Total offers: 9,945
- Applications with at least one click: 1,841
- Total clicks: 1,863
- Total sales: 555
- Total revenue: £21,087.86
- Application clickout rate: 50.0%
- Offer click-through rate: 18.7%
- Click-to-sale conversion: 29.8%
- Revenue per click: £11.32
- Revenue per application: £5.72

### 3. Card performance review
Card-level KPIs were calculated including:
- offers
- clicks
- click-through rate
- sales
- click-to-sale conversion
- revenue
- revenue per click
- revenue per offer
- revenue per sale

This identified Card 29 as the strongest intervention candidate.

Card 29:
- Offers: 1,596
- Clicks: 398
- Sales: 63
- Click-to-sale conversion: 15.8%
- Revenue: £2,772
- Revenue per click: £6.96

Compared with panel baseline:
- Click-to-sale conversion: 29.8%
- Revenue per click: £11.32

Main comparison cards:
- Card 30: 31.7% conversion, £13.94 revenue/click
- Card 31: 26.3% conversion, £11.55 revenue/click

Cards 29, 30 and 31 each generate £44 per sale, so Card 29's weaker monetisation is conversion-driven rather than payout-driven.

### 4. Card 29 competitive context
Same-application comparisons were used to understand how Card 29 behaves when competing directly with other offers.

Card 29 vs Card 30:
- 1,251 applications contained both cards
- Card 29 clicks: 266 / 1,251 = 21.3%
- Card 30 clicks: 112 / 1,251 = 9.0%
- Card 29 was clicked 2.38x as often
- Card 29 had the lower APR in 100% of these pairwise comparisons

Card 29 vs Card 31:
- 1,278 applications contained both cards
- Card 29 clicks: 274 / 1,278 = 21.4%
- Card 31 clicks: 57 / 1,278 = 4.5%
- Card 29 was clicked 4.81x as often
- Card 29 had the lower APR in 100% of these pairwise comparisons

Interpretation:
Card 29 attracts a disproportionate share of clicks when strong alternatives are visible, but converts those clicks relatively weakly downstream.

This is observational evidence of diversion risk, not proof that every Card 29 click would move elsewhere if the card were suppressed.

## Counterfactual Development

### Exploratory full-removal scenario
An initial exploratory counterfactual tested what would happen if Card 29 were removed for all Card 29 clickers.

This was useful for understanding the potential scale of redistribution, but it was not retained as the final business recommendation because 83 Card 29 clickers had no alternative offer.

Removing Card 29 for those applicants would create an unrealistic no-offer outcome and would incorrectly treat them as part of the diversion problem.

The exploratory implementation remains in:

```text
src/run_counterfactual.py
```

It is kept for audit/history only and is not the basis of the final recommendation.

### Final scenario – Conditional suppression
The final intervention is operationally more realistic:

- **Retain Card 29** when it is the applicant's only offer
- **Suppress / deprioritise Card 29** when at least one alternative offer exists

Among the 398 Card 29 clickers:
- 315 had at least one alternative and are part of the intervention population
- 83 had no alternative and retain Card 29

Therefore:
- 79.1% of Card 29 clickers are affected by the intervention
- 20.9% are retained as sole-offer users

## Redistribution Model
After removing Card 29 from the 315 affected applications, ranks were recomputed using the supplied competition/min ranking convention.

A deterministic "next-best-card" approach was not used because 61.3% of affected applicants had more than one card tied at likelihood rank 1 after suppression.

Instead, historical behaviour from applications where Card 29 was absent was used as the behavioural anchor.

### Historical anchor
Historical Card-29-absent applications were grouped by their top-ranked card set.

Likelihood rank 1 captured 95.6% of historical clicks, making the post-suppression rank-1 state the most defensible behavioural matching unit.

A minimum support threshold of 10 historical applications per rank-1 state was used for the point estimate.

This produced:
- Affected applicants: 315
- Empirically supported applicants: 282
- Supported share: 89.5%
- Residual sparse-state group: 33

For the 282 supported applicants, the model estimates:
- Expected replacement clicks: 160.97
- Expected replacement sales: 51.45
- Expected replacement revenue: £2,143.64

The remaining 33 applicants are not forced into a point estimate and are handled through sensitivity analysis.

Lower-ranked clicks are also excluded from the point estimate because lower-card availability differs across otherwise comparable panels. They represented only 4.4% of historical clicks.

## Break-even Sensitivity
Two important quantities cannot be directly observed from the supplied data:

1. how many of Card 29's 63 sales came from the 83 sole-offer users who would retain Card 29
2. how many of the residual 33 sparse-state applicants would transfer to another card after suppression

Sales and revenue are provided only at card level, so the 63 Card 29 sales cannot be directly split between retained and affected applicants.

A two-dimensional break-even sensitivity was therefore used instead of presenting one counterfactual result as certain.

Key reference points:
- Break-even is achievable with full residual transfer once at least ~6 Card 29 sales are retained among the 83 sole-offer users
- At ~15 retained sales, the empirically supported 282 alone are above break-even
- Illustrative proportional reference: if the 83 retained clickers convert at Card 29's overall 15.8% rate, they would imply ~13 retained sales; in that case only ~14.2% of the residual 33 need to transfer to break even

The ~13-sales case is an illustrative sensitivity reference, not an observed subgroup result.

## Final Recommendation
Run a **controlled conditional suppression / deprioritisation test** for Card 29.

### Policy
- Suppress or deprioritise Card 29 when at least one alternative offer exists
- Retain Card 29 when it is the applicant's only offer

### Primary KPI
- Revenue per application

Current baseline:
- £5.72 per application

### Secondary monitoring
- sales per application
- application clickout rate
- click-to-sale conversion
- click redistribution across remaining cards
- destination-card mix

The analysis supports a controlled test rather than immediate permanent removal because the counterfactual outputs are modelled estimates rather than causal measurements.

## How to Run
Run all commands from the repository root.

### 1. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Build the DuckDB database

```bash
python src/build_database.py
```

This creates:

```text
data/processed/ocean_finance.duckdb
```

### 4. Export baseline analytical tables

```bash
python src/export_analysis_tables.py
```

### 5. Run the final conditional counterfactual

```bash
python src/run_conditional_counterfactual.py
```

This writes the final model tables to:

```text
outputs/tables/
```

Key outputs include:
- `conditional_intervention_summary.csv`
- `conditional_alternative_distribution.csv`
- `conditional_rank1_distribution.csv`
- `conditional_support_summary.csv`
- `conditional_rank1_predictions.csv`
- `conditional_expected_clicks_by_card.csv`
- `conditional_supported_economics.csv`
- `conditional_residual_apps.csv`
- `conditional_break_even_sensitivity.csv`
- `conditional_break_even_matrix.csv`

### 6. Build the Excel workings

```bash
python src/build_excel_workings.py
```

The final Excel workbook contains:
1. Executive Summary
2. Panel Baseline
3. Card Performance
4. Card 29 Context
5. Intervention Population
6. Redistribution Model
7. Break-even Sensitivity
8. Methodology

## Final Pipeline
The reproducible final pipeline is:

```text
raw workbook
    ↓
build_database.py
    ↓
ocean_finance.duckdb
    ↓
export_analysis_tables.py
    ↓
run_conditional_counterfactual.py
    ↓
analysis CSV outputs
    ↓
build_excel_workings.py
    ↓
Excel workings + final PowerPoint report
```

`run_counterfactual.py` is intentionally excluded from the final pipeline because it represents the earlier exploratory full-removal scenario.

## Notebooks
The notebooks document the analytical development process.

### `01_panel_analysis.ipynb`
Exploratory panel and card analysis used to identify Card 29 and understand its competitive context.

### `02_conditional_counterfactual.ipynb`
Development and validation of the final conditional-suppression methodology, including:
- intervention population
- post-suppression rank validation
- historical Card-29-absent behaviour
- empirical support thresholds
- destination-card economics
- residual sensitivity
- break-even analysis

The production implementation is reproduced in:

```text
src/run_conditional_counterfactual.py
```

## Assumptions and Limitations
- Sales and revenue are supplied at card level, not application level.
- Card 29's 63 sales therefore cannot be directly allocated between the retained 83 and affected 315 clickers.
- Redirected clicks are assumed to monetise at the destination card's observed overall click-to-sale conversion and revenue per click.
- Historical redistribution is anchored to post-suppression likelihood-rank-1 states.
- Lower-ranked clicks are excluded from the point estimate and represented only indirectly through the conservative modelling approach.
- Sparse historical states are handled via sensitivity rather than unstable point estimates.
- The counterfactual is modelled, not causal.
- The final recommendation is therefore to run a controlled test and monitor outcomes rather than make an immediate permanent product change.

## Deliverables
The repository contains the full reproducible analysis workflow and supports the submitted deliverables:
- final Excel workings
- final 2-slide PowerPoint report
- SQL analysis files
- Python modelling scripts
- analytical notebooks
- exported model tables

