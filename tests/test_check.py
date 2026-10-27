import math
from pathlib import Path

import pandas as pd
import pytest

from grid_audit.balance import read_balance
from grid_audit.check import Source, ba_stats, is_go, render_report, result_label, top_ba_checks

SAMPLE = Path(__file__).parent / "data" / "balance_sample.csv"

# Sample design (UTC hours; d = demand, f = forecast):
# BIG, 26 consecutive hours h1..h26. Base d = 1000 (odd h) / 1250 (even h), f = d + 50, except:
#   h5 d blank; h8 f blank; h10 d = 0; h14 d = 1000, f = 1050 (so d and f repeat at h14 and h15);
#   h21 f = 1300 (repeats h20); h22 f = 0; h25 d = 1100, f = 1150.
# SMALL, hours 06:00, 07:00, 08:00, 10:00 (09:00 absent): d = 100, 100, 200, 200;
#   f = 110, 90, 200, 200. The 10:00 values are not "unchanged" because 09:00 is absent.
# GEN, 2 hours with no demand or forecast.
# NEG, hours 06:00, 07:00, 08:00: d = -50, 100, -80; f = 40, -10, -10.


@pytest.fixture(scope="module")
def stats() -> pd.DataFrame:
    return ba_stats(read_balance(SAMPLE))


def test_sorted_by_average_demand(stats: pd.DataFrame) -> None:
    # BIG 1074 MW, SMALL 150 MW, NEG -10 MW, GEN no demand (last).
    assert list(stats.index) == ["BIG", "SMALL", "NEG", "GEN"]


def test_big_stats(stats: pd.DataFrame) -> None:
    big = stats.loc["BIG"]
    # Demand sum: odd h 11 x 1000 + 1100 (h25) = 12100; even h 11 x 1250 + 0 + 1000 = 14750;
    # 26850 over 25 reported hours.
    assert big["avg_demand_mw"] == pytest.approx(1074.0)
    assert big["hours"] == 26
    # Both present in 24 of 26 hours (h5, h8 missing one value).
    assert big["both_present_pct"] == pytest.approx(100 * 24 / 26)
    assert big["demand_missing_pct"] == pytest.approx(100 * 1 / 26)  # h5
    assert big["demand_zero_pct"] == pytest.approx(100 * 1 / 26)  # h10
    assert big["demand_negative_pct"] == pytest.approx(0.0)
    assert big["demand_unchanged_pct"] == pytest.approx(100 * 2 / 26)  # h14, h15
    assert big["forecast_missing_pct"] == pytest.approx(100 * 1 / 26)  # h8
    assert big["forecast_zero_pct"] == pytest.approx(100 * 1 / 26)  # h22
    assert big["forecast_negative_pct"] == pytest.approx(0.0)
    assert big["forecast_unchanged_pct"] == pytest.approx(100 * 3 / 26)  # h14, h15, h21
    # Scored: 24 both-present hours minus h10 (d = 0) = 23.
    assert big["mape_hours"] == 23
    # APE %: 11 hours at 50/1000 = 5 (10 odd + h14), 9 even at 50/1250 = 4, h21 300/1000 = 30,
    # h22 1250/1250 = 100, h25 50/1100 = 50/11. Sum 55 + 36 + 30 + 100 + 50/11 = 2481/11.
    assert big["mape_pct"] == pytest.approx(2481 / 11 / 23)  # 9.806
    # Abs error: 11 x 50 + 9 x 50 + 300 + 1250 + 50 = 2600.
    # Demand: 11 x 1000 + 9 x 1250 + 1000 (h21) + 1250 (h22) + 1100 (h25) = 25600.
    assert big["wape_pct"] == pytest.approx(100 * 2600 / 25600)  # 10.156
    # Naive: only h25 (vs h1 = 1000: 100/1100) and h26 (vs h2 = 1250: 0) have a 24h-earlier value.
    assert big["naive_mape_pct"] == pytest.approx((100 * 100 / 1100 + 0) / 2)  # 4.545


def test_small_stats(stats: pd.DataFrame) -> None:
    small = stats.loc["SMALL"]
    assert small["avg_demand_mw"] == pytest.approx(150.0)  # 600 / 4
    assert small["hours"] == 4
    assert small["both_present_pct"] == pytest.approx(100.0)
    # Only 07:00 repeats 06:00; 10:00 equals 08:00 but 09:00 is absent, so it does not count.
    assert small["demand_unchanged_pct"] == pytest.approx(25.0)
    assert small["forecast_unchanged_pct"] == pytest.approx(0.0)
    # APE %: 10/100, 10/100, 0, 0.
    assert small["mape_pct"] == pytest.approx(5.0)
    assert small["wape_pct"] == pytest.approx(100 * 20 / 600)
    assert math.isnan(small["naive_mape_pct"])  # no hour has demand 24 hours earlier
    assert small["mape_hours"] == 4


def test_negative_values(stats: pd.DataFrame) -> None:
    neg = stats.loc["NEG"]
    assert neg["avg_demand_mw"] == pytest.approx(-10.0)  # (-50 + 100 - 80) / 3
    assert neg["hours"] == 3
    assert neg["both_present_pct"] == pytest.approx(100.0)
    assert neg["demand_negative_pct"] == pytest.approx(100 * 2 / 3)  # 06:00, 08:00
    assert neg["forecast_negative_pct"] == pytest.approx(100 * 2 / 3)  # 07:00, 08:00
    assert neg["demand_zero_pct"] == pytest.approx(0.0)
    assert neg["demand_unchanged_pct"] == pytest.approx(0.0)
    assert neg["forecast_unchanged_pct"] == pytest.approx(100 * 1 / 3)  # 08:00 repeats -10
    # Only 07:00 has demand > 0; its negative forecast is scored: |-10 - 100| / 100 = 110%.
    assert neg["mape_hours"] == 1
    assert neg["mape_pct"] == pytest.approx(110.0)
    assert neg["wape_pct"] == pytest.approx(110.0)


def test_ba_without_demand(stats: pd.DataFrame) -> None:
    gen = stats.loc["GEN"]
    assert math.isnan(gen["avg_demand_mw"])
    assert gen["hours"] == 2
    assert gen["both_present_pct"] == pytest.approx(0.0)
    assert gen["demand_missing_pct"] == pytest.approx(100.0)
    assert gen["forecast_missing_pct"] == pytest.approx(100.0)
    assert gen["mape_hours"] == 0
    assert math.isnan(gen["mape_pct"]) and math.isnan(gen["wape_pct"])


def checks_for(rows: list[tuple[str, float, float, float]]) -> pd.DataFrame:
    stats = pd.DataFrame(rows, columns=["ba", "avg_demand_mw", "both_present_pct", "mape_pct"])
    return top_ba_checks(stats.set_index("ba"))


# Ten largest BAs: P1..P8 pass (P1 at both boundaries, P2 at the top MAPE boundary),
# F9 fails coverage, F10 fails MAPE. S11 is the 11th largest, so it never counts.
TEN_LARGEST = [
    ("P1", 10_000, 95.0, 0.5),
    ("P2", 9_000, 100.0, 10.0),
    ("P3", 8_000, 99.0, 3.0),
    ("P4", 7_000, 99.0, 3.0),
    ("P5", 6_000, 99.0, 3.0),
    ("P6", 5_000, 99.0, 3.0),
    ("P7", 4_000, 99.0, 3.0),
    ("P8", 3_000, 99.0, 3.0),
    ("F9", 2_000, 94.9, 3.0),
    ("F10", 1_000, 99.0, 10.01),
]


def test_go_when_eight_of_ten_largest_pass() -> None:
    checks = checks_for([*TEN_LARGEST, ("S11", 500, 50.0, 50.0)])
    assert list(checks.index) == [ba for ba, *_ in TEN_LARGEST]
    assert checks["passes"].sum() == 8
    assert is_go(checks)


def test_no_go_when_seven_pass() -> None:
    # P8's MAPE drops below 0.5%; a passing 11th BA does not make up for it.
    rows = [("P8", 3_000, 99.0, 0.49) if ba == "P8" else (ba, *v) for ba, *v in TEN_LARGEST]
    checks = checks_for([*rows, ("S11", 500, 99.0, 3.0)])
    assert checks["passes"].sum() == 7
    assert not is_go(checks)


def test_missing_mape_fails_and_no_demand_is_not_ranked() -> None:
    checks = checks_for([("A", 2_000, 99.0, float("nan")), ("B", float("nan"), 0.0, float("nan"))])
    assert list(checks.index) == ["A"]
    assert not checks.loc["A", "mape_ok"]


def test_result_label() -> None:
    assert result_label(True, True) == "pass"
    assert result_label(False, True) == "fails coverage"
    assert result_label(True, False) == "fails MAPE"
    assert result_label(False, False) == "fails coverage and MAPE"


def test_render_report(stats: pd.DataFrame) -> None:
    hourly = read_balance(SAMPLE)
    source = Source(
        "sample.csv",
        "https://example.invalid/sample.csv",
        "abc123",
        hourly["utc"].min(),
        hourly["utc"].max(),
    )
    report = render_report(stats, source)
    assert "- Hours (end of hour): 2026-01-01 06:00 to 2026-01-02 08:00 UTC" in report
    # Three BAs report demand; SMALL passes, BIG fails coverage (92.3% < 95%), NEG fails MAPE.
    assert "## Verdict: NO-GO" in report
    assert "1 of the 3 largest BAs by average demand pass" in report
    assert "| BIG | 1,074 | 92.3 | 9.81 | fails coverage |" in report
    assert "| SMALL | 150 | 100.0 | 5.00 | pass |" in report
    assert "| NEG | -10 | 100.0 | 110.00 | fails MAPE |" in report
    # Full table rows (values from test_big_stats, test_negative_values, test_ba_without_demand).
    big_row = (
        "| BIG | 1,074 | 26 | 92.3 | 3.8 | 3.8 | 0.0 | 7.7 | 3.8 | 3.8 | 0.0 | 11.5 "
        "| 9.81 | 10.16 | 4.55 | 23 |"
    )
    neg_row = (
        "| NEG | -10 | 3 | 100.0 | 0.0 | 0.0 | 66.7 | 0.0 | 0.0 | 0.0 | 66.7 | 33.3 "
        "| 110.00 | 110.00 | – | 1 |"
    )
    gen_row = (
        "| GEN | – | 2 | 0.0 | 100.0 | 0.0 | 0.0 | 0.0 | 100.0 | 0.0 | 0.0 | 0.0 | – | – | – | 0 |"
    )
    assert big_row in report
    assert neg_row in report
    assert gen_row in report
