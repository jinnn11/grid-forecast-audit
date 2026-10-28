# Contributing

## Environment
- Python 3.11, managed with [uv](https://docs.astral.sh/uv/). `uv sync` installs everything.
- Tests use pytest; lint and formatting use ruff. The exact commands are in AGENTS.md.

## Data
- Source: EIA-930, EIA's Hourly Electric Grid Monitor. We use the six-month BALANCE files
  from https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/.
- Every download is cached under `data/raw/` with its original file name. Code checks the
  cache first and never fetches a file that is already there. To refresh a file on purpose,
  delete it by hand and say so in PLAN.md "Progress".
- EIA revises files in place, so each file's URL, size, download time and SHA-256 are recorded
  in `results/schema_check.md`, which `python -m grid_audit.build_history` writes. The hash
  identifies the snapshot the results came from.
- `data/raw/` and `data/processed/` are gitignored. Run one download at a time.

## Tests
- Tests never touch the network. `tests/conftest.py` blocks sockets; use small saved files in
  `tests/data/` instead.
- Expected values are worked out by hand, with the working in a comment next to the assertion.

## Layout
- `src/grid_audit/download.py`: cached downloads.
- `src/grid_audit/balance.py`: reads a BALANCE file into a tidy pandas DataFrame.
- `src/grid_audit/check.py`: per-BA data-quality stats, go/no-go verdict, Markdown report.
- `src/grid_audit/data_check.py`: `uv run python -m grid_audit.data_check` writes
  `results/data_check.md`.
- `src/grid_audit/download_history.py`: fetches every six-month BALANCE file, one at a time.
- `src/grid_audit/history.py` and `build_history.py`: combine the files into
  `data/processed/balance.parquet` and write `results/schema_check.md`.
- `src/grid_audit/events.py`: evidence from the data for BA starts, stops and footprint changes.
- `data/ba_events.csv` (tracked): the timeline of BA events. Each row cites its source; rows
  with basis "data only" are inferred from the data alone.
- `src/grid_audit/quality.py` and `quality_rules.py`: data-quality rules and
  `results/quality_rules_proposal.md`.
- `tests/`: tests and saved sample files.
