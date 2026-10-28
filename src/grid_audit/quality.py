"""Step 2 data-quality rules and their impact. Pure functions over the combined hourly table.

Every rule judges a series on its own; none looks at forecast error, which is what is audited.
An hour is usable when demand and forecast are both present and no approved rule drops it.
"""

import pandas as pd

from grid_audit.history import half_year

HOUR = pd.Timedelta(hours=1)
R3A_EVENTS = ("start", "stop", "footprint_change")  # event types in data/ba_events.csv
R3A_DAYS = 7
R3B_MIN_USABLE_HOURS = 8_760  # one year


def both_present(hourly: pd.DataFrame) -> pd.Series:
    """Baseline: demand and forecast are both reported."""
    return hourly["demand"].notna() & hourly["forecast"].notna()


def nonpositive(hourly: pd.DataFrame) -> pd.Series:
    """R1: demand or forecast reported as zero or negative."""
    return hourly["demand"].le(0) | hourly["forecast"].le(0)


def repeats_in_runs(hourly: pd.DataFrame, column: str, min_hours: int) -> pd.Series:
    """R2 (demand) or R2b (forecast): hours that repeat the previous hour's value inside a run of
    at least `min_hours` consecutive hours with the same value. The run's first hour is kept.

    Runs are per BA and are broken by a missing value or an absent hour.
    """
    ordered = hourly.sort_values(["ba", "utc"])
    value = ordered[column]
    same = (
        ordered["ba"].eq(ordered["ba"].shift())
        & ordered["utc"].sub(ordered["utc"].shift()).eq(HOUR)
        & value.eq(value.shift())
    )
    run = (~same).cumsum()
    length = run.map(run.value_counts())
    return (same & length.ge(min_hours)).reindex(hourly.index)


def near_events(hourly: pd.DataFrame, events: pd.DataFrame, days: float = R3A_DAYS) -> pd.Series:
    """R3a: a BA's hours strictly within `days` days of one of its start, stop or footprint-change
    events (`events` has columns date, ba and event; dates are UTC midnight)."""
    flags = pd.Series(False, index=hourly.index)
    window = pd.Timedelta(days=days)
    for event in events[events["event"].isin(R3A_EVENTS)].itertuples():
        flags |= hourly["ba"].eq(event.ba) & (hourly["utc"] - event.date).abs().lt(window)
    return flags


def short_history(
    hourly: pd.DataFrame, usable: pd.Series, min_hours: int = R3B_MIN_USABLE_HOURS
) -> pd.Series:
    """R3b: every hour of a BA with fewer than `min_hours` usable hours in total."""
    counts = usable.groupby(hourly["ba"]).sum()
    return hourly["ba"].isin(counts.index[counts < min_hours])


def half_years(hourly: pd.DataFrame) -> pd.Series:
    """Half-year label ('2015 H2') of each row, from its source file."""
    files = pd.Categorical(hourly["source_file"])
    return pd.Series(
        files.rename_categories([half_year(str(c)) for c in files.categories]),
        index=hourly.index,
    )


def rule_impact(hourly: pd.DataFrame, rules: dict[str, pd.Series]) -> pd.DataFrame:
    """Per rule, in order: hours with both values that it removes on its own and after the rules
    before it, and how many BAs lose hours to it on its own."""
    base = both_present(hourly)
    remaining = base.copy()
    rows = []
    for name, flags in rules.items():
        alone, after = base & flags, remaining & flags
        remaining &= ~flags
        rows.append(
            {
                "rule": name,
                "alone": int(alone.sum()),
                "after_earlier": int(after.sum()),
                "bas": hourly.loc[alone, "ba"].nunique(),
            }
        )
    return pd.DataFrame(rows)


def removed_by_ba(hourly: pd.DataFrame, flags: pd.Series) -> pd.DataFrame:
    """BAs losing hours with both values to `flags`: hours lost and percent of those hours."""
    base = both_present(hourly)
    lost = (base & flags).groupby(hourly["ba"]).sum()
    total = base.groupby(hourly["ba"]).sum()
    out = pd.DataFrame({"hours": lost, "pct": 100 * lost / total})
    return out[out["hours"] > 0].sort_values("hours", ascending=False)


def largest_bas(hourly: pd.DataFrame, n: int = 10) -> list[str]:
    """The `n` BAs with the highest mean reported demand."""
    return list(hourly.groupby("ba")["demand"].mean().dropna().nlargest(n).index)


def drop_sensitivity(
    hourly: pd.DataFrame,
    candidates: dict[object, pd.Series],
    other_drops: pd.Series,
    top: list[str],
    keep_pct: float = 95.0,
) -> pd.DataFrame:
    """For each candidate version of a rule (column `key`): hours it removes after `other_drops`,
    BAs losing more than 1% of their hours with both values, and how many `top` BAs keep at
    least `keep_pct` percent of (a) all their hours and (b) their hours with both values."""
    ba = hourly["ba"]
    base = both_present(hourly)
    base_count = base.groupby(ba).sum()
    rows = []
    for key, flags in candidates.items():
        removed = base & ~other_drops & flags
        usable = base & ~other_drops & ~flags
        lost_pct = 100 * removed.groupby(ba).sum() / base_count
        all_pct = 100 * usable.groupby(ba).mean()
        kept_pct = 100 * usable.groupby(ba).sum() / base_count
        rows.append(
            {
                "key": key,
                "removed": int(removed.sum()),
                "bas_over_1pct": int((lost_pct > 1).sum()),
                "top_all_hours": int((all_pct[top] >= keep_pct).sum()),
                "top_present_hours": int((kept_pct[top] >= keep_pct).sum()),
            }
        )
    return pd.DataFrame(rows)


def run_length_sensitivity(
    hourly: pd.DataFrame,
    lengths: list[int],
    other_drops: pd.Series,
    top: list[str],
    keep_pct: float = 95.0,
) -> pd.DataFrame:
    """drop_sensitivity for R2 at each run length N (column `n`), after `other_drops` (R1, R3a)."""
    candidates: dict[object, pd.Series] = {n: repeats_in_runs(hourly, "demand", n) for n in lengths}
    return drop_sensitivity(hourly, candidates, other_drops, top, keep_pct).rename(
        columns={"key": "n"}
    )


def usable_share(hourly: pd.DataFrame, usable: pd.Series) -> pd.DataFrame:
    """Percent of each BA's rows that are usable, one column per half-year (NaN: no rows)."""
    return 100 * usable.groupby([hourly["ba"], half_years(hourly)], observed=True).mean().unstack()
