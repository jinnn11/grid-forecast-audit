"""Truth-series checks. Run: uv run python -m grid_audit.truth_check

Writes results/demand_truth.md from data/processed/balance.parquet and data/ba_events.csv: EIA's
own changes to demand, the energy balance, and a proposed truth series and demand-validity rule.
Applies nothing: the proposal is for the user to approve.
"""

from pathlib import Path

import pandas as pd

from grid_audit.check import fmt, markdown_table
from grid_audit.quality import (
    both_present,
    drop_sensitivity,
    half_years,
    largest_bas,
    near_events,
    nonpositive,
    removed_by_ba,
    repeats_in_runs,
    rule_impact,
    short_history,
)
from grid_audit.quality_rules import EVENTS_PATH, PARQUET_PATH, RUN_HOURS, ba_table, read_events
from grid_audit.truth import (
    BALANCE_TOLERANCE_MW,
    R5_SHARE,
    balance_by_ba,
    checkable,
    eia_changed,
    eia_relations,
    imbalanced,
    share_by_half_year,
    sign_fit,
    stretch_coverage,
)

REPORT_PATH = Path("results/demand_truth.md")
R5_SHARES = [0.05, 0.10, 0.20, 0.50]
COMPONENT_BAS = ["BPAT", "CISO"]  # BAs with long imbalances, shown component by component
# Demand-only stretches from data/ba_events.csv: from the step date to the end of the months the
# year-on-year check flagged. End dates are exclusive.
SHIFT_STRETCHES = {
    "CHPD": ("2015-12-18", "2017-01-01"),
    "SEC": ("2017-12-01", "2022-01-01"),
    "TEPC": ("2018-10-06", "2019-01-01"),
    "SPA": ("2023-08-02", "2024-08-01"),
}


def pct_cell(value: float) -> str:
    """A percentage for a dense table: '–' if undefined, '0' if exactly zero, '<0.1' if tiny."""
    if pd.isna(value):
        return "–"
    if value == 0:
        return "0"
    return "<0.1" if abs(value) < 0.05 else f"{value:.1f}"


def half_year_table(share: pd.DataFrame, order: list[str]) -> str:
    rows = [[ba, *(pct_cell(v) for v in share.loc[ba])] for ba in order if ba in share.index]
    return markdown_table(["BA", *map(str, share.columns)], rows)


def known_stretches(hourly: pd.DataFrame, stale: pd.Series) -> dict[str, pd.Series]:
    """The bad stretches found so far, as row flags."""
    ba, utc = hourly["ba"], hourly["utc"]
    stretches = {
        f"SWPP stale demand (R2, N = {RUN_HOURS})": stale & ba.eq("SWPP"),
        f"All stale demand (R2, N = {RUN_HOURS})": stale,
        "Negative demand": hourly["demand"].lt(0),
        "Zero demand": hourly["demand"].eq(0),
    }
    for name, (start, end) in SHIFT_STRETCHES.items():
        inside = utc.ge(pd.Timestamp(start, tz="UTC")) & utc.lt(pd.Timestamp(end, tz="UTC"))
        last = pd.Timestamp(end) - pd.Timedelta(days=1)
        stretches[f"{name} level shift, {start} to {last:%Y-%m-%d}"] = ba.eq(name) & inside
    return stretches


def components_table(hourly: pd.DataFrame, ba: str) -> str:
    rows = hourly[hourly["ba"].eq(ba)]
    by_half = rows.groupby(half_years(rows), observed=True)
    medians = by_half[["demand", "net_generation", "interchange"]].median()
    medians["balance"] = (
        (rows["net_generation"] - rows["interchange"])
        .groupby(half_years(rows), observed=True)
        .median()
    )
    table_rows = [
        [
            str(half),
            fmt(r.demand, 0),
            fmt(r.net_generation, 0),
            fmt(r.interchange, 0),
            fmt(r.balance, 0),
        ]
        for half, r in medians.iterrows()
    ]
    header = ["Half-year", "Demand", "Net generation", "Interchange", "Generation − interchange"]
    return markdown_table(header, table_rows)


def render_truth_report(hourly: pd.DataFrame, events: pd.DataFrame) -> str:
    """The page for checks (a) and (b) and the truth-series proposal."""
    base = both_present(hourly)
    raw = hourly["demand"].notna()
    can_check = checkable(hourly)
    order = list(hourly.groupby("ba")["demand"].mean().dropna().sort_values(ascending=False).index)
    top = largest_bas(hourly)
    period = f"{hourly['utc'].min():%Y-%m-%d %H:%M} to {hourly['utc'].max():%Y-%m-%d %H:%M} UTC"
    r1, r3a = nonpositive(hourly), near_events(hourly, events)
    r2 = repeats_in_runs(hourly, "demand", RUN_HOURS)
    r4, r5 = eia_changed(hourly), imbalanced(hourly, R5_SHARE)
    r3b_approved = short_history(hourly, base & ~r1 & ~r2 & ~r3a)
    before_r3b = base & ~r1 & ~r2 & ~r3a & ~r4 & ~r5
    r3b = short_history(hourly, before_r3b)
    usable = before_r3b & ~r3b
    usable_approved = base & ~r1 & ~r2 & ~r3a & ~r3b_approved
    pct = f"{R5_SHARE:.0%}"

    # (a) EIA's changes
    rel = eia_relations(hourly)
    relation_rows = [
        ["Rows", rel["rows"]],
        ["Raw demand reported", rel["raw"]],
        ["Imputed demand set", rel["imputed"]],
        ["… raw reported, so EIA replaced it", rel["replaced"]],
        ["… … raw value negative", rel["replaced_negative"]],
        ["… … raw value zero", rel["replaced_zero"]],
        ["… … raw value positive", rel["replaced_positive"]],
        ["… raw blank, so EIA filled it", rel["filled"]],
        ["Adjusted differs from raw (both reported)", rel["adjusted_differs"]],
        ["… with the imputed column blank", rel["adjusted_differs_without_imputed"]],
        ["Imputed set and adjusted equals it", rel["adjusted_is_imputed"]],
        ["Imputed set and adjusted differs from it", rel["adjusted_not_imputed"]],
        ["Raw reported, adjusted blank", rel["raw_without_adjusted"]],
        ["Adjusted reported, raw and imputed blank", rel["adjusted_without_raw_or_imputed"]],
    ]
    halves = half_years(hourly)
    by_half = pd.DataFrame(
        {
            "raw": raw.groupby(halves, observed=True).sum(),
            "replaced": r4.groupby(halves, observed=True).sum(),
            "filled": (hourly["demand_imputed"].notna() & ~raw)
            .groupby(halves, observed=True)
            .sum(),
        }
    )
    half_rows = [
        [str(h), fmt(r.raw, 0), pct_cell(100 * r.replaced / r.raw), fmt(r.filled, 0)]
        for h, r in by_half.iterrows()
    ]
    changed_share = share_by_half_year(hourly, r4, raw)
    ever_changed = [ba for ba in order if r4[hourly["ba"].eq(ba)].any()]
    never_changed = [ba for ba in order if ba not in ever_changed]

    # Stretches
    stretches = stretch_coverage(hourly, known_stretches(hourly, r2), r4, r5)
    stretch_rows = [
        [
            s.stretch,
            fmt(s.hours, 0),
            pct_cell(s.changed_pct),
            pct_cell(s.checkable_pct),
            pct_cell(s.imbalanced_pct),
        ]
        for s in stretches.itertuples()
    ]

    # (b) Energy balance
    fit = sign_fit(hourly)
    gap = hourly["demand"] - (hourly["net_generation"] - hourly["interchange"])
    minus_all = 100 * gap.abs().le(BALANCE_TOLERANCE_MW)[can_check].mean()
    plus = hourly["demand"] - (hourly["net_generation"] + hourly["interchange"])
    plus_all = 100 * plus.abs().le(BALANCE_TOLERANCE_MW)[can_check].mean()
    plus_better = sorted(fit.index[fit["plus_pct"] > fit["minus_pct"]])
    by_ba = balance_by_ba(hourly, R5_SHARE)
    ba_rows = [
        [
            ba,
            fmt(r.hours, 0),
            pct_cell(r.within_pct),
            fmt(r.median_gap_pct, 1),
            pct_cell(r.imbalanced_pct),
        ]
        for ba, r in by_ba.reindex([b for b in order if b in by_ba.index]).iterrows()
    ]
    imbalanced_share = share_by_half_year(hourly, r5, can_check)

    # Proposal
    candidates: dict[object, pd.Series] = {s: imbalanced(hourly, s) for s in R5_SHARES}
    sensitivity = drop_sensitivity(hourly, candidates, r1 | r2 | r3a | r4, top)
    sensitivity_rows = [
        [
            f"{r.key:.0%}" + (" (proposed)" if r.key == R5_SHARE else ""),
            fmt(r.removed, 0),
            fmt(r.bas_over_1pct, 0),
            f"{r.top_all_hours} of {len(top)}",
            f"{r.top_present_hours} of {len(top)}",
        ]
        for r in sensitivity.itertuples()
    ]
    rules = {
        "R1": r1,
        f"R2 (N = {RUN_HOURS})": r2,
        "R3a": r3a,
        "R4 (EIA changed)": r4,
        f"R5 (balance, {pct})": r5,
        "R3b (after all the others)": r3b,
    }
    impact_rows = [
        [r.rule, fmt(r.alone, 0), fmt(r.after_earlier, 0), fmt(r.bas, 0)]
        for r in rule_impact(hourly, rules).itertuples()
    ]
    # BAs that R3b drops although they have usable hours (the rest never had any).
    r3b_bas = sorted(set(hourly.loc[r3b, "ba"]) & set(hourly.loc[before_r3b, "ba"]))
    r3b_new = sorted(set(r3b_bas) - set(hourly.loc[r3b_approved, "ba"]))
    unchecked = usable & ~can_check
    r4_extra = base & ~r1 & ~r2 & ~r3a & r4

    lines = [
        "# Demand truth series: EIA's changes and the energy balance\n",
        "**Status: approved by the user on 2026-10-28**: raw demand as the truth with R4, EIA's "
        "adjusted demand as the robustness check, and R5 at 10% for every BA plus an exception "
        "rule for episodes where another series broke (see `results/data_quality.md`). This "
        "page is the record of checks (a) and (b) and the proposal. Neither check uses the "
        "forecast.\n",
        f"- Data: {fmt(len(hourly), 0)} BA-hours from {hourly['ba'].nunique()} BAs, {period}.",
        f"- Approved on 2026-10-28: R1, R2 (N = {RUN_HOURS}), R3a and R3b, as in "
        "`results/quality_rules_proposal.md`.\n",
        "## (a) EIA's changes to demand\n",
        "### How raw, imputed and adjusted demand relate\n",
        markdown_table(["Hours where", "Hours"], [[k, fmt(v, 0)] for k, v in relation_rows]) + "\n",
        f"- Where adjusted differs from raw, the imputed column is set in "
        f"{fmt(rel['adjusted_differs'] - rel['adjusted_differs_without_imputed'], 0)} of "
        f"{fmt(rel['adjusted_differs'], 0)} hours.",
        f"- Where the imputed column is set, adjusted equals it in "
        f"{fmt(rel['adjusted_is_imputed'], 0)} of {fmt(rel['imputed'], 0)} hours.",
        f"- So adjusted demand is raw demand except where the imputed column is set, and the "
        f"imputed column marks every change EIA made. EIA replaced {fmt(rel['replaced'], 0)} "
        f"reported values ({fmt(rel['replaced_negative'], 0)} negative, "
        f"{fmt(rel['replaced_positive'], 0)} positive, {fmt(rel['replaced_zero'], 0)} zero) and "
        f"filled {fmt(rel['filled'], 0)} blank hours.\n",
        "### By half-year, all BAs\n",
        markdown_table(
            ["Half-year", "Hours with raw demand", "EIA replaced (%)", "Blank hours EIA filled"],
            half_rows,
        )
        + "\n",
        "### Share of hours EIA changed, by BA and half-year\n",
        "Percent of the BA's hours with raw demand where EIA replaced the value. '–': no raw "
        "demand that half-year. BAs sorted by average demand.\n",
        half_year_table(changed_share, ever_changed) + "\n",
        f"EIA changed no hour of these BAs ({len(never_changed)}): "
        f"{', '.join(never_changed) or 'none'}.\n",
        "## Do the checks cover the known bad stretches?\n",
        f'"Checkable" hours have net generation and interchange as well as demand. '
        f'"Imbalanced" means demand differs from net generation minus interchange by more than '
        f"{pct} of demand and more than {fmt(BALANCE_TOLERANCE_MW, 0)} MW; its percent is of the "
        "checkable hours. The level-shift windows run from the step date to the end of the "
        "months the year-on-year check flagged (`data/ba_events.csv`).\n",
        markdown_table(
            [
                "Stretch",
                "Hours with raw demand",
                "EIA changed (%)",
                "Checkable (%)",
                f"Imbalanced > {pct} (%)",
            ],
            stretch_rows,
            left_columns=1,
        )
        + "\n",
        "## (b) Energy balance\n",
        "### Sign convention\n",
        f"- {fmt(can_check.sum(), 0)} of {fmt(raw.sum(), 0)} hours with raw demand "
        f"({fmt(100 * can_check.sum() / raw.sum(), 1)}%) also have net generation and "
        "interchange.",
        f"- In those hours demand is within {fmt(BALANCE_TOLERANCE_MW, 0)} MW of net generation "
        f"minus interchange in {fmt(minus_all, 1)}% of hours, and of net generation plus "
        f"interchange in {fmt(plus_all, 1)}%.",
        f"- Per BA, over hours with interchange beyond {fmt(BALANCE_TOLERANCE_MW, 0)} MW, the "
        f"plus sign fits better in {len(plus_better)} of {len(fit)} BAs"
        + (f" ({', '.join(plus_better)})" if plus_better else "")
        + ". So positive interchange is a net export, and demand = net generation − "
        "interchange.\n",
        "### By BA\n",
        "Gap = demand − (net generation − interchange). Median gap over checkable hours with "
        "positive demand.\n",
        markdown_table(
            [
                "BA",
                "Checkable hours",
                f"Within {fmt(BALANCE_TOLERANCE_MW, 0)} MW (%)",
                "Median gap (% of demand)",
                f"Imbalanced > {pct} (%)",
            ],
            ba_rows,
        )
        + "\n",
        f"### Imbalanced hours (> {pct}) by BA and half-year\n",
        "Percent of the BA's checkable hours. '–': no checkable hours that half-year.\n",
        half_year_table(imbalanced_share, [b for b in order if b in imbalanced_share.index]) + "\n",
        "### An imbalance does not say which number is wrong\n",
        "Half-year medians in MW for two BAs with long imbalances.\n",
    ]
    for ba in COMPONENT_BAS:
        if ba in order:
            lines += [f"#### {ba}\n", components_table(hourly, ba) + "\n"]
    lines += [
        "## Proposal\n",
        "### Truth series\n",
        '- Raw demand ("Demand (MW)") is the truth.',
        f"- R4: drop the hours EIA changed (raw reported and imputed set). Adjusted equals raw "
        f"everywhere else, so these are exactly the hours where EIA's series disagrees with "
        f"the raw one. Of its {fmt(r4.sum(), 0)} hours, {fmt(rel['replaced_negative'], 0)} are "
        f"negative values that R1 already drops; {fmt(r4_extra.sum(), 0)} remain after R1-R3a.",
        "- Robustness check: EIA's adjusted demand as the truth.\n",
        "### Demand-validity rule R5\n",
        f"- Drop an hour when demand differs from net generation minus interchange by more than "
        f"{pct} of demand and more than {fmt(BALANCE_TOLERANCE_MW, 0)} MW.",
        f"- Keep hours missing net generation or interchange: the balance cannot be checked "
        f"there, and missing is not wrong ({fmt(unchecked.sum(), 0)} usable hours).",
        f"- {pct} is the go/no-go check's upper bound for a plausible forecast MAPE. A demand "
        "value that disagrees with its own components by more than that cannot judge forecast "
        "errors of that size.\n",
        "Threshold sensitivity. Hours removed are counted after R1, R2, R3a and R4.\n",
        markdown_table(
            [
                "R5 threshold",
                "Hours removed",
                "BAs losing more than 1%",
                "Top-10 BAs with ≥ 95% of all hours usable",
                "Top-10 BAs keeping ≥ 95% of hours with both values",
            ],
            sensitivity_rows,
        )
        + "\n",
        "### Impact, applied in this order\n",
        markdown_table(
            ["Rule", "Hours removed on its own", "Removed after the rules above", "BAs"],
            impact_rows,
        )
        + "\n",
        f"Usable after all rules: {fmt(usable.sum(), 0)} hours "
        f"({fmt(100 * usable.mean(), 1)}% of all BA-hours), against "
        f"{fmt(usable_approved.sum(), 0)} with the approved rules alone.\n",
        f"R3b now counts usable hours after R4 and R5 as well. BAs with usable hours that it "
        f"drops: "
        f"{', '.join(r3b_bas) or 'none'}"
        + (
            f"; new compared with the approved R3b: {', '.join(r3b_new)}."
            if r3b_new
            else "; no BA is added by counting after R4 and R5."
        )
        + "\n",
        f"### BAs R5 ({pct}) removes hours from, on its own\n",
        ba_table(removed_by_ba(hourly, r5)) + "\n",
    ]
    return "\n".join(lines)


def main() -> None:
    hourly = pd.read_parquet(PARQUET_PATH)
    report = render_truth_report(hourly, read_events(EVENTS_PATH))
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
