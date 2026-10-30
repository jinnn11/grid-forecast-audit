"""Operators' own hourly load and day-ahead load forecasts, for the Q5 check of step 3.

Approved by the user on 2026-10-28, narrowly: CAISO (OASIS) for 2025 and Jan-Jun 2026, SPP
(Marketplace portal) for 2025. Pure functions: file names, URLs, parsing and the comparison with
EIA-930. Downloads are in download_operators.py.
"""

import io
import re
import zipfile
from pathlib import Path
from urllib.parse import quote, urlencode

import pandas as pd

OPERATORS_DIR = Path("data/raw/operators")
HOUR = pd.Timedelta(hours=1)

# CAISO OASIS "SLD_FCST": DAM is the day-ahead forecast, ACTUAL the hourly integrated load.
OASIS_URL = "https://oasis.caiso.com/oasisapi/SingleZip"
CAISO_AREA = "CA ISO-TAC"  # the CAISO balancing authority area total
CAISO_RUNS = ("DAM", "ACTUAL")
CAISO_MONTHS = pd.period_range("2025-01", "2026-06", freq="M")
PACIFIC = "America/Los_Angeles"  # OASIS counts its 31-day limit in Pacific trading days
OASIS_STAMP = "%Y%m%dT%H%M"

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
    if path.name.startswith("OP-MTLF-"):
        issue = pd.to_datetime(path.stem.removeprefix("OP-MTLF-"), format="%Y%m%d%H%M")
        return spp_url(issue)
    raise ValueError(f"not an operator file: {path.name}")


def planned_files(directory: Path = OPERATORS_DIR) -> list[tuple[str, Path]]:
    """Every approved file: (URL, cache path), CAISO first."""
    files = [
        oasis_file(run, month, directory / "caiso") for run in CAISO_RUNS for month in CAISO_MONTHS
    ]
    files += [(spp_url(issue), directory / "spp" / spp_name(issue)) for issue in spp_issues()]
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
    days = pd.Series(best, dtype="Int64").sort_index()
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
