"""Staged data-quality assertions for the BahnDelayStory pipeline.

Each `check_*` function runs against an already-open DuckDB connection, returns
a metrics dict, and raises :class:`QualityError` on a hard failure. The pipeline
calls the three stages in order while it builds:

1. ``check_source``   — after the ``monthly_raw`` view is registered
2. ``check_clean``    — after ``sql/02_clean_stops.sql``
3. ``check_features`` — after ``sql/03_features_delay_metrics.sql``

`verify_database` re-runs the same checks read-only against an existing build
so a finished database can be re-validated without a full rebuild.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from bahn_delay_story.config import DEFAULT_DATABASE

# Feature tables and the share/count columns they all expose.
FEATURE_TABLES = (
    "station_day_metrics",
    "train_type_day_metrics",
    "hourly_delay_metrics",
    "line_metrics",
)

# Cleaning bounds applied in sql/02_clean_stops.sql.
DELAY_MIN_FLOOR = -60
DELAY_MIN_CEIL = 720

# line_metrics keeps only groups with at least this many stops (HAVING clause).
LINE_METRICS_MIN_STOPS = 100


class QualityError(AssertionError):
    """Raised when a pipeline data-quality assertion fails."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise QualityError(message)


def require_file(path: Path) -> None:
    """Raise if a required file is missing."""
    if not path.exists():
        raise FileNotFoundError(f"Required file does not exist: {path}")


def check_source(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Assert the registered ``monthly_raw`` view has usable rows.

    Cleaning later drops rows with a null ``id`` or ``time``; here we only
    report those counts and assert that some source rows exist at all.
    """
    rows_raw, null_ids, null_times = con.execute(
        """
        SELECT
          COUNT(*),
          COUNT(*) FILTER (WHERE id IS NULL),
          COUNT(*) FILTER (WHERE time IS NULL)
        FROM monthly_raw
        """
    ).fetchone()

    metrics = {
        "rows_raw": int(rows_raw),
        "null_ids": int(null_ids),
        "null_times": int(null_times),
    }
    _require(
        metrics["rows_raw"] > 0,
        "monthly_raw is empty; no source Parquet rows were registered.",
    )
    return metrics


def check_clean(con: duckdb.DuckDBPyConnection) -> dict[str, object]:
    """Assert row counts, null rates, key uniqueness, and bounds on stops_clean."""
    row = con.execute(
        f"""
        SELECT
          COUNT(*),
          COUNT(DISTINCT stop_id),
          COUNT(*) FILTER (WHERE stop_id IS NULL),
          COUNT(*) FILTER (WHERE event_time IS NULL),
          COUNT(*) FILTER (WHERE delay_min IS NULL),
          COUNT(*) FILTER (
            WHERE delay_min < {DELAY_MIN_FLOOR} OR delay_min > {DELAY_MIN_CEIL}
          ),
          COUNT(*) FILTER (
            WHERE is_canceled AND (is_late_6_min OR is_late_15_min OR is_late_60_min)
          ),
          COUNT(*) FILTER (WHERE station_name IS NULL),
          COUNT(DISTINCT station_name),
          COUNT(DISTINCT train_type),
          MIN(service_date),
          MAX(service_date)
        FROM stops_clean
        """
    ).fetchone()

    metrics: dict[str, object] = {
        "rows_clean": int(row[0]),
        "distinct_stop_ids": int(row[1]),
        "null_stop_ids": int(row[2]),
        "null_event_times": int(row[3]),
        "null_delay_min": int(row[4]),
        "out_of_range_delays": int(row[5]),
        "canceled_but_late": int(row[6]),
        "null_station_names": int(row[7]),
        "distinct_stations": int(row[8]),
        "distinct_train_types": int(row[9]),
        "min_service_date": str(row[10]),
        "max_service_date": str(row[11]),
    }

    _require(metrics["rows_clean"] > 0, "stops_clean is empty.")
    _require(metrics["null_stop_ids"] == 0, "stops_clean contains null stop_id values.")
    _require(
        metrics["null_event_times"] == 0,
        "stops_clean contains null event_time values.",
    )
    _require(
        metrics["distinct_stop_ids"] == metrics["rows_clean"],
        f"stop_id is not a unique key: {metrics['rows_clean']} rows but "
        f"{metrics['distinct_stop_ids']} distinct stop_id values.",
    )
    _require(
        metrics["out_of_range_delays"] == 0,
        f"stops_clean has delay_min outside the cleaning bounds "
        f"[{DELAY_MIN_FLOOR}, {DELAY_MIN_CEIL}].",
    )
    _require(
        metrics["canceled_but_late"] == 0,
        "stops_clean has canceled stops still flagged by an is_late_* column.",
    )
    return metrics


def check_features(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, int]]:
    """Assert each feature table is non-empty with valid shares and counts."""
    metrics: dict[str, dict[str, int]] = {}

    for table in FEATURE_TABLES:
        rows, bad_shares, canceled_over, bad_stop_count = con.execute(
            f"""
            SELECT
              COUNT(*),
              COUNT(*) FILTER (
                WHERE cancellation_share NOT BETWEEN 0 AND 1
                   OR late_share_6_min  NOT BETWEEN 0 AND 1
                   OR late_share_15_min NOT BETWEEN 0 AND 1
              ),
              COUNT(*) FILTER (WHERE canceled_count > stop_count),
              COUNT(*) FILTER (WHERE stop_count <= 0)
            FROM {table}
            """
        ).fetchone()

        table_metrics = {
            "rows": int(rows),
            "shares_out_of_range": int(bad_shares),
            "canceled_over_stops": int(canceled_over),
            "nonpositive_stop_count": int(bad_stop_count),
        }
        _require(table_metrics["rows"] > 0, f"{table} is empty.")
        _require(
            table_metrics["shares_out_of_range"] == 0,
            f"{table} has share columns outside [0, 1].",
        )
        _require(
            table_metrics["canceled_over_stops"] == 0,
            f"{table} has rows where canceled_count exceeds stop_count.",
        )
        _require(
            table_metrics["nonpositive_stop_count"] == 0,
            f"{table} has rows with a non-positive stop_count.",
        )
        metrics[table] = table_metrics

    below_floor = con.execute(
        f"SELECT COUNT(*) FROM line_metrics WHERE stop_count < {LINE_METRICS_MIN_STOPS}"
    ).fetchone()[0]
    _require(
        int(below_floor) == 0,
        f"line_metrics has rows below the HAVING floor of "
        f"{LINE_METRICS_MIN_STOPS} stops.",
    )
    return metrics


def format_report(report: dict[str, object]) -> str:
    """Render a quality report dict as compact, human-readable lines."""
    source = report["source"]
    clean = report["clean"]
    features = report["features"]
    lines = [
        f"[quality] source   rows_raw={source['rows_raw']:,} "
        f"null_id={source['null_ids']:,} null_time={source['null_times']:,}",
        f"[quality] clean    rows={clean['rows_clean']:,} "
        f"stations={clean['distinct_stations']:,} "
        f"train_types={clean['distinct_train_types']:,} "
        f"dates {clean['min_service_date']}..{clean['max_service_date']} "
        f"null_delay={clean['null_delay_min']:,} "
        f"null_station={clean['null_station_names']:,}",
    ]
    for table, table_metrics in features.items():
        lines.append(f"[quality] feature  {table} rows={table_metrics['rows']:,}")
    lines.append("[quality] all checks passed")
    return "\n".join(lines)


def verify_database(database: Path = DEFAULT_DATABASE) -> dict[str, object]:
    """Re-run every quality check read-only against an existing build."""
    require_file(database)
    with duckdb.connect(str(database), read_only=True) as con:
        report = {
            "source": check_source(con),
            "clean": check_clean(con),
            "features": check_features(con),
        }
    return report


def main() -> None:
    """CLI entry point: validate the default database and print a report."""
    print(format_report(verify_database()))


if __name__ == "__main__":
    main()
