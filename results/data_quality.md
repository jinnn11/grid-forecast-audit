# Data quality: usable hours by BA and half-year

Rules approved by the user on 2026-10-28. An hour is usable when demand and forecast are both reported and no rule drops it.

- Data: 6,135,530 BA-hours from 72 BAs, 2015-07-01 05:00 to 2026-07-01 07:00 UTC.
- Truth series: raw demand ("Demand (MW)"). Forecasts are judged as published, so the only forecast values dropped are impossible ones (R1).
- Usable: 5,033,487 hours, 82.0% of all BA-hours and 98.0% of the 5,136,224 hours with both values.
- Robustness checks for the audit: EIA's adjusted demand as the truth; the audit without R5; R2 with N = 3 and N = 12; repeated forecasts (R2 on the forecast, N = 6) dropped.

## Rules, applied in this order

| Rule | Drops | Hours removed on its own | Removed after the rules above | BAs |
| :-- | :-- | --: | --: | --: |
| R1 | Demand or forecast ≤ 0 | 15,939 | 15,939 | 40 |
| R2 (N = 6) | Hours repeating the previous hour's demand inside a run of at least 6 equal hours (the run's first hour is kept) | 6,399 | 4,808 | 21 |
| R3a | A BA's hours within 7 days of its start, stop, footprint_change events | 2,332 | 2,330 | 9 |
| R4 | Hours where EIA changed the reported demand (imputed demand set) | 9,977 | 513 | 31 |
| R5 | Demand more than 10% and 1 MW away from net generation minus interchange, except in exempted episodes | 85,516 | 78,126 | 50 |
| R3b | Every hour of a BA with fewer than 8,760 usable hours after the other rules | 2,831 | 1,021 | 2 |

## R5 exception rule

- A mismatch episode is a span of UTC days on which at least 50% of the BA's checkable hours are out of balance by more than 10%; such days at most 7 days apart join one episode. Episodes longer than 30 days are checked.
- The check compares medians over checkable hours with positive demand in the 3 calendar months from the episode's first day and in the same months a year earlier. Each window needs such hours for at least 50% of its length.
- The episode is exempt when demand changed by at most 10% while net generation or interchange shifted by more than 10% of the earlier demand. Its demand is kept: R5 drops none of its hours. Exemptions and their evidence are in `data/balance_exemptions.csv`.
- Medians, because single absurd values would swing means (SEC reports net generation up to 429,498,863 MW).

30 episodes checked, 11 exempt. The exemptions give back 80,527 hours that R5 would otherwise drop after R1-R4.

### Hours given back, by BA

| BA | Hours given back | % of the BA's hours with both values |
| :-- | --: | --: |
| BPAT | 60,654 | 62.9 |
| SRP | 4,812 | 5.4 |
| AZPS | 4,311 | 4.5 |
| PACE | 3,484 | 3.7 |
| IID | 3,237 | 3.4 |
| PACW | 2,521 | 2.7 |
| PNM | 795 | 0.8 |
| PGE | 713 | 0.8 |

### Episodes checked

Shifts are later minus earlier medians, as a percent of the earlier median demand. "Hours" counts out-of-balance hours left after R1-R4.

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
| 0 | 36 | 10 | 78,494 |
| 7 (used) | 30 | 11 | 80,527 |
| 14 | 35 | 11 | 83,059 |

## Usable hours by BA and half-year

Percent of the BA's rows that are usable. '–': no rows that half-year. BAs sorted by average demand. Markers: † start, stop or footprint change (R3a); ‡ demand level shift, marked (the shift itself drops no hours); § subregion change. "Repeated forecast" is the share of the BA's hours with both values whose forecast repeats inside a run of 6 or more equal hours; it is reported, not dropped. The last row gives medians across BAs, so a few broken series cannot drive it.

| BA | 2015 H2 | 2016 H1 | 2016 H2 | 2017 H1 | 2017 H2 | 2018 H1 | 2018 H2 | 2019 H1 | 2019 H2 | 2020 H1 | 2020 H2 | 2021 H1 | 2021 H2 | 2022 H1 | 2022 H2 | 2023 H1 | 2023 H2 | 2024 H1 | 2024 H2 | 2025 H1 | 2025 H2 | 2026 H1 | All (%) | Usable hours | Repeated forecast (%) |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| PJM | 100.0 | 99.4 | 100.0 | 99.5 | 99.4 | 99.1 | 89.6 | 93.0 | 98.1 | 92.2 | 98.5 | 100.0 | 99.9 | 99.5 | 100.0 | 100.0 | 99.4 | 99.5 | 99.4 | 99.7 | 97.9 | 99.5 | 98.3 | 94,838 | 0 |
| MISO | 100.0 | 100.0 | 99.8 | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 99.5 | 100.0 | 100.0 | 99.4 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 100.0 | 99.5 | 99.1 | 99.8 | 96,240 | 0 |
| ERCO | 100.0 | 98.9 | 99.5 | 98.3 | 100.0 | 99.4 | 97.3 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.4 | 100.0 | 99.6 | 96,072 | 0 |
| SWPP | 99.4 | 100.0 | 95.7 | 97.8 | 97.0 | 75.2 | 65.2 | 94.2 | 86.0 | 98.6 | 100.0 | 99.8 | 96.7 | 100.0 | 100.0 | 100.0 | 99.5 | 90.1 | 100.0 | 91.9 | 92.0 | 83.4 | 93.8 | 90,407 | <0.1 |
| SOCO | 82.6 | 97.3 | 95.6 | 96.1 | 93.8 | 95.0 | 30.3 | 81.8 | 98.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 94.1 | 90,742 | <0.1 |
| CISO | 99.9 | 99.5 | 96.2 | 99.9 | 99.3 | 98.6 | 97.2 | 86.3 | 62.2 | 37.0 | 83.2 | 98.9 | 99.6 | 98.9 | 97.3 | 98.4 | 96.7 | 94.5 | 97.8 | 92.1 | 93.9 | 59.8 | 90.3 | 87,103 | 0 |
| NYIS | 99.5 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.5 | 98.9 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 99.4 | 99.4 | 99.5 | 99.3 | 99.7 | 96,164 | 0.3 |
| TVA | 99.0 | 99.5 | 100.0 | 94.5 | 99.4 | 98.9 | 90.8 | 99.5 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.1 | 95,577 | 0 |
| FPL | 99.4 | 99.6 | 99.5 | 99.5 | 99.3 | 99.5 | 98.3 | 99.9 | 100.0 | 99.9 | 99.1 | 99.8 | 99.4 | 87.2 | 99.9 | 99.9 | 96.6 | 98.8 | 98.8 | 99.9 | 99.4 | 99.9 | 98.8 | 95,290 | 0 |
| ISNE | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 96,427 | <0.1 |
| DUK | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 99.4 | 99.9 | 96,294 | <0.1 |
| CPLE | 99.4 | 99.5 | 100.0 | 100.0 | 100.0 | 95.0 | 97.8 | 99.4 | 98.9 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 88.9 | 99.0 | 95,468 | 0.5 |
| BPAT | 98.6 | 99.9 | 99.9 | 99.5 | 99.9 | 97.2 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.8 | 99.9 | 100.0 | 99.8 | 96,210 | 0 |
| FPC | 99.0 | 98.3 | 99.8 | 100.0 | 99.9 | 99.4 | 100.0 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 99.4 | 99.8 | 96,196 | <0.1 |
| PACE | 70.4 | 58.9 | 84.8 | 89.7 | 82.8 | 99.7 | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 97.8 | 94.7 | 91,332 | <0.1 |
| PSCO | 99.8 | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 96.8 | 100.0 | 82.6 | 99.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 95.5 | 99.3 | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 98.7 | 95,177 | 0 |
| NEVP | 93.7 | 99.5 | 99.5 | 99.8 | 100.0 | 99.8 | 98.9 | 99.6 | 99.5 | 99.8 | 100.0 | 99.4 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.0 | 99.1 | 93.4 | 91.2 | 86.9 | 98.1 | 94,638 | 0.2 |
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
| IID | 97.8 | 98.9 | 97.2 | 98.9 | 94.9 | 77.7 | 89.2 | 78.7 | 93.5 | 61.1 | 94.0 | 97.4 | 100.0 | 100.0 | 99.3 | 99.4 | 97.8 | 82.4 | 74.5 | 93.3 | 93.3 | 91.1 | 91.4 | 88,130 | 0.2 |
| BANC | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.4 | 90.7 | 88.2 | 98.5 | 97.9 | 82.8 | 97.1 | 98.8 | 98.8 | 99.6 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 98.8 | 98.7 | 97.7 | 94,210 | 0 |
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
| **Median across BAs** | 99.1 | 99.6 | 99.8 | 99.8 | 99.9 | 99.3 | 99.5 | 99.5 | 99.5 | 99.8 | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 98.5 | 94,910 | <0.1 |

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
