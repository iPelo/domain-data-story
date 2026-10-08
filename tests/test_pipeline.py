"""Pipeline data-quality and reproducibility tests.

The pipeline runs on a small sample into a temporary location, so the real
``data/processed`` outputs and the project database are never touched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from bahn_delay_story.config import source_parquet_files
from bahn_delay_story.pipeline import OUTPUT_TABLES, duckdb_string_literal, run_pipeline
from bahn_delay_story.quality import FEATURE_TABLES

# Large enough that line_metrics clears its HAVING COUNT(*) >= 100 floor.
SAMPLE_LIMIT = 500_000

requires_source = pytest.mark.skipif(
    not source_parquet_files(),
    reason="No source Parquet files in data/raw; run `uv run bahn-download` first.",
)


def _build(tmp_path: Path, name: str) -> tuple[dict, Path]:
    """Run the sampled pipeline into an isolated temp location."""
    output_dir = tmp_path / name
    report = run_pipeline(
        database=tmp_path / f"{name}.duckdb",
        sample_limit=SAMPLE_LIMIT,
        output_dir=output_dir,
    )
    return report, output_dir


@requires_source
def test_pipeline_quality_checks_pass(tmp_path: Path) -> None:
    report, output_dir = _build(tmp_path, "run")

    assert report["source"]["rows_raw"] > 0
    assert report["clean"]["rows_clean"] > 0
    assert report["clean"]["distinct_stop_ids"] == report["clean"]["rows_clean"]
    assert report["clean"]["null_stop_ids"] == 0
    assert report["clean"]["null_event_times"] == 0
    assert report["clean"]["out_of_range_delays"] == 0
    assert report["clean"]["canceled_but_late"] == 0

    for table in FEATURE_TABLES:
        assert report["features"][table]["rows"] > 0

    for table in OUTPUT_TABLES:
        assert (output_dir / f"{table}.parquet").exists()


@requires_source
def test_pipeline_is_idempotent(tmp_path: Path) -> None:
    first_report, first_dir = _build(tmp_path, "first")
    second_report, second_dir = _build(tmp_path, "second")

    assert first_report == second_report

    con = duckdb.connect()
    try:
        for table in OUTPUT_TABLES:
            first = duckdb_string_literal(str(first_dir / f"{table}.parquet"))
            second = duckdb_string_literal(str(second_dir / f"{table}.parquet"))
            only_first, only_second = con.execute(
                f"""
                SELECT
                  (SELECT COUNT(*) FROM (
                     SELECT * FROM read_parquet({first})
                     EXCEPT SELECT * FROM read_parquet({second}))),
                  (SELECT COUNT(*) FROM (
                     SELECT * FROM read_parquet({second})
                     EXCEPT SELECT * FROM read_parquet({first})))
                """
            ).fetchone()
            assert (only_first, only_second) == (0, 0), f"{table} differs between runs"
    finally:
        con.close()


def test_pipeline_with_generated_data(tmp_path: Path, monkeypatch) -> None:
    """Exercise cleaning and exports without downloading the real dataset."""
    source = tmp_path / "data-2025-01.parquet"
    with duckdb.connect() as con:
        con.execute(
            """
            CREATE TABLE sample AS
            SELECT
              CAST(i AS VARCHAR) AS id,
              ' Berlin Hbf ' AS station_name,
              'Berlin Hbf' AS xml_station_name,
              '8011160' AS eva,
              'ICE 123' AS train_name,
              'Hamburg Hbf' AS final_destination_station,
              CASE
                WHEN i = 0 THEN -61
                WHEN i = 1 THEN 721
                ELSE 10
              END AS delay_in_min,
              i = 2 AS is_canceled,
              ' ice ' AS train_type,
              'ride-1' AS train_line_ride_id,
              1 AS train_line_station_num,
              CASE WHEN i = 123 THEN NULL
                   ELSE TIMESTAMP '2025-01-01 12:00:00' END AS time,
              TIMESTAMP '2025-01-01 11:50:00' AS arrival_planned_time,
              NULL::TIMESTAMP AS arrival_change_time,
              NULL::TIMESTAMP AS departure_planned_time,
              NULL::TIMESTAMP AS departure_change_time
            FROM range(124) AS rows(i)
            """
        )
        con.execute(f"COPY sample TO {duckdb_string_literal(str(source))} (FORMAT PARQUET)")

    monkeypatch.setattr("bahn_delay_story.pipeline.source_parquet_files", lambda: [source])
    database = tmp_path / "sample.duckdb"
    output_dir = tmp_path / "processed"
    report = run_pipeline(database=database, output_dir=output_dir)

    assert report["source"]["rows_raw"] == 124
    assert report["source"]["null_times"] == 1
    assert report["clean"]["rows_clean"] == 123
    assert report["clean"]["null_delay_min"] == 2
    for table in OUTPUT_TABLES:
        assert (output_dir / f"{table}.parquet").exists()

    with duckdb.connect(database, read_only=True) as con:
        assert con.execute(
            "SELECT DISTINCT station_name, train_type, is_long_distance FROM stops_clean"
        ).fetchall() == [("Berlin Hbf", "ICE", True)]
        assert con.execute(
            "SELECT is_late_6_min, is_late_15_min, is_late_60_min "
            "FROM stops_clean WHERE stop_id = '2'"
        ).fetchone() == (False, False, False)
        stops, canceled, late_share, average_delay = con.execute(
            "SELECT stop_count, canceled_count, late_share_6_min, avg_delay_min "
            "FROM train_type_day_metrics"
        ).fetchone()
        assert (stops, canceled) == (123, 1)
        # The high outlier is still flagged late by the existing source-delay rule.
        assert late_share == pytest.approx(121 / 123)
        assert average_delay == 10

    from bahn_delay_story.quality import verify_database

    assert verify_database(database) == report
    assert run_pipeline(database=database, output_dir=output_dir) == report
