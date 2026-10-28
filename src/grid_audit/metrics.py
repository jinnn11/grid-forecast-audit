"""Step 3 forecast-error metrics (docs/step3_audit_plan.md). Pure functions.

Error e = forecast − demand, in MW. Every metric is a ratio of sums, so per-hour terms are added
up once per group (BA, year, season, hour, ...) and the metrics are taken from the sums.
"""

import pandas as pd

NAIVE_LAG_HOURS = 24
TERMS = ["hours", "ape", "abs_error", "error", "demand", "paired", "paired_ape", "naive_ape"]


def lagged(hourly: pd.DataFrame, column: str, hours: int, source: pd.Series) -> pd.Series:
    """Each row's `column` value from `hours` hours earlier (later if negative) for the same BA,
    matched by timestamp, taken only from rows where `source` is true; NaN otherwise or when that
    hour is absent."""
    keys = pd.MultiIndex.from_arrays([hourly["ba"], hourly["utc"]])
    values = pd.Series(hourly[column].where(source).to_numpy(), index=keys)
    wanted = pd.MultiIndex.from_arrays([hourly["ba"], hourly["utc"] - pd.Timedelta(hours=hours)])
    return pd.Series(values.reindex(wanted).to_numpy(), index=hourly.index)


def naive_forecast(hourly: pd.DataFrame, source: pd.Series) -> pd.Series:
    """The naive forecast: demand 24 hours earlier, from an hour where `source` is true (the
    hours whose demand passes R1, R2, R4 and R5)."""
    return lagged(hourly, "demand", NAIVE_LAG_HOURS, source)


def hour_terms(demand: pd.Series, forecast: pd.Series, naive: pd.Series) -> pd.DataFrame:
    """Per-hour terms the metrics add up. Paired hours are those with a naive value; on them the
    forecast's and the naive forecast's absolute percentage errors are kept for skill."""
    error = forecast - demand
    ape = error.abs() / demand
    paired = naive.notna()
    return pd.DataFrame(
        {
            "hours": 1,
            "ape": ape,
            "abs_error": error.abs(),
            "error": error,
            "demand": demand,
            "paired": paired.astype(int),
            "paired_ape": ape.where(paired, 0.0),
            "naive_ape": ((naive - demand).abs() / demand).where(paired, 0.0),
        }
    )


def from_sums(sums: pd.DataFrame) -> pd.DataFrame:
    """Metrics from summed hour_terms, one row per group, next to the sums:
    - mape: mean |e| / demand, %; wape: Σ|e| / Σ demand, %;
    - bias_pct: Σe / Σ demand, % (positive: over-forecast); bias_mw: mean e, MW;
    - naive_mape: the naive forecast's MAPE on the paired hours, %;
    - skill: 1 − MAPE(forecast) / MAPE(naive), both on the paired hours.
    """
    return sums.assign(
        mape=100 * sums["ape"] / sums["hours"],
        wape=100 * sums["abs_error"] / sums["demand"],
        bias_pct=100 * sums["error"] / sums["demand"],
        bias_mw=sums["error"] / sums["hours"],
        naive_mape=100 * sums["naive_ape"] / sums["paired"],
        skill=1 - sums["paired_ape"] / sums["naive_ape"],
    )


def metrics(hours: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """from_sums per group of `by` columns, for scored hours with demand, forecast and naive."""
    terms = hour_terms(hours["demand"], hours["forecast"], hours["naive"])
    return from_sums(terms.groupby([hours[column] for column in by], observed=True).sum())


def pooled_wape(sums: pd.DataFrame) -> float:
    """Σ|e| / Σ demand over all the groups in `sums`, %: the national figure when the groups
    are the eligible BAs."""
    return float(100 * sums["abs_error"].sum() / sums["demand"].sum())
