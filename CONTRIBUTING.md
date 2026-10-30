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
- Operator data (approved 2026-10-28 for the Q5 check only: CAISO OASIS 2025 to Jan–Jun 2026,
  SPP 2025) is cached under `data/raw/operators/`. SPP files keep their own names. OASIS names
  its files by request time, so CAISO files are named by run, month and the UTC window
  requested. `results/operator_files.csv` records each file's URL, size, download time and
  SHA-256.

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
- `src/grid_audit/truth.py` and `truth_check.py`: checks on demand that avoid the forecast (EIA's
  changes, the energy balance, the R5 exception rule) and `results/demand_truth.md`.
- `src/grid_audit/data_quality.py`: applies the approved rules; writes `results/data_quality.md`
  and `data/balance_exemptions.csv` (tracked, generated: the R5 exemptions with their evidence).
- `docs/step3_audit_plan.md`: the pre-registered plan for the audit (Step 3).
- `src/grid_audit/calendar.py`, `metrics.py`, `stats.py` (pure) and `audit.py`, `figures.py`:
  `uv run python -m grid_audit.audit` writes `results/audit.md` and `results/figures/`.
  `data/weather_events.csv` (tracked) is the plan's event table with sources.
- `src/grid_audit/operators.py` (pure), `download_operators.py` and `operator_check.py`: the
  operators' own load and forecasts, and `results/operator_check.md`.
- `tests/`: tests and saved sample files.
