"""Export the report's key figures as PNG files.

Each figure backs one or more findings in REPORT.md. Trend and decomposition
figures use the stable January-October 2025 panel (``in_stable_panel``);
service rankings use all processed data, as in ``02_analysis.ipynb``.

PNG export uses Kaleido, which needs a local Chrome or Chromium. If none is
found, run ``uv run plotly_get_chrome`` once.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from bahn_delay_story.config import FIGURES_DIR, PROCESSED_DIR
from bahn_delay_story.pipeline import duckdb_string_literal
from bahn_delay_story.plots import hourly_heatmap

VIEWS = {
    "station_day": "station_day_metrics",
    "hourly": "hourly_delay_metrics",
    "lines": "line_metrics",
}

# Months compared in the January-to-October decompositions.
BASE_MONTH = 1
END_MONTH = 10

WIDTH = 1000
HEIGHT = 560


def connect(processed_dir: Path = PROCESSED_DIR) -> duckdb.DuckDBPyConnection:
    """Open an in-memory connection with views over the processed Parquet tables."""
    missing = [
        table for table in VIEWS.values() if not (processed_dir / f"{table}.parquet").exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing processed tables in {processed_dir}: {missing}. Run `uv run bahn-pipeline`."
        )
    con = duckdb.connect()
    for view, table in VIEWS.items():
        path = duckdb_string_literal(str(processed_dir / f"{table}.parquet"))
        con.execute(f"CREATE VIEW {view} AS SELECT * FROM read_parquet({path})")
    return con


def _style(fig: go.Figure, title: str, height: int = HEIGHT) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        width=WIDTH,
        height=height,
        margin={"l": 60, "r": 30, "t": 70, "b": 50},
        legend_title_text="",
    )
    return fig


def _month_change(con: duckdb.DuckDBPyConnection, view: str, key: str) -> pd.DataFrame:
    """January vs October late stops per key on the stable panel."""
    return con.execute(
        f"""
        WITH monthly AS (
          SELECT
            {key},
            EXTRACT(MONTH FROM service_date) AS service_month,
            SUM(stop_count) AS stops,
            SUM(late_eligible_count) AS eligible,
            SUM(late_count_6_min) AS late
          FROM {view}
          WHERE in_stable_panel
            AND EXTRACT(MONTH FROM service_date) IN ({BASE_MONTH}, {END_MONTH})
            AND {key} IS NOT NULL
          GROUP BY ALL
        )
        SELECT
          {key},
          SUM(stops) FILTER (WHERE service_month = {BASE_MONTH}) AS jan_stops,
          SUM(stops) FILTER (WHERE service_month = {END_MONTH}) AS oct_stops,
          SUM(late) FILTER (WHERE service_month = {BASE_MONTH})
            / NULLIF(SUM(eligible) FILTER (WHERE service_month = {BASE_MONTH}), 0)
            AS jan_late_share,
          SUM(late) FILTER (WHERE service_month = {END_MONTH})
            / NULLIF(SUM(eligible) FILTER (WHERE service_month = {END_MONTH}), 0)
            AS oct_late_share,
          COALESCE(SUM(late) FILTER (WHERE service_month = {END_MONTH}), 0)
            - COALESCE(SUM(late) FILTER (WHERE service_month = {BASE_MONTH}), 0)
            AS late_stop_change
        FROM monthly
        GROUP BY ALL
        ORDER BY late_stop_change DESC
        """
    ).df()


def stable_trend(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Findings 1-2: monthly late share by service segment on the stable panel."""
    df = con.execute(
        """
        SELECT
          EXTRACT(MONTH FROM service_date) AS service_month,
          CASE WHEN is_long_distance THEN 'Long-distance' ELSE 'Other services' END AS segment,
          SUM(late_count_6_min) / NULLIF(SUM(late_eligible_count), 0) AS late_share_6_min
        FROM station_day
        WHERE in_stable_panel
        GROUP BY ALL
        ORDER BY ALL
        """
    ).df()
    fig = px.line(
        df,
        x="service_month",
        y="late_share_6_min",
        color="segment",
        markers=True,
        labels={"service_month": "Month (2025)", "late_share_6_min": "Share 6+ min late"},
    )
    fig.update_layout(yaxis_tickformat=".0%")
    fig.update_xaxes(dtick=1)
    return _style(fig, "Late share by month, stable station panel")


def jan_oct_change(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 2: January-to-October change in late and cancellation share."""
    jan = f"EXTRACT(MONTH FROM service_date) = {BASE_MONTH}"
    oct_ = f"EXTRACT(MONTH FROM service_date) = {END_MONTH}"
    change = con.execute(
        f"""
        SELECT
          CASE WHEN is_long_distance THEN 'Long-distance' ELSE 'Other services' END AS segment,
          SUM(late_count_6_min) FILTER (WHERE {oct_})
            / NULLIF(SUM(late_eligible_count) FILTER (WHERE {oct_}), 0)
          - SUM(late_count_6_min) FILTER (WHERE {jan})
            / NULLIF(SUM(late_eligible_count) FILTER (WHERE {jan}), 0)
            AS "Late share 6+ min",
          SUM(canceled_count) FILTER (WHERE {oct_})
            / NULLIF(SUM(stop_count) FILTER (WHERE {oct_}), 0)
          - SUM(canceled_count) FILTER (WHERE {jan})
            / NULLIF(SUM(stop_count) FILTER (WHERE {jan}), 0)
            AS "Cancellation share"
        FROM station_day
        WHERE in_stable_panel
        GROUP BY ALL
        ORDER BY ALL
        """
    ).df()
    long = change.melt(id_vars="segment", var_name="metric", value_name="change")
    fig = px.bar(
        long,
        x="metric",
        y="change",
        color="segment",
        barmode="group",
        labels={"metric": "", "change": "Change, January to October (percentage points)"},
    )
    fig.update_layout(yaxis_tickformat=".1%")
    return _style(fig, "January-to-October change, stable station panel")


def train_type_contribution(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Findings 3-4: which train types add the most late stops, January to October."""
    df = _month_change(con, "station_day", "train_type")
    df = df[(df["jan_stops"].fillna(0) >= 10_000) | (df["oct_stops"].fillna(0) >= 10_000)]
    df = df.head(15).sort_values("late_stop_change")
    fig = px.bar(
        df,
        x="late_stop_change",
        y="train_type",
        orientation="h",
        color="oct_late_share",
        color_continuous_scale="YlOrRd",
        labels={
            "late_stop_change": "Added late stops, January to October",
            "train_type": "Train type",
            "oct_late_share": "October late share",
        },
    )
    fig.update_layout(coloraxis_colorbar_tickformat=".0%")
    return _style(fig, "Train types driving the rise in late stops", height=620)


def station_contribution(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 5: stations adding the most late stops, January to October."""
    df = _month_change(con, "station_day", "station_name").head(20)
    fig = px.bar(
        df.sort_values("late_stop_change"),
        x="late_stop_change",
        y="station_name",
        orientation="h",
        color="oct_late_share",
        color_continuous_scale="YlOrRd",
        labels={
            "late_stop_change": "Added late stops, January to October",
            "station_name": "Station",
            "oct_late_share": "October late share",
        },
    )
    fig.update_layout(coloraxis_colorbar_tickformat=".0%")
    return _style(fig, "Stations driving the rise in late stops", height=680)


def hour_contribution(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 6: added late stops by hour of day, January to October."""
    df = _month_change(con, "hourly", "hour_of_day").sort_values("hour_of_day")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["hour_of_day"], y=df["late_stop_change"], name="Added late stops"))
    fig.add_trace(
        go.Scatter(
            x=df["hour_of_day"],
            y=df["oct_late_share"],
            name="October late share",
            yaxis="y2",
            mode="lines+markers",
        )
    )
    fig.update_layout(
        xaxis={"title": "Hour of day", "dtick": 2},
        yaxis={"title": "Added late stops, January to October"},
        yaxis2={
            "title": "October late share",
            "overlaying": "y",
            "side": "right",
            "tickformat": ".0%",
        },
    )
    return _style(fig, "Hours driving the rise in late stops")


def service_floor_sensitivity(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 7: how the top service late share depends on the minimum-stop floor."""
    df = con.execute(
        """
        SELECT floor_value, MAX(late_share_6_min) AS max_late_share
        FROM lines, (VALUES (100), (500), (1000), (5000)) AS floors(floor_value)
        WHERE stop_count >= floor_value
        GROUP BY ALL
        ORDER BY ALL
        """
    ).df()
    fig = px.line(
        df,
        x="floor_value",
        y="max_late_share",
        markers=True,
        log_x=True,
        labels={"floor_value": "Minimum stops per service", "max_late_share": "Highest late share"},
    )
    fig.update_layout(yaxis_tickformat=".0%")
    return _style(fig, "Top service late share by minimum-stop floor")


def top_services(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 8: highest late-share services with at least 1,000 stops."""
    df = con.execute(
        """
        SELECT
          train_type,
          train_name || ' to ' || COALESCE(final_destination_station, 'unknown') AS service,
          late_share_6_min
        FROM lines
        WHERE stop_count >= 1000
        ORDER BY late_share_6_min DESC, stop_count DESC
        LIMIT 20
        """
    ).df()
    fig = px.bar(
        df.sort_values("late_share_6_min"),
        x="late_share_6_min",
        y="service",
        orientation="h",
        color="train_type",
        labels={"late_share_6_min": "Share 6+ min late", "service": "", "train_type": "Type"},
    )
    fig.update_layout(xaxis_tickformat=".0%")
    return _style(fig, "Highest late-share services (at least 1,000 stops)", height=680)


def weekday_hour(con: duckdb.DuckDBPyConnection) -> go.Figure:
    """Finding 6 context: pooled late share by weekday and hour on the stable panel."""
    df = con.execute("SELECT * FROM hourly WHERE in_stable_panel").df()
    return _style(hourly_heatmap(df), "Late share by weekday and hour, stable station panel")


FIGURES: dict[str, Callable[[duckdb.DuckDBPyConnection], go.Figure]] = {
    "stable_trend": stable_trend,
    "jan_oct_change": jan_oct_change,
    "train_type_contribution": train_type_contribution,
    "station_contribution": station_contribution,
    "hour_contribution": hour_contribution,
    "service_floor_sensitivity": service_floor_sensitivity,
    "top_services": top_services,
    "weekday_hour_heatmap": weekday_hour,
}


def build_figures(con: duckdb.DuckDBPyConnection) -> dict[str, go.Figure]:
    """Build every report figure from an open connection."""
    return {name: build(con) for name, build in FIGURES.items()}


def export_figures(
    processed_dir: Path = PROCESSED_DIR,
    figures_dir: Path = FIGURES_DIR,
    scale: float = 2.0,
) -> list[Path]:
    """Write each report figure to ``figures_dir/<name>.png`` and return the paths."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    with connect(processed_dir) as con:
        figures = build_figures(con)
    paths = []
    for name, fig in figures.items():
        path = figures_dir / f"{name}.png"
        fig.write_image(path, scale=scale)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Export BahnDelayStory report figures as PNG.")
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--figures-dir", type=Path, default=FIGURES_DIR)
    parser.add_argument("--scale", type=float, default=2.0, help="PNG pixel scale factor.")
    args = parser.parse_args()
    for path in export_figures(args.processed_dir, args.figures_dir, args.scale):
        print(path)


if __name__ == "__main__":
    main()
