# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`BahnDelayStory` — a reproducible Deutsche Bahn delay data story built on the `piebro/deutsche-bahn-data` Hugging Face Parquet dataset. Stack: Python 3.11+, DuckDB, Polars, pandas, Plotly, Streamlit. Primary IDE target is JetBrains DataSpell.

The driving question and hypotheses live in `README.md` — read it first to understand analytical scope. `docs/methodology.md` covers metric definitions and the coverage caveat that the source dataset expands from ~100 stations to all stations on 2025-11-02 (any national trend chart must address this).

## Public-repo discipline

This repository is intended to be public on GitHub. Before any commit or push:

- Raw and processed Parquet files, the DuckDB database, virtual environments, IDE files, and secrets must stay out of git. The `.gitignore` enforces this; do not weaken its patterns.
- `.env.example` is intentionally tracked (placeholders only); `.env` is not.
- Verify with:
  ```bash
  git status --short --ignored
  git check-ignore -v data/raw/yearly_processed_data/data-2025-01.parquet
  git check-ignore -v data/processed/stops_clean.parquet
  git check-ignore -v data/bahn_delay_story.duckdb
  git check-ignore -v .env
  ```
- Never use `git add -A` / `git add .` without first reviewing `git status`. Prefer adding files by name.

## Commands

The local machine may not have `uv`. Both forms work; use whichever the environment supports.

```bash
# Run pipeline (full)
uv run bahn-pipeline
.venv/bin/python -m bahn_delay_story.pipeline

# Run pipeline (fast smoke test)
uv run bahn-pipeline --sample-limit 1000000

# Re-validate an existing build (quality assertions only, no rebuild)
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
.venv/bin/python -m pytest tests/test_project_layout.py::test_sql_steps_exist  # single test

# Lint
.venv/bin/python -m ruff check src dashboard tests
```

## Architecture

The pipeline is intentionally thin: SQL does the heavy lifting, Python orchestrates.

1. `src/bahn_delay_story/ingest.py` — downloads source Parquet from Hugging Face into `data/raw/yearly_processed_data/` (also supports `monthly_processed_data/`).
2. `src/bahn_delay_story/pipeline.py` — opens a DuckDB connection at `data/bahn_delay_story.duckdb`, registers all source Parquet files as a single `monthly_raw` view via `read_parquet(..., union_by_name = true)`, then executes the SQL steps in order and exports each output table to `data/processed/*.parquet`. It runs `quality.py` assertions after each stage (source, clean, features); a failed assertion aborts before any output is written, and `run_pipeline` returns the quality report.
2a. `src/bahn_delay_story/quality.py` — staged data-quality checks (row counts, null rates, `stop_id` uniqueness, delay bounds, share ranges). Used by the pipeline and by `tests/test_pipeline.py`; `bahn-quality` re-runs them read-only against an existing build.
3. `sql/01_register_sources.sql` — convenience view for interactive DuckDB sessions only; the pipeline registers its own view in Python so it can apply `--sample-limit`.
4. `sql/02_clean_stops.sql` — produces `stops_clean` with derived columns: `delay_min` (with outliers ≤ -60 or > 720 set to NULL), `is_long_distance` (ICE/IC/EC/ECE/EN/NJ/RJ/RJX/TGV/THA), `is_late_{6,15,60}_min` (false when canceled), and time features.
5. `sql/03_features_delay_metrics.sql` — aggregates four feature tables: `station_day_metrics`, `train_type_day_metrics`, `hourly_delay_metrics`, `line_metrics` (the last filters `HAVING COUNT(*) >= 100`).
6. `dashboard/app.py` — Streamlit dashboard reads only the processed Parquet files via `bahn_delay_story.config.PROCESSED_DIR`; it does not touch the DuckDB database or raw files.

Key invariants:
- All paths derive from `bahn_delay_story.config` — never hardcode `data/...` paths in new code.
- The pipeline is idempotent (`CREATE OR REPLACE`). Re-running on the same inputs must produce identical outputs.
- A canceled stop is excluded from `is_late_*` flags. Cancellation and delay are reported as separate metrics, not combined.

## Files to review first

- `README.md` — project setup and analytical question
- `src/bahn_delay_story/pipeline.py` — DuckDB orchestration
- `sql/02_clean_stops.sql` and `sql/03_features_delay_metrics.sql` — transformations
- `docs/methodology.md` — metric definitions, coverage strategy, limitations
- `docs/data_dictionary.md` — source columns and clean/feature table schemas
- `notebooks/01_eda.ipynb` — next analysis step in DataSpell
- `dashboard/app.py` — Streamlit dashboard

## Last verified pipeline run (2025 data)

- Clean stop rows: 49,014,033
- Date range: 2025-01-01 to 2025-12-31
- Distinct stations: 5,328
- Distinct train types: 106
- Outlier delays set to NULL: 542
- Null station names: 1,218
- Tests: 4 passed
- Ruff: passed

These figures are a sanity baseline — material drift after re-running the pipeline on the same inputs likely indicates a bug.
