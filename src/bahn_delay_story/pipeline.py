"""DuckDB pipeline for turning raw monthly stop data into analysis tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from bahn_delay_story.config import DEFAULT_DATABASE, PROCESSED_DIR, SQL_DIR, source_parquet_files

SQL_STEPS = [
    SQL_DIR / "02_clean_stops.sql",
    SQL_DIR / "03_features_delay_metrics.sql",
]

OUTPUT_TABLES = [
    "stops_clean",
    "station_day_metrics",
    "train_type_day_metrics",
    "hourly_delay_metrics",
    "line_metrics",
]


def duckdb_string_literal(value: str) -> str:
    """Return a safely quoted DuckDB string literal."""
    return "'" + value.replace("'", "''") + "'"


def duckdb_path_list(paths: list[Path]) -> str:
    """Return a DuckDB SQL list literal for local Parquet paths."""
    return "[" + ", ".join(duckdb_string_literal(str(path)) for path in paths) + "]"


def source_files() -> list[Path]:
    """Return downloaded processed Parquet files."""
    return source_parquet_files()


def ensure_source_data() -> None:
    if not source_files():
        raise FileNotFoundError(
            "No source Parquet files found in data/raw/yearly_processed_data or "
            "data/raw/monthly_processed_data. "
            "Run `uv run bahn-download` or see README.md for Hugging Face download commands."
        )


def run_pipeline(database: Path = DEFAULT_DATABASE, sample_limit: int | None = None) -> None:
    """Build cleaned and aggregated Parquet outputs."""
    ensure_source_data()
    if sample_limit is not None:
        sample_limit = int(sample_limit)
        if sample_limit <= 0:
            raise ValueError("sample_limit must be positive.")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    database.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(database) as con:
        source_path_sql = duckdb_path_list(source_files())
        if sample_limit:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW monthly_raw AS
                SELECT *
                FROM read_parquet({source_path_sql}, union_by_name = true)
                LIMIT {sample_limit}
                """,
            )
        else:
            con.execute(
                f"""
                CREATE OR REPLACE VIEW monthly_raw AS
                SELECT *
                FROM read_parquet({source_path_sql}, union_by_name = true)
                """,
            )

        for step in SQL_STEPS:
            con.execute(step.read_text())

        for table in OUTPUT_TABLES:
            output_path = PROCESSED_DIR / f"{table}.parquet"
            con.execute(
                f"COPY {table} TO {duckdb_string_literal(str(output_path))} (FORMAT PARQUET)"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BahnDelayStory DuckDB pipeline.")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=None,
        help="Optional row limit for fast smoke tests.",
    )
    args = parser.parse_args()
    run_pipeline(database=args.database, sample_limit=args.sample_limit)


if __name__ == "__main__":
    main()
