from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from bahn_delay_story.config import PROCESSED_DIR  # noqa: E402
from bahn_delay_story.plots import hourly_heatmap, train_type_late_share  # noqa: E402

st.set_page_config(page_title="BahnDelayStory", layout="wide")


@st.cache_data(show_spinner=False)
def load_parquet(name: str) -> pd.DataFrame:
    path = PROCESSED_DIR / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    with duckdb.connect() as con:
        return con.execute("SELECT * FROM read_parquet($path)", {"path": str(path)}).df()


train_type_day = load_parquet("train_type_day_metrics")
hourly = load_parquet("hourly_delay_metrics")
line_metrics = load_parquet("line_metrics")

st.title("BahnDelayStory")

if train_type_day.empty:
    st.info("Run `uv run bahn-pipeline` to create processed data for the dashboard.")
    st.stop()

train_types = sorted(train_type_day["train_type"].dropna().unique().tolist())
selected_train_types = st.sidebar.multiselect(
    "Train types",
    train_types,
    default=[value for value in ["ICE", "IC", "EC", "RE", "RB", "S"] if value in train_types],
)

if selected_train_types:
    train_type_day = train_type_day[train_type_day["train_type"].isin(selected_train_types)]
    hourly = hourly[hourly["train_type"].isin(selected_train_types)]
    line_metrics = line_metrics[line_metrics["train_type"].isin(selected_train_types)]

total_stops = train_type_day["stop_count"].sum()
weights = train_type_day["stop_count"].clip(lower=1)


def weighted_mean(series: pd.Series, weight: pd.Series) -> float:
    valid = series.notna() & weight.notna()
    if not valid.any():
        return float("nan")
    return float((series[valid] * weight[valid]).sum() / weight[valid].sum())


late_share = weighted_mean(train_type_day["late_share_6_min"], weights)
cancellation_share = weighted_mean(train_type_day["cancellation_share"], weights)
avg_delay = weighted_mean(train_type_day["avg_delay_min"], weights)

metric_cols = st.columns(4)
metric_cols[0].metric("Stops", f"{total_stops:,.0f}")
metric_cols[1].metric("Late share 6+ min", f"{late_share:.1%}")
metric_cols[2].metric("Cancellation share", f"{cancellation_share:.1%}")
metric_cols[3].metric("Average delay", f"{avg_delay:.1f} min")

left, right = st.columns([1.25, 1])

with left:
    st.subheader("Late Share By Train Type")
    st.plotly_chart(train_type_late_share(train_type_day), use_container_width=True)

with right:
    st.subheader("Weekday/Hour Delay Pattern")
    if hourly.empty:
        st.warning("No hourly metrics available for the selected filters.")
    else:
        st.plotly_chart(hourly_heatmap(hourly), use_container_width=True)

st.subheader("Highest Late-Share Services")
if line_metrics.empty:
    st.warning("No line metrics available for the selected filters.")
else:
    top_lines = (
        line_metrics.sort_values(["late_share_6_min", "stop_count"], ascending=[False, False])
        .head(25)
        .loc[
            :,
            [
                "train_type",
                "train_name",
                "final_destination_station",
                "stop_count",
                "late_share_6_min",
                "avg_delay_min",
                "p90_delay_min",
                "cancellation_share",
            ],
        ]
    )
    display_lines = top_lines.copy()
    display_lines["late_share_6_min"] = display_lines["late_share_6_min"].map("{:.1%}".format)
    display_lines["cancellation_share"] = display_lines["cancellation_share"].map("{:.1%}".format)
    display_lines["avg_delay_min"] = display_lines["avg_delay_min"].map("{:.1f}".format)
    display_lines["p90_delay_min"] = display_lines["p90_delay_min"].map("{:.1f}".format)

    st.dataframe(
        display_lines,
        use_container_width=True,
        hide_index=True,
    )
