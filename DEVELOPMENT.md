# Development Notes

This file documents local development workflow for the BahnDelayStory project.

## Project

`BahnDelayStory` is a reproducible Deutsche Bahn delay data story built on the
`piebro/deutsche-bahn-data` Hugging Face Parquet dataset. Stack: Python 3.11+,
DuckDB, Polars, pandas, Plotly, and Streamlit. Primary IDE target is JetBrains
DataSpell.

The driving question and hypotheses live in `README.md`. `docs/methodology.md`
covers metric definitions and the coverage caveat that the source dataset
expands from about 100 stations to all stations on 2025-11-02. Any national
trend chart must address this.

## Public-Repo Discipline

Before any commit or push:

- Raw and processed Parquet files, the DuckDB database, virtual environments,
  IDE files, caches, and secrets must stay out of git.
- `.env.example` is intentionally tracked with placeholders only; `.env` is not.
- Verify ignored local artifacts with:

```bash
git status --short --ignored
git check-ignore -v data/raw/yearly_processed_data/data-2025-01.parquet
git check-ignore -v data/processed/stops_clean.parquet
git check-ignore -v data/bahn_delay_story.duckdb
git check-ignore -v .env
```

Prefer adding files by name after reviewing `git status`.

## Commands

The local machine may not have `uv`. Both forms work; use whichever the
environment supports.

```bash
# Run pipeline
uv run bahn-pipeline
.venv/bin/python -m bahn_delay_story.pipeline

# Run pipeline smoke test
uv run bahn-pipeline --sample-limit 1000000

# Re-validate an existing build
uv run bahn-quality
.venv/bin/python -m bahn_delay_story.quality

# Download source data from Hugging Face
uv run bahn-download
uv run bahn-download --allow-pattern "yearly_processed_data/data-2025-*.parquet"

# Dashboard
uv run streamlit run dashboard/app.py
.venv/bin/python -m streamlit run dashboard/app.py

# Tests
uv run pytest
.venv/bin/python -m pytest
.venv/bin/python -m pytest tests/test_project_layout.py::test_sql_steps_exist

# Lint
.venv/bin/python -m ruff check src dashboard tests
```

## Architecture

The pipeline is intentionally thin: SQL does the heavy lifting, Python
orchestrates.

1. `src/bahn_delay_story/ingest.py` downloads source Parquet from Hugging Face
   into `data/raw/yearly_processed_data/`; `monthly_processed_data/` is also
   supported.
2. `src/bahn_delay_story/pipeline.py` opens a DuckDB connection at
   `data/bahn_delay_story.duckdb`, registers source Parquet files as the
   `monthly_raw` view, executes the SQL steps, runs staged quality checks, and
   exports output tables to `data/processed/*.parquet`.
3. `src/bahn_delay_story/quality.py` contains staged data-quality checks for
   source rows, `stops_clean`, and feature tables. `bahn-quality` re-runs them
   read-only against an existing build.
4. `sql/01_register_sources.sql` is for interactive DuckDB sessions only; the
   Python pipeline registers its own view.
5. `sql/02_clean_stops.sql` produces `stops_clean`.
6. `sql/03_features_delay_metrics.sql` produces the analysis feature tables.
7. `dashboard/app.py` reads processed Parquet files only.

Key invariants:

- All paths derive from `bahn_delay_story.config`.
- The pipeline is idempotent.
- A canceled stop is excluded from `is_late_*` flags. Cancellation and delay are
  reported as separate metrics.

## Last Verified Pipeline Run

- Clean stop rows: 49,014,033
- Date range: 2025-01-01 to 2025-12-31
- Distinct stations: 5,328
- Distinct train types: 106
- Outlier delays set to NULL: 542
- Null station names: 1,218
- Tests: 4 passed
- Ruff: passed
