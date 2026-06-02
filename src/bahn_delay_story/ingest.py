"""Download helpers for the Hugging Face monthly processed data."""

from __future__ import annotations

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

from bahn_delay_story.config import RAW_DIR

DATASET_ID = "piebro/deutsche-bahn-data"
DEFAULT_ALLOW_PATTERN = "yearly_processed_data/data-*.parquet"


def download_monthly_processed(
    local_dir: Path = RAW_DIR,
    allow_pattern: str = DEFAULT_ALLOW_PATTERN,
) -> Path:
    """Download monthly processed Parquet files into data/raw."""
    local_dir.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=DATASET_ID,
        repo_type="dataset",
        local_dir=local_dir,
        allow_patterns=[allow_pattern],
    )
    return local_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BahnDelayStory source data.")
    parser.add_argument(
        "--allow-pattern",
        default=DEFAULT_ALLOW_PATTERN,
        help='Hugging Face allow pattern, e.g. "yearly_processed_data/data-2025-*.parquet".',
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=RAW_DIR,
        help="Local destination directory. Defaults to data/raw.",
    )
    args = parser.parse_args()
    download_monthly_processed(local_dir=args.local_dir, allow_pattern=args.allow_pattern)


if __name__ == "__main__":
    main()
