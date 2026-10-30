# CISO check: the one-hour lag and CAISO's battery charging

Follow-ups to `results/operator_check.md`, approved by the user on 2026-10-30: CAISO's actual load and day-ahead forecast from OASIS back to 2016 if needed, sampling one month per year first and then fetching only the months needed to pin the change down. No other download. Files and their SHA-256 are in `results/operator_files.csv`. Nothing here changes the audit's main results; the lag correction is used only in the audit's verified-corrections robustness variant.

## Findings

- **EIA-930 reports CISO's demand an hour late in two spans: from before 2016 to 2016-09-12, and from 2022-06-14 (steadily from 2022-06-16) to 2025-12-02.** In every checked month EIA's forecast equals CAISO's day-ahead forecast as published; the lead is in EIA's demand, as in 2025.
  - Audit years with the lead: 2016 (to 2016-09-12), 2022 (from mid-June), 2023, 2024 and 2025 (to 2 December). The audit's own Q5 table shows it only for 2023–2025, the CISO years it checked.
  - Samples (July of 2016–2024): late in 2016, 2022, 2023, 2024; on time in the others. The switches were pinned with Sep 2016 and Jun 2022, and the start of the audit years with Jan 2016.
- **Most of CAISO's own forecast gap is battery charging.** In 2025 CAISO's forecast is 6.9% below its actual load (all hours); the hourly gap follows charging almost MW for MW (b = 0.90, R² = 0.79) and not discharging (c = -0.08). Against actual load less charging the bias falls to -1.1% in 2025 and -1.9% in Jan–Jun 2026 (from -6.9% and -9.6%), the 2025 MAPE to 3.40% (from 7.31%), and CAISO's forecast beats the naive forecast (skill 0.40, from -0.51). In the sampled months before 2021, with little storage, the bias was within ±1.1%.
  - The rest, about 523 MW in every hour, is not explained here. One candidate is non-dispatchable pump load, which the forecast leaves out (see the documentation below); whether the actual load includes it is not documented, and EIA-930 has no CISO pumping series, so it is not tested.
  - So the actual-load series counts charging as load and the day-ahead forecast does not (see the documentation below). EIA-930's CISO demand equals CAISO's actual load and its forecast equals CAISO's day-ahead forecast, so the audit's CISO error carries the same mismatch. The audit is unchanged; this is reported, not corrected.

## 1. When EIA-930's CISO demand runs an hour late

### Audit years that show the one-hour lead

The audit's Q5 check moves the forecast by −24, −1, 0, +1 and +24 hours, but only for large BAs in years they lose to the naive forecast: for CISO, 2023, 2024, 2025, and +1 h was best in all three. The same check on every month (EIA-930 alone; the forecast moved −1, 0 and +1 h against demand, all hours with both values above 0) shows the lead in more years:

| Year | Months best at +1 h | Months best at 0 | Months best at −1 h |
| :-- | --: | --: | --: |
| 2016 | 8 | 4 | 0 |
| 2017 | 0 | 12 | 0 |
| 2018 | 0 | 12 | 0 |
| 2019 | 1 | 11 | 0 |
| 2020 | 0 | 12 | 0 |
| 2021 | 0 | 12 | 0 |
| 2022 | 6 | 6 | 0 |
| 2023 | 12 | 0 | 0 |
| 2024 | 12 | 0 | 0 |
| 2025 | 11 | 1 | 0 |
| 2026 | 0 | 6 | 0 |

Months best at +1 h: Jan 2016 to Aug 2016, Dec 2019, Jul 2022 to Nov 2025. December 2019 is a month of broken forecast values (MAPE above 300% at every shift), not a lead.

### Checked against CAISO's own data

Per month: whether EIA's forecast equals CAISO's day-ahead forecast as published (within 1 MW), and how EIA's demand lines up with CAISO's actual load as published and with CAISO's load moved +1 h (EIA's value for hour t against CAISO's for t − 1). Gap: mean absolute difference, % of EIA's mean. Change correlation: correlation of the two series' hour-to-hour changes, which ignores a level difference; it is the deciding test, because in some months EIA's demand sits 1–2% from CAISO's at every shift (July 2019: 1.99% and 1.92%). Days: local days whose changes match best at +1 h / 0 / −1 h.

| Month | Fetched as | Forecast equal as published (%) | Demand gap as published / +1 h (%) | Change correlation as published / +1 h | Days late / on time / early |
| :-- | :-- | --: | --: | --: | --: |
| 2016-01 | pin-down | 100.0 | 3.03 / 0.27 | 0.779 / 0.998 | 31 / 0 / 0 |
| 2016-07 | sample | 100.0 | 3.52 / 0.36 | 0.925 / 0.998 | 31 / 0 / 0 |
| 2016-09 | pin-down | 100.0 | 1.40 / 2.67 | 0.963 / 0.903 | 11 / 19 / 0 |
| 2017-07 | sample | 100.0 | 0.38 / 4.43 | 0.999 / 0.915 | 0 / 31 / 0 |
| 2018-07 | sample | 100.0 | 1.24 / 3.84 | 0.992 / 0.923 | 0 / 27 / 4 |
| 2019-07 | sample | 100.0 | 1.99 / 1.92 | 0.986 / 0.970 | 0 / 31 / 0 |
| 2020-07 | sample | 100.0 | 1.54 / 2.64 | 0.991 / 0.956 | 0 / 31 / 0 |
| 2021-07 | sample | 100.0 | 1.32 / 2.41 | 0.992 / 0.935 | 0 / 31 / 0 |
| 2022-06 | pin-down | 100.0 | 3.34 / 1.73 | 0.904 / 0.961 | 16 / 14 / 0 |
| 2022-07 | sample | 100.0 | 4.66 / 1.24 | 0.853 / 0.993 | 31 / 0 / 0 |
| 2023-07 | sample | 100.0 | 4.77 / 1.22 | 0.838 / 0.992 | 31 / 0 / 0 |
| 2024-07 | sample | 100.0 | 4.16 / 0.51 | 0.823 / 0.999 | 31 / 0 / 0 |
| 2025-01 | earlier check | 100.0 | 3.22 / 0.26 | 0.586 / 0.999 | 31 / 0 / 0 |
| 2025-02 | earlier check | 100.0 | 3.22 / 0.31 | 0.634 / 0.999 | 28 / 0 / 0 |
| 2025-03 | earlier check | 100.0 | 3.44 / 0.33 | 0.645 / 0.999 | 30 / 0 / 0 |
| 2025-04 | earlier check | 100.0 | 3.46 / 0.53 | 0.601 / 0.965 | 30 / 0 / 0 |
| 2025-05 | earlier check | 100.0 | 3.52 / 0.50 | 0.680 / 0.998 | 31 / 0 / 0 |
| 2025-06 | earlier check | 100.0 | 3.76 / 0.52 | 0.733 / 0.999 | 30 / 0 / 0 |
| 2025-07 | earlier check | 100.0 | 3.74 / 0.59 | 0.602 / 0.786 | 30 / 1 / 0 |
| 2025-08 | earlier check | 100.0 | 4.04 / 0.42 | 0.767 / 0.999 | 31 / 0 / 0 |
| 2025-09 | earlier check | 100.0 | 3.65 / 0.37 | 0.769 / 0.999 | 30 / 0 / 0 |
| 2025-10 | earlier check | 100.0 | 3.24 / 0.36 | 0.617 / 0.999 | 31 / 0 / 0 |
| 2025-11 | earlier check | 100.0 | 3.14 / 0.28 | 0.578 / 0.999 | 29 / 0 / 0 |
| 2025-12 | earlier check | 100.0 | 0.33 / 2.97 | 0.973 / 0.567 | 2 / 29 / 0 |
| 2026-01 | earlier check | 100.0 | 0.11 / 3.07 | 1.000 / 0.483 | 0 / 31 / 0 |
| 2026-02 | earlier check | 100.0 | 0.13 / 3.27 | 1.000 / 0.537 | 0 / 28 / 0 |
| 2026-03 | earlier check | 100.0 | 0.13 / 3.37 | 1.000 / 0.683 | 0 / 30 / 0 |
| 2026-04 | earlier check | 100.0 | 0.15 / 3.03 | 0.999 / 0.601 | 0 / 30 / 0 |
| 2026-05 | earlier check | 100.0 | 0.14 / 3.43 | 1.000 / 0.680 | 0 / 31 / 0 |
| 2026-06 | earlier check | 100.0 | 0.14 / 3.36 | 1.000 / 0.702 | 0 / 30 / 0 |

### The late spans

From the checks above, EIA-930's CISO demand is CAISO's actual load one hour late in these spans (UTC hour ends; the first span starts before EIA-930's 2016 data and is taken from the first hour of 2016):

| First late hour (UTC) | Pacific | Last late hour (UTC) | Pacific |
| :-- | :-- | :-- | :-- |
| 2016-01-01 09:00 | 2016-01-01 01:00 PST | 2016-09-12 21:00 | 2016-09-12 14:00 PDT |
| 2022-06-14 08:00 | 2022-06-14 01:00 PDT | 2022-06-15 07:00 | 2022-06-15 00:00 PDT |
| 2022-06-16 08:00 | 2022-06-16 01:00 PDT | 2025-12-02 23:00 | 2025-12-02 15:00 PST |

On the checked days wholly inside a span, 514 of 515 match best at +1 h; on those wholly outside, 392 of 396 match best as published. Exceptions: 2025-07-31 (inside, best +0 h); 2018-07-01 (outside, best -1 h); 2018-07-02 (outside, best -1 h); 2018-07-03 (outside, best -1 h); 2018-07-04 (outside, best -1 h). On 2018-07-01 to 04 CAISO's own actual load matches CAISO's own forecast best moved +1 h, while EIA's demand matches that forecast as published, so those days are an hour off in CAISO's OASIS series, not in EIA's.

Hours either side of each switch (MW):

| UTC hour end | Local | EIA demand | CAISO, same hour | CAISO, hour before | EIA closer to |
| :-- | :-- | --: | --: | --: | --: |
| 2016-09-12 19:00 | 09-12 12:00 | 28,396 | 28,633 | 28,358 | hour before (late) |
| 2016-09-12 20:00 | 09-12 13:00 | 28,668 | 28,894 | 28,633 | hour before (late) |
| 2016-09-12 21:00 (last late hour) | 09-12 14:00 | 28,926 | 29,452 | 28,894 | hour before (late) |
| 2016-09-12 22:00 | 09-12 15:00 | – | 29,940 | 29,452 | – |
| 2016-09-12 23:00 | 09-12 16:00 | – | 30,355 | 29,940 | – |
| 2022-06-14 06:00 | 06-13 23:00 | 28,177 | 27,751 | 29,627 | same |
| 2022-06-14 07:00 | 06-14 00:00 | 26,311 | 25,974 | 27,751 | same |
| 2022-06-14 08:00 (first late hour) | 06-14 01:00 | 26,274 | 24,548 | 25,974 | hour before (late) |
| 2022-06-14 09:00 | 06-14 02:00 | 24,779 | 23,560 | 24,548 | hour before (late) |
| 2022-06-14 10:00 | 06-14 03:00 | 23,711 | 22,897 | 23,560 | hour before (late) |
| 2022-06-15 05:00 | 06-14 22:00 | 32,195 | 30,944 | 32,046 | hour before (late) |
| 2022-06-15 06:00 | 06-14 23:00 | 31,371 | 28,734 | 30,944 | hour before (late) |
| 2022-06-15 07:00 (last late hour) | 06-15 00:00 | 29,225 | 26,525 | 28,734 | hour before (late) |
| 2022-06-15 08:00 | 06-15 01:00 | 25,377 | 25,087 | 26,525 | same |
| 2022-06-15 09:00 | 06-15 02:00 | 24,116 | 23,906 | 25,087 | same |
| 2022-06-16 06:00 | 06-15 23:00 | 30,164 | 29,593 | 31,860 | same |
| 2022-06-16 07:00 | 06-16 00:00 | 27,764 | 27,346 | 29,593 | same |
| 2022-06-16 08:00 (first late hour) | 06-16 01:00 | 27,722 | 25,748 | 27,346 | hour before (late) |
| 2022-06-16 09:00 | 06-16 02:00 | 26,009 | 24,592 | 25,748 | hour before (late) |
| 2022-06-16 10:00 | 06-16 03:00 | 24,817 | 23,616 | 24,592 | hour before (late) |
| 2025-12-02 21:00 | 12-02 13:00 | 26,619 | 26,842 | 26,818 | hour before (late) |
| 2025-12-02 22:00 | 12-02 14:00 | 26,681 | 26,994 | 26,842 | hour before (late) |
| 2025-12-02 23:00 (last late hour) | 12-02 15:00 | 26,740 | 27,229 | 26,994 | hour before (late) |
| 2025-12-03 00:00 | 12-02 16:00 | 25,466 | 25,597 | 27,229 | same |
| 2025-12-03 01:00 | 12-02 17:00 | 26,628 | 26,655 | 25,597 | same |

EIA's demand is blank for the five hours after the 2016 switch. Just before the 2025 switch (2025-12-02 16:00–23:00 UTC) EIA's values match neither CAISO hour closely; they are counted as late, the nearer of the two.

Outside the spans, EIA's own check finds short runs (two days or more) that fit best at +1 h: 2020-05-09 to 2020-05-10, 2020-05-23 to 2020-05-25, 2020-07-30 to 2020-07-31, 2021-05-29 to 2021-05-30. CAISO's data for them were not fetched, so they are neither confirmed nor corrected.

## 2. CAISO's forecast gap and battery charging

### What each series includes (CAISO's documentation)

- **Day-ahead forecast (OASIS `DAM`).** CAISO's day-ahead forecast comes from its Automated Load Forecast System (BPM for Market Operations v107, §6.1.5, https://bpmcm.caiso.com/BPM%20Document%20Library/Market%20Operations/BPM_for_Market%20Operations_V107_Redline.pdf). CAISO removed battery charging from that system's inputs in June 2021: "Currently battery charging is present in the load values feeding our Automated Load Forecast System (ALFS) … the ISO will be removing batteries when charging from the load values in ALFS" (Market Performance and Planning Forum, 22 June 2021, slide 44, https://www.caiso.com/documents/presentation-marketperformance-planningforum-jun222021.pdf). CAISO's market monitor lists day-ahead demand as "the day-ahead load forecast, non-dispatchable pump load, self-scheduled exports, and upward ancillary service requirements", with "The day-ahead load forecast factors in losses" (DMM, 2025 Annual Report on Market Issues and Performance, section on day-ahead supply and demand, footnote 121, https://www.caiso.com/documents/2025-annual-report-on-market-issues-and-performance.pdf). So the forecast excludes battery charging, non-dispatchable pump load and exports, and includes losses.
- **Actual load (OASIS `ACTUAL`).** CAISO describes it only as "The actual demand measurement by Hourly basis" (OASIS Interface Specification v5.1.2, field `SYS_FCST_ACT_MW`, https://www.caiso.com/Documents/OASIS-InterfaceSpecification_v5_1_2Clean_Fall2017Release.pdf) and "a total actual hourly integrated Demand" (BPM for Market Instruments v95, §13.3, https://bpmcm.caiso.com/BPM%20Document%20Library/Market%20Instruments/BPM_for_Market%20Instruments_V95_Redline.pdf). We found no CAISO document that says whether it includes battery charging or pump load.
- **Elsewhere.** CAISO's Today's Outlook says its demand "trend data do not include dispatchable pump loads or battery storage that is charging on the system" (https://www.caiso.com/todays-outlook; the change took effect on 22 June 2021, https://www.caiso.com/documents/todaysoutlookdemandgraphchanges.html). EIA-930's instructions say storage charging "should be excluded from the actual demand reported on Form EIA-930 and instead be included as a negative contribution to net generation" (https://www.eia.gov/survey/form/eia_930/instructions.pdf).
- **What the documents leave open** is the actual-load side, so the test below asks the data.

### Storage in EIA-930 for CISO

EIA-930's `Battery Storage` column (in the files from July 2024) is blank for CISO in every hour. CISO's `Other Fuel Sources` behaves like storage: below 0 in the middle of the day (charging) and above 0 in the evening (discharging), growing from tens of MW in 2019 to about ±10 GW in 2026. It is used here as CISO's storage, which is an inference from its pattern, not a label: charging is −other where other is below 0.

| Year | Hours with a battery value | Other fuel, 5th percentile (MW) | Other fuel, 95th percentile (MW) |
| :-- | --: | --: | --: |
| 2018 | 0 | -42 | 51 |
| 2019 | 0 | -50 | 54 |
| 2020 | 0 | -85 | 72 |
| 2021 | 0 | -584 | 719 |
| 2022 | 0 | -1,009 | 1,444 |
| 2023 | 0 | -2,026 | 2,298 |
| 2024 | 0 | -4,456 | 4,537 |
| 2025 | 0 | -6,106 | 6,238 |
| 2026 | 0 | -7,679 | 7,484 |

### Does the gap track charging?

CAISO's day-ahead forecast against its own actual load, per fetched month and for 2025 and Jan–Jun 2026 (all hours with both). Months before July 2018 have no fuel data, and CISO's other-fuel values are blank in July 2020. Fit: actual − forecast = a + b × charging + c × discharging (MW), least squares over the hours with storage data. Less charging: the actual load minus charging. Skill against each truth's value 24 hours earlier.

| Period | Hours | Bias (%) | Charging (% of load) | a (MW) | b | c | R² | Bias, less charging (%) | MAPE / less charging (%) | Skill / less charging |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| Jan 2016 | 744 | -0.25 | – | – | – | – | – | – | 1.59 / – | 0.59 / – |
| Jul 2016 | 744 | -0.53 | – | – | – | – | – | – | 1.70 / – | 0.63 / – |
| Sep 2016 | 720 | 1.09 | – | – | – | – | – | – | 2.11 / – | 0.61 / – |
| Jul 2017 | 744 | 0.13 | – | – | – | – | – | – | 1.78 / – | 0.62 / – |
| Jul 2018 | 744 | -0.99 | 0.03 | 350 | 1.59 | -3.09 | 0.01 | -0.96 | 2.80 / 2.78 | 0.46 / 0.46 |
| Jul 2019 | 744 | 0.64 | 0.03 | -160 | 5.58 | -7.73 | 0.05 | 0.67 | 2.15 / 2.16 | 0.56 / 0.55 |
| Jul 2020 | 744 | 0.47 | – | – | – | – | – | – | 2.13 / – | 0.36 / – |
| Jul 2021 | 744 | -1.80 | 0.57 | 382 | 1.67 | -0.87 | 0.26 | -1.24 | 3.15 / 2.69 | 0.28 / 0.39 |
| Jun 2022 | 720 | -3.05 | 0.76 | 740 | 1.30 | -0.48 | 0.33 | -2.30 | 3.98 / 3.24 | 0.37 / 0.50 |
| Jul 2022 | 744 | -1.95 | 0.79 | 413 | 1.39 | -0.49 | 0.42 | -1.17 | 3.18 / 2.44 | 0.26 / 0.44 |
| Jul 2023 | 744 | -0.35 | 1.49 | -385 | 1.29 | -0.19 | 0.44 | 1.16 | 3.61 / 2.78 | 0.25 / 0.43 |
| Jul 2024 | 744 | -2.66 | 3.26 | -65 | 0.95 | -0.08 | 0.55 | 0.63 | 5.01 / 3.46 | 0.10 / 0.42 |
| 2025 | 8,760 | -6.87 | 5.78 | 523 | 0.90 | -0.08 | 0.79 | -1.14 | 7.31 / 3.40 | -0.51 / 0.40 |
| Jan–Jun 2026 | 4,343 | -9.58 | 7.85 | 515 | 1.02 | -0.07 | 0.95 | -1.85 | 9.74 / 2.84 | -0.93 / 0.50 |

2025 by Pacific hour ending: mean actual − forecast, charging and discharging (MW).

| Hour | Actual − forecast | Charging | Discharging |
| :-- | --: | --: | --: |
| 1 | 457 | 40 | 1,041 |
| 2 | 484 | 57 | 701 |
| 3 | 691 | 186 | 256 |
| 4 | 722 | 392 | 73 |
| 5 | 498 | 433 | 53 |
| 6 | 361 | 200 | 206 |
| 7 | 429 | 28 | 930 |
| 8 | 1,320 | 55 | 1,505 |
| 9 | 3,224 | 1,115 | 443 |
| 10 | 4,693 | 3,150 | 41 |
| 11 | 5,474 | 4,521 | 11 |
| 12 | 5,819 | 5,260 | 4 |
| 13 | 5,559 | 5,589 | 2 |
| 14 | 4,821 | 5,233 | 2 |
| 15 | 3,622 | 4,313 | 2 |
| 16 | 2,100 | 2,859 | 27 |
| 17 | 1,084 | 1,450 | 411 |
| 18 | 451 | 626 | 1,129 |
| 19 | 76 | 113 | 2,189 |
| 20 | -60 | 0 | 4,065 |
| 21 | -46 | 1 | 5,685 |
| 22 | 40 | 0 | 5,376 |
| 23 | 179 | 3 | 4,329 |
| 24 | 307 | 16 | 2,351 |
