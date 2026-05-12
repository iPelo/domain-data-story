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


def hourly_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of late share by weekday and hour."""
    fig = px.density_heatmap(
        df,
        x="hour_of_day",
        y="weekday",
        z="late_share_6_min",
        histfunc="avg",
        color_continuous_scale="YlOrRd",
        labels={
            "hour_of_day": "Hour",
            "weekday": "Weekday",
            "late_share_6_min": "Share 6+ min late",
        },
    )
    fig.update_layout(coloraxis_colorbar_tickformat=".0%")
    return fig
