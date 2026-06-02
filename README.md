# BahnDelayStory

BahnDelayStory is a local analysis project for Deutsche Bahn stop-level delay data. It turns monthly Parquet files into cleaned DuckDB-backed feature tables, notebooks, and a Streamlit dashboard for exploring where delays concentrate by train type, station, hour, and route.

**Status:** In development
**Primary data source:** [`piebro/deutsche-bahn-data`](https://huggingface.co/datasets/piebro/deutsche-bahn-data) monthly processed Parquet files
**Optional extension:** [DB Timetables API](https://developers.deutschebahn.com/db-api-marketplace/apis/product/timetables) for live spot checks
**Tech:** Python, DuckDB, Polars, Streamlit, Quarto

## Analysis Question

For the stable 2025 station panel, where did stop-level lateness get worse, and which train types, hubs, routes, and hours explain the change?

The current local dataset contains 2025 files. The source dataset expands from a large-station panel to all stations in November 2025, so trend claims should use the stable station set unless the coverage break is explicitly shown.

## What This Repo Builds

- A reproducible pipeline from raw monthly Parquet files to analysis-ready tables.
- Data quality checks for row counts, keys, nulls, delay bounds, and metric ranges.
- Notebooks for exploratory analysis, trend decomposition, and chart production.
- A Streamlit dashboard for station, train-type, route, and hour-level comparisons.

## Working Hypotheses

1. Long-distance trains have higher late-share rates and heavier tail delays than local services.
2. Added late stops concentrate at major hubs and afternoon/evening travel windows.
3. Cancellation and delay patterns differ enough that they should be reported separately.

## Project Structure

```text
domain-data-story/
├── README.md
├── pyproject.toml
├── data/
│   ├── raw/
│   │   ├── yearly_processed_data/
│   │   └── monthly_processed_data/
│   ├── interim/
│   └── processed/
├── sql/
│   ├── 01_register_sources.sql
│   ├── 02_clean_stops.sql
│   └── 03_features_delay_metrics.sql
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_analysis.ipynb
│   └── 03_post_figures.ipynb
├── src/
│   └── bahn_delay_story/
│       ├── config.py
│       ├── ingest.py
│       ├── pipeline.py
│       ├── plots.py
│       └── quality.py
├── dashboard/
│   └── app.py
├── docs/
│   ├── data_dictionary.md
│   ├── dataspell_setup.md
│   └── methodology.md
├── reports/
│   └── figures/
└── tests/
    └── test_project_layout.py
```

## Data

Use the monthly processed Parquet files. They include station name, EVA station number, train name, destination, delay minutes, cancellation flag, train type, planned times, changed times, and a stop id.

Download the 2025 files:

```bash
uv run --with huggingface-hub hf download piebro/deutsche-bahn-data \
  --repo-type=dataset \
  --local-dir=data/raw \
  --include "yearly_processed_data/data-2025-*.parquet"
```

Download all monthly processed data when you are ready:

```bash
uv run --with huggingface-hub hf download piebro/deutsche-bahn-data \
  --repo-type=dataset \
  --local-dir=data/raw \
  --include "yearly_processed_data/*"
```

Expected local path:

```text
data/raw/yearly_processed_data/data-YYYY-MM.parquet
```

The code also supports `data/raw/monthly_processed_data/data-YYYY-MM.parquet` if you later use that folder name.

## Setup

1. Open this folder in DataSpell or another Python IDE.
2. Create a virtual environment with Python 3.11 or newer.
3. In the terminal, run `uv sync --extra dev`.
4. Select `.venv/bin/python` as the project interpreter.
5. Mark `src/` as a Sources Root if the IDE does not detect the package imports.
6. Open `notebooks/01_eda.ipynb` and select the same interpreter as the notebook kernel.

If `uv` is not installed yet, either install it first or use:

```bash
python -m pip install -e ".[dev]"
```

More detailed steps are in [`docs/dataspell_setup.md`](docs/dataspell_setup.md).

## Run The Pipeline

After downloading data:

```bash
uv run bahn-pipeline
```

The pipeline creates:

- `data/processed/stops_clean.parquet`
- `data/processed/station_day_metrics.parquet`
- `data/processed/train_type_day_metrics.parquet`
- `data/processed/hourly_delay_metrics.parquet`
- `data/processed/line_metrics.parquet`

## Run The Dashboard

```bash
uv run streamlit run dashboard/app.py
```

The dashboard reads `data/processed/*.parquet`. If those files do not exist yet, run the pipeline first.

## Analysis Artifacts

- `notebooks/01_eda.ipynb`: profile coverage, distributions, missingness, and first plots
- `notebooks/02_analysis.ipynb`: trend and station-hour analysis
- `notebooks/03_post_figures.ipynb`: polished charts for the final writeup
- `docs/methodology.md`: assumptions, limitations, metric definitions
- `dashboard/app.py`: interactive view for train type, station, and hour patterns

## License

Code in this project is MIT unless changed later. Data licensing follows the source dataset and Deutsche Bahn API terms; document attribution in the final writeup.
