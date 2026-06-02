# DataSpell Setup

These steps keep the notebook kernel, package imports, and command-line tools on the same Python environment.

## Interpreter

1. Open the project folder in DataSpell.
2. Open the built-in terminal.
3. Install dependencies:

```bash
uv sync --extra dev
```

If `uv` is not installed yet, use the selected virtual environment directly:

```bash
python -m pip install -e ".[dev]"
```

4. Go to `Settings > Project > Python Interpreter`.
5. Select the interpreter at `.venv/bin/python`.

## Notebook Kernel

1. Open `notebooks/01_eda.ipynb`.
2. Select the project interpreter as the kernel.
3. Run the setup/import cell.
4. If `bahn_delay_story` cannot be imported, mark `src/` as Sources Root:
   - right-click `src/`
   - choose `Mark Directory as > Sources Root`

## Data Download

Download the 2025 source files:

```bash
uv run --with huggingface-hub hf download piebro/deutsche-bahn-data \
  --repo-type=dataset \
  --local-dir=data/raw \
  --include "yearly_processed_data/data-2025-*.parquet"
```

Then run:

```bash
uv run bahn-pipeline --sample-limit 1000000
```

Remove `--sample-limit` for the full build.

## Useful Run Configurations

Create these DataSpell run configurations:

| Name | Command |
|---|---|
| Pipeline sample | `uv run bahn-pipeline --sample-limit 1000000` |
| Pipeline full | `uv run bahn-pipeline` |
| Dashboard | `uv run streamlit run dashboard/app.py` |
| Tests | `uv run pytest` |
