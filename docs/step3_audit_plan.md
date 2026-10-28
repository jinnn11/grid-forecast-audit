# Step 3 audit plan (pre-registration)

**Status: approved by the user on 2026-10-28, with the answers folded in below. No forecast error
has been computed.** The user commits this file, with the exception-rule fix of the same day,
before any result exists, so the commit date shows the plan came first.

## Data and scope

- Hours: the usable hours of `results/data_quality.md` (R1, R2 with N = 6, R3a, R4, R5 with its
  exemptions from daily and hour-of-day episodes, R3b). Truth: raw demand. Forecast: the
  day-ahead forecast as published in EIA-930.
- Local time: add "Local Time at End of Hour" to `data/processed/balance.parquet`, rebuilt from the
  cached files (no download). Each hour belongs to the local day and hour in which it starts (hour
  end minus one hour). Years, seasons, holidays and hour of day all use local time. Hour of day is
  reported as hour ending 1–24.
- Years: 2016–2025. 2015 and 2026 are half-years and are left out.
- A BA-year is eligible when at least 50% of its hours are usable. From the usable-hour flags
  (no errors used): 53 BAs are eligible in 2025, 50 in every year 2016–2025 (the trend panel,
  which includes all 10 largest BAs), and 49 in both 2019 and 2025 once WACM and SPA (footprint
  changes in 2022 and 2023) are left out. The hour-of-day fix to the exception rule changes none
  of these counts.
- CHPD and TEPC stay in. Their results are marked "published forecast inconsistent with demand"
  for 2016-01 to 2021-06 (CHPD, about 2.4x) and 2018-10 to 2019-05 (TEPC, 1.2–2.2x).
- No result is used to change a rule or threshold. Diagnostics (Q5) never change the main
  results; anything they suggest is brought to the user.

## Metrics

Per BA and period, over usable hours, with error e = forecast − demand:

| Metric | Definition | Role |
| :-- | :-- | :-- |
| MAPE | mean of \|e\| / demand, in % | Primary (what operators report) |
| WAPE | Σ\|e\| / Σ demand, in % | Secondary |
| Bias | Σe / Σ demand, in % (positive: over-forecast); also mean e in MW | Secondary |
| Skill | 1 − MAPE(forecast) / MAPE(naive), on the same hours | Secondary |

- Naive forecast: demand 24 hours earlier, matched by timestamp, taken only from an hour whose
  demand passes R1, R2, R4 and R5. Forecast and naive are scored on the same hours. Skill below
  0 means the BA loses to the naive forecast.
- Caveat: the naive value for late hours may not be known when the day-ahead forecast is issued,
  so the naive forecast is a demanding benchmark.
- Summaries: the median across eligible BAs, plus one national figure, Σ\|e\| / Σ demand over
  every eligible BA's usable hours (demand-weighted). MAPE can be large for very small BAs; the
  median keeps a few such BAs from driving the summary.

## Questions

**Q1. How accurate is each BA's published day-ahead forecast in 2025?**
Table of the 53 eligible BAs: MAPE, WAPE, bias, skill and usable hours, sorted by MAPE, with the
median across BAs and the national figure. Figure 1.

**Q2. Is accuracy getting worse?**
- Per BA: yearly MAPE 2016–2025. The trend is the Theil–Sen slope (percentage points per year)
  over the BA's eligible years, for BAs with at least 8. A BA is "worse" or "better" when the
  two-sided Mann–Kendall test gives p < 0.05, otherwise "no clear trend". We report how many
  BAs fall in each group and how many would by chance (5% of those tested).
- Across BAs: the median MAPE of the 50-BA panel per year, with the same slope and test, and the
  national figure per year on the same panel. Figure 2.

**Q3. When do forecasts miss most?** Over 2016–2025:
- Season (DJF, MAM, JJA, SON) and hour of day: each BA's MAPE per season and hour, then the median
  across BAs per cell. Figure 3.
- Holidays (table below): each BA's MAPE on holiday days against the same local weekday one and
  two weeks before and after, leaving out other holidays and events. We report the ratio, as the
  median across BAs per holiday.
- Extreme-weather events (table below), for the listed BAs: MAPE and bias in the event window,
  against the same BA's hours in the 14 days before and after the window (leaving out holidays
  and other events). We report the ratio per event and BA, and the median across the event's BAs.
- Second check (approved; uses demand only): extreme-demand days. These are days whose daily
  peak is above the BA's 99th percentile of daily peaks within that season of that year, so
  that demand growth does not push the extremes into recent years. December counts with the
  following January and February. The daily peak is the highest demand over the day's usable
  hours, and days with fewer than 20 usable hours are skipped. With about 90 days per season,
  this is in practice each season's highest day. Each is compared with the BA's other days in
  the same season and year. It covers every year and BA, which a list of named events cannot.

**Q4. Did errors grow more where demand grew fastest?**
For the 49 BAs: x = mean demand over usable hours, 2025 / 2019 − 1; y = MAPE 2025 − MAPE 2019,
in percentage points. Spearman rank correlation, with a two-sided permutation p-value (10,000
permutations, fixed seed). Figure 4.

**Q5. How many BAs lose to the naive forecast each year?**
Per year 2016–2025: the number and share of eligible BAs with skill below 0, and which BAs they
are (table, no figure). For any of the 10 largest BAs among them:
1. Checks inside the EIA-930 data (no download):
   - the repeated-forecast share;
   - whether shifting the forecast by ±1 or ±24 hours lowers its MAPE (a sign of misaligned
     hours or a stale series);
   - R5 flags and BA events that year;
   - whether the loss is concentrated in particular months or hours.
2. Compare a few weeks against the operator's own published load and day-ahead forecast.
   Candidate sources: CAISO OASIS, SPP Marketplace, ERCOT MIS, PJM Data Miner 2, MISO market
   reports, NYISO MIS and ISO-NE ISO Express. We know of no public hourly forecast archive for
   SOCO, TVA or FPL. **We ask before downloading anything.**

## Holidays

A holiday day is the actual date, plus the observed weekday when the holiday falls on a weekend
(in brackets). Dates come from the federal calendar (pandas `USFederalHolidayCalendar`), plus
the day after Thanksgiving, Christmas Eve and New Year's Eve.

| Holiday | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| New Year's Day | 01-01 | 01-01 (01-02) | 01-01 | 01-01 | 01-01 | 01-01 | 01-01 (2021-12-31) | 01-01 (01-02) | 01-01 | 01-01 |
| Memorial Day | 05-30 | 05-29 | 05-28 | 05-27 | 05-25 | 05-31 | 05-30 | 05-29 | 05-27 | 05-26 |
| Independence Day | 07-04 | 07-04 | 07-04 | 07-04 | 07-04 (07-03) | 07-04 (07-05) | 07-04 | 07-04 | 07-04 | 07-04 |
| Labor Day | 09-05 | 09-04 | 09-03 | 09-02 | 09-07 | 09-06 | 09-05 | 09-04 | 09-02 | 09-01 |
| Thanksgiving Day | 11-24 | 11-23 | 11-22 | 11-28 | 11-26 | 11-25 | 11-24 | 11-23 | 11-28 | 11-27 |
| Day after Thanksgiving | 11-25 | 11-24 | 11-23 | 11-29 | 11-27 | 11-26 | 11-25 | 11-24 | 11-29 | 11-28 |
| Christmas Eve | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 | 12-24 |
| Christmas Day | 12-25 (12-26) | 12-25 | 12-25 | 12-25 | 12-25 | 12-25 (12-24) | 12-25 (12-26) | 12-25 | 12-25 | 12-25 |
| New Year's Eve | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 | 12-31 |

## Extreme-weather events

**Selection rule:** a weather-driven event in 2016–2025 that meets one of these:

- (a) it was the subject of a joint FERC–NERC inquiry or review;
- (b) it made an operator shed firm load or declare an Energy Emergency Alert (EEA) at level 2
  or 3;
- (c) it was a US hurricane landfall at Category 3 or above.

Events under (b) were found by searching public reports and may not be complete; the
extreme-demand days in Q3 are the complete, systematic check.

**Windows (local dates):** the source's event span where it gives one, otherwise the emergency
days plus one day either side. For hurricanes, the day before landfall to three days after.

**BAs:** those named in the source, plus BAs in the affected area (our judgment from geography).

| # | Event | Window | Criterion | BAs | Source |
| --: | :-- | :-- | :-- | :-- | :-- |
| 1 | South Central US cold | 2018-01-16 to 01-18 | (a) | MISO, SWPP, TVA, AECI | [FERC–NERC report, July 2019](https://www.ferc.gov/legal/staff-reports/2019/07-18-19-ferc-nerc-report.pdf) (event of Jan 17) |
| 2 | Polar vortex | 2019-01-29 to 02-01 | (b) MISO EEA 2, Jan 30 | MISO, PJM, SWPP, AECI | [MISO IMM winter 2019 report](https://potomaceconomics.com/wp-content/uploads/2019/03/IMM-Quarterly-Report_Winter-2019_Final.pdf) |
| 3 | Winter Storm Uri | 2021-02-13 to 02-20 | (a), (b) | ERCO, SWPP, MISO, AECI, SPA | [FERC–NERC report, Nov 2021](https://nerc.com/pa/rrm/ea/Documents/February_2021_Cold_Weather_Report.pdf) (extreme-cold phase Feb 14–19) |
| 4 | California heat wave | 2020-08-13 to 08-16 | (b) CAISO rotating outages, Aug 14–15 | CISO, BANC, LDWP, IID, TIDC | [CAISO–CPUC–CEC root cause analysis](https://www.caiso.com/documents/preliminary-root-cause-analysis-rotating-outages-august-2020.pdf) |
| 5 | Pacific Northwest heat dome | 2021-06-27 to 07-01 | (b) Avista rotating outages, Jun 28–30 | AVA, BPAT, PSEI, SCL, TPWR, PGE, PACW, CHPD, DOPD, GCPD | [Avista release](https://investor.avistacorp.com/node/25381); [PBS/AP](https://www.pbs.org/newshour/nation/rolling-blackouts-hit-parts-of-u-s-northwest-amid-heat-wave) |
| 6 | Western heat wave | 2022-09-05 to 09-07 | (b) CAISO EEA 3, Sep 6 | CISO, BANC, LDWP, IID, TIDC | [EIA Today in Energy](https://www.eia.gov/todayinenergy/detail.php?id=54039) |
| 7 | Winter Storm Elliott | 2022-12-21 to 12-26 | (a), (b) TVA and Duke load shed | PJM, MISO, TVA, DUK, CPLE, CPLW, SOCO, LGEE, SC, SCEG, AECI, NYIS, ISNE, SWPP | [FERC–NERC release, Sep 2023](https://www.nerc.com/news/Headlines%20DL/Elliott%20report%20release%20092123.pdf) |
| 8 | Texas heat | 2023-09-05 to 09-07 | (b) ERCOT EEA 2, Sep 6 | ERCO | [ERCOT release](https://www.ercot.com/news/release/2023-09-06-ercot-has-initiated) |
| 9 | Winter Storms Gerri and Heather | 2024-01-10 to 01-17 | (a) | ERCO, SWPP, MISO, PJM, TVA, AECI, BPAT, PGE, PACW | [FERC–NERC review](https://ferc.gov/news-events/news/january-2024-arctic-storms-review-finds-no-major-gas-electric-performance-problems) |
| 10 | Hurricane Harvey (Cat 4, landfall Aug 25) | 2017-08-24 to 08-28 | (c) | ERCO, MISO | NHC Tropical Cyclone Report |
| 11 | Hurricane Irma (Cat 4, Sep 10) | 2017-09-09 to 09-13 | (c) | FPL, FPC, TEC, JEA, FMPP, TAL, GVL, SEC, HST, SOCO | NHC Tropical Cyclone Report |
| 12 | Hurricane Michael (Cat 5, Oct 10) | 2018-10-09 to 10-13 | (c) | SOCO, TAL, AEC, FPC | NHC Tropical Cyclone Report |
| 13 | Hurricane Laura (Cat 4, Aug 27) | 2020-08-26 to 08-30 | (c) | MISO | NHC Tropical Cyclone Report |
| 14 | Hurricane Zeta (Cat 3, Oct 28) | 2020-10-27 to 10-31 | (c) | MISO, SOCO | NHC Tropical Cyclone Report |
| 15 | Hurricane Ida (Cat 4, Aug 29) | 2021-08-28 to 09-01 | (c) | MISO | NHC Tropical Cyclone Report |
| 16 | Hurricane Ian (Cat 4, Sep 28) | 2022-09-27 to 10-01 | (c) | FPL, TEC, FPC, FMPP, SEC, JEA, GVL | NHC Tropical Cyclone Report |
| 17 | Hurricane Idalia (Cat 3, Aug 30) | 2023-08-29 to 09-02 | (c) | FPC, TAL, SEC, GVL, JEA, SOCO | NHC Tropical Cyclone Report |
| 18 | Hurricane Helene (Cat 4, Sep 26) | 2024-09-25 to 09-29 | (c) | FPC, TAL, TEC, SEC, GVL, JEA, SOCO, DUK, CPLE, CPLW, SC, SCEG | NHC Tropical Cyclone Report |
| 19 | Hurricane Milton (Cat 3, Oct 9) | 2024-10-08 to 10-12 | (c) | FPC, TEC, FPL, FMPP, SEC, JEA, GVL, HST | NHC Tropical Cyclone Report |

**Considered and not added.** They do not meet the rule, and the user decided on 2026-10-28 not
to add them: adding notable cases that fail the rule would be cherry-picking, and the
extreme-demand days catch them systematically.

- January 2025 Arctic outbreak: PJM set an all-time winter peak on Jan 22, but issued alerts
  only, with no EEA 2 or higher ([PJM cold weather update](https://www.pjm.com/-/media/DotCom/committees-groups/committees/oc/2025/20250306/20250306-item-15---january-2025-cold-weather-update.pdf)).
- June 2025 Eastern heat wave: PJM peaked at about 161.8 GW on Jun 23 and MISO declared an EEA 1
  ([Power Engineering](https://www.power-eng.com/business/policy-and-regulation/grid-operators-issue-emergency-alerts-in-response-to-early-summer-heat-wave/)).
- Hurricanes Beryl (2024) and Florence (2018): both Category 1 at landfall.

We found no Category 3+ US landfall in 2016, 2019 or 2025. The landfall dates and categories will
be checked against the NHC reports when `data/weather_events.csv` is built.

## Figures

1. Q1: dot plot of 2025 MAPE per BA, sorted, with the naive MAPE as a second marker and lines for
   the median across BAs and the national figure.
2. Q2: yearly MAPE 2016–2025, a thin line per panel BA with the median across BAs in bold and the
   national figure dashed.
3. Q3: heatmap of the median MAPE across BAs by season (rows) and local hour ending (columns).
   Holidays and events go in tables.
4. Q4: scatter of demand change (x) against MAPE change (y), 2019 to 2025, one point per BA, with
   the 10 largest BAs labelled and Spearman's ρ in the caption.

Each figure is a PNG with a CSV of the data it plots. Q5 is a table.

## Robustness

One table next to the main results. Columns: median 2025 MAPE across BAs; national 2025 figure;
panel-median trend slope 2016–2025; BAs worse and better (Q2); Spearman ρ (Q4); BAs losing to
the naive forecast in 2025 (Q5). Rows:

| Variant | Change from the main run |
| :-- | :-- |
| Main | — |
| EIA adjusted demand | Adjusted demand is the truth; all rules re-applied to it, except R4 |
| Without R5 | No energy-balance rule |
| R2 with N = 3 | Repeated-demand runs of 3 hours or more dropped |
| R2 with N = 12 | Only runs of 12 hours or more dropped |
| Repeated forecasts dropped | R2b (forecast runs of 6 hours or more) applied |

## Build

- `balance.py` and `build_history.py`: local time column; parquet rebuilt from cached files.
- `data/weather_events.csv` (tracked): the event table above, and the holiday rule in code.
- `metrics.py` (pure): errors, naive forecast, MAPE, WAPE, bias, skill.
- `stats.py` (pure, numpy only): Theil–Sen slope, Mann–Kendall test, Spearman correlation with a
  permutation p-value. No new dependency for these.
- `calendar.py` (pure): local day and hour, seasons, holidays, event windows and baselines.
- `audit.py`: `results/audit.md`, `results/figures/*.png` and their CSVs.
- matplotlib is added for the figures (approved; new dependency, for the PNGs only).
- Every metric and statistic gets tests with hand-checked values.
