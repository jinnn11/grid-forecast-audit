import pandas as pd
import pytest

from grid_audit.metrics import lagged, metrics, naive_forecast, pooled_wape

NAN = float("nan")


def test_metrics_hand_example() -> None:
    hours = pd.DataFrame(
        {
            "ba": ["X", "X", "X", "Y"],
            "demand": [100.0, 200.0, 400.0, 50.0],
            "forecast": [110.0, 180.0, 400.0, 40.0],
            "naive": [90.0, NAN, 420.0, 45.0],
        }
    )
    result = metrics(hours, ["ba"])
    x = result.loc["X"]
    # e = 10, -20, 0; |e| / demand = 0.1, 0.1, 0.
    assert x["hours"] == 3
    assert x["mape"] == pytest.approx(100 * 0.2 / 3)  # 6.667%
    assert x["wape"] == pytest.approx(100 * 30 / 700)  # 4.286%
    assert x["bias_pct"] == pytest.approx(100 * -10 / 700)  # -1.429%: under-forecast
    assert x["bias_mw"] == pytest.approx(-10 / 3)
    # Paired hours (naive present): the 1st and 3rd. Forecast 0.1 + 0; naive |90 - 100| / 100 +
    # |420 - 400| / 400 = 0.1 + 0.05 = 0.15. Skill 1 - 0.1 / 0.15 = 1/3.
    assert x["paired"] == 2
    assert x["naive_mape"] == pytest.approx(7.5)
    assert x["skill"] == pytest.approx(1 / 3)
    # Y: e = -10 on 50, naive -5 on 50: MAPE 20%, naive 10%, skill 1 - 0.2 / 0.1 = -1 (loses).
    y = result.loc["Y"]
    assert y["mape"] == pytest.approx(20.0) and y["skill"] == pytest.approx(-1.0)
    # National: (30 + 10) / (700 + 50) = 5.333%.
    assert pooled_wape(result) == pytest.approx(100 * 40 / 750)


@pytest.fixture
def hourly() -> pd.DataFrame:
    # X: hours 00, 01 on Jan 1 and 00, 01, 02 on Jan 2 (Jan 1 02:00 absent). Y: Jan 1 00:00 only.
    utc = pd.to_datetime(
        [
            "2025-01-01 00:00",
            "2025-01-01 01:00",
            "2025-01-02 00:00",
            "2025-01-02 01:00",
            "2025-01-02 02:00",
            "2025-01-01 00:00",
        ],
        utc=True,
    )
    return pd.DataFrame(
        {
            "ba": ["X"] * 5 + ["Y"],
            "utc": utc,
            "demand": [10.0, 11.0, 12.0, 13.0, 14.0, 99.0],
            "forecast": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )


def test_naive_forecast_matches_by_timestamp(hourly: pd.DataFrame) -> None:
    source = pd.Series([True, False, True, True, True, True])
    naive = naive_forecast(hourly, source)
    # Jan 2 00:00 <- Jan 1 00:00 (10). Jan 2 01:00 <- Jan 1 01:00, not a source hour: NaN.
    # Jan 2 02:00 <- Jan 1 02:00, absent: NaN. Jan 1 hours have no earlier day. Y never takes
    # X's values.
    assert naive.iloc[2] == 10.0
    assert naive.drop(index=2).isna().all()


def test_lagged_both_directions(hourly: pd.DataFrame) -> None:
    every = pd.Series(True, index=hourly.index)
    # Forecast 1 hour earlier: Jan 1 01:00 <- 00:00 (1); Jan 2 01:00 <- 00:00 (3), 02:00 <- 4.
    assert lagged(hourly, "forecast", 1, every).tolist()[:5] == [
        pytest.approx(NAN, nan_ok=True),
        1.0,
        pytest.approx(NAN, nan_ok=True),
        3.0,
        4.0,
    ]
    # -24: the value a day later. Jan 1 00:00 <- Jan 2 00:00 (3); Jan 1 01:00 <- 4.
    later = lagged(hourly, "forecast", -24, every)
    assert later.iloc[0] == 3.0 and later.iloc[1] == 4.0 and later.iloc[2:].isna().all()
