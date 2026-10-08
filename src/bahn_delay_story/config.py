"""Project paths and shared constants."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_MONTHLY_DIR = RAW_DIR / "monthly_processed_data"
RAW_YEARLY_DIR = RAW_DIR / "yearly_processed_data"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
SQL_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = DATA_DIR / "bahn_delay_story.duckdb"

RAW_PROCESSED_DIRS = [RAW_YEARLY_DIR, RAW_MONTHLY_DIR]


def source_parquet_files() -> list[Path]:
    """Return local processed source Parquet files from supported raw data folders."""
    files: list[Path] = []
    for source_dir in RAW_PROCESSED_DIRS:
        files.extend(source_dir.glob("data-*.parquet"))
    return sorted(files)
