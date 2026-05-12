"""Quality checks for pipeline inputs and outputs."""

from __future__ import annotations

from pathlib import Path

import duckdb

from bahn_delay_story.config import DEFAULT_DATABASE, PROCESSED_DIR


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file does not exist: {path}")


def run_output_checks(database: Path = DEFAULT_DATABASE) -> dict[str, int | float]:
    """Run lightweight checks against the built DuckDB database."""
    require_file(database)
    with duckdb.connect(database, read_only=True) as con:
        metrics = con.execute(
            """
            SELECT
              COUNT(*) AS rows_clean,
              COUNT(*) FILTER (WHERE stop_id IS NULL) AS null_stop_ids,
              COUNT(*) FILTER (WHERE event_time IS NULL) AS null_event_times,
              COUNT(*) FILTER (WHERE delay_min > 360) AS delays_over_6h
            FROM stops_clean
            """
        ).fetchone()

    result = {
        "rows_clean": int(metrics[0]),
        "null_stop_ids": int(metrics[1]),
        "null_event_times": int(metrics[2]),
        "delays_over_6h": int(metrics[3]),
    }

    if result["rows_clean"] == 0:
        raise AssertionError("stops_clean is empty.")
    if result["null_stop_ids"] > 0:
        raise AssertionError("stops_clean contains null stop_id values.")
    if result["null_event_times"] > 0:
        raise AssertionError("stops_clean contains null event_time values.")

    return result


def processed_outputs() -> list[Path]:
    return sorted(PROCESSED_DIR.glob("*.parquet"))
