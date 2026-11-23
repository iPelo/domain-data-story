"""Pipeline data-quality and reproducibility tests.

The pipeline runs on a small sample into a temporary location, so the real
``data/processed`` outputs and the project database are never touched.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from bahn_delay_story.config import SQL_DIR, source_parquet_files
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
              '123' AS train_number,
              CASE WHEN i = 5 THEN 'L9' END AS line_number,
              'Hamburg Hbf' AS final_destination_station,
              CASE
                WHEN i = 0 THEN -61
                WHEN i = 1 THEN 721
                WHEN i = 2 THEN 100
                WHEN i = 3 THEN NULL
                ELSE 10
              END AS delay_in_min,
              i = 2 AS arrival_is_canceled,
              i = 4 AS departure_is_canceled,
              false AS is_additional_stop,
              false AS is_replacement_train,
              NULL::VARCHAR AS replaced_train_type,
              NULL::VARCHAR AS replaced_train_number,
              true AS has_plan_record,
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
    assert report["clean"]["null_delay_min"] == 3
    # Out-of-range delays (-61, 721) and the missing delay leave lateness unknown.
    assert report["clean"]["unknown_late_flags"] == 3
    for table in OUTPUT_TABLES:
        assert (output_dir / f"{table}.parquet").exists()

    with duckdb.connect(database, read_only=True) as con:
        assert con.execute(
            "SELECT DISTINCT station_name, train_type, is_long_distance FROM stops_clean"
        ).fetchall() == [("Berlin Hbf", "ICE", True)]
        # Line number wins over train number when present.
        assert con.execute(
            "SELECT train_name, COUNT(*) FROM stops_clean GROUP BY 1 ORDER BY 1"
        ).fetchall() == [("ICE 123", 122), ("ICE L9", 1)]
        # Arrival-only (2) and departure-only (4) cancellations both count.
        for stop_id in ("2", "4"):
            assert con.execute(
                "SELECT is_canceled, is_late_6_min, is_late_15_min, is_late_60_min "
                f"FROM stops_clean WHERE stop_id = '{stop_id}'"
            ).fetchone() == (True, False, False, False)
        # Unknown or out-of-range delay is unknown lateness, not on time.
        for stop_id in ("0", "1", "3"):
            assert con.execute(
                "SELECT is_late_6_min, is_late_15_min, is_late_60_min "
                f"FROM stops_clean WHERE stop_id = '{stop_id}'"
            ).fetchone() == (None, None, None)
        stops, canceled, eligible, late, late_share, delay_count, average_delay, p90 = (
            con.execute(
                "SELECT stop_count, canceled_count, late_eligible_count, late_count_6_min, "
                "late_share_6_min, delay_count, avg_delay_min, p90_delay_min "
                "FROM train_type_day_metrics"
            ).fetchone()
        )
        assert (stops, canceled, eligible) == (123, 2, 120)
        assert late == 118
        assert late_share == pytest.approx(118 / 120)
        # The cancelled stop's 100-minute delay is excluded from delay statistics.
        assert delay_count == 118
        assert average_delay == 10
        assert p90 == 10

    from bahn_delay_story.quality import verify_database

    assert verify_database(database) == report
    assert run_pipeline(database=database, output_dir=output_dir) == report


@pytest.mark.parametrize(
    ("train_type", "expected"),
    [("ICE", True), ("flx", True), ("EST", True), ("RE", False), ("SBB", False), (None, False)],
)
def test_long_distance_flag(tmp_path: Path, train_type: str | None, expected: bool) -> None:
    with duckdb.connect() as con:
        con.execute(
            """
            CREATE VIEW monthly_raw AS
            SELECT
              '1' AS id, 'A' AS station_name, 'A' AS xml_station_name, '1' AS eva,
              '1' AS train_number, NULL::VARCHAR AS line_number, 'B' AS final_destination_station,
              0 AS delay_in_min, false AS arrival_is_canceled, false AS departure_is_canceled,
              $train_type::VARCHAR AS train_type, false AS is_additional_stop,
              false AS is_replacement_train, NULL::VARCHAR AS replaced_train_type,
              NULL::VARCHAR AS replaced_train_number, true AS has_plan_record,
              'r' AS train_line_ride_id, 1 AS train_line_station_num,
              TIMESTAMP '2025-01-01 08:00' AS time,
              NULL::TIMESTAMP AS arrival_planned_time, NULL::TIMESTAMP AS arrival_change_time,
              NULL::TIMESTAMP AS departure_planned_time, NULL::TIMESTAMP AS departure_change_time
            """.replace("$train_type", "NULL" if train_type is None else f"'{train_type}'")
        )
        con.execute((SQL_DIR / "clean_stops.sql").read_text())
        assert con.execute("SELECT is_long_distance FROM stops_clean").fetchone() == (expected,)


def test_stable_panel_flag(tmp_path: Path, monkeypatch) -> None:
    """Only stations seen in every month Jan-Oct 2025, dated Jan-Oct, are in the panel."""
    source = tmp_path / "data-2025.parquet"
    with duckdb.connect() as con:
        con.execute(
            """
            CREATE TABLE sample AS
            -- Hub: 120 stops in each month January-November.
            SELECT 'hub-' || m || '-' || i AS id, 'Hub' AS station_name, m, 5 AS delay_in_min
            FROM range(1, 12) AS months(m), range(120) AS rows(i)
            UNION ALL
            -- Gap: present January-September only, so never in the panel.
            SELECT 'gap-' || m || '-' || i, 'Gap', m, 5
            FROM range(1, 10) AS months(m), range(20) AS rows(i)
            """
        )
        con.execute(
            f"""
            COPY (
              SELECT
                id,
                station_name,
                station_name AS xml_station_name,
                '1' AS eva,
                '1' AS train_number,
                NULL::VARCHAR AS line_number,
                'End' AS final_destination_station,
                delay_in_min,
                false AS arrival_is_canceled,
                false AS departure_is_canceled,
                false AS is_additional_stop,
                false AS is_replacement_train,
                NULL::VARCHAR AS replaced_train_type,
                NULL::VARCHAR AS replaced_train_number,
                true AS has_plan_record,
                'ICE' AS train_type,
                'ride-1' AS train_line_ride_id,
                1 AS train_line_station_num,
                make_timestamp(2025, m, 15, 8, 0, 0) AS time,
                NULL::TIMESTAMP AS arrival_planned_time,
                NULL::TIMESTAMP AS arrival_change_time,
                NULL::TIMESTAMP AS departure_planned_time,
                NULL::TIMESTAMP AS departure_change_time
              FROM sample
            ) TO {duckdb_string_literal(str(source))} (FORMAT PARQUET)
            """
        )

    monkeypatch.setattr("bahn_delay_story.pipeline.source_parquet_files", lambda: [source])
    database = tmp_path / "panel.duckdb"
    report = run_pipeline(database=database, output_dir=tmp_path / "processed")

    assert report["clean"]["stable_panel_rows"] == 10 * 120
    with duckdb.connect(database, read_only=True) as con:
        assert con.execute(
            "SELECT station_name, service_month FROM stops_clean "
            "WHERE in_stable_panel GROUP BY ALL ORDER BY ALL"
        ).fetchall() == [("Hub", month) for month in range(1, 11)]
        assert con.execute(
            "SELECT SUM(stop_count) FROM train_type_day_metrics WHERE in_stable_panel"
        ).fetchone() == (1200,)
        assert con.execute("SELECT stop_count FROM line_metrics").fetchall() == [(1500,)]
        assert con.execute("SELECT stop_count FROM stable_line_metrics").fetchall() == [(1200,)]
