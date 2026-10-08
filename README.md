# BahnDelayStory

A Python project exploring Deutsche Bahn stop-level delays in 2025.
It turns monthly train data into charts and a small dashboard for comparing
train types, travel times, and services.

## Features

- Clean delay records and check missing values, duplicate IDs, and delay bounds.
- Explore station coverage and compare delay trends in Jupyter notebooks.
- Filter dashboard charts by train type and view weekday/hour delay patterns.
- Rank services by late share and export interactive charts as HTML.

## Technologies

Python 3.11+, DuckDB, pandas, Plotly, Streamlit, Jupyter, and Hugging Face Hub.

## Getting Started

Clone the repository, open its folder, and install [uv](https://docs.astral.sh/uv/).
Then run:

```bash
uv sync
uv run bahn-download --allow-pattern "yearly_processed_data/data-2025-*.parquet"
uv run bahn-pipeline
uv run streamlit run app.py
```

The [source dataset](https://huggingface.co/datasets/piebro/deutsche-bahn-data)
can be large. For a quick pipeline run, add `--sample-limit 1000000`; this reads
the first rows and is not a representative sample for analysis.

Run `uv run jupyter lab` to open the notebooks in order: `01_eda`,
`02_analysis`, then `03_post_figures`. The last notebook saves charts to
`reports/figures/`. Raw data, processed tables, and charts stay local.

Station coverage expands in November 2025, so the analysis notebook uses the
stable January–October panel for trend comparisons. The dashboard shows all
processed data. See [data notes](DATA.md) for metrics, limitations, and attribution.

For development checks: `uv sync --extra dev`, then `uv run pytest` and
`uv run ruff check .`.

Code in this project is MIT unless changed later. Data licensing follows the
source dataset; its attribution notice is in [DATA.md](DATA.md).
