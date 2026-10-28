# Proposed data-quality rules

**Status: proposal. No rule has been applied.** `results/data_quality.md` is written only after the rules are approved.

- Data: 6,135,530 BA-hours from 72 BAs, 2015-07-01 05:00 to 2026-07-01 07:00 UTC.
- Baseline: 5,136,224 hours (83.7%) have both demand and forecast. Rules remove hours from this baseline.
- No rule uses forecast error, because that is what the audit measures.

## Rules

| Rule | Drops | Status |
| :-- | :-- | :-- |
| R1 | Hours with demand ≤ 0 or forecast ≤ 0 | Proposed |
| R2 | Hours repeating the previous hour's demand inside a run of at least N consecutive hours with the same value; the first hour is kept | Proposed, N = 6 |
| R3a | A BA's hours within 7 days of one of its events of type start, stop, footprint_change in `data/ba_events.csv` | Proposed |
| R3b | Every hour of a BA with fewer than 8,760 usable hours (one year) after R1-R3a | Proposed |
| R2b | R2 applied to the forecast | Not applied (forecasts are judged as published); reported as a column |

## Impact with N = 6, applied in this order

| Rule | Hours removed on its own | Removed after the rules above | BAs losing hours |
| :-- | --: | --: | --: |
| R1 | 15,939 | 15,939 | 40 |
| R2 (N = 6) | 6,399 | 4,808 | 21 |
| R3a | 2,332 | 2,330 | 9 |
| R3b | 2,831 | 1,288 | 2 |

Usable after all four rules: 5,111,859 hours (83.3% of all BA-hours).

## How many hours make a run (R2)

Hours removed are counted after R1 and R3a. The 10 largest BAs by average demand are PJM, MISO, ERCO, SWPP, SOCO, CISO, NYIS, TVA, FPL, ISNE. "All hours" counts every row the BA has; "hours with both values" counts only rows with demand and forecast, so it isolates the rules.

| N (hours) | Hours removed | BAs losing more than 1% | Top-10 BAs with ≥ 95% of all hours usable | Top-10 BAs keeping ≥ 95% of hours with both values |
| :-- | --: | --: | --: | --: |
| 2 | 71,674 | 22 | 9 of 10 | 10 of 10 |
| 3 | 14,158 | 6 | 9 of 10 | 10 of 10 |
| 4 | 6,407 | 3 | 9 of 10 | 10 of 10 |
| 6 (proposed) | 4,808 | 2 | 9 of 10 | 10 of 10 |
| 12 | 4,662 | 2 | 9 of 10 | 10 of 10 |
| 24 | 4,393 | 2 | 9 of 10 | 10 of 10 |

## BAs each rule removes hours from

### R1: non-positive values

| BA | Hours removed | % of the BA's hours with both values |
| :-- | --: | --: |
| SEC | 9,229 | 9.66 |
| SPA | 1,508 | 1.58 |
| IID | 682 | 0.71 |
| CPLW | 624 | 0.65 |
| FMPP | 572 | 0.60 |
| CPLE | 481 | 0.50 |
| TVA | 412 | 0.43 |
| TIDC | 350 | 0.36 |
| AZPS | 281 | 0.29 |
| NYIS | 268 | 0.28 |
| BANC | 238 | 0.25 |
| WACM | 172 | 0.18 |
| WAUW | 144 | 0.16 |
| WALC | 111 | 0.12 |
| NWMT | 105 | 0.11 |

25 more BAs lose fewer hours.

### R2: repeated demand, N = 6

| BA | Hours removed | % of the BA's hours with both values |
| :-- | --: | --: |
| SWPP | 2,892 | 3.10 |
| SWPW | 1,221 | 56.55 |
| IID | 415 | 0.43 |
| TVA | 404 | 0.42 |
| SEC | 259 | 0.27 |
| TIDC | 255 | 0.27 |
| OVEC | 229 | 0.99 |
| BANC | 203 | 0.21 |
| LDWP | 157 | 0.16 |
| NWMT | 70 | 0.07 |
| FPL | 53 | 0.06 |
| PNM | 47 | 0.05 |
| TEPC | 47 | 0.05 |
| HST | 40 | 0.04 |
| NSB | 31 | 0.09 |

6 more BAs lose fewer hours.

### R3a: 7 days either side of BA events

| Date | BA | Event | Basis | Hours removed |
| :-- | :-- | :-- | :-- | --: |
| 2015-10-01 | WAUE | stop | EIA | 0 |
| 2018-05-03 | GRMA | stop | EIA | 0 |
| 2018-07-31 | AVRN | start | EIA | 0 |
| 2018-12-01 | OVEC | stop | EIA | 173 |
| 2020-01-08 | NSB | stop | EIA | 96 |
| 2020-02-29 | EEI | stop | EIA | 0 |
| 2020-02-29 | GLHB | start | EIA | 0 |
| 2021-09-01 | AEC | stop | EIA | 172 |
| 2022-07-30 | WACM | footprint_change | data only | 335 |
| 2022-09-01 | GLHB | stop | EIA | 0 |
| 2023-08-02 | SPA | footprint_change | data only | 335 |
| 2023-11-01 | GRIF | stop | EIA | 0 |
| 2025-06-01 | HGMA | stop | EIA | 0 |
| 2025-06-01 | SIKE | start | EIA | 0 |
| 2025-10-01 | WWA | stop | EIA | 0 |
| 2026-03-17 | WALC | footprint_change | data only | 335 |
| 2026-04-01 | WALC | footprint_change | data only | 335 |
| 2026-04-01 | WACM | stop | EIA | 55 |
| 2026-04-01 | WAUW | stop | EIA | 174 |
| 2026-04-01 | SWPW | start | EIA | 161 |
| 2026-04-01 | BHBA | start | EIA | 161 |

Events with no hours removed are BAs without demand (generation-only) or hours that already lack a value.

### R3b: short histories

| BA | Usable hours after R1-R3a |
| :-- | --: |
| BHBA | 511 |
| SWPW | 777 |

BAs with no usable hours at all (14): AVRN, DEAA, EEI, GLHB, GRID, GRIF, GRMA, GWA, HGMA, SEPA, SIKE, WAUE, WWA, YAD.

## Events no rule acts on

These events in `data/ba_events.csv` are recorded but trigger no rule.

| Date | BA | Event | Basis | Evidence |
| :-- | :-- | :-- | :-- | :-- |
| 2015-12-18 | CHPD | demand_level_shift | data only | 14-day mean demand x0.65 on 2015-12-18 while the forecast moved x1.09; half-year median 415 MW (2015 H2) to 172 MW (2016 H1); year-on-year monthly median x0.37 from 2016-07 for 6 months. |
| 2017-12-01 | SEC | demand_level_shift | data only | Demand level unstable 2017-12 to 2021-12: year-on-year monthly median outside 0.75-1.33 in 5 runs; 14-day mean steps x21.8 on 2019-07-30, x5.5 on 2020-01-18 and x0.43 on 2021-03-12 while the forecast moved x0.97-1.11. |
| 2018-10-06 | TEPC | demand_level_shift | data only | 14-day mean demand x0.51 on 2018-10-06 while the forecast moved x1.00; year-on-year monthly median x0.57 from 2018-10 for 3 months (865 vs 1,514 MW). |
| 2021-04-14 | PNM | subregion_change | EIA | No step in PNM demand near this date: the largest 14-day change within 20 days is x0.93 on 2021-03-28, with the forecast x0.91, consistent with weather. |

## Repeated forecasts (R2b, reported, not applied), N = 6

| BA | % of hours with both values |
| :-- | --: |
| OVEC | 97.95 |
| TEPC | 1.53 |
| WAUW | 0.73 |
| CPLW | 0.65 |
| FMPP | 0.56 |
| CPLE | 0.50 |
| AZPS | 0.27 |
| NYIS | 0.25 |
| IID | 0.17 |
| NEVP | 0.15 |
