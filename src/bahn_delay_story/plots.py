"""Reusable plotting helpers for notebooks and the Streamlit app."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def train_type_late_share(df: pd.DataFrame) -> go.Figure:
    """Line chart of late share by train type over time."""
    fig = px.line(
        df,
        x="service_date",
        y="late_share_6_min",
        color="train_type",
        markers=True,
        labels={
            "service_date": "Date",
            "late_share_6_min": "Share 6+ min late",
            "train_type": "Train type",
        },
    )
    fig.update_layout(yaxis_tickformat=".0%", legend_title_text="Train type")
    return fig


WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def weekday_hour_late_share(df: pd.DataFrame) -> pd.DataFrame:
    """Pool late stops and stops into a weekday x hour grid of late share.

    Rows are summed before dividing, so each cell is total late stops over total
    stops rather than an unweighted mean of group-level rates. Weekday codes
    '0'..'6' (Sunday first) become Sun..Sat row labels.
    """
    cells = df.groupby(["weekday", "hour_of_day"], as_index=False)[
        ["late_count_6_min", "stop_count"]
    ].sum()
    cells["late_share_6_min"] = cells["late_count_6_min"] / cells["stop_count"]
    grid = cells.pivot(index="weekday", columns="hour_of_day", values="late_share_6_min")
    grid = grid.reindex(index=[str(day) for day in range(7)], columns=range(24))
    grid.index = WEEKDAY_LABELS
    return grid


def hourly_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of pooled late share by weekday and hour."""
    fig = px.imshow(
        weekday_hour_late_share(df),
        aspect="auto",
        color_continuous_scale="YlOrRd",
        labels={"x": "Hour", "y": "Weekday", "color": "Share 6+ min late"},
    )
    fig.update_layout(coloraxis_colorbar_tickformat=".0%")
    return fig
