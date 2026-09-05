from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ocean_finance.duckdb"
)

SQL_DIR = PROJECT_ROOT / "sql"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "tables"


QUERIES = {
    "panel_baseline": "01_panel_baseline.sql",
    "card_performance": "02_card_performance.sql",
    "card29_context": "03_card29_context.sql",
}


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with duckdb.connect(
        str(DB_PATH),
        read_only=True
    ) as con:

        for output_name, sql_file in QUERIES.items():

            sql = (
                SQL_DIR
                / sql_file
            ).read_text()

            df = con.execute(sql).fetchdf()

            output_path = (
                OUTPUT_DIR
                / f"{output_name}.csv"
            )

            df.to_csv(
                output_path,
                index=False
            )

            print(
                f"{output_name}: "
                f"{len(df):,} rows -> "
                f"{output_path}"
            )


if __name__ == "__main__":
    main()