from pathlib import Path

from bahn_delay_story.config import PROJECT_ROOT, SQL_DIR
from bahn_delay_story.pipeline import SQL_STEPS


def test_expected_directories_exist() -> None:
    expected = [
        "data/raw/yearly_processed_data",
        "data/interim",
        "data/processed",
        "dashboard",
        "docs",
        "notebooks",
        "reports/figures",
        "sql",
        "src/bahn_delay_story",
    ]

    for relative_path in expected:
        assert (PROJECT_ROOT / relative_path).exists()


def test_sql_steps_exist() -> None:
    assert (SQL_DIR / "01_register_sources.sql").exists()
    for step in SQL_STEPS:
        assert Path(step).exists()
