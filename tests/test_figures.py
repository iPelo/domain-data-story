"""Report figures build from processed tables without writing images."""

from __future__ import annotations

from pathlib import Path

import duckdb
import plotly.graph_objects as go
import pytest

from bahn_delay_story.figures import FIGURES, build_figures, connect
from bahn_delay_story.pipeline import duckdb_string_literal, run_pipeline


@pytest.fixture
def processed(tmp_path: Path, monkeypatch) -> Path:
    """Two stations and two train types across January-November 2025."""
    source = tmp_path / "data-2025.parquet"
    with duckdb.connect() as con:
        con.execute(
            f"""
            COPY (
              SELECT
                CAST(i AS VARCHAR) AS id,
                ['Hub A', 'Hub B'][1 + i % 2] AS station_name,
                'x' AS xml_station_name,
                CAST(i % 2 AS VARCHAR) AS eva,
                CAST(i % 3 AS VARCHAR) AS train_number,
                NULL::VARCHAR AS line_number,
                'End' AS final_destination_station,
                CAST((i * 37) % 20 AS INTEGER) - 2 AS delay_in_min,
                i % 41 = 0 AS arrival_is_canceled,
                false AS departure_is_canceled,
                false AS is_additional_stop,
                false AS is_replacement_train,
                NULL::VARCHAR AS replaced_train_type,
                NULL::VARCHAR AS replaced_train_number,
                true AS has_plan_record,
                ['ICE', 'RE'][1 + i % 2] AS train_type,
                'ride-' || (i % 50) AS train_line_ride_id,
                1 AS train_line_station_num,
                make_timestamp(2025, 1 + i % 11, 1 + i % 28, i % 24, 0, 0) AS time,
                NULL::TIMESTAMP AS arrival_planned_time,
                NULL::TIMESTAMP AS arrival_change_time,
                NULL::TIMESTAMP AS departure_planned_time,
                NULL::TIMESTAMP AS departure_change_time
              FROM range(30000) AS rows(i)
            ) TO {duckdb_string_literal(str(source))} (FORMAT PARQUET)
            """
        )
    monkeypatch.setattr("bahn_delay_story.pipeline.source_parquet_files", lambda: [source])
    output_dir = tmp_path / "processed"
    run_pipeline(database=tmp_path / "figures.duckdb", output_dir=output_dir)
    return output_dir


def test_build_figures(processed: Path) -> None:
    with connect(processed) as con:
        figures = build_figures(con)

    assert set(figures) == set(FIGURES)
    for name, fig in figures.items():
        assert isinstance(fig, go.Figure), name
        assert fig.data, f"{name} has no traces"
        assert fig.layout.title.text, f"{name} has no title"


def test_connect_reports_missing_tables(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="bahn-pipeline"):
        connect(tmp_path)
