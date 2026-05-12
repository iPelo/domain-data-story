# BahnDelayStory

> A reproducible data story about Deutsche Bahn delays, cancellations, and the station-hour patterns that explain them.

**Status:** In development  
**Primary data source:** [`piebro/deutsche-bahn-data`](https://huggingface.co/datasets/piebro/deutsche-bahn-data) monthly processed Parquet files  
**Optional extension:** [DB Timetables API](https://developers.deutschebahn.com/db-api-marketplace/apis/product/timetables) for live spot checks  
**IDE:** JetBrains DataSpell  
**Tech:** Python, DuckDB, Polars, Streamlit, Quarto

## Question

Since July 2024, have Deutsche Bahn delays become more likely or more severe, and which train types, stations, routes, and hours explain the change?

This first version should focus on a stable analytical slice:

- compare train types, especially ICE/IC/EC versus regional and S-Bahn services
- track late share, average delay, median delay, severe delays, and cancellations
- isolate station-hour and train-type patterns instead of only reporting national averages
- account for the coverage break: the source dataset covers the biggest roughly 100 stations from 2024-07 to 2025-11-02, then all stations after that

## Hypotheses

1. Long-distance trains have a higher late share and more severe tail delays than local services.
2. Delay increases are concentrated in specific hub stations and evening/weekend time windows.
3. Cancellation rates and delay minutes tell different stories, so both must be reported.

## Project Structure

```text
domain-data-story/
├── README.md
├── README-03-data-analysis.md
├── pyproject.toml
├── data/
│   ├── raw/
│   │   ├── yearly_processed_data/      # your current data-YYYY-MM.parquet files
│   │   └── monthly_processed_data/     # alternate source naming, also supported
│   ├── interim/
│   └── processed/                      # pipeline outputs
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

Use the monthly processed Parquet files first. They are already normalized enough for analysis and include station name, EVA station number, train name, destination, delay minutes, cancellation flag, train type, planned times, changed times, and a stop id.

Download a first manageable slice:

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

## Setup In DataSpell

1. Open this folder as a DataSpell project.
2. Create a virtual environment with Python 3.11 or newer.
3. In the terminal, run `uv sync --extra dev`.
4. Select `.venv/bin/python` as the project interpreter.
5. Mark `src/` as a Sources Root if DataSpell does not detect the package imports.
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

## Analysis Deliverables

- `notebooks/01_eda.ipynb`: profile coverage, distributions, missingness, and first plots
- `notebooks/02_analysis.ipynb`: trend and station-hour analysis
- `notebooks/03_post_figures.ipynb`: polished charts for the final writeup
- `docs/methodology.md`: assumptions, limitations, metric definitions
- `dashboard/app.py`: interactive view for train type, station, and hour patterns

## License

Code in this project is MIT unless changed later. Data licensing follows the source dataset and Deutsche Bahn API terms; document attribution in the final writeup.
