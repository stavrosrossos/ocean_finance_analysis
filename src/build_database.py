from pathlib import Path  # noqa: I001

import duckdb
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Credit Platform_Analytics Engineer_exercise.xlsx"
)

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ocean_finance.duckdb"
)


def main():
    quote_data = pd.read_excel(
        RAW_FILE,
        sheet_name="CreditCardQuoteData"
    )

    sales_data = pd.read_excel(
        RAW_FILE,
        sheet_name="Sales Data"
    )

    # Standardise column names for SQL
    quote_data = quote_data.rename(
        columns={
            "ComparisonApplicationID": "application_id",
            "Credit Card ID": "card_id",
            "ComparisonCardClicked": "clicked",
            "ComparisonCardAPR": "apr",
            "RankComparisonCardAPR": "apr_rank",
            "ComparisonCardLikelihood": "likelihood",
            "RankComparisonCardLikelihood": "likelihood_rank",
        }
    )

    sales_data = sales_data.rename(
        columns={
            "Card ID": "card_id",
            "Sales": "sales",
            "Revenue": "revenue",
        }
    )

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with duckdb.connect(str(DB_PATH)) as con:
        con.register("quote_df", quote_data)
        con.register("sales_df", sales_data)

        con.execute("""
            CREATE OR REPLACE TABLE quotes AS
            SELECT *
            FROM quote_df
        """)

        con.execute("""
            CREATE OR REPLACE TABLE sales AS
            SELECT *
            FROM sales_df
        """)

        quote_rows = con.execute(
            "SELECT COUNT(*) FROM quotes"
        ).fetchone()[0]

        sales_rows = con.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

    print(f"Database created: {DB_PATH}")
    print(f"Quote rows: {quote_rows:,}")
    print(f"Sales rows: {sales_rows:,}")


if __name__ == "__main__":
    main()