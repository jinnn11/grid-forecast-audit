# Data quality: usable hours by BA and half-year

Rules approved by the user on 2026-10-28. An hour is usable when demand and forecast are both reported and no rule drops it.

- Data: 6,135,530 BA-hours from 72 BAs, 2015-07-01 05:00 to 2026-07-01 07:00 UTC.
- Truth series: raw demand ("Demand (MW)"). Forecasts are judged as published, so the only forecast values dropped are impossible ones (R1).
- Usable: 5,038,714 hours, 82.1% of all BA-hours and 98.1% of the 5,136,224 hours with both values.
- Robustness checks for the audit: EIA's adjusted demand as the truth; the audit without R5; R2 with N = 3 and N = 12; repeated forecasts (R2 on the forecast, N = 6) dropped.

## Rules, applied in this order

| Rule | Drops | Hours removed on its own | Removed after the rules above | BAs |
| :-- | :-- | --: | --: | --: |
| R1 | Demand or forecast ≤ 0 | 15,939 | 15,939 | 40 |
| R2 (N = 6) | Hours repeating the previous hour's demand inside a run of at least 6 equal hours (the run's first hour is kept) | 6,399 | 4,808 | 21 |
| R3a | A BA's hours within 7 days of its start, stop, footprint_change events | 2,332 | 2,330 | 9 |
| R4 | Hours where EIA changed the reported demand (imputed demand set) | 9,977 | 513 | 31 |
| R5 | Demand more than 10% and 1 MW away from net generation minus interchange, except in exempted episodes | 80,236 | 72,899 | 50 |
| R3b | Every hour of a BA with fewer than 8,760 usable hours after the other rules | 2,831 | 1,021 | 2 |

## R5 exception rule

- Daily episodes: spans of UTC days on which at least 50% of the BA's checkable hours are out of balance by more than 10%; such days at most 7 days apart join one episode.
- Hour-of-day episodes (added 2026-10-28, before any forecast error was computed, because daily episodes cannot see a mismatch confined to the same hours of each day): for each UTC hour of the day, spans of days on which that hour is out of balance, joined the same way, kept when the hour is out of balance on at least 50% of the span's checkable days. They are searched only among hours outside the checked daily episodes, so each hour is judged by at most one checked episode.
- Episodes longer than 30 days are checked. The check compares medians over checkable hours with positive demand in the 3 calendar months from the episode's first day and in the same months a year earlier; an hour-of-day episode is measured on its own hour. Each window needs such hours for at least 50% of the hours it could hold.
- The episode is exempt when demand changed by at most 10% while net generation or interchange shifted by more than 10% of the earlier demand. Its demand is kept: R5 drops none of its hours. Exemptions and their evidence are in `data/balance_exemptions.csv`.
- Medians, because single absurd values would swing means (SEC reports net generation up to 429,498,863 MW).

30 daily and 141 hour-of-day episodes checked; 11 and 82 exempt. The exemptions give back 85,754 hours that R5 would otherwise drop after R1-R4.

### Hours given back, by BA

| BA | Daily episodes | Hour-of-day episodes | Total | % of the BA's hours with both values |
| :-- | --: | --: | --: | --: |
| BPAT | 60,654 | 0 | 60,654 | 62.9 |
| IID | 3,237 | 2,006 | 5,243 | 5.5 |
| SRP | 4,812 | 0 | 4,812 | 5.4 |
| AZPS | 4,311 | 0 | 4,311 | 4.5 |
| PACE | 3,484 | 324 | 3,808 | 4.1 |
| PACW | 2,521 | 0 | 2,521 | 2.7 |
| CISO | 0 | 1,428 | 1,428 | 1.5 |
| NEVP | 0 | 1,073 | 1,073 | 1.1 |
| PNM | 795 | 0 | 795 | 0.8 |
| PGE | 713 | 0 | 713 | 0.8 |
| BANC | 0 | 358 | 358 | 0.4 |
| PJM | 0 | 38 | 38 | 0.0 |

### Daily episodes checked

Shifts are later minus earlier medians, as a percent of the earlier median demand. "Hours" counts out-of-balance hours left after R1-R4. Hour-of-day episodes are listed at the end of this page.

| BA | First day | Last day | Days | Hours | Demand change (%) | Net generation shift (%) | Interchange shift (%) | Decision |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: |
| AZPS | 2019-12-04 | 2020-05-31 | 180 | 4,311 | -2.6 | -166.8 | -5.8 | exempt: net generation |
| BPAT | 2018-06-30 | 2025-05-31 | 2,528 | 60,654 | -1.1 | -78.0 | 10.6 | exempt: net generation and interchange |
| CISO | 2019-10-02 | 2020-08-22 | 326 | 5,025 | -1.5 | -9.6 | -0.8 | R5 applies: no other series shifted |
| IID | 2020-01-06 | 2020-03-22 | 77 | 1,517 | -3.6 | 9.5 | -3.9 | R5 applies: no other series shifted |
| IID | 2023-10-12 | 2023-12-31 | 81 | 1,461 | -0.3 | 10.3 | 27.6 | exempt: net generation and interchange |
| IID | 2024-01-11 | 2024-02-10 | 31 | 349 | -2.0 | -30.9 | -19.1 | exempt: net generation and interchange |
| IID | 2024-05-10 | 2024-07-02 | 54 | 722 | 9.0 | -24.1 | -26.3 | exempt: net generation and interchange |
| IID | 2024-11-15 | 2024-12-31 | 47 | 705 | 1.0 | -12.8 | -17.2 | exempt: net generation and interchange |
| JEA | 2015-07-01 | 2015-08-26 | 57 | 126 | – | – | – | R5 applies: too little data to compare |
| LDWP | 2016-10-24 | 2016-12-30 | 68 | 1,150 | 1.1 | -3.4 | 4.6 | R5 applies: no other series shifted |
| OVEC | 2017-08-07 | 2018-12-01 | 482 | 11,348 | -51.3 | -74.4 | -76.3 | R5 applies: demand changed |
| PACE | 2017-12-06 | 2018-06-20 | 197 | 3,484 | 0.7 | 11.8 | -2.2 | exempt: net generation |
| PACW | 2017-09-16 | 2018-01-25 | 132 | 2,521 | -3.3 | 26.8 | 10.7 | exempt: net generation and interchange |
| PACW | 2018-02-09 | 2018-04-23 | 74 | 1,138 | -1.9 | 4.4 | -5.1 | R5 applies: no other series shifted |
| PACW | 2018-05-11 | 2018-06-20 | 41 | 576 | -2.0 | 2.7 | -3.1 | R5 applies: no other series shifted |
| PGE | 2015-08-17 | 2016-02-03 | 171 | 3,309 | – | – | – | R5 applies: too little data to compare |
| PGE | 2018-07-01 | 2018-09-02 | 64 | 713 | -2.0 | 5.4 | 14.3 | exempt: interchange |
| PJM | 2018-12-10 | 2019-01-15 | 37 | 382 | -0.9 | -4.8 | 1.9 | R5 applies: no other series shifted |
| PNM | 2026-04-01 | 2026-05-21 | 51 | 795 | 4.1 | 19.3 | 6.7 | exempt: net generation |
| SC | 2018-12-01 | 2019-11-07 | 342 | 7,170 | – | – | – | R5 applies: too little data to compare |
| SC | 2019-11-23 | 2020-04-11 | 141 | 3,200 | -4.5 | -7.7 | -5.6 | R5 applies: no other series shifted |
| SC | 2020-05-15 | 2020-09-01 | 110 | 2,118 | -7.7 | -1.2 | 7.3 | R5 applies: no other series shifted |
| SEC | 2015-11-18 | 2015-12-28 | 41 | 902 | – | – | – | R5 applies: too little data to compare |
| SEC | 2016-03-09 | 2016-08-04 | 149 | 2,908 | – | – | – | R5 applies: too little data to compare |
| SEC | 2017-12-07 | 2019-06-04 | 545 | 9,504 | 79.3 | -285.3 | 36.2 | R5 applies: demand changed |
| SEC | 2019-07-30 | 2020-02-24 | 210 | 1,097 | – | – | – | R5 applies: too little data to compare |
| SEC | 2020-03-09 | 2020-12-11 | 278 | 4,353 | – | – | – | R5 applies: too little data to compare |
| SEC | 2021-02-16 | 2021-03-18 | 31 | 532 | -34.5 | -1.3 | 8.4 | R5 applies: demand changed |
| SRP | 2018-07-25 | 2019-02-28 | 219 | 4,812 | 2.4 | 64.9 | 82.8 | exempt: net generation and interchange |
| TEPC | 2015-09-01 | 2015-10-27 | 57 | 1,183 | – | – | – | R5 applies: too little data to compare |

### How the episode gap affects the result

| Gap (days) | Episodes checked | Exempt | Hours given back |
| :-- | --: | --: | --: |
| 0 | 104 | 61 | 81,765 |
| 7 (used) | 171 | 93 | 85,754 |
| 14 | 139 | 74 | 87,785 |

## Usable hours by BA and half-year

Percent of the BA's rows that are usable. '–': no rows that half-year. BAs sorted by average demand. Markers: † start, stop or footprint change (R3a); ‡ demand level shift, marked (the shift itself drops no hours); § subregion change. "Repeated forecast" is the share of the BA's hours with both values whose forecast repeats inside a run of 6 or more equal hours; it is reported, not dropped. The last row gives medians across BAs, so a few broken series cannot drive it.

| BA | 2015 H2 | 2016 H1 | 2016 H2 | 2017 H1 | 2017 H2 | 2018 H1 | 2018 H2 | 2019 H1 | 2019 H2 | 2020 H1 | 2020 H2 | 2021 H1 | 2021 H2 | 2022 H1 | 2022 H2 | 2023 H1 | 2023 H2 | 2024 H1 | 2024 H2 | 2025 H1 | 2025 H2 | 2026 H1 | All (%) | Usable hours | Repeated forecast (%) |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| PJM | 100.0 | 99.4 | 100.0 | 99.5 | 99.4 | 99.1 | 90.5 | 93.0 | 98.1 | 92.2 | 98.5 | 100.0 | 99.9 | 99.5 | 100.0 | 100.0 | 99.4 | 99.5 | 99.4 | 99.7 | 97.9 | 99.5 | 98.4 | 94,876 | 0 |
| MISO | 100.0 | 100.0 | 99.8 | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 99.5 | 100.0 | 100.0 | 99.4 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 100.0 | 99.5 | 99.1 | 99.8 | 96,240 | 0 |
| ERCO | 100.0 | 98.9 | 99.5 | 98.3 | 100.0 | 99.4 | 97.3 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.4 | 100.0 | 99.6 | 96,072 | 0 |
| SWPP | 99.4 | 100.0 | 95.7 | 97.8 | 97.0 | 75.2 | 65.2 | 94.2 | 86.0 | 98.6 | 100.0 | 99.8 | 96.7 | 100.0 | 100.0 | 100.0 | 99.5 | 90.1 | 100.0 | 91.9 | 92.0 | 83.4 | 93.8 | 90,407 | <0.1 |
| SOCO | 82.6 | 97.3 | 95.6 | 96.1 | 93.8 | 95.0 | 30.3 | 81.8 | 98.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 94.1 | 90,742 | <0.1 |
| CISO | 99.9 | 99.5 | 96.2 | 99.9 | 99.3 | 98.6 | 97.6 | 86.3 | 62.2 | 37.0 | 83.2 | 98.9 | 99.6 | 98.9 | 97.3 | 98.4 | 96.7 | 95.4 | 97.8 | 92.1 | 95.8 | 89.4 | 91.8 | 88,531 | 0 |
| NYIS | 99.5 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.5 | 98.9 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 99.4 | 99.4 | 99.5 | 99.3 | 99.7 | 96,164 | 0.3 |
| TVA | 99.0 | 99.5 | 100.0 | 94.5 | 99.4 | 98.9 | 90.8 | 99.5 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.1 | 95,577 | 0 |
| FPL | 99.4 | 99.6 | 99.5 | 99.5 | 99.3 | 99.5 | 98.3 | 99.9 | 100.0 | 99.9 | 99.1 | 99.8 | 99.4 | 87.2 | 99.9 | 99.9 | 96.6 | 98.8 | 98.8 | 99.9 | 99.4 | 99.9 | 98.8 | 95,290 | 0 |
| ISNE | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 96,427 | <0.1 |
| DUK | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 99.4 | 99.9 | 96,294 | <0.1 |
| CPLE | 99.4 | 99.5 | 100.0 | 100.0 | 100.0 | 95.0 | 97.8 | 99.4 | 98.9 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 88.9 | 99.0 | 95,468 | 0.5 |
| BPAT | 98.6 | 99.9 | 99.9 | 99.5 | 99.9 | 97.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 99.9 | 100.0 | 99.8 | 96,210 | 0 |
| FPC | 99.0 | 98.3 | 99.8 | 100.0 | 99.9 | 99.4 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 99.4 | 99.8 | 96,196 | <0.1 |
| PACE | 70.4 | 58.9 | 84.8 | 89.7 | 90.2 | 99.7 | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 97.8 | 95.0 | 91,656 | <0.1 |
| PSCO | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 96.8 | 100.0 | 82.6 | 99.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 95.5 | 99.3 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 98.7 | 95,177 | 0 |
| NEVP | 93.7 | 99.5 | 99.5 | 99.8 | 100.0 | 99.8 | 98.9 | 99.6 | 99.5 | 99.8 | 100.0 | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.0 | 99.1 | 98.9 | 98.3 | 98.8 | 99.3 | 95,711 | 0.2 |
| LGEE | 98.9 | 100.0 | 99.1 | 99.7 | 100.0 | 100.0 | 99.5 | 99.4 | 99.4 | 100.0 | 97.4 | 96.4 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 95,959 | 0 |
| AZPS | 98.8 | 99.9 | 99.9 | 99.4 | 99.9 | 98.3 | 100.0 | 93.2 | 100.0 | 99.8 | 98.8 | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 100.0 | 99.7 | 99.4 | 95,847 | 0.3 |
| SRP | 91.5 | 99.6 | 100.0 | 100.0 | 98.9 | 95.6 | 86.4 | 84.1 | 98.9 | 99.3 | 97.2 | 98.3 | 99.3 | 91.7 | 15.4 | 91.4 | 100.0 | 97.8 | 100.0 | 99.8 | 100.0 | 97.8 | 92.8 | 89,529 | 0.1 |
| WACM | 85.8 | 96.7 | 98.6 | 94.8 | 99.8 | 100.0 | 99.8 | 99.9 | 99.9 | 99.9 | 99.9 | 96.4 | 99.1 | 99.8 | 92.2† | 99.2 | 98.9 | 99.9 | 99.9 | 99.4 | 99.9 | 88.2† | 97.9 | 92,224 | <0.1 |
| PSEI | 100.0 | 98.4 | 100.0 | 99.4 | 100.0 | 100.0 | 13.0 | 100.0 | 88.6 | 0.6 | 0.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 86.3 | 83,255 | 0.1 |
| LDWP | 98.9 | 99.6 | 73.3 | 100.0 | 99.5 | 95.1 | 93.6 | 99.0 | 99.4 | 99.5 | 99.4 | 99.5 | 97.3 | 100.0 | 100.0 | 100.0 | 97.7 | 100.0 | 100.0 | 100.0 | 99.4 | 100.0 | 97.8 | 94,274 | <0.1 |
| SC | 100.0 | 98.9 | 100.0 | 99.9 | 64.7 | 58.6 | 81.1 | 7.4 | 24.6 | 21.3 | 75.5 | 99.5 | 98.8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 | 99.8 | 98.9 | 83.1 | 80,155 | 0 |
| SWPW | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | 0† | 0 | 0 | 0 |
| SCEG | 100.0 | 100.0 | 100.0 | 99.4 | 100.0 | 92.8 | 100.0 | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 97.3 | 100.0 | 100.0 | 98.9 | 98.9 | 99.5 | 98.3 | 96.1 | 94.5 | 91.7 | 98.5 | 94,982 | 0 |
| AECI | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 96,409 | 0 |
| PACW | 68.8 | 75.5 | 83.5 | 88.9 | 96.4 | 58.3 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 94.2 | 90,796 | 0 |
| TEC | 98.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.4 | 98.9 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 96,250 | 0 |
| PGE | 1.9 | 82.0 | 99.9 | 100.0 | 100.0 | 100.0 | 98.6 | 99.6 | 99.1 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 97.3 | 100.0 | 100.0 | 100.0 | 100.0 | 99.7 | 94.4 | 91,058 | 0 |
| FMPP | 92.9 | 90.7 | 98.3 | 97.2 | 98.5 | 98.9 | 99.4 | 99.4 | 96.7 | 98.2 | 99.4 | 99.9 | 100.0 | 100.0 | 99.4 | 100.0 | 99.4 | 100.0 | 99.4 | 100.0 | 88.1 | 99.8 | 98.0 | 94,483 | 0.6 |
| IPCO | 100.0 | 99.7 | 99.6 | 99.5 | 98.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 96,328 | 0 |
| PNM | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.4 | 100.0§ | 100.0 | 99.1 | 100.0 | 99.8 | 99.0 | 100.0 | 100.0 | 100.0 | 100.0 | 97.5 | 99.7 | 96,164 | <0.1 |
| TEPC | 70.8 | 87.5 | 99.8 | 100.0 | 100.0 | 99.4 | 93.5‡ | 99.4 | 97.8 | 99.9 | 100.0 | 82.3 | 98.6 | 100.0 | 100.0 | 100.0 | 97.6 | 98.9 | 100.0 | 100.0 | 100.0 | 98.9 | 96.6 | 93,112 | 1.5 |
| JEA | 35.3 | 52.5 | 52.3 | 65.4 | 87.4 | 98.4 | 98.8 | 96.8 | 65.4 | 74.1 | 95.8 | 96.9 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 93.3 | 100.0 | 100.0 | 100.0 | 86.9 | 83,774 | 0 |
| AVA | 90.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 95,973 | 0 |
| NWMT | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 98.9 | 98.3 | 99.4 | 99.4 | 94.5 | 93.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 99.9 | 99.9 | 99.3 | 95,725 | <0.1 |
| SCL | 99.4 | 100.0 | 98.6 | 100.0 | 99.0 | 99.5 | 99.9 | 99.4 | 97.8 | 98.4 | 98.4 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 100.0 | 100.0 | 100.0 | 99.5 | 95,972 | <0.1 |
| WALC | 98.8 | 99.8 | 100.0 | 99.8 | 99.8 | 98.9 | 99.5 | 99.9 | 99.4 | 100.0 | 100.0 | 100.0 | 98.8 | 100.0 | 100.0 | 99.8 | 99.8 | 100.0 | 98.4 | 99.9 | 100.0 | 84.3†† | 99.0 | 95,428 | 0 |
| EPE | 99.9 | 100.0 | 99.8 | 99.1 | 99.9 | 100.0 | 100.0 | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.8 | 99.9 | 96,299 | 0 |
| BHBA | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | 0† | 0 | 0 | 0 |
| GCPD | 99.5 | 99.7 | 99.0 | 99.8 | 99.9 | 99.8 | 99.9 | 99.3 | 99.9 | 99.9 | 99.8 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 99.8 | 96,261 | 0 |
| CPLW | 99.0 | 98.4 | 100.0 | 100.0 | 100.0 | 98.4 | 97.8 | 99.5 | 98.2 | 100.0 | 100.0 | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 86.2 | 98.9 | 95,393 | 0.6 |
| TPWR | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 96,430 | 0 |
| AEC | 99.9 | 99.9 | 99.9 | 99.9 | 99.9 | 96.6 | 95.5 | 96.6 | 99.8 | 98.5 | 99.8 | 99.9 | 88.3† | – | – | – | – | – | – | – | – | – | 98.6 | 53,312 | 0 |
| IID | 97.8 | 98.9 | 97.2 | 98.9 | 94.9 | 85.9 | 91.4 | 89.4 | 97.1 | 61.1 | 94.0 | 97.4 | 100.0 | 100.0 | 99.3 | 99.4 | 97.8 | 89.0 | 89.1 | 93.3 | 93.3 | 91.1 | 93.5 | 90,136 | 0.2 |
| BANC | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 90.7 | 88.2 | 98.5 | 97.9 | 90.9 | 97.1 | 98.8 | 98.8 | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.8 | 98.7 | 98.1 | 94,568 | 0 |
| TAL | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 83.7 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.2 | 95,700 | 0 |
| TIDC | 99.1 | 99.4 | 98.0 | 100.0 | 99.4 | 96.8 | 99.8 | 97.6 | 98.1 | 98.7 | 99.7 | 98.2 | 97.6 | 99.7 | 99.8 | 100.0 | 99.9 | 99.7 | 97.4 | 99.9 | 99.3 | 99.1 | 99.0 | 95,430 | 0 |
| GVL | 45.7 | 89.8 | 100.0 | 99.7 | 100.0 | 99.2 | 99.5 | 74.4 | 96.3 | 95.1 | 88.1 | 94.5 | 99.9 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.9 | 98.1 | 98.5 | 96.3 | 94.3 | 90,918 | <0.1 |
| CHPD | 99.6‡ | 100.0 | 100.0 | 100.0 | 99.5 | 99.5 | 99.5 | 99.5 | 100.0 | 99.5 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 96,278 | <0.1 |
| DOPD | 98.0 | 86.8 | 94.7 | 92.5 | 95.1 | 97.2 | 92.4 | 94.5 | 94.0 | 94.0 | 76.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 96.2 | 92,734 | <0.1 |
| WAUW | 42.4 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.9 | 99.8 | 99.9 | 99.8 | 99.8 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 91.9† | 97.0 | 91,463 | 0.7 |
| HST | 78.5 | 93.7 | 96.2 | 98.3 | 81.8 | 61.8 | 99.5 | 98.8 | 100.0 | 98.9 | 96.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 98.8 | 99.9 | 100.0 | 95.6 | 92,148 | 0.1 |
| OVEC | 54.3 | 60.4 | 66.3 | 60.6 | 16.8 | 0 | <0.1† | – | – | – | – | – | – | – | – | – | – | – | – | – | – | – | 37.8 | 11,342 | 97.9 |
| NSB | 96.2 | 94.5 | 98.3 | 94.9 | 96.1 | 88.4 | 58.1 | 95.0 | 88.8 | 0† | – | – | – | – | – | – | – | – | – | – | – | – | 89.6 | 35,542 | 0.1 |
| SPA | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 91.2 | 94.3 | 100.0 | 100.0 | 100.0 | 95.5 | 99.6 | 100.0 | 92.0† | 93.7 | 99.5 | 99.4 | 87.9 | 78.6 | 96.9 | 93,414 | <0.1 |
| SEC | 71.9 | 44.9 | 80.2 | 96.9 | 67.2‡ | 1.7 | 10.7 | 8.1 | 10.6 | 30.7 | 37.2 | 79.7 | 95.1 | 98.5 | 98.9 | 97.8 | 98.7 | 98.4 | 99.2 | 96.0 | 98.7 | 98.7 | 69.1 | 66,611 | <0.1 |
| **Median across BAs** | 99.1 | 99.6 | 99.8 | 99.8 | 99.9 | 99.3 | 99.5 | 99.5 | 99.5 | 99.8 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 98.6 | 95,080 | <0.1 |

BAs that never report demand (14, no usable hours): AVRN, DEAA, EEI, GLHB, GRID, GRIF, GRMA, GWA, HGMA, SEPA, SIKE, WAUE, WWA, YAD.

## Marked half-years

Events in `data/ba_events.csv` for BAs that report demand.

| Date | BA | Event | Basis | Marker | Handling |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 2015-12-18 | CHPD | demand_level_shift | data only | ‡ | marked; the shift itself drops no hours |
| 2017-12-01 | SEC | demand_level_shift | data only | ‡ | marked; the shift itself drops no hours |
| 2018-10-06 | TEPC | demand_level_shift | data only | ‡ | marked; the shift itself drops no hours |
| 2018-12-01 | OVEC | stop | EIA | † | R3a drops 7 days either side |
| 2020-01-08 | NSB | stop | EIA | † | R3a drops 7 days either side |
| 2021-04-14 | PNM | subregion_change | EIA | § | recorded; no rule acts on it |
| 2021-09-01 | AEC | stop | EIA | † | R3a drops 7 days either side |
| 2022-07-30 | WACM | footprint_change | data only | † | R3a drops 7 days either side |
| 2023-08-02 | SPA | footprint_change | data only | † | R3a drops 7 days either side |
| 2026-03-17 | WALC | footprint_change | data only | † | R3a drops 7 days either side |
| 2026-04-01 | WALC | footprint_change | data only | † | R3a drops 7 days either side |
| 2026-04-01 | WACM | stop | EIA | † | R3a drops 7 days either side |
| 2026-04-01 | WAUW | stop | EIA | † | R3a drops 7 days either side |
| 2026-04-01 | SWPW | start | EIA | † | R3a drops 7 days either side |
| 2026-04-01 | BHBA | start | EIA | † | R3a drops 7 days either side |

### Demand level shifts

| Date | BA | Evidence |
| :-- | :-- | :-- |
| 2015-12-18 | CHPD | Published forecast inconsistent with demand (about 2.4x; monthly medians 1.8-2.8x) from 2016-01 to 2021-06; from 2021-07 the forecast matches demand (about 0.98x). 14-day mean demand x0.65 on 2015-12-18 while the forecast moved x1.09; half-year median 415 MW (2015 H2) to 172 MW (2016 H1); year-on-year monthly median x0.37 from 2016-07 for 6 months. From 2015-12-18 to 2016-12-31 demand equals net generation minus interchange (under 0.1% of hours off by more than 10%), and EIA changed none of these hours (results/demand_truth.md). |
| 2017-12-01 | SEC | Demand level unstable 2017-12 to 2021-12: year-on-year monthly median outside 0.75-1.33 in 5 runs; 14-day mean steps x21.8 on 2019-07-30, x5.5 on 2020-01-18 and x0.43 on 2021-03-12 while the forecast moved x0.97-1.11. From 2017-12-01 to 2021-12-31, 58.7% of hours have demand more than 10% away from net generation minus interchange, and EIA changed 21.9% of them. SEC's net generation is itself impossible in 209 hours (over 1 million MW, up to 429,498,863 MW) (results/demand_truth.md). |
| 2018-10-06 | TEPC | Published forecast inconsistent with demand (monthly medians 1.2-2.2x) from 2018-10 to 2019-05; from 2019-06 it matches demand again (about 1.0x). 14-day mean demand x0.51 on 2018-10-06 while the forecast moved x1.00; year-on-year monthly median x0.57 from 2018-10 for 3 months (865 vs 1,514 MW). From 2018-10-06 to 2018-12-31 demand equals net generation minus interchange (no hour off by more than 10%), and EIA changed none of these hours (results/demand_truth.md). |

## Hour-of-day episodes checked

As the daily table; "Hour" is the UTC hour of the hour-end time, and each episode is measured on that hour only.

| BA | Hour (UTC) | First day | Last day | Days | Hours | Demand change (%) | Net generation shift (%) | Interchange shift (%) | Decision |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| BANC | 08 | 2020-09-03 | 2020-11-01 | 60 | 46 | 9.2 | 5.5 | -18.2 | exempt: interchange |
| BANC | 09 | 2020-08-12 | 2020-10-29 | 79 | 57 | 10.7 | 6.3 | -15.7 | R5 applies: demand changed |
| BANC | 10 | 2020-08-12 | 2020-10-29 | 79 | 57 | 9.7 | 7.7 | -14.0 | exempt: interchange |
| BANC | 11 | 2020-08-21 | 2020-10-29 | 70 | 59 | 10.2 | 9.1 | -15.3 | R5 applies: demand changed |
| BANC | 12 | 2020-08-11 | 2020-10-29 | 80 | 61 | 7.2 | 6.5 | -14.2 | exempt: interchange |
| BANC | 13 | 2020-08-11 | 2020-10-29 | 80 | 63 | 5.6 | 4.7 | -14.5 | exempt: interchange |
| BANC | 14 | 2020-08-12 | 2020-10-29 | 79 | 57 | 2.0 | -2.4 | -16.8 | exempt: interchange |
| BANC | 15 | 2020-09-03 | 2020-10-29 | 57 | 42 | 1.4 | -5.5 | -15.2 | exempt: interchange |
| BANC | 16 | 2020-09-05 | 2020-10-29 | 55 | 32 | 4.1 | -0.8 | -11.5 | exempt: interchange |
| CISO | 00 | 2025-12-26 | 2026-07-01 | 188 | 166 | 8.8 | -21.7 | -7.6 | exempt: net generation |
| CISO | 01 | 2025-01-02 | 2025-03-14 | 72 | 38 | 4.1 | 0.9 | -6.5 | R5 applies: no other series shifted |
| CISO | 01 | 2025-03-23 | 2025-05-08 | 47 | 24 | 7.3 | 4.6 | -3.2 | R5 applies: no other series shifted |
| CISO | 01 | 2026-04-02 | 2026-07-01 | 91 | 70 | 6.8 | -15.4 | -0.1 | exempt: net generation |
| CISO | 02 | 2024-02-23 | 2024-06-20 | 119 | 68 | -3.8 | 3.0 | 0.6 | R5 applies: no other series shifted |
| CISO | 02 | 2025-01-31 | 2025-07-05 | 156 | 98 | 1.5 | -0.1 | -5.0 | R5 applies: no other series shifted |
| CISO | 05 | 2018-07-06 | 2018-08-08 | 34 | 18 | 0.6 | -11.4 | -2.0 | exempt: net generation |
| CISO | 07 | 2022-06-15 | 2022-10-10 | 118 | 81 | 11.2 | 10.3 | 1.3 | R5 applies: demand changed |
| CISO | 07 | 2023-06-21 | 2023-10-02 | 104 | 52 | -4.1 | 1.5 | 7.2 | R5 applies: no other series shifted |
| CISO | 15 | 2019-02-27 | 2019-04-15 | 48 | 34 | -13.9 | 3.4 | 5.1 | R5 applies: demand changed |
| CISO | 15 | 2024-04-06 | 2024-06-19 | 75 | 41 | -2.1 | -11.3 | -0.8 | exempt: net generation |
| CISO | 15 | 2025-06-11 | 2025-09-14 | 96 | 55 | – | – | – | R5 applies: too little data to compare |
| CISO | 15 | 2026-04-04 | 2026-06-30 | 88 | 75 | 7.9 | 3.0 | -0.3 | R5 applies: no other series shifted |
| CISO | 16 | 2019-02-26 | 2019-04-13 | 47 | 34 | -13.6 | -0.8 | 4.1 | R5 applies: demand changed |
| CISO | 16 | 2024-03-09 | 2024-05-05 | 58 | 28 | -2.6 | -4.5 | 3.6 | R5 applies: no other series shifted |
| CISO | 16 | 2025-02-23 | 2025-04-22 | 59 | 28 | 2.5 | -1.0 | -4.1 | R5 applies: no other series shifted |
| CISO | 16 | 2026-02-08 | 2026-06-30 | 143 | 120 | 4.6 | -2.0 | -0.0 | R5 applies: no other series shifted |
| CISO | 17 | 2025-12-16 | 2026-06-30 | 197 | 179 | 2.9 | -11.0 | -3.5 | exempt: net generation |
| CISO | 18 | 2019-02-07 | 2019-03-23 | 45 | 25 | -13.4 | -0.5 | 4.9 | R5 applies: demand changed |
| CISO | 18 | 2025-12-16 | 2026-06-30 | 197 | 188 | 3.7 | -24.1 | -3.4 | exempt: net generation |
| CISO | 19 | 2025-12-16 | 2026-06-30 | 197 | 192 | 4.7 | -31.5 | -5.9 | exempt: net generation |
| CISO | 20 | 2025-12-16 | 2026-06-30 | 197 | 193 | 6.8 | -34.7 | -6.7 | exempt: net generation |
| CISO | 21 | 2025-12-16 | 2026-06-30 | 197 | 192 | 9.6 | -35.1 | -6.5 | exempt: net generation |
| CISO | 22 | 2019-02-05 | 2019-03-07 | 31 | 17 | -14.1 | -2.6 | 6.0 | R5 applies: demand changed |
| CISO | 22 | 2025-12-16 | 2026-06-30 | 197 | 193 | 11.3 | -34.0 | -5.2 | R5 applies: demand changed |
| CISO | 23 | 2025-12-16 | 2026-06-30 | 197 | 189 | 9.6 | -28.9 | -6.0 | exempt: net generation |
| GVL | 03 | 2016-04-13 | 2016-05-18 | 36 | 20 | – | – | – | R5 applies: too little data to compare |
| GVL | 07 | 2016-04-12 | 2016-05-18 | 37 | 20 | – | – | – | R5 applies: too little data to compare |
| GVL | 08 | 2016-04-12 | 2016-05-18 | 37 | 22 | – | – | – | R5 applies: too little data to compare |
| GVL | 09 | 2016-04-12 | 2016-05-18 | 37 | 24 | – | – | – | R5 applies: too little data to compare |
| GVL | 10 | 2016-04-12 | 2016-05-18 | 37 | 20 | – | – | – | R5 applies: too little data to compare |
| GVL | 11 | 2016-04-18 | 2016-05-18 | 31 | 17 | – | – | – | R5 applies: too little data to compare |
| IID | 00 | 2018-11-28 | 2019-01-16 | 50 | 27 | 0.2 | -9.5 | -15.4 | exempt: interchange |
| IID | 00 | 2024-07-03 | 2024-08-08 | 37 | 30 | 7.1 | -15.8 | -10.1 | exempt: net generation and interchange |
| IID | 00 | 2024-09-04 | 2024-11-14 | 72 | 44 | 11.5 | -30.5 | -25.1 | R5 applies: demand changed |
| IID | 01 | 2024-07-03 | 2024-08-07 | 36 | 27 | 8.4 | -14.9 | -15.4 | exempt: net generation and interchange |
| IID | 01 | 2024-10-12 | 2024-11-14 | 34 | 31 | -1.8 | -30.3 | -8.1 | exempt: net generation |
| IID | 02 | 2024-02-11 | 2024-03-13 | 32 | 26 | 3.2 | -27.6 | -10.1 | exempt: net generation and interchange |
| IID | 02 | 2024-10-12 | 2024-11-14 | 34 | 30 | -0.3 | -29.3 | -11.7 | exempt: net generation and interchange |
| IID | 03 | 2024-02-11 | 2024-05-08 | 88 | 80 | 2.5 | -28.9 | -5.7 | exempt: net generation |
| IID | 03 | 2024-10-12 | 2024-11-14 | 34 | 30 | -0.3 | -30.0 | -13.4 | exempt: net generation and interchange |
| IID | 04 | 2024-02-11 | 2024-05-08 | 88 | 81 | 1.4 | -30.1 | -6.9 | exempt: net generation |
| IID | 04 | 2024-10-09 | 2024-11-14 | 37 | 30 | -1.1 | -33.8 | -17.3 | exempt: net generation and interchange |
| IID | 05 | 2024-02-11 | 2024-05-08 | 88 | 73 | 0.3 | -29.1 | -7.7 | exempt: net generation |
| IID | 06 | 2024-03-27 | 2024-05-08 | 43 | 26 | -0.9 | -41.8 | -33.1 | exempt: net generation and interchange |
| IID | 07 | 2019-05-15 | 2019-07-09 | 56 | 38 | -3.1 | 12.9 | 8.5 | exempt: net generation |
| IID | 08 | 2019-05-16 | 2019-07-10 | 56 | 46 | -4.0 | 15.4 | 12.3 | exempt: net generation and interchange |
| IID | 09 | 2019-05-16 | 2019-07-21 | 67 | 56 | -0.7 | 15.0 | 18.3 | exempt: net generation and interchange |
| IID | 10 | 2019-05-16 | 2019-07-21 | 67 | 60 | -2.5 | 16.5 | 20.8 | exempt: net generation and interchange |
| IID | 11 | 2019-05-16 | 2019-07-22 | 68 | 62 | -2.4 | 15.9 | 20.4 | exempt: net generation and interchange |
| IID | 12 | 2019-05-16 | 2019-07-22 | 68 | 63 | -3.2 | 17.0 | 18.9 | exempt: net generation and interchange |
| IID | 13 | 2019-05-16 | 2019-07-22 | 68 | 63 | -3.0 | 16.0 | 19.7 | exempt: net generation and interchange |
| IID | 14 | 2019-05-16 | 2019-07-22 | 68 | 63 | -4.5 | 18.3 | 16.0 | exempt: net generation and interchange |
| IID | 15 | 2018-04-05 | 2018-06-24 | 81 | 44 | -0.3 | -24.6 | -4.9 | exempt: net generation |
| IID | 15 | 2019-05-16 | 2019-07-21 | 67 | 59 | -5.5 | 18.0 | 13.9 | exempt: net generation and interchange |
| IID | 15 | 2024-07-03 | 2024-08-09 | 38 | 32 | 10.7 | -20.8 | -19.8 | R5 applies: demand changed |
| IID | 15 | 2024-08-26 | 2024-11-11 | 78 | 38 | 7.1 | -43.7 | -39.2 | exempt: net generation and interchange |
| IID | 16 | 2018-04-07 | 2018-06-25 | 80 | 68 | 0.3 | -21.8 | 2.1 | exempt: net generation |
| IID | 16 | 2019-05-17 | 2019-07-09 | 54 | 40 | -4.5 | 13.9 | 11.8 | exempt: net generation and interchange |
| IID | 16 | 2024-07-03 | 2024-08-15 | 44 | 36 | 12.4 | -27.0 | -16.9 | R5 applies: demand changed |
| IID | 16 | 2024-10-02 | 2024-11-02 | 32 | 26 | -1.0 | -35.7 | -28.0 | exempt: net generation and interchange |
| IID | 17 | 2018-04-09 | 2018-06-24 | 77 | 61 | -2.1 | -20.2 | 0.9 | exempt: net generation |
| IID | 17 | 2018-11-27 | 2019-01-15 | 50 | 31 | 14.1 | -10.7 | -27.6 | R5 applies: demand changed |
| IID | 17 | 2019-05-17 | 2019-07-09 | 54 | 28 | -6.3 | 14.5 | 13.1 | exempt: net generation and interchange |
| IID | 17 | 2020-11-25 | 2021-01-12 | 49 | 32 | -3.5 | -6.5 | 3.5 | R5 applies: no other series shifted |
| IID | 17 | 2024-07-03 | 2024-08-07 | 36 | 31 | 12.2 | -22.1 | -12.9 | R5 applies: demand changed |
| IID | 17 | 2024-08-26 | 2024-10-12 | 48 | 34 | 4.9 | -41.8 | -45.6 | exempt: net generation and interchange |
| IID | 18 | 2018-04-05 | 2018-06-19 | 76 | 62 | -3.3 | -18.5 | -1.1 | exempt: net generation |
| IID | 18 | 2018-11-27 | 2019-01-15 | 50 | 30 | 15.5 | -8.6 | -28.5 | R5 applies: demand changed |
| IID | 18 | 2020-11-16 | 2021-01-12 | 58 | 39 | -2.2 | -6.2 | 1.9 | R5 applies: no other series shifted |
| IID | 18 | 2024-07-03 | 2024-08-07 | 36 | 32 | 10.0 | -19.9 | -7.1 | exempt: net generation |
| IID | 18 | 2024-09-03 | 2024-10-12 | 40 | 31 | -2.9 | -36.8 | -44.1 | exempt: net generation and interchange |
| IID | 19 | 2018-04-05 | 2018-06-18 | 75 | 53 | -3.7 | -17.8 | -2.7 | exempt: net generation |
| IID | 19 | 2018-11-27 | 2019-01-15 | 50 | 29 | 14.2 | -11.3 | -24.5 | R5 applies: demand changed |
| IID | 19 | 2020-11-25 | 2021-01-12 | 49 | 40 | 1.0 | -5.5 | 4.8 | R5 applies: no other series shifted |
| IID | 19 | 2024-07-03 | 2024-08-07 | 36 | 35 | 9.8 | -15.5 | -2.8 | exempt: net generation |
| IID | 19 | 2024-08-23 | 2024-10-12 | 51 | 36 | -0.5 | -28.4 | -31.5 | exempt: net generation and interchange |
| IID | 20 | 2018-04-05 | 2018-05-05 | 31 | 26 | -3.0 | -17.5 | -6.9 | exempt: net generation |
| IID | 20 | 2018-05-14 | 2018-06-18 | 36 | 22 | -4.8 | -13.8 | -3.0 | exempt: net generation |
| IID | 20 | 2018-11-27 | 2019-01-15 | 50 | 29 | 9.5 | -12.3 | -22.7 | exempt: net generation and interchange |
| IID | 20 | 2020-11-25 | 2021-01-12 | 49 | 39 | 1.0 | -3.3 | 5.6 | R5 applies: no other series shifted |
| IID | 20 | 2024-07-03 | 2024-08-05 | 34 | 33 | 9.6 | -15.5 | -0.3 | exempt: net generation |
| IID | 20 | 2024-08-22 | 2024-10-12 | 52 | 35 | -0.2 | -27.2 | -31.6 | exempt: net generation and interchange |
| IID | 21 | 2018-05-14 | 2018-06-17 | 35 | 18 | -4.4 | -11.9 | -0.1 | exempt: net generation |
| IID | 21 | 2018-11-27 | 2019-01-15 | 50 | 29 | 6.5 | -12.6 | -19.8 | exempt: net generation and interchange |
| IID | 21 | 2020-11-25 | 2021-01-12 | 49 | 37 | 1.5 | -2.5 | 5.2 | R5 applies: no other series shifted |
| IID | 21 | 2024-07-03 | 2024-08-05 | 34 | 32 | 6.9 | -14.1 | 0.7 | exempt: net generation |
| IID | 21 | 2024-08-22 | 2024-10-12 | 52 | 36 | 3.3 | -23.1 | -28.3 | exempt: net generation and interchange |
| IID | 22 | 2018-05-14 | 2018-06-17 | 35 | 17 | -3.0 | -9.8 | 1.5 | R5 applies: no other series shifted |
| IID | 22 | 2018-11-27 | 2019-01-15 | 50 | 29 | 5.1 | -14.2 | -20.8 | exempt: net generation and interchange |
| IID | 22 | 2020-11-25 | 2021-01-12 | 49 | 38 | 1.7 | -5.4 | 6.3 | R5 applies: no other series shifted |
| IID | 22 | 2024-07-03 | 2024-08-07 | 36 | 33 | 7.8 | -13.9 | -5.6 | exempt: net generation |
| IID | 22 | 2024-08-23 | 2024-11-02 | 72 | 38 | 3.2 | -25.4 | -30.9 | exempt: net generation and interchange |
| IID | 23 | 2018-11-27 | 2019-01-15 | 50 | 28 | 3.4 | -12.2 | -16.9 | exempt: net generation and interchange |
| IID | 23 | 2020-11-26 | 2021-01-12 | 48 | 34 | 0.2 | -2.1 | 7.2 | R5 applies: no other series shifted |
| IID | 23 | 2024-07-03 | 2024-08-07 | 36 | 29 | 8.3 | -13.9 | -8.3 | exempt: net generation |
| IID | 23 | 2024-09-03 | 2024-11-02 | 61 | 36 | 10.2 | -33.5 | -32.4 | R5 applies: demand changed |
| NEVP | 05 | 2025-03-20 | 2025-05-27 | 69 | 62 | 9.3 | 27.1 | 3.2 | exempt: net generation |
| NEVP | 05 | 2025-06-10 | 2025-10-20 | 133 | 127 | -1.7 | -25.6 | -0.5 | exempt: net generation |
| NEVP | 05 | 2026-03-09 | 2026-07-01 | 115 | 115 | 5.7 | -109.7 | -8.6 | exempt: net generation |
| NEVP | 06 | 2025-03-20 | 2025-05-27 | 69 | 59 | 8.0 | 56.7 | 1.1 | exempt: net generation |
| NEVP | 06 | 2025-06-10 | 2025-10-20 | 133 | 125 | -1.8 | -28.0 | 6.3 | exempt: net generation |
| NEVP | 06 | 2026-01-01 | 2026-07-01 | 182 | 178 | 5.9 | -25.8 | -5.0 | exempt: net generation |
| NEVP | 07 | 2025-03-20 | 2025-05-27 | 69 | 54 | 2.8 | 68.7 | 2.9 | exempt: net generation |
| NEVP | 07 | 2025-06-10 | 2025-10-20 | 133 | 125 | -1.5 | -26.1 | 4.7 | exempt: net generation |
| NEVP | 07 | 2026-01-01 | 2026-07-01 | 182 | 172 | 4.4 | -20.9 | -5.5 | exempt: net generation |
| NEVP | 08 | 2026-01-01 | 2026-03-08 | 67 | 56 | 4.8 | -11.9 | -5.4 | exempt: net generation |
| PACE | 00 | 2017-09-29 | 2017-12-03 | 66 | 56 | 1.8 | 7.2 | -4.8 | R5 applies: no other series shifted |
| PACE | 01 | 2017-09-27 | 2017-12-05 | 70 | 69 | 0.5 | 14.3 | -4.2 | exempt: net generation |
| PACE | 02 | 2017-09-27 | 2017-12-05 | 70 | 69 | 1.4 | 14.0 | -4.7 | exempt: net generation |
| PACE | 03 | 2017-09-27 | 2017-12-05 | 70 | 67 | 2.0 | 14.0 | -4.7 | exempt: net generation |
| PACE | 04 | 2017-09-27 | 2017-12-05 | 70 | 61 | 2.0 | 13.5 | -4.9 | exempt: net generation |
| PACE | 05 | 2017-09-27 | 2017-12-05 | 70 | 58 | 2.9 | 12.8 | -3.0 | exempt: net generation |
| PACE | 22 | 2017-10-17 | 2017-11-16 | 31 | 22 | 0.8 | 3.8 | -3.9 | R5 applies: no other series shifted |
| PACE | 23 | 2017-09-29 | 2017-11-22 | 55 | 37 | 1.1 | 5.7 | -5.7 | R5 applies: no other series shifted |
| PJM | 02 | 2018-09-20 | 2018-11-06 | 48 | 34 | -0.5 | -8.6 | 1.0 | R5 applies: no other series shifted |
| PJM | 03 | 2018-09-20 | 2018-11-09 | 51 | 38 | -0.1 | -10.3 | 1.1 | exempt: net generation |
| PJM | 03 | 2020-02-02 | 2020-03-03 | 31 | 31 | -9.1 | -7.6 | 1.5 | R5 applies: no other series shifted |
| PJM | 04 | 2018-09-20 | 2018-11-05 | 47 | 23 | 0.0 | -10.0 | 0.7 | R5 applies: no other series shifted |
| PJM | 05 | 2020-02-02 | 2020-03-07 | 35 | 21 | -8.3 | -9.0 | 0.7 | R5 applies: no other series shifted |
| SOCO | 00 | 2018-10-04 | 2018-12-03 | 61 | 35 | -1.6 | -0.6 | -7.8 | R5 applies: no other series shifted |
| SOCO | 07 | 2019-03-24 | 2019-05-03 | 41 | 21 | -2.1 | 0.9 | -3.9 | R5 applies: no other series shifted |
| SOCO | 08 | 2019-03-31 | 2019-05-03 | 34 | 19 | -0.3 | -0.2 | -4.0 | R5 applies: no other series shifted |
| SOCO | 09 | 2019-03-31 | 2019-05-03 | 34 | 18 | -0.2 | 0.9 | -4.1 | R5 applies: no other series shifted |
| SOCO | 18 | 2019-02-05 | 2019-03-11 | 35 | 18 | -0.3 | 0.0 | -8.6 | R5 applies: no other series shifted |
| SOCO | 22 | 2018-10-03 | 2018-12-04 | 63 | 37 | -1.0 | 0.6 | -9.1 | R5 applies: no other series shifted |
| SOCO | 23 | 2018-10-01 | 2018-12-02 | 63 | 37 | -0.7 | 1.1 | -8.5 | R5 applies: no other series shifted |
| SWPW | 00 | 2026-05-04 | 2026-06-03 | 31 | 0 | – | – | – | R5 applies: too little data to compare |
| SWPW | 01 | 2026-05-04 | 2026-06-03 | 31 | 0 | – | – | – | R5 applies: too little data to compare |
| SWPW | 02 | 2026-04-22 | 2026-06-03 | 43 | 0 | – | – | – | R5 applies: too little data to compare |
| SWPW | 03 | 2026-04-22 | 2026-06-03 | 43 | 0 | – | – | – | R5 applies: too little data to compare |
| SWPW | 04 | 2026-05-01 | 2026-06-03 | 34 | 0 | – | – | – | R5 applies: too little data to compare |
