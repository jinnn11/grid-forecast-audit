"""Checks on reported demand that do not use the forecast, for choosing the truth series.

(a) EIA's own changes: "Demand (MW) (Imputed)" holds EIA's value where it replaced or filled raw
demand, and "Demand (MW) (Adjusted)" is raw demand with those values applied.
(b) The energy balance: a BA's demand should equal its net generation minus its total
interchange (positive interchange is a net export).
"""

import pandas as pd

from grid_audit.quality import half_years

BALANCE_TOLERANCE_MW = 1.0  # values are whole MW, so rounding can leave a 1 MW gap
R5_SHARE = 0.10  # approved 2026-10-28: the go/no-go check's upper bound for a plausible MAPE
# R5 exception rule (user, 2026-10-28). The user set the 30 days, 3 months and 10%; the episode
# definition (day share and gap) is ours.
EPISODE_DAY_SHARE = 0.5  # a day is out of balance when at least half its checkable hours are
EPISODE_GAP_DAYS = 7  # out-of-balance days at most this many days apart join one episode
EXEMPTION_MIN_DAYS = 30  # only episodes longer than this are checked
EXEMPTION_MONTHS = 3
EXEMPTION_SHARE = 0.10
EXEMPTION_MIN_COVERAGE = 0.5  # each compared window needs checkable data in this share of hours
SHIFTS = {"generation_shift": "net generation", "interchange_shift": "interchange"}


def eia_changed(hourly: pd.DataFrame) -> pd.Series:
    """R4: hours where EIA replaced a reported demand value (raw and imputed both set)."""
    return hourly["demand"].notna() & hourly["demand_imputed"].notna()


def eia_relations(hourly: pd.DataFrame) -> dict[str, int]:
    """Hour counts showing how raw, imputed and adjusted demand relate."""
    raw, imputed, adjusted = (
        hourly["demand"],
        hourly["demand_imputed"],
        hourly["demand_adjusted"],
    )
    replaced = eia_changed(hourly)
    differs = raw.notna() & adjusted.notna() & adjusted.ne(raw)
    flags = {
        "raw": raw.notna(),
        "imputed": imputed.notna(),
        "replaced": replaced,
        "replaced_negative": replaced & raw.lt(0),
        "replaced_zero": replaced & raw.eq(0),
        "replaced_positive": replaced & raw.gt(0),
        "filled": raw.isna() & imputed.notna(),
        "adjusted_differs": differs,
        "adjusted_differs_without_imputed": differs & imputed.isna(),
        "adjusted_is_imputed": imputed.notna() & adjusted.eq(imputed),
        "adjusted_not_imputed": imputed.notna() & ~adjusted.eq(imputed),
        "raw_without_adjusted": raw.notna() & adjusted.isna(),
        "adjusted_without_raw_or_imputed": raw.isna() & imputed.isna() & adjusted.notna(),
    }
    return {"rows": len(hourly)} | {name: int(f.sum()) for name, f in flags.items()}


def balance_gap(hourly: pd.DataFrame) -> pd.Series:
    """Demand minus (net generation minus interchange), MW; NaN if any of the three is blank."""
    return hourly["demand"] - (hourly["net_generation"] - hourly["interchange"])


def checkable(hourly: pd.DataFrame) -> pd.Series:
    """Hours with demand, net generation and interchange all reported."""
    return balance_gap(hourly).notna()


def sign_fit(hourly: pd.DataFrame, tolerance_mw: float = BALANCE_TOLERANCE_MW) -> pd.DataFrame:
    """Per BA, over checkable hours whose interchange is larger than `tolerance_mw` either way:
    hours, and the percent where demand is within `tolerance_mw` of net generation minus
    interchange (`minus_pct`) and of net generation plus interchange (`plus_pct`)."""
    demand, generation, interchange = (
        hourly["demand"],
        hourly["net_generation"],
        hourly["interchange"],
    )
    rows = checkable(hourly) & interchange.abs().gt(tolerance_mw)
    ba = hourly.loc[rows, "ba"]
    minus = (demand - (generation - interchange)).abs().le(tolerance_mw)[rows]
    plus = (demand - (generation + interchange)).abs().le(tolerance_mw)[rows]
    return pd.DataFrame(
        {
            "hours": ba.groupby(ba).size(),
            "minus_pct": 100 * minus.groupby(ba).mean(),
            "plus_pct": 100 * plus.groupby(ba).mean(),
        }
    )


def imbalanced(
    hourly: pd.DataFrame, max_share: float, tolerance_mw: float = BALANCE_TOLERANCE_MW
) -> pd.Series:
    """R5: hours where demand differs from net generation minus interchange by more than
    `max_share` of |demand| and by more than `tolerance_mw`. False where any of the three is
    blank, because the balance cannot be checked there."""
    gap = balance_gap(hourly).abs()
    return gap.gt(max_share * hourly["demand"].abs()) & gap.gt(tolerance_mw)


def balance_by_ba(hourly: pd.DataFrame, max_share: float) -> pd.DataFrame:
    """Per BA that reports demand: checkable hours, percent within BALANCE_TOLERANCE_MW, median
    gap as a percent of demand (hours with demand > 0), and percent imbalanced at `max_share`.
    Percentages are NaN for a BA with no checkable hours."""
    ba = hourly["ba"]
    rows = checkable(hourly)
    gap = balance_gap(hourly)
    positive = rows & hourly["demand"].gt(0)
    counts = rows.groupby(ba).sum()
    out = pd.DataFrame(
        {
            "hours": counts,
            "within_pct": 100 * gap.abs().le(BALANCE_TOLERANCE_MW)[rows].groupby(ba).sum() / counts,
            "median_gap_pct": (100 * gap / hourly["demand"])[positive].groupby(ba).median(),
            "imbalanced_pct": 100 * imbalanced(hourly, max_share)[rows].groupby(ba).sum() / counts,
        }
    )
    return out[hourly["demand"].notna().groupby(ba).any()]


def share_by_half_year(hourly: pd.DataFrame, flags: pd.Series, among: pd.Series) -> pd.DataFrame:
    """Percent of each BA's `among` hours where `flags` is true, one column per half-year (NaN
    where the BA has no `among` hours in that half-year)."""
    groups = [hourly["ba"], half_years(hourly)]
    hits = (flags & among).groupby(groups, observed=True).sum()
    total = among.groupby(groups, observed=True).sum()
    return (100 * hits / total.where(total > 0)).unstack()


def stretch_coverage(
    hourly: pd.DataFrame,
    stretches: dict[str, pd.Series],
    changed: pd.Series,
    unbalanced: pd.Series,
) -> pd.DataFrame:
    """Per named stretch (row flags): hours with raw demand, percent EIA changed, percent
    checkable against the balance, and percent of the checkable hours that are imbalanced."""
    raw = hourly["demand"].notna()
    can_check = checkable(hourly)
    rows = []
    for name, flags in stretches.items():
        hours = int((flags & raw).sum())
        checked = int((flags & can_check).sum())
        rows.append(
            {
                "stretch": name,
                "hours": hours,
                "changed_pct": 100 * (flags & changed).sum() / hours if hours else float("nan"),
                "checkable_pct": 100 * checked / hours if hours else float("nan"),
                "imbalanced_pct": (
                    100 * (flags & unbalanced).sum() / checked if checked else float("nan")
                ),
            }
        )
    return pd.DataFrame(rows)


def imbalance_episodes(
    hourly: pd.DataFrame,
    unbalanced: pd.Series,
    day_share: float = EPISODE_DAY_SHARE,
    gap_days: int = EPISODE_GAP_DAYS,
) -> pd.DataFrame:
    """Per BA, spans of UTC days (by hour-end time) on which at least `day_share` of the
    checkable hours are `unbalanced`, joined when at most `gap_days` days lie between them.

    Columns: ba, start and end (first and last such day, UTC midnight) and days (inclusive).
    """
    rows = checkable(hourly)
    day = hourly.loc[rows, "utc"].dt.floor("D")
    share = unbalanced[rows].groupby([hourly.loc[rows, "ba"], day]).mean()
    spans = []
    for ba, daily in share.groupby(level=0):
        bad = daily.droplevel(0).index[daily.to_numpy() >= day_share]
        if bad.empty:
            continue
        start = previous = bad[0]
        for current in bad[1:]:
            if (current - previous).days - 1 > gap_days:
                spans.append((ba, start, previous))
                start = current
            previous = current
        spans.append((ba, start, previous))
    episodes = pd.DataFrame(spans, columns=["ba", "start", "end"])
    episodes["days"] = (episodes["end"] - episodes["start"]).dt.days + 1
    return episodes


def level_change(
    rows: pd.DataFrame, start: pd.Timestamp, months: int = EXEMPTION_MONTHS
) -> dict[str, float]:
    """For one BA's rows: medians over checkable hours with positive demand in the `months`
    months from `start` and in the same months a year earlier.

    Returns the demand change as a share of the earlier median demand, and the net generation
    and interchange shifts (later minus earlier median) as shares of the same earlier demand.
    All NaN when either window has such hours for less than EXEMPTION_MIN_COVERAGE of its
    length, or the earlier median demand is not positive.
    """
    nan = dict.fromkeys(["demand_change", *SHIFTS], float("nan"))
    usable = rows[checkable(rows) & rows["demand"].gt(0)]
    medians = []
    for first in (start - pd.DateOffset(years=1), start):
        last = first + pd.DateOffset(months=months)
        window = usable[usable["utc"].ge(first) & usable["utc"].lt(last)]
        if len(window) < EXEMPTION_MIN_COVERAGE * (last - first) / pd.Timedelta(hours=1):
            return nan
        medians.append(window[["demand", "net_generation", "interchange"]].median())
    before, after = medians
    if before["demand"] <= 0:
        return nan
    return {
        "demand_change": after["demand"] / before["demand"] - 1,
        "generation_shift": (after["net_generation"] - before["net_generation"]) / before["demand"],
        "interchange_shift": (after["interchange"] - before["interchange"]) / before["demand"],
    }


def exemption_checks(
    hourly: pd.DataFrame,
    episodes: pd.DataFrame,
    min_days: int = EXEMPTION_MIN_DAYS,
    share: float = EXEMPTION_SHARE,
) -> pd.DataFrame:
    """The R5 exception rule for each episode longer than `min_days`: level_change columns, and
    `exempt` when demand changed by at most `share` while net generation or interchange shifted
    by more than `share` of demand. `attributed_to` names the shifted series; `reason` says why
    an episode is not exempt."""
    rows = []
    for episode in episodes[episodes["days"] > min_days].itertuples(index=False):
        change = level_change(hourly[hourly["ba"].eq(episode.ba)], episode.start)
        shifted = [name for key, name in SHIFTS.items() if abs(change[key]) > share]
        if pd.isna(change["demand_change"]):
            reason = "too little data to compare"
        elif abs(change["demand_change"]) > share:
            reason = "demand changed"
        elif not shifted:
            reason = "no other series shifted"
        else:
            reason = ""
        attributed = "" if reason else " and ".join(shifted)
        decision = {"exempt": not reason, "attributed_to": attributed, "reason": reason}
        rows.append(episode._asdict() | change | decision)
    columns = [*episodes.columns, "demand_change", *SHIFTS, "exempt", "attributed_to", "reason"]
    return pd.DataFrame(rows, columns=columns)


def in_episodes(hourly: pd.DataFrame, episodes: pd.DataFrame) -> pd.Series:
    """Hours of an episode's BA from the start of its first day to the end of its last day."""
    flags = pd.Series(False, index=hourly.index)
    day = hourly["utc"].dt.floor("D")
    for episode in episodes.itertuples():
        flags |= hourly["ba"].eq(episode.ba) & day.ge(episode.start) & day.le(episode.end)
    return flags
