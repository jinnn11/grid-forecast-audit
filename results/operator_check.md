# Operator check (Q5 step 2): CAISO and SPP against EIA-930

Step 2 of the plan's Q5 checks, for the 10 largest BAs that lose to the naive forecast. Approved by the user on 2026-10-28, narrowly: CAISO's own day-ahead load forecast and actual load for 2025 and Jan–Jun 2026, and SPP's for 2025. FPL (losing in 2016–2017) has no public hourly forecast archive that we know of. Nothing here changes the audit's results.

## Findings

- **CISO's one-hour lead comes from EIA-930's demand data, not from CAISO's forecast.**
  - EIA's CISO forecast is CAISO's own day-ahead forecast, unshifted, in 100.0% of hours in both periods.
  - EIA's CISO demand is CAISO's actual load one hour late on 333 of the 334 days with data from 2025-01-01 to 2025-12-02: it lines up with CAISO's load moved +1 h (mean gap 0.62%, against 3.25% as published). From 2025-12-03 it lines up as published, which is why the shift did not help in Jan–Jun 2026.
  - Against its own load, CAISO's forecast does best as published (MAPE 7.34%, 8.65% moved +1 h).
  - The rest of CISO's error is in CAISO's own published series: its day-ahead forecast is 6.9% below its own actual load in 2025 and 8.6% below in Jan–Jun 2026 (MAPE 7.34% and 8.79%). With CAISO's own data, CISO would still lose to the naive forecast in 2025 (skill -0.53). Most of that gap is battery charging, which CAISO's actual load counts and its day-ahead forecast leaves out (`results/ciso_check.md`).
  - The same late demand covers 2016-01 to 2016-09-12 and 2022-06-14 to 2025-12-02, checked against CAISO's data back to 2016 (approved 2026-10-30; `results/ciso_check.md`).
- **SWPP's over-forecast comes from EIA-930's forecast data, not from SPP's forecast.**
  - Until 2025-05-06 EIA's SWPP forecast follows SPP's own day-ahead forecast: within 2% on 122 of 125 days. From 2025-05-07 to 2025-12-31 it is more than 2% away on 219 of 238 days, at 1.11–1.14 times SPP's forecast by monthly median in May–Dec.
  - EIA's SWPP demand matches SPP's actual load throughout (monthly medians 0.998–1.004).
  - SPP's own forecast is 0.8% below its own load (MAPE 1.71%); with SPP's own data, SWPP would not lose to the naive forecast in 2025 (skill 0.58). EIA's series gives MAPE 7.79% and bias 6.41%.
  - What changed in the forecast EIA-930 carries for SWPP is not visible in these files; EIA or SPP would have to say.

In numbers:

- **CAISO against CISO, 2025.**
  - EIA's forecast equals the operator's (within 1 MW) in 100.0% of hours as published (mean gap 0.00%); the closest alignment is as published (100.0% equal, gap 0.00%).
  - EIA's demand / actual load equals the operator's (within 1 MW) in 0.8% of hours as published (mean gap 3.25%); the closest alignment is with the operator moved +1 h (3.6% equal, gap 0.62%).
  - EIA forecast against EIA demand: MAPE 8.28%, bias -6.82%, 7.26% moved +1 h.
  - CAISO's forecast against its own actual load: MAPE 7.34%, bias -6.91%, 8.65% moved +1 h.
- **CAISO against CISO, Jan–Jun 2026.**
  - EIA's forecast equals the operator's (within 1 MW) in 100.0% of hours as published (mean gap 0.00%); the closest alignment is as published (100.0% equal, gap 0.00%).
  - EIA's demand / actual load equals the operator's (within 1 MW) in 10.6% of hours as published (mean gap 0.13%); the closest alignment is as published (10.6% equal, gap 0.13%).
  - EIA forecast against EIA demand: MAPE 8.86%, bias -8.66%, 9.44% moved +1 h.
  - CAISO's forecast against its own actual load: MAPE 8.79%, bias -8.57%, 9.37% moved +1 h.
- **SPP against SWPP, 2025.**
  - EIA's forecast equals the operator's (within 1 MW) in 1.6% of hours as published (mean gap 7.03%); the closest alignment is as published (1.6% equal, gap 7.03%).
  - EIA's demand / actual load equals the operator's (within 1 MW) in 1.0% of hours as published (mean gap 1.08%); the closest alignment is as published (1.0% equal, gap 1.08%).
  - EIA forecast against EIA demand: MAPE 7.79%, bias 6.41%, 8.16% moved +1 h.
  - SPP's forecast against its own actual load: MAPE 1.71%, bias -0.82%, 2.88% moved +1 h.

## Files

Cached under `data/raw/operators/`, one at a time; each file's URL, size, download time and SHA-256 are in `results/operator_files.csv`.

| Source | Files | Bytes | Downloaded (UTC) |
| :-- | --: | --: | --: |
| CAISO | 60 | 11,211,084 | 2026-10-28 22:04:59 to 2026-10-30 11:16:29 |
| SPP | 389 | 3,596,689 | 2026-10-28 22:05:45 to 2026-10-28 22:41:16 |

- CAISO OASIS, query `SLD_FCST`, area `CA ISO-TAC` (the CAISO balancing authority area): `DAM` is "Demand Forecast Day Ahead", `ACTUAL` is "Total Actual Hourly Integrated Load". One query per month and run, Pacific midnight to Pacific midnight (OASIS counts its 31-day limit in Pacific days; the first five files used 08:00 UTC and are kept). OASIS names its files by request time, so they are cached as `CAISO_SLD_FCST_<run>_<month>_<UTC window>.zip`. No account, login or terms were needed. On 2026-10-30 a further 13 months were fetched to date CISO's one-hour lag (July 2016–2024, then Jan 2016, Sep 2016 and Jun 2022; `results/ciso_check.md`); they are listed here but not used below.
- SPP Marketplace portal, folder `mtlf-vs-actual`: one file per issue hour with the mid-term load forecast (MTLF) and the averaged actual load. No account, login or terms were needed. To find which issue is SPP's day-ahead forecast, all 24 issues of 2025-01-01 were fetched: EIA-930's SWPP forecast for 2025-01-02 equals the 03:00 issue in all 24 hours and no other issue in more than one. SPP's day-ahead forecast for each day of 2025 is taken as the 03:00 issue of the day before (04:00 on 2025-03-09, when clocks go forward and SPP has no 03:00 file). Over the year EIA's forecast follows it closely but is rarely identical (see the findings), so EIA most often reports another issue. The actual load comes from the same files (the latest issue wins; 362 hours differ between issues).
- SPP keeps 2024 only as a yearly archive (`2024.zip`), which holds a year of data outside the approval and was not fetched. Without its 2024-12-31 issue, SPP's forecast for 2025-01-01 is missing; that day's actual load is covered.

## CAISO against EIA-930 CISO, 2025

### Hour alignment

The operator's series moved k hours later (its value for hour t − k set against EIA's at t), over all hours with both values. Equal: within 1 MW. Gap: mean absolute difference as a percent of EIA's mean.

| Operator moved by | Demand hours | Demand equal (%) | Demand gap (%) | Forecast hours | Forecast equal (%) | Forecast gap (%) |
| :-- | --: | --: | --: | --: | --: | --: |
| -2 h | 8,712 | 0.0 | 8.68 | 8,712 | 0.0 | 8.03 |
| -1 h | 8,712 | 0.0 | 6.16 | 8,712 | 0.0 | 4.17 |
| 0 (as published) | 8,712 | 0.8 | 3.25 | 8,712 | 100.0 | 0.00 |
| +1 h | 8,711 | 3.6 | 0.62 | 8,711 | 0.0 | 4.17 |
| +2 h | 8,710 | 0.1 | 3.51 | 8,710 | 0.0 | 8.03 |

Day by day (local days), the shift of −1, 0 or +1 h with the smallest gap, as runs of at least 3 days. A day aligns at no shift when even the best gap is above 2%.

| Series | First day | Last day | Days | Best shift |
| :-- | --: | --: | --: | --: |
| Demand | 2025-01-01 | 2025-07-30 | 210 | operator moved +1 h |
| Demand | 2025-08-01 | 2025-12-02 | 123 | operator moved +1 h |
| Demand | 2025-12-03 | 2025-12-31 | 29 | as published |
| Forecast | 2025-01-01 | 2025-12-31 | 363 | as published |

Demand: 1 days in 1 shorter runs.

### MAPE and bias

Each forecast against each truth, over the audit's usable hours where the operator reports both series. "Moved +1 h": the forecast moved one hour later, as in the audit's Q5 check. Skill: 1 − MAPE / MAPE of that truth 24 hours earlier, on the hours that have it (below 0: loses to the naive forecast).

| Forecast | Truth | Hours | MAPE (%) | Bias (%) | MAPE moved +1 h (%) | Skill |
| :-- | :-- | --: | --: | --: | --: | --: |
| EIA-930 | EIA-930 | 8,230 | 8.28 | -6.82 | 7.26 | -0.74 |
| EIA-930 | Operator | 8,230 | 7.34 | -6.91 | 8.65 | -0.53 |
| Operator | EIA-930 | 8,230 | 8.28 | -6.82 | 7.26 | -0.74 |
| Operator | Operator | 8,230 | 7.34 | -6.91 | 8.65 | -0.53 |

### By local month

Medians of EIA / operator for demand and forecast; bias of each forecast against its own source's truth (Σe / Σ demand, %).

| Month | Demand EIA / operator | Forecast EIA / operator | EIA bias (%) | Operator bias (%) |
| :-- | --: | --: | --: | --: |
| 01 | 1.0112 | 1.0000 | -5.79 | -5.83 |
| 02 | 1.0111 | 1.0000 | -5.85 | -5.69 |
| 03 | 1.0101 | 1.0000 | -6.73 | -6.65 |
| 04 | 1.0074 | 1.0000 | -8.69 | -8.69 |
| 05 | 1.0003 | 1.0000 | -7.68 | -7.81 |
| 06 | 1.0019 | 1.0000 | -6.92 | -6.94 |
| 07 | 1.0021 | 1.0000 | -6.89 | -7.05 |
| 08 | 1.0037 | 1.0000 | -5.98 | -6.18 |
| 09 | 1.0028 | 1.0000 | -5.94 | -6.10 |
| 10 | 1.0042 | 1.0000 | -8.27 | -8.43 |
| 11 | 1.0059 | 1.0000 | -7.41 | -7.63 |
| 12 | 1.0000 | 1.0000 | -6.18 | -6.29 |

## CAISO against EIA-930 CISO, Jan–Jun 2026

### Hour alignment

The operator's series moved k hours later (its value for hour t − k set against EIA's at t), over all hours with both values. Equal: within 1 MW. Gap: mean absolute difference as a percent of EIA's mean.

| Operator moved by | Demand hours | Demand equal (%) | Demand gap (%) | Forecast hours | Forecast equal (%) | Forecast gap (%) |
| :-- | --: | --: | --: | --: | --: | --: |
| -2 h | 4,311 | 0.1 | 5.88 | 4,318 | 0.0 | 8.88 |
| -1 h | 4,312 | 0.1 | 3.21 | 4,319 | 0.0 | 4.63 |
| 0 (as published) | 4,313 | 10.6 | 0.13 | 4,320 | 100.0 | 0.00 |
| +1 h | 4,313 | 0.1 | 3.26 | 4,320 | 0.0 | 4.63 |
| +2 h | 4,313 | 0.0 | 5.94 | 4,320 | 0.0 | 8.88 |

Day by day (local days), the shift of −1, 0 or +1 h with the smallest gap, as runs of at least 3 days. A day aligns at no shift when even the best gap is above 2%.

| Series | First day | Last day | Days | Best shift |
| :-- | --: | --: | --: | --: |
| Demand | 2026-01-01 | 2026-06-30 | 180 | as published |
| Forecast | 2026-01-01 | 2026-06-30 | 180 | as published |


### MAPE and bias

Each forecast against each truth, over the audit's usable hours where the operator reports both series. "Moved +1 h": the forecast moved one hour later, as in the audit's Q5 check. Skill: 1 − MAPE / MAPE of that truth 24 hours earlier, on the hours that have it (below 0: loses to the naive forecast).

| Forecast | Truth | Hours | MAPE (%) | Bias (%) | MAPE moved +1 h (%) | Skill |
| :-- | :-- | --: | --: | --: | --: | --: |
| EIA-930 | EIA-930 | 3,884 | 8.86 | -8.66 | 9.44 | -0.84 |
| EIA-930 | Operator | 3,884 | 8.79 | -8.57 | 9.37 | -0.81 |
| Operator | EIA-930 | 3,884 | 8.86 | -8.66 | 9.44 | -0.84 |
| Operator | Operator | 3,884 | 8.79 | -8.57 | 9.37 | -0.81 |

### By local month

Medians of EIA / operator for demand and forecast; bias of each forecast against its own source's truth (Σe / Σ demand, %).

| Month | Demand EIA / operator | Forecast EIA / operator | EIA bias (%) | Operator bias (%) |
| :-- | --: | --: | --: | --: |
| 01 | 1.0001 | 1.0000 | -7.33 | -7.24 |
| 02 | 1.0001 | 1.0000 | -7.77 | -7.67 |
| 03 | 1.0000 | 1.0000 | -8.45 | -8.36 |
| 04 | 1.0001 | 1.0000 | -10.27 | -10.17 |
| 05 | 1.0001 | 1.0000 | -9.51 | -9.43 |
| 06 | 1.0000 | 1.0000 | -8.73 | -8.66 |

## SPP against EIA-930 SWPP, 2025

### Hour alignment

The operator's series moved k hours later (its value for hour t − k set against EIA's at t), over all hours with both values. Equal: within 1 MW. Gap: mean absolute difference as a percent of EIA's mean.

| Operator moved by | Demand hours | Demand equal (%) | Demand gap (%) | Forecast hours | Forecast equal (%) | Forecast gap (%) |
| :-- | --: | --: | --: | --: | --: | --: |
| -2 h | 8,759 | 0.0 | 5.10 | 8,714 | 0.0 | 8.23 |
| -1 h | 8,759 | 0.1 | 3.00 | 8,713 | 0.1 | 7.60 |
| 0 (as published) | 8,759 | 1.0 | 1.08 | 8,712 | 1.6 | 7.03 |
| +1 h | 8,759 | 0.2 | 3.06 | 8,711 | 0.1 | 7.59 |
| +2 h | 8,759 | 0.1 | 5.14 | 8,710 | 0.0 | 8.26 |

Day by day (local days), the shift of −1, 0 or +1 h with the smallest gap, as runs of at least 3 days. A day aligns at no shift when even the best gap is above 2%.

| Series | First day | Last day | Days | Best shift |
| :-- | --: | --: | --: | --: |
| Demand | 2025-01-01 | 2025-02-17 | 48 | as published |
| Demand | 2025-02-19 | 2025-03-19 | 29 | as published |
| Demand | 2025-03-25 | 2025-04-10 | 17 | as published |
| Demand | 2025-04-16 | 2025-05-18 | 33 | as published |
| Demand | 2025-05-19 | 2025-05-24 | 6 | none (gap above 2% at every shift) |
| Demand | 2025-05-28 | 2025-06-15 | 19 | as published |
| Demand | 2025-06-16 | 2025-06-18 | 3 | none (gap above 2% at every shift) |
| Demand | 2025-06-22 | 2025-07-09 | 18 | as published |
| Demand | 2025-07-15 | 2025-10-06 | 84 | as published |
| Demand | 2025-10-07 | 2025-10-10 | 4 | none (gap above 2% at every shift) |
| Demand | 2025-10-13 | 2025-12-15 | 64 | as published |
| Demand | 2025-12-16 | 2025-12-22 | 7 | none (gap above 2% at every shift) |
| Demand | 2025-12-23 | 2025-12-31 | 9 | as published |
| Forecast | 2025-01-02 | 2025-01-12 | 11 | as published |
| Forecast | 2025-01-14 | 2025-02-18 | 36 | as published |
| Forecast | 2025-02-20 | 2025-05-02 | 72 | as published |
| Forecast | 2025-05-04 | 2025-05-06 | 3 | as published |
| Forecast | 2025-05-07 | 2025-06-06 | 31 | none (gap above 2% at every shift) |
| Forecast | 2025-06-08 | 2025-06-18 | 11 | none (gap above 2% at every shift) |
| Forecast | 2025-06-20 | 2025-06-28 | 9 | none (gap above 2% at every shift) |
| Forecast | 2025-06-30 | 2025-08-03 | 34 | none (gap above 2% at every shift) |
| Forecast | 2025-08-04 | 2025-08-06 | 3 | as published |
| Forecast | 2025-08-09 | 2025-08-13 | 5 | none (gap above 2% at every shift) |
| Forecast | 2025-08-15 | 2025-08-23 | 9 | none (gap above 2% at every shift) |
| Forecast | 2025-08-26 | 2025-09-08 | 14 | none (gap above 2% at every shift) |
| Forecast | 2025-09-09 | 2025-09-12 | 4 | as published |
| Forecast | 2025-09-13 | 2025-10-09 | 27 | none (gap above 2% at every shift) |
| Forecast | 2025-10-11 | 2025-10-20 | 10 | none (gap above 2% at every shift) |
| Forecast | 2025-10-22 | 2025-11-01 | 11 | none (gap above 2% at every shift) |
| Forecast | 2025-11-03 | 2025-11-18 | 16 | none (gap above 2% at every shift) |
| Forecast | 2025-11-22 | 2025-12-31 | 40 | none (gap above 2% at every shift) |

Demand: 24 days in 16 shorter runs. Forecast: 17 days in 16 shorter runs.

### MAPE and bias

Each forecast against each truth, over the audit's usable hours where the operator reports both series. "Moved +1 h": the forecast moved one hour later, as in the audit's Q5 check. Skill: 1 − MAPE / MAPE of that truth 24 hours earlier, on the hours that have it (below 0: loses to the naive forecast).

| Forecast | Truth | Hours | MAPE (%) | Bias (%) | MAPE moved +1 h (%) | Skill |
| :-- | :-- | --: | --: | --: | --: | --: |
| EIA-930 | EIA-930 | 8,030 | 7.79 | 6.41 | 8.16 | -0.68 |
| EIA-930 | Operator | 8,030 | 7.44 | 6.43 | 7.80 | -0.82 |
| Operator | EIA-930 | 8,030 | 1.99 | -0.84 | 3.22 | 0.57 |
| Operator | Operator | 8,030 | 1.71 | -0.82 | 2.88 | 0.58 |

### By local month

Medians of EIA / operator for demand and forecast; bias of each forecast against its own source's truth (Σe / Σ demand, %).

| Month | Demand EIA / operator | Forecast EIA / operator | EIA bias (%) | Operator bias (%) |
| :-- | --: | --: | --: | --: |
| 01 | 1.0043 | 0.9988 | -1.39 | -0.74 |
| 02 | 1.0014 | 0.9998 | -1.19 | -1.06 |
| 03 | 0.9997 | 1.0012 | -0.26 | -0.41 |
| 04 | 0.9993 | 1.0002 | -0.46 | -0.53 |
| 05 | 1.0003 | 1.1203 | 8.50 | -0.95 |
| 06 | 1.0015 | 1.1159 | 8.83 | -1.33 |
| 07 | 0.9984 | 1.1103 | 9.46 | -1.28 |
| 08 | 0.9985 | 1.1065 | 7.79 | -0.95 |
| 09 | 0.9989 | 1.1136 | 9.25 | -0.83 |
| 10 | 0.9985 | 1.1185 | 11.14 | -0.31 |
| 11 | 0.9988 | 1.1206 | 10.87 | -0.83 |
| 12 | 0.9992 | 1.1378 | 14.69 | -0.32 |
