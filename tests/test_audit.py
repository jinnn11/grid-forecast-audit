import pandas as pd
import pytest

from grid_audit.audit import (
    LOAD_SHEDDING_PATH,
    WEATHER_EVENTS_PATH,
    Run,
    audit_run,
    ba_trends,
    charging_counts,
    cut_demand,
    demand_growth,
    event_effects,
    extreme_day_effects,
    holiday_effects,
    hour_ranges,
    loss_checks,
    marked,
    marked_year,
    naive_source,
    panel_bas,
    read_load_shedding,
    read_weather_events,
    shed_ids,
    usable_after,
    variant_rules,
    verified_corrections,
    year_ranks,
)
from grid_audit.calendar import holiday_days, local_hours
from grid_audit.data_quality import Applied

NAN = float("nan")


def frame(ba: str, hours: int, start: str = "2016-01-01 01:00") -> pd.DataFrame:
    """`hours` consecutive hours for one BA; local time equals UTC (offset 0)."""
    utc = pd.date_range(start, periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "ba": ba,
            "utc": utc,
            "local": utc.tz_localize(None),
            "demand": 100.0,
            "forecast": 110.0,
        }
    )


def test_usable_after_counts_r3b_last() -> None:
    # A: 8,762 hours, a rule drops 2 -> 8,760 left, enough for R3b (8,760). B: 8,761 hours, 2
    # dropped -> 8,759, so R3b drops all of B.
    hourly = pd.concat([frame("A", 8_762), frame("B", 8_761)], ignore_index=True)
    rule = pd.Series(False, index=hourly.index)
    rule.iloc[[0, 1, 8_762, 8_763]] = True
    usable = usable_after(hourly, {"X": rule})
    assert usable.groupby(hourly["ba"]).sum().to_dict() == {"A": 8_760, "B": 0}


def test_naive_source_uses_demand_rules_only() -> None:
    # Rows 0-5 are each flagged by one rule; row 6 has demand -1 and row 7 is clean.
    hourly = pd.DataFrame({"demand": [100.0] * 6 + [-1.0, 100.0]})
    names = ["R1", "R2 (N = 3)", "R3a", "R4", "R5", "R2b (N = 6)"]
    rules = {name: pd.Series([i == row for i in range(8)]) for row, name in enumerate(names)}
    # R1's forecast part, R3a and R2b do not stop an hour's demand being the naive value; R2,
    # R4, R5 and demand <= 0 do.
    assert naive_source(hourly, rules).tolist() == [
        True,
        False,
        True,
        False,
        False,
        True,
        False,
        True,
    ]


def test_variant_rules() -> None:
    # Demand 5, 5, 5, 5, then distinct values: one run of 4 equal hours.
    hourly = frame("A", 10)
    hourly["demand"] = [5.0, 5.0, 5.0, 5.0, 1.0, 2.0, 3.0, 4.0, 6.0, 7.0]
    none = pd.Series(False, index=hourly.index)
    r5 = none.copy()
    r5.iloc[9] = True
    rules = {"R1": none, "R2 (N = 6)": none, "R3a": none, "R4": none, "R5": r5, "R3b": none}
    variants = variant_rules(hourly, Applied(rules, none, none, pd.DataFrame(), none))
    assert list(variants["Main"]) == ["R1", "R2 (N = 6)", "R3a", "R4", "R5"]
    assert list(variants["Without R5"]) == ["R1", "R2 (N = 6)", "R3a", "R4"]
    # N = 3: the run of 4 drops its last 3 hours; N = 12 drops nothing.
    assert (
        variants["R2 with N = 3"]["R2 (N = 3)"].tolist() == [False, True, True, True] + [False] * 6
    )
    assert not variants["R2 with N = 12"]["R2 (N = 12)"].any()
    assert variants["R2 with N = 3"]["R5"] is r5  # R5 is reused as applied
    # R2b: the forecast (110 throughout) is one run of 10 equal hours; 9 repeat.
    assert int(variants["Repeated forecasts dropped"]["R2b (N = 6)"].sum()) == 9


def test_audit_run_eligibility() -> None:
    # A: every hour of local 2016 (8,784, leap year), all usable; then 10 hours of 2017, of
    # which 4 have a forecast: 40% usable, so 2017 is not eligible. Total usable 8,788 >= 8,760.
    hourly = frame("A", 8_794)
    hourly.loc[8_788:, "forecast"] = NAN
    hourly["demand"] = [100.0 + (k // 24) % 2 * 10 for k in range(len(hourly))]  # 100, 110 by day
    run = audit_run(hourly, local_hours(hourly["local"]), {})
    assert list(run.yearly.index) == [("A", 2016)]
    row = run.yearly.loc[("A", 2016)]
    assert row["hours"] == 8_784
    # Forecast 110 on demand 100 (183 days) and 110 (183 days): MAPE (183 x 24 x 0.1) / 8,784
    # = 5%. The first 24 hours have no demand a day earlier: 8,760 paired.
    assert row["mape"] == pytest.approx(5.0)
    assert row["paired"] == 8_760


def yearly_frame(rows: dict[str, dict[int, tuple[float, float]]]) -> pd.DataFrame:
    """Yearly metrics from {ba: {year: (mape, mean demand)}}, with 10 hours per BA-year."""
    records = [
        {"ba": ba, "year": year, "mape": mape, "demand": 10 * mean, "hours": 10}
        for ba, years in rows.items()
        for year, (mape, mean) in years.items()
    ]
    return pd.DataFrame(records).set_index(["ba", "year"])


def test_trends_panel_and_demand_growth() -> None:
    years = range(2016, 2026)
    yearly = yearly_frame(
        {
            # Rises 1 point a year: S = 45, p = 8.3e-5 -> worse, slope 1.
            "UP": {y: (2.0 + y - 2016, 100.0 + (y == 2025) * 50) for y in years},
            # Falls every year -> better.
            "DOWN": {y: (20.0 - (y - 2016), 200.0) for y in years},
            # 7 years only: not tested, not in the panel.
            "SHORT": {y: (3.0, 50.0) for y in range(2019, 2026)},
            # Left out of Q4 by name.
            "SPA": {y: (5.0, 10.0) for y in years},
        }
    )
    trends = ba_trends(yearly)
    assert sorted(trends.index) == ["DOWN", "SPA", "UP"]
    assert trends.loc["UP", "verdict"] == "worse" and trends.loc["UP", "slope"] == pytest.approx(1)
    assert trends.loc["DOWN", "verdict"] == "better"
    assert trends.loc["SPA", "verdict"] == "no clear trend"  # constant: S = 0
    assert panel_bas(yearly) == ["DOWN", "SPA", "UP"]
    points = demand_growth(yearly)
    assert sorted(points.index) == ["DOWN", "SHORT", "UP"]
    # UP: mean demand 100 in 2019 and 150 in 2025 -> +50%; MAPE 5 -> 11: +6 points.
    assert points.loc["UP", "x"] == pytest.approx(0.5)
    assert points.loc["UP", "y"] == pytest.approx(6.0)


def test_marked() -> None:
    # CHPD is marked 2016-01 to 2021-06; TEPC 2018-10 to 2019-05.
    assert marked_year("CHPD", 2021) and not marked_year("CHPD", 2022)
    assert marked_year("TEPC", 2018) and marked_year("TEPC", 2019)
    assert not marked_year("TEPC", 2020) and not marked_year("PJM", 2018)
    june_30, july_1 = pd.Timestamp("2021-06-30"), pd.Timestamp("2021-07-01")
    assert marked("CHPD", pd.Timestamp("2021-06-27"), july_1)  # heat dome window
    assert not marked("CHPD", july_1, pd.Timestamp("2021-07-05"))
    assert marked("CHPD", june_30, june_30)


def test_hour_ranges() -> None:
    assert hour_ranges([23, 9, 10, 11, 15, 24]) == "9-11, 15, 23-24"
    assert hour_ranges([]) == "none"


def day_hours(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """One scored hour per (ba, day, forecast) with demand 100 and no naive value."""
    hours = pd.DataFrame(rows, columns=["ba", "day", "forecast"])
    hours["day"] = pd.to_datetime(hours["day"])
    return hours.assign(demand=100.0, naive=NAN)


def test_holiday_effects() -> None:
    # Thanksgiving 2025 (Thu Nov 27) against Nov 13, Nov 20, Dec 4 and Dec 11. Dec 11 is an
    # event day for A, so it is left out.
    hours = day_hours(
        [
            ("A", "2025-11-27", 110.0),  # |e| / demand 0.10
            ("A", "2025-11-13", 102.0),  # 0.02
            ("A", "2025-11-20", 98.0),  # 0.02
            ("A", "2025-12-04", 102.0),  # 0.02
            ("A", "2025-12-11", 150.0),  # 0.50, event day
        ]
    )
    events = pd.DataFrame({"id": [1], "ba": ["A"], "day": pd.to_datetime(["2025-12-11"])})
    result = holiday_effects(hours, holiday_days(range(2025, 2026)), events)
    row = result.loc[("Thanksgiving Day", "A")]
    # Holiday MAPE 10%, comparison 2%: ratio 5.
    assert row["holiday"] == pytest.approx(10.0)
    assert row["comparison"] == pytest.approx(2.0)
    assert row["ratio"] == pytest.approx(5.0)


def test_event_effects() -> None:
    # Window Jul 10-11 2025; baseline Jun 26 - Jul 9 and Jul 12-25, without Jul 4 (a holiday).
    hours = day_hours(
        [
            ("A", "2025-07-10", 120.0),  # 0.20, e = +20
            ("A", "2025-07-11", 80.0),  # 0.20, e = -20
            ("A", "2025-07-01", 110.0),  # 0.10, e = +10
            ("A", "2025-07-20", 110.0),  # 0.10, e = +10
            ("A", "2025-07-04", 190.0),  # holiday: left out of the baseline
            ("A", "2025-08-20", 190.0),  # outside both
        ]
    )
    weather = pd.DataFrame(
        {
            "id": [1],
            "first_day": pd.to_datetime(["2025-07-10"]),
            "last_day": pd.to_datetime(["2025-07-11"]),
            "bas": [["A", "B"]],
        }
    )
    events = pd.DataFrame(
        {"id": [1, 1], "ba": ["A", "A"], "day": pd.to_datetime(["2025-07-10", "2025-07-11"])}
    )
    result = event_effects(hours, weather, holiday_days(range(2025, 2026)), events).set_index("ba")
    a = result.loc["A"]
    assert a["window_hours"] == 2 and a["baseline_hours"] == 2
    # Window MAPE 20%, bias (20 - 20) / 200 = 0; baseline MAPE 10%, bias 20 / 200 = +10%.
    assert a["window_mape"] == pytest.approx(20.0) and a["window_bias"] == pytest.approx(0.0)
    assert a["baseline_mape"] == pytest.approx(10.0) and a["baseline_bias"] == pytest.approx(10.0)
    assert a["ratio"] == pytest.approx(2.0)
    assert pd.isna(result.loc["B", "ratio"])  # no hours


def test_extreme_day_effects() -> None:
    # A, summer 2025: three days of 20 hours with peaks 100, 200 and 150, and a fourth day with
    # only 19 hours (skipped). 99th percentile of 100, 150, 200: 150 + 0.98 x 50 = 199, so only
    # the 200 day is extreme.
    rows = []
    for day, demand, forecast, count in [
        ("2025-07-01", 100.0, 105.0, 20),  # 0.05
        ("2025-07-02", 200.0, 220.0, 20),  # 0.10
        ("2025-07-03", 150.0, 157.5, 20),  # 0.05
        ("2025-07-04", 300.0, 450.0, 19),  # skipped
    ]:
        rows += [(day, demand, forecast)] * count
    hours = pd.DataFrame(rows, columns=["day", "demand", "forecast"])
    hours["day"] = pd.to_datetime(hours["day"])
    hours = hours.assign(ba="A", season="JJA", season_year=2025, naive=NAN)
    days, effects = extreme_day_effects(hours)
    assert len(days) == 3 and days["extreme"].tolist() == [False, True, False]
    for season in ("JJA", "All"):
        row = effects.loc[(season, "A")]
        # Extreme-day MAPE 10%, other days 5%: ratio 2.
        assert row["extreme"] == pytest.approx(10.0) and row["other"] == pytest.approx(5.0)
        assert row["ratio"] == pytest.approx(2.0)


def test_loss_checks_finds_an_hour_offset() -> None:
    # Demand cycles 100, 110, 120 over 72 hours; the forecast published for hour t is demand at
    # t + 1, i.e. its hours are labelled one hour early. Scored: the middle 24 hours, where every
    # shift exists.
    hourly = frame("X", 72, start="2025-01-01 01:00")
    cycle = [100.0, 110.0, 120.0]
    hourly["demand"] = [cycle[k % 3] for k in range(72)]
    hourly["forecast"] = [cycle[(k + 1) % 3] for k in range(72)]
    local = local_hours(hourly["local"])
    hours = pd.concat([hourly, local], axis=1).iloc[24:48].assign(naive=NAN)
    none = pd.Series(False, index=hourly.index)
    applied = Applied({"R5": none}, none, none, pd.DataFrame(), none)
    events = pd.DataFrame({"ba": [], "date": pd.to_datetime([]), "event": []})
    checks = loss_checks(
        hourly, local, applied, Run(none, hours, pd.DataFrame()), none, events, "X", 2025
    )
    mape = checks["shift_mape"]
    # Unshifted: errors 100->110, 110->120, 120->100 = 0.1, 0.0909, 0.1667; mean 11.92%. Moved
    # +1 h the forecast matches demand: 0. Moved -1 h: 0.2, 0.0909, 0.0833; mean 12.47%. A
    # 24-hour shift is 8 whole cycles, so it equals the unshifted error.
    assert mape[0] == pytest.approx(11.92, abs=0.01)
    assert mape[1] == pytest.approx(0.0)
    assert mape[-1] == pytest.approx(12.47, abs=0.01)
    assert mape[24] == pytest.approx(mape[0]) and mape[-24] == pytest.approx(mape[0])
    assert checks["best_shift"] == 1
    assert checks["r5_hours"] == 0 and checks["events"] == "none"


def test_year_ranks() -> None:
    # Errors 2016-2025: 3.0 except 2018 = 4.0, 2024 = 3.5 and 2025 = 5.0. Highest first: 2025
    # (1), 2018 (2), 2024 (3).
    values = pd.Series(3.0, index=range(2016, 2026))
    values[2018], values[2024], values[2025] = 4.0, 3.5, 5.0
    assert year_ranks(values) == {2024: 3, 2025: 1}
    # A tie shares the better rank: 2024 equal to 2018 -> both 2.
    values[2024] = 4.0
    assert year_ranks(values) == {2024: 2, 2025: 1}


def test_cut_demand() -> None:
    # The hurricanes (criterion (c)) and the events with documented load shedding. Elliott was
    # unmarked until the user asked on 2026-10-30 for every such event to be marked.
    shed = {3, 7}
    assert cut_demand(3, "(a), (b)", shed)  # Uri
    assert cut_demand(15, "(c)", shed)  # Ida
    assert cut_demand(7, "(a), (b) TVA and Duke load shed", shed)  # Elliott
    assert not cut_demand(8, "(b) ERCOT EEA 2, Sep 6", shed)  # Texas heat, no load shed


def test_load_shedding_file_cites_every_event() -> None:
    shedding = read_load_shedding(LOAD_SHEDDING_PATH)
    weather = read_weather_events(WEATHER_EVENTS_PATH).set_index("id")
    # One row per non-hurricane event, with its name, a verdict, a source URL and a quote.
    assert sorted(shedding["id"]) == sorted(weather.index[weather["criterion"].ne("(c)")])
    assert (shedding["event"] == weather.loc[shedding["id"], "event"].to_numpy()).all()
    assert shedding["load_shed"].isin(["yes", "no"]).all()
    assert shedding["source"].str.startswith("http").all() and shedding["quote"].ne("").all()
    # Every BA named as shedding load is on the event's list.
    for row in shedding.itertuples():
        assert set(row.bas.split()) <= set(weather.loc[row.id, "bas"])
    assert shed_ids(shedding) == {3, 4, 5, 6, 7}


def test_verified_corrections() -> None:
    # CISO inside the last late span (2022-06-16 to 2025-12-02) and SWPP on 2025-05-07.
    ciso_utc = pd.date_range("2025-06-01 10:00", periods=3, freq="h", tz="UTC")
    swpp_utc = pd.DatetimeIndex([pd.Timestamp("2025-05-07 12:00", tz="UTC")])
    hourly = pd.DataFrame(
        {
            "ba": ["CISO"] * 3 + ["SWPP"],
            "utc": ciso_utc.append(swpp_utc),
            "demand": [1.0, 2.0, 3.0, 50.0],
            "forecast": [1.0, 1.0, 1.0, 100.0],
            "demand_imputed": float("nan"),
            "demand_adjusted": [1.0, 2.0, 3.0, 50.0],
        }
    )
    local = pd.DataFrame({"day": pd.to_datetime(["2025-06-01"] * 3 + ["2025-05-07"])})
    spp = pd.Series([90.0], index=swpp_utc)
    corrected, counts = verified_corrections(hourly, local, spp)
    # CISO hours 10-12 take hours 11-12's values; 13:00 is not in the table, so 12:00 is
    # blank. SWPP's forecast becomes SPP's 90.
    assert corrected["demand"].tolist()[:2] == [2.0, 3.0] and pd.isna(corrected["demand"][2])
    assert corrected["forecast"].tolist() == [1.0, 1.0, 1.0, 90.0]
    assert counts == {"ciso_moved": 3, "ciso_blanked": 1, "swpp_replaced": 1, "swpp_missing": 0}


def test_charging_counts() -> None:
    times = ["2018-06-30 12:00", "2018-07-01 08:00", "2025-06-01 10:00", "2025-06-01 11:00"]
    utc = pd.to_datetime([*times, "2025-06-01 10:00"], utc=True)
    hourly = pd.DataFrame({"ba": ["CISO"] * 4 + ["BANC"], "utc": utc})
    local = pd.DataFrame({"year": [2018, 2018, 2025, 2025, 2025]})
    charge = pd.Series([5.0, 0.0, 100.0], index=utc[:3])
    # June 2018 is before fuel types and BANC is not CISO. Of the three CISO hours left, two
    # have a value (0 and 100) and 2025-06-01 11:00 has none; 2025's mean is 100.
    assert charging_counts(hourly, local, charge) == {
        "with": 2,
        "without": 1,
        "without_recent": 1,  # the 2025 hour
        "mean_final": 100.0,
    }
