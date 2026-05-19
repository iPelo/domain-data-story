"""DuckDB pipeline for turning raw monthly stop data into analysis tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from bahn_delay_story.config import DEFAULT_DATABASE, PROCESSED_DIR, SQL_DIR, source_parquet_files
from bahn_delay_story.quality import (
    check_clean,
    check_features,
    check_source,
    format_report,
)

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


def run_pipeline(
    database: Path = DEFAULT_DATABASE,
    sample_limit: int | None = None,
    output_dir: Path = PROCESSED_DIR,
) -> dict[str, object]:
    """Build cleaned and aggregated Parquet outputs.

    Quality assertions run after each stage: against the registered source
    view, against ``stops_clean``, and against the feature tables. Any failure
    raises and aborts before outputs are written. Returns the quality report.
    """
    ensure_source_data()
    if sample_limit is not None:
        sample_limit = int(sample_limit)
        if sample_limit <= 0:
            raise ValueError("sample_limit must be positive.")

    output_dir.mkdir(parents=True, exist_ok=True)
    database.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(database) as con:
        source_path_sql = duckdb_path_list(source_files())
        limit_clause = f"\nLIMIT {sample_limit}" if sample_limit else ""
        con.execute(
            f"""
            CREATE OR REPLACE VIEW monthly_raw AS
            SELECT *
            FROM read_parquet({source_path_sql}, union_by_name = true){limit_clause}
            """,
        )

        report: dict[str, object] = {"source": check_source(con)}

        con.execute(SQL_STEPS[0].read_text())
        report["clean"] = check_clean(con)

        con.execute(SQL_STEPS[1].read_text())
        report["features"] = check_features(con)

        for table in OUTPUT_TABLES:
            output_path = output_dir / f"{table}.parquet"
            con.execute(
                f"COPY {table} TO {duckdb_string_literal(str(output_path))} (FORMAT PARQUET)"
            )

    print(format_report(report))
    return report


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
