"""Tests for plot data preparation."""

from __future__ import annotations

import pandas as pd
import pytest

from bahn_delay_story.plots import WEEKDAY_LABELS, hourly_heatmap, weekday_hour_late_share


def test_weekday_hour_late_share_pools_counts() -> None:
    # Same Monday 08:00 cell: a tiny group that is always late and a large
    # group that is rarely late. An unweighted mean of rates would give 0.55.
    df = pd.DataFrame(
        {
            "weekday": ["1", "1"],
            "hour_of_day": [8, 8],
            "late_count_6_min": [1, 10],
            "late_eligible_count": [1, 100],
        }
    )

    grid = weekday_hour_late_share(df)

    assert grid.loc["Mon", 8] == pytest.approx(11 / 101)
    assert list(grid.index) == WEEKDAY_LABELS
    assert list(grid.columns) == list(range(24))
    assert grid.drop(index="Mon").isna().all().all()


def test_hourly_heatmap_uses_weekday_labels() -> None:
    df = pd.DataFrame(
        {
            "weekday": ["0", "6"],
            "hour_of_day": [0, 23],
            "late_count_6_min": [1, 2],
            "late_eligible_count": [4, 4],
        }
    )

    fig = hourly_heatmap(df)

    assert list(fig.data[0].y) == WEEKDAY_LABELS
