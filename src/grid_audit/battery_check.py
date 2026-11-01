"""Exploratory, not in the pre-registered plan (user, 2026-10-30): for every BA that reports
battery storage in EIA-930, does its forecast gap track charging the way CISO's does?

Run: uv run python -m grid_audit.battery_check
Writes results/battery_check.md. Reads only cached files; no new downloads.
"""

from pathlib import Path

import pandas as pd

from grid_audit.calendar import local_hours
from grid_audit.check import fmt, markdown_table
from grid_audit.data_quality import apply_rules
from grid_audit.operators import (
    CISO_LATE_SPANS,
    charging_fit,
    demand_moved_back,
    moved_back,
    score,
)
from grid_audit.quality_rules import EVENTS_PATH, PARQUET_PATH, read_events
from grid_audit.storage import all_storage, charging

REPORT_PATH = Path("results/battery_check.md")
YEAR = 2025


def ba_check(hours: pd.DataFrame) -> dict[str, float]:
    """One BA's usable hours with demand, forecast and storage (net generation from storage,
    MW): how its forecast gap relates to charging."""
    hours = hours[hours["storage"].notna()]
    charge = charging(hours["storage"])
    gap = charging_fit(hours["demand"] - hours["forecast"], hours["storage"])
    plain = score(hours["forecast"], hours["demand"])
    less = score(hours["forecast"], hours["demand"] - charge)
    return {
        "hours": len(hours),
        "charging_hours": int(charge.gt(0).sum()),
        "peak_charging": charge.max(),
        "charging_pct": 100 * charge.mean() / hours["demand"].mean(),
        "gap_b": gap["charging"],
        "gap_c": gap["discharging"],
        "gap_r2": gap["r2"],
        "bias": plain["bias"],
        "bias_less": less["bias"],
        "mape": plain["mape"],
        "mape_less": less["mape"],
    }


def checks(hourly: pd.DataFrame, usable: pd.Series, storage: pd.DataFrame) -> pd.DataFrame:
    """ba_check for every BA with a battery value in YEAR's usable hours, and for CISO with its
    other-fuel net generation; where EIA-930 has CISO an hour late, its demand and that column
    are both moved back (results/ciso_check.md)."""
    year = local_hours(hourly["local"])["year"].eq(YEAR)
    rows = hourly[usable & year].merge(storage, on=["ba", "utc"], how="left")
    reporting = rows.groupby("ba")["battery"].count()
    results = {}
    for ba in reporting.index[reporting > 0]:
        part = rows[rows["ba"].eq(ba)].assign(storage=lambda t: t["battery"])
        results[(ba, "Battery storage")] = ba_check(part)
    ciso = demand_moved_back(hourly[hourly["ba"].eq("CISO")], "CISO", CISO_LATE_SPANS)
    other = storage[storage["ba"].eq("CISO")].set_index("utc")["other"].sort_index()
    other = moved_back(other, CISO_LATE_SPANS)
    ciso = ciso[(usable & year)[ciso.index]]
    ciso = ciso.assign(storage=other.reindex(ciso["utc"]).to_numpy())
    results[("CISO", "Other fuel sources")] = ba_check(ciso)
    table = pd.DataFrame.from_dict(results, orient="index").rename_axis(["ba", "column"])
    return table.sort_values("charging_pct", ascending=False)


MIN_CHARGING_PCT = 1.0  # below this share of demand, too little charging to read the gap


def tracks(row: pd.Series) -> bool:
    """A reading for this exploratory table, not a test: the gap moves with charging as CISO's
    does, at least half a MW per MW."""
    return row["gap_b"] >= 0.5


def render(table: pd.DataFrame) -> str:
    rows = [
        [
            ba,
            column,
            fmt(r.hours, 0),
            fmt(r.charging_hours, 0),
            fmt(r.peak_charging, 0),
            fmt(r.charging_pct, 2),
            f"{fmt(r.gap_b, 2)} / {fmt(r.gap_c, 2)} ({fmt(r.gap_r2, 2)})",
            f"{fmt(r.bias, 2)} → {fmt(r.bias_less, 2)}",
            f"{fmt(r.mape, 2)} → {fmt(r.mape_less, 2)}",
        ]
        for (ba, column), r in table.iterrows()
    ]
    readable = table[table["charging_pct"] >= MIN_CHARGING_PCT]
    like = [ba for (ba, _), r in readable.iterrows() if tracks(r)]
    unlike = readable[[not tracks(r) for _, r in readable.iterrows()]]
    worse = [ba for (ba, _), r in unlike.iterrows() if r["mape_less"] > r["mape"]]
    small = [
        ba
        for (ba, _), r in table.iterrows()
        if 0 < r["peak_charging"] and r["charging_pct"] < MIN_CHARGING_PCT
    ]
    silent = [ba for (ba, _), r in table.iterrows() if not r["peak_charging"] > 0]
    rare = " ".join(
        f"{ba} reports charging as large as {fmt(r.peak_charging, 0)} MW but in only "
        f"{fmt(r.charging_hours, 0)} of {fmt(r.hours, 0)} hours, so its battery series is "
        "almost discharge only."
        for (ba, _), r in table.iterrows()
        if ba in small and r["peak_charging"] >= 1000
    )
    unlike_names = [ba for ba, _ in unlike.index]
    return "\n".join(
        [
            "# Battery check: does the forecast gap track charging? (exploratory)\n",
            "**Exploratory, not in the pre-registered plan** (`docs/step3_audit_plan.md`). Asked "
            "by the user on 2026-10-30 after the CISO check found that CAISO's actual load "
            "counts battery charging and its day-ahead forecast does not "
            "(`results/ciso_check.md`). Nothing here changes the audit. No new downloads: "
            "EIA-930's cached BALANCE files only.\n",
            "## Findings\n",
            f"- {len(table) - 1} BAs report `Battery Storage` in EIA-930 in {YEAR}; "
            f"{len(silent)} of them never report charging (no value below 0): "
            f"{', '.join(silent) or 'none'}. CISO leaves that column blank; its row uses "
            "`Other Fuel Sources`, which matches CAISO's own battery output "
            "(`results/ciso_check.md`).",
            f"- Among BAs whose charging is at least {fmt(MIN_CHARGING_PCT, 0)}% of demand, the "
            "forecast gap moves with charging as CISO's does (at least 0.5 MW per MW of "
            f"charging; a reading, not a test) only for {', '.join(like) or 'none'}. It does not "
            f"for {', '.join(unlike_names) or 'none'}; for "
            f"{'all of them' if worse == unlike_names else ', '.join(worse) or 'none'} taking "
            "charging out of demand makes the MAPE worse, "
            "which fits demand that already leaves charging out, as EIA's instructions ask.",
            f"- Too little charging to tell (under {fmt(MIN_CHARGING_PCT, 0)}% of demand): "
            f"{', '.join(small) or 'none'}. {rare}\n",
            "## Per BA\n",
            f"The audit's usable hours in {YEAR} (main run) that have a storage value. Charging: "
            "−(net generation from storage) where it is below 0. Gap: demand − forecast = a + "
            "b × charging + c × discharging, b / c (R²); b near 1 means the gap grows MW for MW "
            "with charging. Arrows: as published → against demand less charging. CISO's demand "
            "and storage column are moved back an hour where EIA-930 has them late.\n",
            markdown_table(
                [
                    "BA",
                    "Storage column",
                    "Hours",
                    "Hours charging",
                    "Peak charging (MW)",
                    "Charging (% of demand)",
                    "Gap b / c (R²)",
                    "Bias (%)",
                    "MAPE (%)",
                ],
                rows,
                left_columns=2,
            )
            + "\n",
        ]
    )


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH)
    usable = apply_rules(hourly, read_events(EVENTS_PATH)).usable
    storage = all_storage()
    REPORT_PATH.write_text(render(checks(hourly, usable, storage)), "utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
