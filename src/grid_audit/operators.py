"""Operators' own hourly load and day-ahead load forecasts, for the Q5 check of step 3.

Approved by the user on 2026-10-28, narrowly: CAISO (OASIS) for 2025 and Jan-Jun 2026, SPP
(Marketplace portal) for 2025; and on 2026-10-30, CAISO back to 2016 where needed to date CISO's
one-hour lag. Pure functions: file names, URLs, parsing, the comparison with EIA-930 and the
verified corrections. Downloads are in download_operators.py.
"""

import io
import re
import zipfile
from pathlib import Path
from urllib.parse import quote, urlencode

import numpy as np
import pandas as pd

OPERATORS_DIR = Path("data/raw/operators")
HOUR = pd.Timedelta(hours=1)

# CAISO OASIS "SLD_FCST": DAM is the day-ahead forecast, ACTUAL the hourly integrated load.
OASIS_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
CAISO_AREA = "CA ISO-TAC"  # the CAISO balancing authority area total
CAISO_RUNS = ("DAM", "ACTUAL")
CAISO_MONTHS = pd.period_range("2025-01", "2026-06", freq="M")
# When CISO's one-hour lag started (user, 2026-10-30: back to 2016 if needed): first one month per
# year (July, which has no clock change), then only the months needed to pin each change down.
CAISO_SAMPLE_MONTHS = pd.PeriodIndex([f"{year}-07" for year in range(2016, 2025)], freq="M")
# The sample showed EIA-930's CISO demand an hour late in July 2016 and July 2022-2024, and on time
# in July 2017-2021. EIA-930's forecast equals CAISO's in every sampled hour, so EIA's own
# forecast-against-demand timing, day by day, places the two switches: 2016-09-12/13 and
# 2022-06-17 (the 2025-12-02/03 switch it also shows was already confirmed with CAISO's data).
CAISO_PINNED_MONTHS = pd.PeriodIndex(["2016-01", "2016-09", "2022-06"], freq="M")
# The short spells EIA's own check flags outside the late spans (user, 2026-10-30: only the months
# involved); July 2020 is already in the sample.
CAISO_SPELL_MONTHS = pd.PeriodIndex(["2020-05", "2021-05"], freq="M")
CAISO_HISTORY_MONTHS = CAISO_SAMPLE_MONTHS.union(CAISO_PINNED_MONTHS).union(CAISO_SPELL_MONTHS)
PACIFIC = "America/Los_Angeles"  # OASIS counts its 31-day limit in Pacific trading days
OASIS_STAMP = "%Y%m%dT%H%M"

# CAISO's own battery output for 2025 (user, 2026-10-30), to check what CISO reports under
# EIA-930's "Other Fuel Sources": Today's Outlook daily fuel-mix files, MW every 5 minutes on the
# Pacific clock. "Batteries" is the fleet's net output, below 0 while charging.
OUTLOOK_URL = "https://www.caiso.com/outlook/history/{day:%Y%m%d}/fuelsource.csv"
OUTLOOK_DAYS = pd.date_range("2025-01-01", "2025-12-31", freq="D")
OUTLOOK_MIN_READINGS = 10  # of 12 five-minute readings, for an hourly mean

# SPP "MTLF vs Actual": one file per issue hour (named on SPP's Central clock), with the mid-term
# load forecast for the next days and the averaged actual load for the past hours. SPP's
# day-ahead forecast is taken as the 03:00 issue of the day before: of the 24 issues of
# 2025-01-01, it alone equals EIA-930's SWPP forecast for 2025-01-02 (all 24 hours).
SPP_URL = "https://portal.spp.org/file-browser-api/download/mtlf-vs-actual"
SPP_ISSUE_HOUR = 3
SPP_DAYS = pd.date_range("2025-01-01", "2025-12-31", freq="D")
# Earlier years sit in one archive per year (2024.zip), which holds a year of data outside the
# approval. Without the 2024-12-31 issue, SPP's forecast for 2025-01-01 is missing.
SPP_FIRST_DAILY_ISSUE = pd.Timestamp("2025-01-01")
SPP_TIME_FORMAT = "%m/%d/%Y %H:%M:%S"
CENTRAL = "America/Chicago"


def oasis_window(month: pd.Period) -> tuple[pd.Timestamp, pd.Timestamp]:
    """A month as OASIS counts it: Pacific midnight to Pacific midnight, in UTC."""
    start, end = (pd.Timestamp(m.start_time).tz_localize(PACIFIC) for m in (month, month + 1))
    return start.tz_convert("UTC"), end.tz_convert("UTC")


def oasis_name(run: str, month: pd.Period, start: pd.Timestamp, end: pd.Timestamp) -> str:
    """Cache name for one month of a CAISO run, with the UTC window it was requested for.
    OASIS's own names carry the request time, so they cannot serve as a cache key."""
    return f"CAISO_SLD_FCST_{run}_{month:%Y-%m}_{start:{OASIS_STAMP}}-{end:{OASIS_STAMP}}.zip"


def oasis_url(run: str, start: pd.Timestamp, end: pd.Timestamp) -> str:
    """OASIS SingleZip query (at most 31 days) for `run` from `start` to `end` (UTC), as CSV."""
    params = {
        "resultformat": 6,
        "queryname": "SLD_FCST",
        "version": 1,
        "market_run_id": run,
        "startdatetime": f"{start:%Y%m%dT%H:%M}-0000",
        "enddatetime": f"{end:%Y%m%dT%H:%M}-0000",
    }
    return f"{OASIS_URL}?{urlencode(params, safe=':')}"


def oasis_file(run: str, month: pd.Period, directory: Path) -> tuple[str, Path]:
    """(URL, cache path) for one month of a CAISO run: the cached file if there is one, whatever
    window it was requested for, otherwise the month's oasis_window."""
    cached = sorted(directory.glob(f"CAISO_SLD_FCST_{run}_{month:%Y-%m}_*.zip"))
    path = cached[0] if cached else directory / oasis_name(run, month, *oasis_window(month))
    return source_url(path), path


def spp_issues(days: pd.DatetimeIndex = SPP_DAYS) -> list[pd.Timestamp]:
    """Issues needed for `days`: the day before each day (its forecast) and the day after the
    last (the actual load of the last day's final hours), from SPP_FIRST_DAILY_ISSUE on."""
    first, last = days[0] - pd.Timedelta(days=1), days[-1] + pd.Timedelta(days=1)
    issues = [spp_issue(day) for day in pd.date_range(first, last, freq="D")]
    return [issue for issue in issues if issue >= SPP_FIRST_DAILY_ISSUE]


def spp_issue(day: pd.Timestamp) -> pd.Timestamp:
    """The day's SPP_ISSUE_HOUR issue. On the day Central clocks go forward SPP has no 03:00
    file (its 04:00 file is the next one), so the 04:00 issue is used."""
    midnight, evening = (day + pd.Timedelta(hours=h) for h in (0, 23))
    offsets = [t.tz_localize(CENTRAL).utcoffset() for t in (midnight, evening)]
    springs_forward = offsets[1] > offsets[0]
    return day + pd.Timedelta(hours=SPP_ISSUE_HOUR + springs_forward)


def outlook_name(day: pd.Timestamp) -> str:
    """Cache name for one day's Today's Outlook fuel mix (CAISO names every day fuelsource.csv)."""
    return f"CAISO_OUTLOOK_fuelsource_{day:%Y%m%d}.csv"


def outlook_url(day: pd.Timestamp) -> str:
    return OUTLOOK_URL.format(day=day)


def read_outlook(source: Path | io.StringIO, day: pd.Timestamp, column: str = "Batteries"):
    """`column` (MW) from one Today's Outlook fuel-mix file, by UTC hour end: the mean of the
    hour's 5-minute readings (stamped at their start on the Pacific clock of `day`), NaN with
    fewer than OUTLOOK_MIN_READINGS. Every file has 288 rows: on the spring change the missing
    hour is listed blank; on the autumn change the repeated hour is listed once, so which of the
    two it is is unknown and it is left out."""
    table = pd.read_csv(source)
    local = pd.to_datetime(f"{day:%Y-%m-%d} " + table["Time"], format="%Y-%m-%d %H:%M")
    utc = local.dt.tz_localize(PACIFIC, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    readings = pd.Series(table[column].astype(float).to_numpy(), index=pd.DatetimeIndex(utc))
    readings = readings[readings.index.notna()]
    hours = readings.resample("h", closed="left", label="right")
    return hours.mean().where(hours.count() >= OUTLOOK_MIN_READINGS).rename_axis("utc")


def spp_name(issue: pd.Timestamp) -> str:
    return f"OP-MTLF-{issue:%Y%m%d%H}00.csv"


def spp_url(issue: pd.Timestamp) -> str:
    path = f"/{issue:%Y/%m/%d}/{spp_name(issue)}"
    return f"{SPP_URL}?path={quote(path, safe='')}"


def source_url(path: Path) -> str:
    """The URL a cached operator file came from, rebuilt from its name."""
    if path.name.startswith("CAISO_SLD_FCST_"):
        run, _, window = path.stem.removeprefix("CAISO_SLD_FCST_").split("_")
        start, end = (pd.to_datetime(t, format=OASIS_STAMP, utc=True) for t in window.split("-"))
        return oasis_url(run, start, end)
    if path.name.startswith("CAISO_OUTLOOK_fuelsource_"):
        return outlook_url(pd.to_datetime(path.stem.rsplit("_", 1)[1], format="%Y%m%d"))
    if path.name.startswith("OP-MTLF-"):
        issue = pd.to_datetime(path.stem.removeprefix("OP-MTLF-"), format="%Y%m%d%H%M")
        return spp_url(issue)
    raise ValueError(f"not an operator file: {path.name}")


def planned_files(directory: Path = OPERATORS_DIR) -> list[tuple[str, Path]]:
    """Every approved file: (URL, cache path), CAISO first."""
    months = CAISO_HISTORY_MONTHS.union(CAISO_MONTHS)
    files = [oasis_file(run, month, directory / "caiso") for run in CAISO_RUNS for month in months]
    files += [(spp_url(issue), directory / "spp" / spp_name(issue)) for issue in spp_issues()]
    files += [
        (outlook_url(day), directory / "caiso_outlook" / outlook_name(day)) for day in OUTLOOK_DAYS
    ]
    return files


def read_oasis(source: Path | io.BytesIO, area: str = CAISO_AREA) -> pd.Series:
    """MW for `area` by UTC hour end, from an OASIS SingleZip result. OASIS reports a refused
    query as an XML file inside the zip; that raises ValueError."""
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        csvs = [name for name in names if name.lower().endswith(".csv")]
        if len(csvs) != 1:
            text = archive.read(names[0]).decode(errors="replace") if names else ""
            reasons = re.findall(r"<m:ERR_(?:CODE|DESC)>([^<]*)<", text)
            raise ValueError(f"OASIS returned no CSV: {' '.join(reasons) or text[:300]}")
        table = pd.read_csv(archive.open(csvs[0]))
    table = table[table["TAC_AREA_NAME"].eq(area)]
    utc = pd.to_datetime(table["INTERVALENDTIME_GMT"], utc=True)
    series = pd.Series(table["MW"].to_numpy(dtype=float), index=pd.DatetimeIndex(utc, name="utc"))
    if series.index.duplicated().any():
        raise ValueError(f"repeated hours for {area}")
    return series.sort_index()


def read_spp(source: Path | io.StringIO) -> pd.DataFrame:
    """One SPP MTLF-vs-actual file: utc (hour end), local_end (SPP's "Interval", the hour end on
    its own clock), mtlf and actual (MW; NaN if blank)."""
    table = pd.read_csv(source)
    return pd.DataFrame(
        {
            "utc": pd.to_datetime(table["GMTIntervalEnd"], format=SPP_TIME_FORMAT, utc=True),
            "local_end": pd.to_datetime(table["Interval"], format=SPP_TIME_FORMAT),
            "mtlf": table["MTLF"].astype(float),
            "actual": table["Averaged Actual"].astype(float),
        }
    )


# Assembling each operator's hourly series


def caiso_series(months: dict[str, list[pd.Series]]) -> pd.DataFrame:
    """CAISO's forecast (DAM) and actual (ACTUAL) by UTC hour end, from monthly read_oasis
    results per run. A month boundary hour reported twice must agree."""
    columns = {}
    for run, name in (("DAM", "forecast"), ("ACTUAL", "actual")):
        series = pd.concat(months[run])
        repeated = series.index.duplicated(keep=False)
        if series[repeated].groupby(level=0).nunique().gt(1).any():
            raise ValueError(f"CAISO {run}: a repeated hour disagrees")
        columns[name] = series[~series.index.duplicated()]
    return pd.DataFrame(columns).sort_index()


def spp_series(issues: dict[pd.Timestamp, pd.DataFrame]) -> tuple[pd.DataFrame, int]:
    """SPP's day-ahead forecast and actual load by UTC hour end, from read_spp results keyed by
    issue time, and the number of hours whose actual differs between issues.

    The forecast for day D is the MTLF of the issue at SPP_ISSUE_HOUR on D - 1, for the hours
    that start on D by SPP's own clock. The actual is the averaged actual of the latest issue
    that reports the hour (SPP may revise it)."""
    forecasts, actuals = [], []
    for issue, table in sorted(issues.items()):
        day = issue.normalize() + pd.Timedelta(days=1)
        starts_on = (table["local_end"] - HOUR).dt.normalize()
        forecasts.append(table.loc[starts_on.eq(day), ["utc", "mtlf"]])
        actuals.append(table.loc[table["actual"].notna(), ["utc", "actual"]])
    actual = pd.concat(actuals)
    revised = int(actual.groupby("utc")["actual"].nunique().gt(1).sum())
    actual = actual.drop_duplicates("utc", keep="last").set_index("utc")["actual"]
    forecast = pd.concat(forecasts).drop_duplicates("utc", keep="last")
    frame = pd.DataFrame({"forecast": forecast.set_index("utc")["mtlf"], "actual": actual})
    return frame.sort_index(), revised


# Comparing an operator's series with EIA-930's

SHIFTS = (-2, -1, 0, 1, 2)
EQUAL_MW = 1.0  # EIA-930 reports whole MW; OASIS forecasts have decimals
ALIGNED_GAP_PCT = 2.0  # a day counts as aligned at a shift when its mean gap is at most this
NAIVE_HOURS = 24


def moved(series: pd.Series, index: pd.DatetimeIndex, hours: int) -> pd.Series:
    """`series` moved later by `hours`: at each t of `index`, its value at t - hours."""
    return pd.Series(series.reindex(index - pd.Timedelta(hours=hours)).to_numpy(), index=index)


def alignment(
    eia: pd.Series, operator: pd.Series, shifts: tuple[int, ...] = SHIFTS
) -> pd.DataFrame:
    """For each shift k (the operator's series moved k hours later): hours with both values,
    the share within EQUAL_MW of EIA's value, and the mean absolute difference as a percent of
    EIA's mean."""
    rows = {}
    for k in shifts:
        other = moved(operator, eia.index, k)
        both = eia.notna() & other.notna()
        gap = (eia[both] - other[both]).abs()
        rows[k] = {
            "hours": int(both.sum()),
            "equal_pct": 100 * gap.le(EQUAL_MW).mean(),
            "mean_gap_pct": 100 * gap.mean() / eia[both].mean(),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("shift")


def score(forecast: pd.Series, demand: pd.Series) -> dict[str, float]:
    """MAPE and bias (Σe / Σ demand, %) of `forecast` against `demand`, over hours with both and
    demand > 0 (NaN when there are none)."""
    both = forecast.notna() & demand.notna() & demand.gt(0)
    if not both.any():
        return {"hours": 0, "mape": float("nan"), "bias": float("nan")}
    error = forecast[both] - demand[both]
    return {
        "hours": int(both.sum()),
        "mape": 100 * (error.abs() / demand[both]).mean(),
        "bias": 100 * error.sum() / demand[both].sum(),
    }


def score_table(hours: pd.DataFrame, shift: int = 1) -> pd.DataFrame:
    """For `hours` with eia_forecast, eia_demand, op_forecast, op_actual, and eia_naive and
    op_naive (each truth NAIVE_HOURS earlier): MAPE and bias of each forecast against each
    truth, as published and moved `shift` hours later, and skill against that truth's naive
    forecast on the hours that have it."""
    rows = {}
    truths = (("EIA-930", "eia_demand", "eia_naive"), ("Operator", "op_actual", "op_naive"))
    for f_name, forecast in (("EIA-930", "eia_forecast"), ("Operator", "op_forecast")):
        for t_name, truth, naive in truths:
            plain = score(hours[forecast], hours[truth])
            later = score(moved(hours[forecast], hours.index, shift), hours[truth])
            paired = hours[hours[naive].notna()]
            skill = 1 - (
                score(paired[forecast], paired[truth])["mape"]
                / score(paired[naive], paired[truth])["mape"]
            )
            rows[(f_name, t_name)] = plain | {"mape_moved": later["mape"], "skill": skill}
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis(["forecast", "truth"])


def monthly(hours: pd.DataFrame, local_month: pd.Series) -> pd.DataFrame:
    """Per month: EIA / operator median ratio of demand and of forecast, and the bias of each
    forecast against its own truth."""
    rows = {}
    for month, part in hours.groupby(local_month):
        rows[month] = {
            "demand_ratio": (part["eia_demand"] / part["op_actual"]).median(),
            "forecast_ratio": (part["eia_forecast"] / part["op_forecast"]).median(),
            "eia_bias": score(part["eia_forecast"], part["eia_demand"])["bias"],
            "op_bias": score(part["op_forecast"], part["op_actual"])["bias"],
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def offset_runs(
    eia: pd.Series, operator: pd.Series, day: pd.Series, shifts: tuple[int, ...] = (-1, 0, 1)
) -> pd.DataFrame:
    """Spans of consecutive days on which the same shift aligns `operator` best with `eia`
    (smallest mean gap), for days on which they overlap. `day` gives each EIA hour's local day.
    A day whose best gap is above ALIGNED_GAP_PCT is aligned at no shift (shift <NA>): the
    levels differ, and the best shift would be noise.

    Columns: first, last, shift and days."""
    best = {}
    for date, part in eia.groupby(day.to_numpy()):
        table = alignment(part, operator, shifts)
        if table["hours"].gt(0).all():
            k = int(table["mean_gap_pct"].idxmin())
            best[date] = k if table.loc[k, "mean_gap_pct"] <= ALIGNED_GAP_PCT else pd.NA
    return day_runs(pd.Series(best, dtype="Int64"))


def ramp_match(eia: pd.Series, operator: pd.Series, shifts: tuple[int, ...] = SHIFTS) -> pd.Series:
    """For each shift k (the operator's series moved k hours later): the correlation of EIA's
    hour-to-hour changes with the operator's. Unlike the gap it ignores the levels, so it shows
    the timing even where the two series differ by a percent or two. `eia` must be hourly."""
    changes = eia.diff()
    return pd.Series(
        {k: changes.corr(moved(operator, eia.index, k).diff()) for k in shifts}
    ).rename_axis("shift")


def ramp_runs(
    eia: pd.Series, operator: pd.Series, day: pd.Series, shifts: tuple[int, ...] = (-1, 0, 1)
) -> pd.DataFrame:
    """Like offset_runs, with each day's shift the one whose hour-to-hour changes match best
    (ramp_match), for days with at least 12 hourly changes in both series."""
    best = {}
    for date, part in eia.groupby(day.to_numpy()):
        other = moved(operator, part.index, 0)
        if (part.diff().notna() & other.diff().notna()).sum() >= 12:
            best[date] = int(ramp_match(part, operator, shifts).idxmax())
    return day_runs(pd.Series(best, dtype="Int64"))


def day_runs(best: pd.Series) -> pd.DataFrame:
    """Spans of consecutive entries of `best` (a shift per day, <NA> for none) with the same
    value. Columns: first, last, shift and days."""
    days = best.sort_index()
    label = pd.Series(
        ["none" if pd.isna(k) else str(k) for k in days], index=days.index, dtype=object
    )
    groups = days.groupby(label.ne(label.shift()).cumsum())
    return pd.DataFrame(
        {
            "first": groups.apply(lambda s: s.index.min()),
            "last": groups.apply(lambda s: s.index.max()),
            "shift": groups.first().astype("Int64"),
            "days": groups.size(),
        }
    ).reset_index(drop=True)


# CISO's lag over the years, CAISO's battery charging and the verified corrections (user,
# 2026-10-30)

# UTC hour ends in which EIA-930's CISO demand is CAISO's actual load an hour late, as checked hour
# by hour against CAISO's data (results/ciso_check.md). The first span starts before 2016; it is
# taken from the first hour of 2016 (Pacific), the earliest month checked.
CISO_LATE_SPANS = tuple(
    (pd.Timestamp(first, tz="UTC"), pd.Timestamp(last, tz="UTC"))
    for first, last in (
        ("2016-01-01 09:00", "2016-09-12 21:00"),
        ("2022-06-14 08:00", "2022-06-15 07:00"),
        ("2022-06-16 08:00", "2025-12-02 23:00"),
    )
)
# EIA-930's SWPP forecast is more than 2% from SPP's own from this local day on
# (results/operator_check.md); the variant uses SPP's own forecast through the end of 2025.
SWPP_REPLACED_DAYS = ("2025-05-07", "2025-12-31")


def lead_by_month(
    forecast: pd.Series, demand: pd.Series, month: pd.Series, shifts: tuple[int, ...] = (-1, 0, 1)
) -> pd.DataFrame:
    """Per month: MAPE (%) of `forecast` against `demand` with the forecast moved k hours later,
    on the hours where demand and every moved forecast are > 0, and `best`, the k with the
    lowest. The three series share one index of UTC hour ends."""
    forecasts = pd.DataFrame({k: moved(forecast, forecast.index, k) for k in shifts})
    ok = demand.gt(0) & forecasts.gt(0).all(axis=1)
    ape = 100 * forecasts[ok].sub(demand[ok], axis=0).abs().div(demand[ok], axis=0)
    table = ape.groupby(month[ok]).mean()
    return table.assign(best=table.idxmin(axis=1))


def series_match(
    eia: pd.Series, operator: pd.Series, shifts: tuple[int, ...] = (-1, 0, 1)
) -> pd.DataFrame:
    """For each shift k (the operator's series moved k hours later): hours with both values,
    their correlation, the mean absolute difference (MW) and the least-squares slope of EIA's
    value on the operator's. For series near 0 on average, such as net storage, where a gap as
    a percent of the mean means nothing."""
    rows = {}
    for k in shifts:
        other = moved(operator, eia.index, k)
        both = eia.notna() & other.notna()
        x, y = other[both], eia[both]
        rows[k] = {
            "hours": int(both.sum()),
            "corr": x.corr(y),
            "mean_abs_diff": (y - x).abs().mean(),
            "slope": ((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum(),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("shift")


def charging_fit(gap: pd.Series, storage: pd.Series) -> dict[str, float]:
    """Least-squares fit of gap = a + b × charging + c × discharging (MW) over the hours with
    both, where `storage` is net generation from storage (below 0 while charging), and R²."""
    both = gap.notna() & storage.notna()
    y, net = gap[both].to_numpy(), storage[both].to_numpy()
    x = np.column_stack([np.ones(len(y)), np.clip(-net, 0, None), np.clip(net, 0, None)])
    coef = np.linalg.lstsq(x, y, rcond=None)[0]
    spread = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - x @ coef) ** 2).sum() / spread if spread > 0 else float("nan")
    return {
        "hours": len(y),
        "intercept": coef[0],
        "charging": coef[1],
        "discharging": coef[2],
        "r2": r2,
    }


def demand_moved_back(
    hourly: pd.DataFrame, ba: str, spans: tuple[tuple[pd.Timestamp, pd.Timestamp], ...]
) -> pd.DataFrame:
    """`hourly` with the BA's demand for the UTC hour ends `first` to `last` of each span taken
    from one hour later, for spans where EIA-930 reports each hour's demand an hour late. EIA's
    imputed and adjusted demand travel with it. The value for a span's last hour is not in the
    data, so it is NaN."""
    own = hourly["ba"].eq(ba)
    table = hourly[own].set_index("utc")
    corrected = hourly.copy()
    for first, last in spans:
        rows = own & hourly["utc"].between(first, last)
        later = hourly.loc[rows, "utc"] + HOUR
        for column in ("demand", "demand_imputed", "demand_adjusted"):
            values = table[column].reindex(later).to_numpy()
            corrected.loc[rows, column] = np.where(later.eq(last + HOUR), np.nan, values)
    return corrected


def moved_back(
    series: pd.Series, spans: tuple[tuple[pd.Timestamp, pd.Timestamp], ...]
) -> pd.Series:
    """`series` (by UTC hour end) with its values for the hour ends `first` to `last` of each
    span taken from one hour later, as demand_moved_back does for demand; NaN at each span's
    last hour."""
    moved_series = series.copy()
    for first, last in spans:
        inside = series.index[(series.index >= first) & (series.index <= last)]
        values = series.reindex(inside + HOUR).to_numpy()
        moved_series[inside] = np.where(inside == last, np.nan, values)
    return moved_series


def charging_removed(hourly: pd.DataFrame, ba: str, charge: pd.Series) -> pd.DataFrame:
    """`hourly` with the BA's charging (MW by UTC hour end, on the same timing as its demand)
    taken out of its demand. Hours without a charging value keep their demand."""
    rows = hourly["ba"].eq(ba)
    taken = charge.reindex(hourly.loc[rows, "utc"]).fillna(0).to_numpy()
    corrected = hourly.copy()
    corrected.loc[rows, "demand"] = hourly.loc[rows, "demand"].to_numpy() - taken
    return corrected


def forecast_replaced(
    hourly: pd.DataFrame, ba: str, replacement: pd.Series, first: pd.Timestamp, last: pd.Timestamp
) -> pd.DataFrame:
    """`hourly` with the BA's forecast for the UTC hour ends `first` to `last` replaced by
    `replacement` (by UTC hour end); hours it lacks become NaN."""
    rows = hourly["ba"].eq(ba) & hourly["utc"].between(first, last)
    corrected = hourly.copy()
    corrected.loc[rows, "forecast"] = replacement.reindex(hourly.loc[rows, "utc"]).to_numpy()
    return corrected
