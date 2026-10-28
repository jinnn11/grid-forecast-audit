import pandas as pd
import pytest

from grid_audit.truth import (
    balance_by_ba,
    balance_gap,
    eia_changed,
    eia_relations,
    exemption_checks,
    imbalance_episodes,
    imbalanced,
    in_episodes,
    level_change,
    share_by_half_year,
    sign_fit,
    stretch_coverage,
)

NAN = float("nan")
F1, F2 = "EIA930_BALANCE_2015_Jul_Dec.csv", "EIA930_BALANCE_2016_Jan_Jun.csv"
COLUMNS = ["demand", "demand_imputed", "demand_adjusted", "net_generation", "interchange"]

# Hours from 2016-01-01 00:00 UTC. Columns: demand, imputed, adjusted, net generation, interchange.
# A, h0-h2 from F1 and h3-h5 from F2:
#   h0  100   -    100   150   50    balances (100 = 150 - 50)
#   h1   -5   90    90   140   50    EIA replaced a negative value; gap -5 - 90 = -95
#   h2    -   95    95   145   50    EIA filled a gap
#   h3  100   -    100   120   50    gap 100 - 70 = 30, i.e. 30% of demand
#   h4  100   80    85   150   50    replaced, and adjusted is not the imputed value; gap 0
#   h5  100   -    100   155    -    interchange blank, so the balance cannot be checked
# B, h0-h1 from F1:
#   h0    5   -      5   5.8    0    gap -0.8: over 10% of demand but within the 1 MW tolerance
#   h1    0   -      0     0    0
# C, h0-h2 from F1, no generation or interchange:
#   h0   50   -     55    -     -    adjusted differs from raw with no imputed value
#   h1   20   -      -    -     -    raw demand with no adjusted value
#   h2    -   -     30    -     -    adjusted with neither raw nor imputed
ROWS = {
    "A": [
        (100, NAN, 100, 150, 50),
        (-5, 90, 90, 140, 50),
        (NAN, 95, 95, 145, 50),
        (100, NAN, 100, 120, 50),
        (100, 80, 85, 150, 50),
        (100, NAN, 100, 155, NAN),
    ],
    "B": [(5, NAN, 5, 5.8, 0), (0, NAN, 0, 0, 0)],
    "C": [(50, NAN, 55, NAN, NAN), (20, NAN, NAN, NAN, NAN), (NAN, NAN, 30, NAN, NAN)],
}


@pytest.fixture
def hourly() -> pd.DataFrame:
    start = pd.Timestamp("2016-01-01", tz="UTC")
    frames = []
    for ba, rows in ROWS.items():
        frame = pd.DataFrame(rows, columns=COLUMNS, dtype=float)
        frame.insert(0, "ba", ba)
        frame.insert(1, "utc", [start + pd.Timedelta(hours=h) for h in range(len(rows))])
        frame["source_file"] = [F1 if h < 3 else F2 for h in range(len(rows))]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def flagged(flags: pd.Series, hourly: pd.DataFrame) -> list[str]:
    """'A1'-style labels (BA and hour number) of the flagged rows."""
    start = pd.Timestamp("2016-01-01", tz="UTC")
    picked = hourly[flags]
    return [f"{r.ba}{int((r.utc - start) / pd.Timedelta(hours=1))}" for r in picked.itertuples()]


def test_eia_changed(hourly: pd.DataFrame) -> None:
    assert flagged(eia_changed(hourly), hourly) == ["A1", "A4"]  # A2 was blank, so it was filled


def test_eia_relations(hourly: pd.DataFrame) -> None:
    assert eia_relations(hourly) == {
        "rows": 11,
        "raw": 9,  # A 5, B 2, C 2
        "imputed": 3,  # A1, A2, A4
        "replaced": 2,  # A1, A4
        "replaced_negative": 1,  # A1
        "replaced_zero": 0,
        "replaced_positive": 1,  # A4
        "filled": 1,  # A2
        "adjusted_differs": 3,  # A1 (90 vs -5), A4 (85 vs 100), C0 (55 vs 50)
        "adjusted_differs_without_imputed": 1,  # C0
        "adjusted_is_imputed": 2,  # A1, A2
        "adjusted_not_imputed": 1,  # A4
        "raw_without_adjusted": 1,  # C1
        "adjusted_without_raw_or_imputed": 1,  # C2
    }


def test_balance_gap_and_imbalanced(hourly: pd.DataFrame) -> None:
    gap = balance_gap(hourly)
    assert gap[:2].tolist() == [0, -95]
    assert gap[3] == 30 and gap[4] == 0 and gap[6] == pytest.approx(-0.8)
    blank = [False, False, True, False, False, True] + [False, False] + [True, True, True]
    assert gap.isna().tolist() == blank  # A2, A5 and all of C
    # 10%: A1 (95 > 0.5 MW), A3 (30 > 10 MW). B0 is over 10% of 5 MW but not over 1 MW.
    assert flagged(imbalanced(hourly, 0.10), hourly) == ["A1", "A3"]
    # 50%: A3's 30 MW is under half of 100 MW.
    assert flagged(imbalanced(hourly, 0.50), hourly) == ["A1"]


def test_sign_fit(hourly: pd.DataFrame) -> None:
    fit = sign_fit(hourly)
    # Only A has interchange over 1 MW: A0, A1, A3, A4. Minus fits A0 and A4; plus fits none
    # (A0: 100 vs 150 + 50 = 200). B's interchange is 0 and C's is blank.
    assert list(fit.index) == ["A"]
    assert fit.loc["A"].tolist() == [4, 50.0, 0.0]


def test_balance_by_ba(hourly: pd.DataFrame) -> None:
    table = balance_by_ba(hourly, 0.10)
    assert list(table.index) == ["A", "B", "C"]
    # A: checkable A0, A1, A3, A4; within 1 MW A0, A4; gaps over positive demand 0, 30, 0
    # (A1's demand is negative), median 0%; imbalanced A1, A3.
    assert table.loc["A"].tolist() == [4, 50.0, 0.0, 50.0]
    # B: both hours within 1 MW; median gap over B0 only, -0.8 / 5 = -16%; none imbalanced.
    assert table.loc["B"].tolist() == pytest.approx([2, 100.0, -16.0, 0.0])
    # C reports demand but has no checkable hour.
    assert table.loc["C", "hours"] == 0 and table.loc["C"].iloc[1:].isna().all()


def test_share_by_half_year(hourly: pd.DataFrame) -> None:
    share = share_by_half_year(hourly, eia_changed(hourly), hourly["demand"].notna())
    assert share.loc["A", "2015 H2"] == pytest.approx(50.0)  # A1 of A0, A1
    assert share.loc["A", "2016 H1"] == pytest.approx(100 / 3)  # A4 of A3, A4, A5
    assert share.loc["B", "2015 H2"] == 0.0
    assert pd.isna(share.loc["B", "2016 H1"])  # B has no rows then
    assert share.loc["C", "2015 H2"] == 0.0  # C0, C1


def test_stretch_coverage(hourly: pd.DataFrame) -> None:
    stretches = {"all of A": hourly["ba"].eq("A"), "negative": hourly["demand"].lt(0)}
    table = stretch_coverage(
        hourly, stretches, eia_changed(hourly), imbalanced(hourly, 0.10)
    ).set_index("stretch")
    # A: raw demand in A0, A1, A3, A4, A5; changed A1, A4 (2 of 5); checkable 4 of 5;
    # imbalanced A1, A3 (2 of 4).
    assert table.loc["all of A"].tolist() == [5, 40.0, 80.0, 50.0]
    assert table.loc["negative"].tolist() == [1, 100.0, 100.0, 100.0]


def utc(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz="UTC")


def test_imbalance_episodes() -> None:
    # X has hours at 06:00 and 18:00 on 2016-01-01 to 01-18. Out-of-balance hours per day:
    # days 1-3 both, day 4 one of two (share 0.5), day 7 both, day 16 both, and on day 18 the
    # only checkable hour (18:00 has no interchange, so only 06:00 counts). Y is never out.
    rows, flags = [], []
    bad = {1: 2, 2: 2, 3: 2, 4: 1, 7: 2, 16: 2, 18: 1}
    for ba in ("X", "Y"):
        for day in range(1, 19):
            for n, hour in enumerate((6, 18)):
                interchange = float("nan") if (day, hour) == (18, 18) else 0.0
                rows.append((ba, utc(f"2016-01-{day:02d} {hour:02d}:00"), 1.0, 1.0, interchange))
                flags.append(ba == "X" and n < bad.get(day, 0))
    hourly = pd.DataFrame(rows, columns=["ba", "utc", "demand", "net_generation", "interchange"])
    unbalanced = pd.Series(flags)

    def spans(**kwargs: float) -> list[tuple[int, int, int]]:
        table = imbalance_episodes(hourly, unbalanced, **kwargs)
        return [(r.start.day, r.end.day, r.days) for r in table.itertuples()]

    # Gap 2: days 4 and 7 have 2 days between them, so 1-7 joins; 16 and 18 have 1 between.
    assert spans(day_share=0.5, gap_days=2) == [(1, 7, 7), (16, 18, 3)]
    assert spans(day_share=0.5, gap_days=1) == [(1, 4, 4), (7, 7, 1), (16, 18, 3)]
    # Share 0.6 drops day 4, so 3 and 7 have 3 days between them.
    assert spans(day_share=0.6, gap_days=2) == [(1, 3, 3), (7, 7, 1), (16, 18, 3)]
    assert list(imbalance_episodes(hourly, unbalanced)["ba"].unique()) == ["X"]


def windows(ba: str, before: tuple, after: tuple, months: int = 3) -> pd.DataFrame:
    """Hourly rows for `months` months from 2016-01-01 and from 2017-01-01, with constant
    (demand, net generation, interchange) values `before` and `after`."""
    frames = []
    for first, values in ((utc("2016-01-01"), before), (utc("2017-01-01"), after)):
        hours = pd.date_range(
            first, first + pd.DateOffset(months=months), freq="h", inclusive="left"
        )
        frame = pd.DataFrame(
            [values] * len(hours), columns=["demand", "net_generation", "interchange"]
        )
        frames.append(frame.assign(ba=ba, utc=hours))
    return pd.concat(frames, ignore_index=True)


def test_level_change() -> None:
    rows = windows("G", before=(100, 150, 50), after=(105, 130, 50), months=1)
    rows.loc[800, "net_generation"] = 1e9  # one absurd hour (in January 2017) moves no median
    change = level_change(rows, utc("2017-01-01"), months=1)
    # Demand 105 vs 100: +5%. Net generation 130 vs 150: -20 MW, -20% of 100 MW. Interchange 0.
    assert change == pytest.approx(
        {"demand_change": 0.05, "generation_shift": -0.20, "interchange_shift": 0.0}
    )
    # January 2017 has 744 hours; with interchange blank in 400 of them only 344 are checkable,
    # under half, so nothing is compared.
    rows.loc[744 : 744 + 399, "interchange"] = float("nan")
    assert all(pd.isna(v) for v in level_change(rows, utc("2017-01-01"), months=1).values())


def test_exemption_checks() -> None:
    # Before: demand 100, net generation 150, interchange 50 in Jan-Mar 2016, for every BA
    # except N, which has no rows then.
    n = windows("N", (100, 150, 50), (105, 130, 50))
    hourly = pd.concat(
        [
            windows("G", (100, 150, 50), (105, 130, 50)),  # demand +5%, generation -20%
            windows("D", (100, 150, 50), (130, 180, 50)),  # demand +30%
            windows("S", (100, 150, 50), (102, 155, 50)),  # demand +2%, generation +5%
            windows("T", (100, 150, 50), (95, 130, 70)),  # demand -5%, both shift by 20 MW
            windows("E", (100, 150, 50), (105, 130, 50)),  # like G, but a short episode
            n[n["utc"].ge(utc("2017-01-01"))],
        ],
        ignore_index=True,
    )
    episodes = pd.DataFrame(
        {
            "ba": ["G", "D", "S", "T", "E", "N"],
            "start": utc("2017-01-01"),
            "end": utc("2017-03-01"),
            "days": [60, 60, 60, 60, 30, 60],
        }
    )
    checks = exemption_checks(hourly, episodes).set_index("ba")
    assert list(checks.index) == ["G", "D", "S", "T", "N"]  # E is not longer than 30 days
    assert checks["exempt"].tolist() == [True, False, False, True, False]
    assert checks["attributed_to"].tolist() == [
        "net generation",
        "",
        "",
        "net generation and interchange",
        "",
    ]
    assert checks["reason"].tolist() == [
        "",
        "demand changed",
        "no other series shifted",
        "",
        "too little data to compare",  # N has no rows a year earlier
    ]
    assert checks.loc["G", "generation_shift"] == pytest.approx(-0.20)


def test_in_episodes() -> None:
    hourly = pd.DataFrame(
        {
            "ba": ["X", "X", "X", "X", "Y"],
            "utc": [
                utc(t)
                for t in (
                    "2016-01-01 23:00",
                    "2016-01-02 00:00",
                    "2016-01-03 23:00",
                    "2016-01-04 00:00",
                    "2016-01-02 12:00",
                )
            ],
        }
    )
    episodes = pd.DataFrame({"ba": ["X"], "start": [utc("2016-01-02")], "end": [utc("2016-01-03")]})
    assert in_episodes(hourly, episodes).tolist() == [False, True, True, False, False]
