import io
import subprocess
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from grid_audit.download import fetch_url
from grid_audit.operators import (
    alignment,
    caiso_series,
    charging_fit,
    demand_moved_back,
    forecast_replaced,
    lead_by_month,
    monthly,
    moved,
    oasis_file,
    oasis_name,
    oasis_url,
    oasis_window,
    offset_runs,
    ramp_match,
    ramp_runs,
    read_oasis,
    read_spp,
    score,
    score_table,
    source_url,
    spp_issue,
    spp_issues,
    spp_name,
    spp_series,
    spp_url,
)

NAN = float("nan")
OASIS_HEADER = (
    "INTERVALSTARTTIME_GMT,INTERVALENDTIME_GMT,LOAD_TYPE,OPR_DT,OPR_HR,OPR_INTERVAL,"
    "MARKET_RUN_ID,TAC_AREA_NAME,LABEL,XML_DATA_ITEM,POS,MW,EXECUTION_TYPE,GROUP"
)
SPP_HEADER = "Interval,GMTIntervalEnd,MTLF,Averaged Actual"


def oasis_zip(rows: list[tuple[str, str, float]]) -> io.BytesIO:
    """A SingleZip result with (hour-end UTC, area, MW) rows, in OASIS's CSV layout."""
    lines = [OASIS_HEADER]
    for end, area, mw in rows:
        start = pd.Timestamp(end) - pd.Timedelta(hours=1)
        lines.append(
            f"{start:%Y-%m-%dT%H:%M:%S}-00:00,{end}-00:00,1,2025-01-01,1,0,DAM,{area},"
            f"Demand Forecast Day Ahead,SYS_FCST_DA_MW,6,{mw},DAM,1"
        )
    return zip_with("result.csv", "\n".join(lines))


def zip_with(name: str, text: str) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, text)
    buffer.seek(0)
    return buffer


def test_oasis_window_follows_pacific_midnight() -> None:
    # February: standard time at both ends, midnight = 08:00 UTC. March: daylight time starts on
    # Mar 9, so Apr 1 midnight is 07:00 UTC. November: daylight time ends on Nov 2.
    def window(month: str) -> list[str]:
        return [f"{t:%m-%d %H:%M}" for t in oasis_window(pd.Period(month, freq="M"))]

    assert window("2025-02") == ["02-01 08:00", "03-01 08:00"]
    assert window("2025-03") == ["03-01 08:00", "04-01 07:00"]
    assert window("2025-11") == ["11-01 07:00", "12-01 08:00"]


def test_oasis_name_and_url() -> None:
    start, end = oasis_window(pd.Period("2025-05", freq="M"))
    name = oasis_name("DAM", pd.Period("2025-05", freq="M"), start, end)
    assert name == "CAISO_SLD_FCST_DAM_2025-05_20250501T0700-20250601T0700.zip"
    assert oasis_url("DAM", start, end) == (
        "https://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=SLD_FCST&version=1"
        "&market_run_id=DAM&startdatetime=20250501T07:00-0000&enddatetime=20250601T07:00-0000"
    )


def test_oasis_file_prefers_the_cached_window(tmp_path: Path) -> None:
    month = pd.Period("2025-03", freq="M")
    # Nothing cached: the month's own window.
    url, path = oasis_file("DAM", month, tmp_path)
    assert path.name == "CAISO_SLD_FCST_DAM_2025-03_20250301T0800-20250401T0700.zip"
    # A file requested with another window is reused, and its URL is the one it came from.
    cached = tmp_path / "CAISO_SLD_FCST_DAM_2025-03_20250301T0800-20250401T0800.zip"
    cached.write_bytes(b"")
    url, path = oasis_file("DAM", month, tmp_path)
    assert path == cached
    assert url.endswith("startdatetime=20250301T08:00-0000&enddatetime=20250401T08:00-0000")


def test_spp_issues_name_and_url() -> None:
    days = pd.date_range("2025-01-01", "2025-01-03", freq="D")
    # The day before the first day (its forecast) to the day after the last (its last actuals),
    # but none before 2025: 2024's files exist only inside a yearly archive.
    issues = spp_issues(days)
    assert [f"{i:%Y-%m-%d %H:%M}" for i in issues] == [
        "2025-01-01 03:00",
        "2025-01-02 03:00",
        "2025-01-03 03:00",
        "2025-01-04 03:00",
    ]
    assert spp_issues(pd.date_range("2025-03-01", "2025-03-01", freq="D"))[0] == pd.Timestamp(
        "2025-02-28 03:00"
    )
    assert spp_name(issues[0]) == "OP-MTLF-202501010300.csv"
    assert spp_url(issues[0]) == (
        "https://portal.spp.org/file-browser-api/download/mtlf-vs-actual"
        "?path=%2F2025%2F01%2F01%2FOP-MTLF-202501010300.csv"
    )


def test_source_url_round_trip() -> None:
    caiso = Path("caiso/CAISO_SLD_FCST_ACTUAL_2026-06_20260601T0700-20260701T0700.zip")
    start, end = oasis_window(pd.Period("2026-06", freq="M"))
    assert source_url(caiso) == oasis_url("ACTUAL", start, end)
    spp = Path("data/raw/operators/spp/OP-MTLF-202501011700.csv")
    assert source_url(spp) == spp_url(pd.Timestamp("2025-01-01 17:00"))
    with pytest.raises(ValueError):
        source_url(Path("other.csv"))


def test_read_oasis_keeps_the_caiso_total() -> None:
    result = read_oasis(
        oasis_zip(
            [
                ("2025-01-01T09:00:00", "CA ISO-TAC", 20_000.5),
                ("2025-01-01T08:00:00", "CA ISO-TAC", 21_000.0),
                ("2025-01-01T08:00:00", "PGE-TAC", 9_000.0),
            ]
        )
    )
    # Only CA ISO-TAC, indexed by UTC hour end and sorted.
    assert list(result.index.strftime("%H:%M")) == ["08:00", "09:00"]
    assert result.tolist() == [21_000.0, 20_000.5]
    assert str(result.index.tz) == "UTC"


def test_read_oasis_reports_a_refused_query() -> None:
    xml = (
        '<?xml version="1.0"?><m:OASISReport><m:ERR_CODE>1015</m:ERR_CODE>'
        "<m:ERR_DESC>Too many requests</m:ERR_DESC></m:OASISReport>"
    )
    with pytest.raises(ValueError, match="1015 Too many requests"):
        read_oasis(zip_with("INVALID_REQUEST.xml", xml))


def test_read_spp() -> None:
    text = "\n".join(
        [
            SPP_HEADER,
            "01/02/2025 01:00:00,01/02/2025 07:00:00,30000,",
            "01/01/2025 01:00:00,01/01/2025 07:00:00,31000,31500",
        ]
    )
    table = read_spp(io.StringIO(text))
    assert table.loc[0, "utc"] == pd.Timestamp("2025-01-02 07:00", tz="UTC")
    assert table.loc[0, "local_end"] == pd.Timestamp("2025-01-02 01:00")
    assert table.loc[0, "mtlf"] == 30_000.0 and pd.isna(table.loc[0, "actual"])
    assert table.loc[1, "actual"] == 31_500.0


def test_caiso_series_joins_months() -> None:
    hour = pd.Timestamp("2025-02-01 08:00", tz="UTC")
    jan = pd.Series([1.0, 2.0], index=[hour - pd.Timedelta(hours=1), hour])
    feb = pd.Series([2.0, 3.0], index=[hour, hour + pd.Timedelta(hours=1)])
    frame = caiso_series({"DAM": [jan, feb], "ACTUAL": [jan * 10, feb * 10]})
    # The boundary hour appears in both months with the same value, and is kept once.
    assert frame["forecast"].tolist() == [1.0, 2.0, 3.0]
    assert frame["actual"].tolist() == [10.0, 20.0, 30.0]
    with pytest.raises(ValueError, match="disagrees"):
        caiso_series({"DAM": [jan, feb + 1], "ACTUAL": [jan, feb]})


def spp_table(rows: list[tuple[str, str, float, float]]) -> pd.DataFrame:
    """read_spp-like table from (local hour end, UTC hour end, mtlf, actual)."""
    return pd.DataFrame(
        {
            "utc": pd.to_datetime([r[1] for r in rows], utc=True),
            "local_end": pd.to_datetime([r[0] for r in rows]),
            "mtlf": [r[2] for r in rows],
            "actual": [r[3] for r in rows],
        }
    )


def test_spp_series_takes_the_day_before_issue() -> None:
    first = spp_table(
        [
            ("2025-01-01 00:00", "2025-01-01 06:00", 90.0, 95.0),  # starts Dec 31: actual only
            ("2025-01-02 00:00", "2025-01-02 06:00", 98.0, NAN),  # starts Jan 1: not this issue's
            ("2025-01-02 01:00", "2025-01-02 07:00", 100.0, NAN),  # starts Jan 2: forecast
            ("2025-01-03 00:00", "2025-01-03 06:00", 101.0, NAN),  # starts Jan 2: forecast
            ("2025-01-03 01:00", "2025-01-03 07:00", 102.0, NAN),  # starts Jan 3: next issue's
        ]
    )
    second = spp_table(
        [
            ("2025-01-01 00:00", "2025-01-01 06:00", 90.0, 96.0),  # actual revised: 95 -> 96
            ("2025-01-02 01:00", "2025-01-02 07:00", 100.0, 105.0),
            ("2025-01-03 01:00", "2025-01-03 07:00", 103.0, NAN),  # starts Jan 3: forecast
        ]
    )
    frame, revised = spp_series(
        {pd.Timestamp("2025-01-01 03:00"): first, pd.Timestamp("2025-01-02 03:00"): second}
    )
    forecast = frame["forecast"].dropna()
    assert list(forecast.index.strftime("%m-%d %H:%M")) == [
        "01-02 07:00",
        "01-03 06:00",
        "01-03 07:00",
    ]
    assert forecast.tolist() == [100.0, 101.0, 103.0]
    actual = frame["actual"].dropna()
    assert actual.tolist() == [96.0, 105.0]  # the later issue wins
    assert revised == 1


def test_alignment_finds_an_hour_offset() -> None:
    index = pd.date_range("2025-01-01 01:00", periods=4, freq="h", tz="UTC")
    eia = pd.Series([100.0, 110.0, 120.0, 130.0], index=index)
    # The operator labels each value one hour early: its value at t is EIA's at t + 1.
    operator = pd.Series([110.0, 120.0, 130.0], index=index[:3])
    table = alignment(eia, operator, shifts=(0, 1))
    # Moved 1 h later it matches in the 3 hours it covers.
    assert table.loc[1, "hours"] == 3 and table.loc[1, "equal_pct"] == 100.0
    assert table.loc[1, "mean_gap_pct"] == 0.0
    # As published: 3 hours (the first three), each 10 MW apart; EIA's mean there is 110, so
    # the gap is 10 / 110 = 9.09%.
    assert table.loc[0, "hours"] == 3 and table.loc[0, "equal_pct"] == 0.0
    assert table.loc[0, "mean_gap_pct"] == pytest.approx(100 * 10 / 110)
    assert moved(operator, index, 1).tolist()[1:] == [110.0, 120.0, 130.0]


def test_score_and_score_table() -> None:
    # Forecast 110 and 90 on demand 100: MAPE 10%, bias 0. A zero demand is not scored.
    s = score(pd.Series([110.0, 90.0, 5.0]), pd.Series([100.0, 100.0, 0.0]))
    assert s == {"hours": 2, "mape": pytest.approx(10.0), "bias": pytest.approx(0.0)}
    index = pd.date_range("2025-01-01 01:00", periods=3, freq="h", tz="UTC")
    hours = pd.DataFrame(
        {
            "eia_demand": [100.0, 200.0, 100.0],
            "eia_forecast": [200.0, 100.0, 200.0],  # EIA demand one hour early
            "op_actual": [100.0, 200.0, 100.0],
            "op_forecast": [100.0, 200.0, 100.0],  # perfect
            "eia_naive": NAN,  # skill is tested in test_score_table_skill
            "op_naive": NAN,
        },
        index=index,
    )
    table = score_table(hours)
    eia = table.loc[("EIA-930", "EIA-930")]
    # As published: 100% on 100, 50% on 200, 100% on 100 -> MAPE 83.33%. Moved +1 h (hours 2
    # and 3 only): 200 vs 200, 100 vs 100 -> 0.
    assert eia["mape"] == pytest.approx(250 / 3) and eia["mape_moved"] == pytest.approx(0.0)
    operator = table.loc[("Operator", "Operator")]
    assert operator["mape"] == 0.0 and operator["bias"] == 0.0


def test_monthly() -> None:
    hours = pd.DataFrame(
        {
            "eia_demand": [100.0, 100.0],
            "eia_forecast": [110.0, 120.0],
            "op_actual": [95.0, 100.0],
            "op_forecast": [100.0, 100.0],
        }
    )
    table = monthly(hours, pd.Series([5, 6]))
    # May: demand 100 / 95, forecast 110 / 100; EIA bias +10%, operator +5.26% (5 / 95).
    assert table.loc[5, "demand_ratio"] == pytest.approx(100 / 95)
    assert table.loc[5, "forecast_ratio"] == pytest.approx(1.1)
    assert table.loc[5, "eia_bias"] == pytest.approx(10.0)
    assert table.loc[5, "op_bias"] == pytest.approx(100 * 5 / 95)
    assert table.loc[6, "eia_bias"] == pytest.approx(20.0)


def test_fetch_url_returns_cached_file_without_downloading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cached = tmp_path / "operators" / "file.csv"
    cached.parent.mkdir()
    cached.write_text("cached")

    def no_curl(*args: object, **kwargs: object) -> None:
        raise RuntimeError("curl must not run for a cached file")

    # conftest blocks sockets only in this process, so curl itself is blocked here.
    monkeypatch.setattr(subprocess, "run", no_curl)
    assert fetch_url("https://example.invalid/file.csv", cached) == cached
    assert cached.read_text() == "cached"


def test_offset_runs() -> None:
    # EIA reports hours 10:00 and 11:00 (UTC) on three days. On Jan 1 and 2 the operator's value
    # one hour earlier equals EIA's (EIA runs one hour late); on Jan 3 they agree as published.
    def hours(day: str, times: list[str]) -> pd.DatetimeIndex:
        return pd.to_datetime([f"{day} {t}" for t in times], utc=True)

    index = hours("2025-01-01", ["10:00", "11:00"]).append(
        [hours("2025-01-02", ["10:00", "11:00"]), hours("2025-01-03", ["10:00", "11:00"])]
    )
    eia = pd.Series([100.0, 110.0, 200.0, 210.0, 300.0, 310.0], index=index)
    times = ["09:00", "10:00", "11:00"]
    operator = pd.Series(
        [100.0, 110.0, 120.0, 200.0, 210.0, 220.0, 290.0, 300.0, 310.0],
        index=hours("2025-01-01", times).append(
            [hours("2025-01-02", times), hours("2025-01-03", times)]
        ),
    )
    # Jan 1: moved +1 h gives 100, 110 (gap 0); as published 110, 120 (gap 10). Jan 2 alike.
    # Jan 3: as published 300, 310 (gap 0); moved +1 h 290, 300 (gap 10).
    day = pd.Series(index.normalize().tz_localize(None), index=index)
    runs = offset_runs(eia, operator, day, shifts=(0, 1))
    assert runs[["shift", "days"]].values.tolist() == [[1, 2], [0, 1]]
    assert runs.loc[0, "first"] == pd.Timestamp("2025-01-01")
    assert runs.loc[0, "last"] == pd.Timestamp("2025-01-02")
    assert runs.loc[1, "first"] == pd.Timestamp("2025-01-03")


def test_spp_issue_on_daylight_saving_days() -> None:
    # Central clocks go forward on 2025-03-09 and back on 2025-11-02. SPP has no 03:00 file on
    # Mar 9, so its 04:00 issue is used; Nov 2 and ordinary days use 03:00.
    assert spp_issue(pd.Timestamp("2025-03-09")) == pd.Timestamp("2025-03-09 04:00")
    assert spp_issue(pd.Timestamp("2025-03-08")) == pd.Timestamp("2025-03-08 03:00")
    assert spp_issue(pd.Timestamp("2025-11-02")) == pd.Timestamp("2025-11-02 03:00")


def test_offset_runs_marks_days_aligned_at_no_shift() -> None:
    # One day, EIA 100 and 100 at 10:00 and 11:00; the operator reports 110 throughout. Every
    # shift leaves a 10% gap, above ALIGNED_GAP_PCT (2%), so the day is aligned at no shift.
    index = pd.to_datetime(["2025-01-01 10:00", "2025-01-01 11:00"], utc=True)
    eia = pd.Series([100.0, 100.0], index=index)
    operator = pd.Series(
        110.0, index=pd.date_range("2025-01-01 08:00", periods=5, freq="h", tz="UTC")
    )
    day = pd.Series(index.normalize().tz_localize(None), index=index)
    runs = offset_runs(eia, operator, day, shifts=(-1, 0, 1))
    assert len(runs) == 1 and pd.isna(runs.loc[0, "shift"]) and runs.loc[0, "days"] == 1


def test_score_table_skill() -> None:
    # Truth 100 then 120; its naive value (24 h earlier) is 90 then 100: |e| / truth = 0.1 and
    # 0.1667, naive MAPE 13.33%. A forecast of 110 and 108: 0.1 and 0.1, MAPE 10%. Skill
    # 1 - 10 / 13.33 = 0.25.
    index = pd.date_range("2025-01-02 01:00", periods=2, freq="h", tz="UTC")
    hours = pd.DataFrame(
        {
            "eia_demand": [100.0, 120.0],
            "eia_forecast": [110.0, 108.0],
            "eia_naive": [90.0, 100.0],
            "op_actual": [100.0, 120.0],
            "op_forecast": [110.0, 108.0],
            "op_naive": [90.0, NAN],  # only the first hour has a naive value: 0.1 vs 0.1 -> 0
        },
        index=index,
    )
    table = score_table(hours)
    assert table.loc[("EIA-930", "EIA-930"), "skill"] == pytest.approx(0.25)
    assert table.loc[("Operator", "Operator"), "skill"] == pytest.approx(0.0)


def test_lead_by_month_finds_a_forecast_one_hour_early() -> None:
    index = pd.date_range("2025-01-01 01:00", periods=6, freq="h", tz="UTC")
    demand = pd.Series([100.0, 200.0, 400.0, 200.0, 100.0, 200.0], index=index)
    # The forecast for t is demand at t + 1 (one hour early); the last value is 100.
    forecast = pd.Series([200.0, 400.0, 200.0, 100.0, 200.0, 100.0], index=index)
    month = pd.Series(pd.Period("2025-01", "M"), index=index)
    table = lead_by_month(forecast, demand, month)
    # Hours 2-5 have all three moved forecasts. +1: exact (0). As published: |400-200|/200,
    # |200-400|/400, |100-200|/200, |200-100|/100 = 100, 50, 50, 100% -> 75. Moved -1 (value
    # for t + 1): 200 vs 200, 100 vs 400, 200 vs 200, 100 vs 100 -> 0, 75, 0, 0 -> 18.75.
    row = table.loc[pd.Period("2025-01", "M")]
    assert row[1] == 0.0 and row[0] == 75.0 and row[-1] == 18.75
    assert row["best"] == 1


def test_charging_fit_recovers_an_exact_relation() -> None:
    storage = pd.Series([-100.0, -200.0, 50.0, 100.0, 0.0, -50.0])
    # gap = 10 + 0.9 x charging - 0.1 x discharging: 10 + 90, 10 + 180, 10 - 5, 10 - 10, 10;
    # the last hour has no gap and is left out.
    gap = pd.Series([100.0, 190.0, 5.0, 0.0, 10.0, NAN])
    fit = charging_fit(gap, storage)
    assert fit["hours"] == 5
    assert fit["intercept"] == pytest.approx(10.0)
    assert fit["charging"] == pytest.approx(0.9)
    assert fit["discharging"] == pytest.approx(-0.1)
    assert fit["r2"] == pytest.approx(1.0)


def hourly_two_bas() -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    index = pd.date_range("2025-06-01 01:00", periods=5, freq="h", tz="UTC")
    a = pd.DataFrame(
        {
            "ba": "A",
            "utc": index,
            "demand": [10.0, 20.0, 30.0, 40.0, 50.0],
            "forecast": 5.0,
            "demand_imputed": [NAN, NAN, 33.0, NAN, NAN],
            "demand_adjusted": [10.0, 20.0, 33.0, 40.0, 50.0],
        }
    )
    b = a.assign(ba="B", demand=[1.0, 2.0, 3.0, 4.0, 5.0], demand_imputed=NAN)
    return pd.concat([a, b], ignore_index=True), index


def test_demand_moved_back_takes_the_next_hour() -> None:
    hourly, t = hourly_two_bas()
    corrected = demand_moved_back(hourly, "A", ((t[1], t[3]),))
    a = corrected[corrected["ba"].eq("A")]
    # Hours 2-4 take hours 3-5's values; hour 4, the span's last, would need the true value
    # for hour 4, which the data do not have (hour 5 is on time), so it is blank.
    assert a["demand"].tolist()[:3] == [10.0, 30.0, 40.0]
    assert pd.isna(a["demand"].iloc[3]) and a["demand"].iloc[4] == 50.0
    # EIA's imputed and adjusted values travel with the demand: 33 moves from hour 3 to 2.
    assert a["demand_imputed"].iloc[1] == 33.0 and a["demand_imputed"].iloc[2:].isna().all()
    assert a["demand_adjusted"].tolist()[:3] == [10.0, 33.0, 40.0]
    assert corrected[corrected["ba"].eq("B")].equals(hourly[hourly["ba"].eq("B")])
    # Two spans, hours 1-2 and 4-5: 1 <- 2 (20), 2 blank, 3 kept, 4 <- 5 (50), 5 blank.
    two = demand_moved_back(hourly, "A", ((t[0], t[1]), (t[3], t[4])))
    values = two.loc[two["ba"].eq("A"), "demand"].tolist()
    assert values[0] == 20.0 and pd.isna(values[1]) and values[2:4] == [30.0, 50.0]
    assert pd.isna(values[4])


def test_forecast_replaced() -> None:
    hourly, t = hourly_two_bas()
    replacement = pd.Series([7.0, 8.0], index=t[1:3])
    corrected = forecast_replaced(hourly, "A", replacement, t[1], t[3])
    # Hours 2 and 3 replaced; hour 4 is in the span but has no replacement, so it is blank.
    forecast = corrected.loc[corrected["ba"].eq("A"), "forecast"].tolist()
    assert forecast[:3] == [5.0, 7.0, 8.0] and pd.isna(forecast[3]) and forecast[4] == 5.0
    assert corrected.loc[corrected["ba"].eq("B"), "forecast"].eq(5.0).all()


def test_ramp_match_ignores_a_level_difference() -> None:
    index = pd.date_range("2025-01-01 01:00", periods=5, freq="h", tz="UTC")
    eia = pd.Series([100.0, 110.0, 130.0, 120.0, 140.0], index=index)
    # The operator reports each hour one hour early and 50 MW higher.
    operator = pd.Series([150.0, 160.0, 180.0, 170.0, 190.0], index=index - pd.Timedelta("1h"))
    ramps = ramp_match(eia, operator, shifts=(0, 1))
    # Moved +1 h the changes are identical: correlation 1, despite the 50 MW gap.
    assert ramps[1] == pytest.approx(1.0)
    # As published, the changes at hours 3-5 are EIA (10, 20, -10) against the operator's
    # (20, -10, 20): deviations from the means (20/3, 10) are (10/3, 40/3, -50/3) and
    # (10, -20, 10), so r = -400 / sqrt(4200/9 x 600) = -0.756.
    assert ramps[0] == pytest.approx(-400 / (4200 / 9 * 600) ** 0.5)


def test_ramp_runs_by_day() -> None:
    index = pd.date_range("2025-01-01 01:00", periods=48, freq="h", tz="UTC")
    eia = pd.Series([100.0 + (37 * i) % 50 for i in range(48)], index=index)
    # Day 1: the operator's value for t is EIA's for t + 1 (one hour early); day 2: on time.
    early = pd.Series(eia.to_numpy()[1:25], index=index[:24])
    operator = pd.concat([early, eia.iloc[24:]])
    day = pd.Series([pd.Timestamp("2025-01-01")] * 24 + [pd.Timestamp("2025-01-02")] * 24)
    runs = ramp_runs(eia, operator, day.set_axis(index))
    assert runs["shift"].tolist() == [1, 0]
    assert runs["days"].tolist() == [1, 1]
