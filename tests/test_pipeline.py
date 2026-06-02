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
