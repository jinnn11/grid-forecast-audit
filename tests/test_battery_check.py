import pandas as pd
import pytest

from grid_audit.battery_check import ba_check


def test_ba_check_on_a_gap_that_is_charging() -> None:
    hours = pd.DataFrame(
        {
            "storage": [-100.0, -200.0, 50.0, 0.0, float("nan")],
            "demand": [1100.0, 1200.0, 1000.0, 1000.0, 5000.0],
            "forecast": 1000.0,
        }
    )
    row = ba_check(hours)
    # The hour without a storage value is left out: 4 hours, 2 of them charging (100, 200).
    assert row["hours"] == 4 and row["charging_hours"] == 2 and row["peak_charging"] == 200.0
    # Mean charging 300 / 4 = 75 against mean demand 4300 / 4 = 1075.
    assert row["charging_pct"] == pytest.approx(100 * 75 / 1075)
    # Demand - forecast is (100, 200, 0, 0): exactly the charging, so b = 1, c = 0, R² = 1.
    assert row["gap_b"] == pytest.approx(1.0) and row["gap_c"] == pytest.approx(0.0, abs=1e-9)
    assert row["gap_r2"] == pytest.approx(1.0)
    # As published: bias (-100 - 200) / 4300; MAPE (100/1100 + 200/1200) / 4. Less charging,
    # demand is 1000 in every hour, so both are 0.
    assert row["bias"] == pytest.approx(100 * -300 / 4300)
    assert row["mape"] == pytest.approx(100 * (100 / 1100 + 200 / 1200) / 4)
    assert row["bias_less"] == pytest.approx(0.0) and row["mape_less"] == pytest.approx(0.0)
