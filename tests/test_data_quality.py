import pandas as pd
import pytest

from grid_audit.data_quality import apply_rules, exemptions_table, render_data_quality

FILES = {
    (2016, 1): "EIA930_BALANCE_2016_Jan_Jun.csv",
    (2016, 2): "EIA930_BALANCE_2016_Jul_Dec.csv",
    (2017, 1): "EIA930_BALANCE_2017_Jan_Jun.csv",
}


@pytest.fixture
def hourly() -> pd.DataFrame:
    # Hours from 2016-01-01 00:00 to 2017-03-31 23:00 UTC: 8,784 in 2016, 2,160 in 2017. With
    # k the hour's index and x = k % 7, consecutive hours never repeat a value.
    # 2016, both BAs: demand 100 + x, net generation 150 + x, interchange 50 (balanced).
    # 2017, G: demand 105 + x, net generation 80 + x: gap 75 MW, out of balance, and net
    #          generation broke while demand barely moved.
    # 2017, D: demand 130 + x, net generation 150 + x: gap 30 MW, out of balance, and demand
    #          moved.
    utc = pd.date_range("2016-01-01", "2017-03-31 23:00", freq="h", tz="UTC")
    x = pd.Series(range(len(utc))) % 7
    late = pd.Series(utc >= pd.Timestamp("2017-01-01", tz="UTC"))
    files = [FILES[(t.year, 1 if t.month <= 6 else 2)] for t in utc]
    frames = []
    for ba, (demand_2017, generation_2017) in {"G": (105, 80), "D": (130, 150)}.items():
        demand = x + late.map({False: 100, True: demand_2017})
        generation = x + late.map({False: 150, True: generation_2017})
        frames.append(
            pd.DataFrame(
                {
                    "ba": ba,
                    "utc": utc,
                    "demand": demand.astype(float),
                    "forecast": demand.astype(float),
                    "demand_imputed": float("nan"),
                    "demand_adjusted": demand.astype(float),
                    "net_generation": generation.astype(float),
                    "interchange": 50.0,
                    "source_file": files,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2017-01-01"], utc=True),
            "ba": ["D"],
            "event": ["demand_level_shift"],
            "basis": ["data only"],
            "evidence": ["D's demand jumped"],
        }
    )


def test_apply_rules(hourly: pd.DataFrame, events: pd.DataFrame) -> None:
    applied = apply_rules(hourly, events)
    # Only R5 drops hours: D's 2,160 hours in 2017. G's are just as out of balance but exempt.
    assert {name: int(flags.sum()) for name, flags in applied.rules.items()} == {
        "R1": 0,
        "R2 (N = 6)": 0,
        "R3a": 0,
        "R4": 0,
        "R5": 2_160,
        "R3b": 0,  # G keeps 10,944 hours and D 8,784, both at least 8,760
    }
    assert int(applied.usable.sum()) == 2 * 10_944 - 2_160
    assert applied.given_back.groupby(hourly["ba"]).sum().to_dict() == {"D": 0, "G": 2_160}
    checks = applied.checks.set_index("ba")
    assert checks["exempt"].to_dict() == {"D": False, "G": True}
    assert checks.loc["D", "reason"] == "demand changed"


def test_exemptions_table(hourly: pd.DataFrame, events: pd.DataFrame) -> None:
    table = exemptions_table(hourly, apply_rules(hourly, events))
    # Medians: Jan-Mar 2016 is 2,184 hours, 312 of each x, so x = 3: demand 103, generation
    # 153. Jan-Mar 2017 starts at x = 8,784 % 7 = 6 and has 2,160 hours; the 1,080th and
    # 1,081st smallest x are both 3, so G's demand is 108 and its generation 83.
    # Demand 108 / 103 - 1 = +4.9%; generation (83 - 153) / 103 = -68.0%; interchange 0.
    assert table.to_dict("records") == [
        {
            "ba": "G",
            "hour_utc": "",  # a daily episode
            "first_day": "2017-01-01",
            "last_day": "2017-03-31",
            "days": 90,
            "hours_given_back": 2_160,
            "compared": "2017-01-01 to 2017-03-31 vs 2016-01-01 to 2016-03-31",
            "demand_change_pct": 4.9,
            "net_generation_shift_pct": -68.0,
            "interchange_shift_pct": 0.0,
            "attributed_to": "net generation",
        }
    ]


def test_render_data_quality(hourly: pd.DataFrame, events: pd.DataFrame) -> None:
    page = render_data_quality(hourly, events, apply_rules(hourly, events))
    assert "- Usable: 19,728 hours, 90.1% of all BA-hours" in page  # 19,728 / 21,888
    assert "| R5 | Demand more than 10%" in page and "| 2,160 | 2,160 | 1 |" in page
    # Both BAs' 2017 hours sit in checked daily episodes, so no hour-of-day episode is searched.
    assert "2 daily and 0 hour-of-day episodes checked; 1 and 0 exempt." in page
    assert "The exemptions give back 2,160 hours" in page
    assert "| G | 2,160 | 0 | 2,160 | 19.7 |" in page  # 2,160 of G's 10,944 hours
    # D's demand: median 133 vs 103, +29.1%; its generation median is 153 both years.
    span = "| 2017-01-01 | 2017-03-31 | 90 | 2,160 |"
    assert f"| D {span} 29.1 | 0.0 | 0.0 | R5 applies: demand changed |" in page
    assert f"| G {span} 4.9 | -68.0 | 0.0 | exempt: net generation |" in page
    assert "| 7 (used) | 2 | 1 | 2,160 |" in page
    # D (higher mean demand) first. D keeps 8,784 of 10,944 rows (80.3%); its shift is marked.
    assert "| D | 100.0 | 100.0 | 0‡ | 80.3 | 8,784 | 0 |" in page
    assert "| G | 100.0 | 100.0 | 100.0 | 100.0 | 10,944 | 0 |" in page
    # Medians across the two BAs: (0 + 100) / 2, (80.26 + 100) / 2, (8,784 + 10,944) / 2.
    assert "| **Median across BAs** | 100.0 | 100.0 | 50.0 | 90.1 | 9,864 | 0 |" in page
    assert "| 2017-01-01 | D | demand_level_shift | data only | ‡ |" in page
    assert "BAs that never report demand (0, no usable hours): none." in page
