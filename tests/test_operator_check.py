import pandas as pd

from grid_audit.operator_check import days_at, signed


def test_days_at_counts_days_in_a_span() -> None:
    runs = pd.DataFrame(
        {
            "first": pd.to_datetime(["2025-01-01", "2025-01-11", "2025-01-12", "2025-02-01"]),
            "last": pd.to_datetime(["2025-01-10", "2025-01-11", "2025-01-31", "2025-02-05"]),
            "shift": pd.array([1, pd.NA, 1, 0], dtype="Int64"),
            "days": [10, 1, 20, 5],
        }
    )
    # Jan 1-31: 10 + 20 = 30 days at +1 h of 31 days with data; the Feb run is outside.
    assert days_at(runs, 1, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-31")) == (30, 31)
    # Aligned at no shift: 1 day of 31.
    assert days_at(runs, None, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-31")) == (1, 31)


def test_signed() -> None:
    assert signed(-6.91) == "6.9% below"
    assert signed(0.25) == "0.2% above"
