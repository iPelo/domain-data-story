from __future__ import annotations

import duckdb
import pandas as pd
import streamlit as st

from bahn_delay_story.config import PROCESSED_DIR
from bahn_delay_story.plots import hourly_heatmap, train_type_late_share

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

st.title("BahnDelayStory")

if train_type_day.empty:
    st.info("Run `uv run bahn-pipeline` to create processed data for the dashboard.")
    st.stop()

show_all_data = st.sidebar.toggle(
    "Show all data",
    value=False,
    help=(
        "Off: stable panel of stations present in every month January-October 2025, "
        "for like-for-like comparisons. On: every processed stop, including the "
        "November 2025 coverage expansion to all stations."
    ),
)

if show_all_data:
    line_metrics = load_parquet("line_metrics")
    st.caption(
        "All processed data. Station coverage expands in November 2025, so trends "
        "across that break are not like-for-like."
    )
else:
    train_type_day = train_type_day[train_type_day["in_stable_panel"]]
    if not hourly.empty:
        hourly = hourly[hourly["in_stable_panel"]]
    line_metrics = load_parquet("stable_line_metrics")
    st.caption("Stable panel: stations present in every month January-October 2025.")
    if train_type_day.empty:
        st.info("The processed data has no stable-panel rows. Turn on **Show all data**.")
        st.stop()

train_types = sorted(train_type_day["train_type"].dropna().unique().tolist())
selected_train_types = st.sidebar.multiselect(
    "Train types",
    train_types,
    default=[value for value in ["ICE", "IC", "EC", "RE", "RB", "S"] if value in train_types],
)

if selected_train_types:
    train_type_day = train_type_day[train_type_day["train_type"].isin(selected_train_types)]
    if not hourly.empty:
        hourly = hourly[hourly["train_type"].isin(selected_train_types)]
    if not line_metrics.empty:
        line_metrics = line_metrics[line_metrics["train_type"].isin(selected_train_types)]


def ratio(numerator: pd.Series, denominator: pd.Series) -> float:
    total = denominator.sum()
    return float(numerator.sum() / total) if total else float("nan")


total_stops = train_type_day["stop_count"].sum()
late_share = ratio(train_type_day["late_count_6_min"], train_type_day["late_eligible_count"])
cancellation_share = ratio(train_type_day["canceled_count"], train_type_day["stop_count"])
avg_delay = ratio(
    train_type_day["avg_delay_min"].fillna(0) * train_type_day["delay_count"],
    train_type_day["delay_count"],
)

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
    for column in ["late_share_6_min", "cancellation_share"]:
        display_lines[column] = display_lines[column].map("{:.1%}".format)

    st.dataframe(
        display_lines,
        column_config={
            "avg_delay_min": st.column_config.NumberColumn(format="%.1f"),
            "p90_delay_min": st.column_config.NumberColumn(format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
    )
