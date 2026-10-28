# Step 3 audit: day-ahead demand forecasts in EIA-930, 2016–2025

Computed as pre-registered in `docs/step3_audit_plan.md` (commit `edd06df`). **Stopped for the user's review.**

- Data: `data/processed/balance.parquet`, 6,135,530 BA-hours, 2015-07-01 to 2026-07-01 UTC. Truth: raw demand. Forecast: the day-ahead forecast as published.
- Scored: the usable hours of eligible BA-years in local years 2016–2025, 4,582,331 hours. A BA-year is eligible when at least 50% of its hours are usable: 53 BAs in 2025, a 50-BA panel eligible in every year, 49 BAs for Q4.
- Error e = forecast − demand. Naive forecast: demand 24 hours earlier, matched by timestamp, from an hour whose demand passes R1, R2, R4 and R5. The naive value for late hours may not be known when the day-ahead forecast is issued, so it is a demanding benchmark.
- Summaries across BAs are medians; the national figure is Σ|e| / Σ demand over every eligible BA's usable hours.

## Q1. How accurate is each BA's published day-ahead forecast in 2025?

53 eligible BAs, sorted by MAPE; the 10 largest by average demand in bold. Bias is Σe / Σ demand (positive: over-forecast) and mean e in MW. Skill is 1 − MAPE / naive MAPE on the hours with a naive value; below 0 the BA loses to the naive forecast. The national figure is Σ|e| / Σ demand over all these BAs' usable hours. Figure 1: `results/figures/q1_mape_2025.png`.

| BA | MAPE (%) | WAPE (%) | Bias (%) | Bias (MW) | Naive MAPE (%) | Skill | Usable hours |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| **SOCO** | 1.22 | 1.24 | -0.97 | -267 | 6.11 | 0.80 | 8,756 |
| PGE | 1.43 | 1.47 | 0.31 | 8 | 4.71 | 0.70 | 8,760 |
| AECI | 1.55 | 1.52 | -0.17 | -4 | 8.16 | 0.81 | 8,756 |
| AVA | 1.72 | 1.74 | 0.32 | 5 | 4.56 | 0.62 | 8,757 |
| BPAT | 2.00 | 2.00 | 0.21 | 15 | 3.54 | 0.44 | 8,750 |
| GCPD | 2.03 | 2.07 | -1.32 | -10 | 2.76 | 0.26 | 8,760 |
| TPWR | 2.24 | 2.23 | 1.12 | 6 | 5.41 | 0.59 | 8,760 |
| NWMT | 2.30 | 2.04 | -0.07 | -1 | 4.66 | 0.51 | 8,755 |
| **TVA** | 2.31 | 2.39 | 1.30 | 254 | 6.60 | 0.65 | 8,760 |
| **MISO** | 2.38 | 2.36 | 1.94 | 1,472 | 4.18 | 0.43 | 8,737 |
| BANC | 2.40 | 2.52 | 0.21 | 4 | 5.49 | 0.56 | 8,708 |
| **ERCO** | 2.46 | 2.45 | 1.19 | 662 | 4.52 | 0.46 | 8,688 |
| TEPC | 2.51 | 2.46 | -0.13 | -2 | 4.77 | 0.47 | 8,760 |
| **ISNE** | 2.52 | 2.33 | -1.65 | -217 | 7.99 | 0.68 | 8,758 |
| DUK | 2.57 | 2.61 | 0.55 | 69 | 7.08 | 0.64 | 8,735 |
| **NYIS** | 2.70 | 2.76 | -2.20 | -381 | 5.76 | 0.53 | 8,712 |
| CHPD | 2.97 | 3.06 | 0.22 | 1 | 5.55 | 0.46 | 8,760 |
| TIDC | 3.06 | 3.06 | -0.04 | -0 | 6.78 | 0.55 | 8,721 |
| EPE | 3.13 | 3.28 | -0.07 | -1 | 6.18 | 0.49 | 8,760 |
| **FPL** | 3.25 | 3.22 | 0.47 | 79 | 4.79 | 0.32 | 8,732 |
| SCL | 3.39 | 3.45 | -2.31 | -25 | 5.03 | 0.33 | 8,758 |
| SC | 3.40 | 3.39 | 1.49 | 47 | 6.84 | 0.50 | 8,748 |
| **PJM** | 3.44 | 3.43 | -1.46 | -1,406 | 4.98 | 0.31 | 8,652 |
| IID | 3.47 | 3.52 | 0.40 | 2 | 6.72 | 0.48 | 8,172 |
| SRP | 3.93 | 3.94 | -2.45 | -102 | 5.31 | 0.26 | 8,751 |
| PACE | 4.11 | 4.11 | 2.87 | 176 | 3.94 | -0.04 | 8,760 |
| TAL | 4.16 | 4.40 | -2.00 | -7 | 7.72 | 0.46 | 8,759 |
| CPLW | 4.22 | 4.41 | -0.31 | -2 | 8.33 | 0.49 | 8,735 |
| FMPP | 4.27 | 4.30 | -0.02 | -1 | 5.52 | 0.23 | 8,233 |
| CPLE | 4.28 | 4.31 | 1.66 | 120 | 8.94 | 0.52 | 8,735 |
| TEC | 4.53 | 4.61 | 1.95 | 50 | 6.16 | 0.26 | 8,758 |
| JEA | 4.72 | 4.71 | 3.03 | 48 | 7.40 | 0.36 | 8,759 |
| SCEG | 4.89 | 4.93 | -3.76 | -107 | 7.40 | 0.34 | 8,349 |
| IPCO | 5.01 | 4.99 | -0.31 | -7 | 4.51 | -0.11 | 8,760 |
| PNM | 6.38 | 6.39 | -6.25 | -104 | 4.33 | -0.47 | 8,758 |
| DOPD | 6.48 | 6.44 | 2.83 | 8 | 4.22 | -0.53 | 8,760 |
| HST | 6.48 | 6.39 | 1.79 | 1 | 7.33 | 0.12 | 8,704 |
| PSCO | 7.54 | 7.73 | -7.17 | -371 | 6.57 | -0.15 | 8,757 |
| LGEE | 7.73 | 7.75 | -7.67 | -339 | 7.69 | -0.01 | 8,759 |
| NEVP | 7.74 | 7.84 | -7.34 | -340 | 3.97 | -0.95 | 8,641 |
| **SWPP** | 7.77 | 7.52 | 6.40 | 2,184 | 4.35 | -0.79 | 8,055 |
| **CISO** | 8.28 | 8.31 | -6.82 | -1,754 | 4.71 | -0.78 | 8,230 |
| AZPS | 10.21 | 9.90 | -6.43 | -285 | 5.69 | -0.80 | 8,736 |
| SEC | 10.85 | 10.03 | -4.05 | -9 | 13.73 | 0.21 | 8,530 |
| GVL | 10.90 | 11.37 | -10.44 | -26 | 6.94 | -0.58 | 8,612 |
| PACW | 11.36 | 9.65 | 8.71 | 201 | 5.57 | -1.04 | 8,760 |
| LDWP | 11.70 | 10.52 | -8.45 | -238 | 9.03 | -0.30 | 8,734 |
| WALC | 12.03 | 11.27 | 0.03 | 0 | 6.36 | -0.89 | 8,756 |
| WAUW | 14.14 | 13.26 | 1.96 | 2 | 6.90 | -1.05 | 8,759 |
| WACM | 19.95 | 15.82 | -15.62 | -612 | 9.79 | -1.04 | 8,727 |
| FPC | 23.27 | 23.35 | -23.35 | -1,551 | 6.21 | -2.75 | 8,735 |
| PSEI | 29.90 | 31.11 | -30.52 | -866 | 4.73 | -5.32 | 8,760 |
| SPA | 101.41 | 78.44 | 69.08 | 15 | 38.12 | -1.66 | 8,198 |
| **Median across BAs** | 4.16 | 4.30 | -0.07 | -1 | 5.76 | 0.32 | 8,751 |
| **National (demand-weighted)** |  | 4.24 | -0.75 |  |  |  | 459,785 |

## Q2. Is accuracy getting worse?

Per BA: yearly MAPE over its eligible years, for the 52 BAs with at least 8. Slope: Theil–Sen, percentage points per year. Verdict: two-sided Mann–Kendall p < 0.05.

- **Worse: 11. Better: 10. No clear trend: 31.** By chance alone about 2.6 of 52 would reach p < 0.05 (5%).

Across BAs: the 50-BA panel eligible in every year 2016–2025.

- Median MAPE across the panel: slope 0.010 points per year, Mann–Kendall S = 9, p = 0.474 (no clear trend).
- National figure on the panel: slope 0.061 points per year, S = 23, p = 0.049 (worse).

| Year | Panel median MAPE (%) | Panel national WAPE (%) |
| :-- | --: | --: |
| 2016 | 3.72 | 3.43 |
| 2017 | 3.65 | 3.25 |
| 2018 | 4.08 | 3.43 |
| 2019 | 3.78 | 3.72 |
| 2020 | 3.74 | 3.78 |
| 2021 | 3.67 | 3.81 |
| 2022 | 3.66 | 3.66 |
| 2023 | 3.71 | 3.63 |
| 2024 | 3.92 | 3.69 |
| 2025 | 4.13 | 4.08 |

Figure 2: `results/figures/q2_mape_by_year.png`.

### Per-BA yearly MAPE (%), sorted by slope

Blank: not eligible that year. ‡: published forecast inconsistent with demand (see Notes).

| BA | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | Slope (pp/yr) | p | Verdict |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| SPA | 11.8 | 12.0 | 12.3 | 11.4 | 14.4 | 15.1 | 16.9 | 178.6 | 148.4 | 101.4 | 1.82 | 0.004 | worse |
| WACM | 3.7 | 3.6 | 6.0 | 5.3 | 6.5 | 34.7 | 9.9 | 14.3 | 16.3 | 19.9 | 1.78 | 0.004 | worse |
| LDWP | 4.2 | 4.7 | 5.4 | 7.0 | 8.2 | 12.4 | 11.7 | 6.5 | 13.9 | 11.7 | 1.08 | 0.012 | worse |
| **CISO** | 3.3 | 1.9 | 2.0 | 3.6 | 2.4 | 2.1 | 3.5 | 5.5 | 7.0 | 8.3 | 0.60 | 0.012 | worse |
| LGEE | 4.7 | 3.1 | 4.0 | 5.0 | 4.7 | 6.4 | 7.2 | 8.0 | 7.8 | 7.7 | 0.58 | 0.007 | worse |
| PNM | 2.9 | 2.4 | 2.7 | 2.8 | 3.3 | 5.6 | 6.8 | 6.2 | 6.3 | 6.4 | 0.53 | 0.004 | worse |
| NEVP | 3.1 | 3.1 | 4.1 | 3.4 | 2.8 | 3.2 | 4.9 | 4.8 | 6.8 | 7.7 | 0.47 | 0.012 | worse |
| WAUW | 6.4 | 6.3 | 6.3 | 6.3 | 5.7 | 6.0 | 6.4 | 7.8 | 9.5 | 14.1 | 0.36 | 0.152 | no clear trend |
| FPC | 20.4 | 21.2 | 21.3 | 21.8 | 21.6 | 22.5 | 23.0 | 22.6 | 23.5 | 23.3 | 0.33 | 0.001 | worse |
| WALC | 9.3 | 16.0 | 41.8 | 16.7 | 13.5 | 26.0 | 11.2 | 16.2 | 39.6 | 12.0 | 0.27 | 0.858 | no clear trend |
| SCEG | 2.9 | 2.9 | 2.9 | 4.5 | 5.1 | 4.9 | 5.2 | 4.3 | 4.5 | 4.9 | 0.23 | 0.049 | worse |
| PSCO | 4.0 | 3.5 | 3.3 | 3.0 | 3.2 | 2.9 | 2.8 | 4.6 | 6.0 | 7.5 | 0.19 | 0.721 | no clear trend |
| AZPS | 2.8 | 3.0 | 3.0 | 3.7 | 3.7 | 3.6 | 3.7 | 3.5 | 4.1 | 10.2 | 0.17 | 0.012 | worse |
| CPLW | 3.6 | 3.8 | 4.2 | 4.1 | 4.6 | 4.4 | 4.2 | 4.6 | 8.7 | 4.2 | 0.12 | 0.020 | worse |
| **PJM** | 2.4 | 2.3 | 2.4 | 3.6 | 3.9 | 3.6 | 3.6 | 3.5 | 3.6 | 3.4 | 0.11 | 0.592 | no clear trend |
| SCL | 3.4 | 2.5 | 2.6 | 2.4 | 3.0 | 4.9 | 5.1 | 3.4 | 3.3 | 3.4 | 0.11 | 0.371 | no clear trend |
| **SWPP** | 2.6 | 3.3 | 3.2 | 3.4 | 4.0 | 3.7 | 3.7 | 2.9 | 2.0 | 7.8 | 0.09 | 0.371 | no clear trend |
| TIDC | 2.7 | 2.8 | 2.8 | 2.6 | 3.4 | 3.9 | 3.3 | 3.8 | 3.2 | 3.1 | 0.06 | 0.210 | no clear trend |
| TEC | 4.3 | 4.8 | 4.7 | 4.1 | 5.0 | 4.4 | 5.3 | 4.4 | 5.2 | 4.5 | 0.05 | 0.474 | no clear trend |
| PACW | 3.8 | 157.8 | 5.6 | 3.1 | 3.0 | 3.3 | 4.7 | 4.0 | 4.0 | 11.4 | 0.04 | 0.858 | no clear trend |
| CPLE | 3.8 | 3.6 | 4.1 | 4.0 | 4.2 | 4.3 | 4.0 | 4.2 | 3.9 | 4.3 | 0.04 | 0.074 | no clear trend |
| DUK | 2.6 | 2.7 | 2.9 | 2.7 | 2.8 | 2.8 | 2.9 | 2.5 | 2.9 | 2.6 | 0.01 | 1.000 | no clear trend |
| **TVA** | 2.9 | 2.0 | 2.1 | 2.3 | 2.4 | 2.2 | 2.4 | 2.4 | 2.1 | 2.3 | 0.00 | 1.000 | no clear trend |
| EPE | 3.2 | 3.2 | 3.2 | 3.0 | 3.8 | 3.8 | 3.2 | 3.3 | 3.2 | 3.1 | -0.00 | 1.000 | no clear trend |
| BPAT | 2.1 | 2.1 | 1.8 | 1.9 | 2.0 | 2.1 | 2.1 | 2.0 | 2.0 | 2.0 | -0.01 | 0.592 | no clear trend |
| **ERCO** | 2.6 | 2.6 | 2.4 | 2.4 | 2.2 | 2.9 | 2.8 | 2.6 | 2.2 | 2.5 | -0.02 | 0.592 | no clear trend |
| GVL | 14.1 | 9.0 | 7.2 | 6.6 | 6.8 | 6.4 | 7.2 | 11.8 | 11.0 | 10.9 | -0.02 | 1.000 | no clear trend |
| **ISNE** | 2.9 | 2.9 | 2.6 | 2.4 | 2.4 | 2.4 | 2.4 | 2.4 | 2.8 | 2.5 | -0.03 | 0.210 | no clear trend |
| **MISO** | 3.1 | 2.2 | 2.6 | 3.2 | 3.2 | 2.3 | 3.0 | 3.0 | 2.8 | 2.4 | -0.03 | 0.721 | no clear trend |
| TPWR | 2.7 | 2.7 | 3.1 | 2.9 | 2.8 | 3.0 | 2.8 | 2.8 | 2.2 | 2.2 | -0.05 | 0.283 | no clear trend |
| TAL | 4.7 | 4.2 | 5.1 | 3.2 | 1.5 | 2.6 | 3.6 | 3.5 | 4.6 | 4.2 | -0.05 | 0.858 | no clear trend |
| GCPD | 2.7 | 2.6 | 2.1 | 2.7 | 2.6 | 2.6 | 2.4 | 2.4 | 2.1 | 2.0 | -0.07 | 0.007 | better |
| **NYIS** | 3.1 | 3.3 | 3.6 | 2.9 | 2.5 | 2.7 | 2.6 | 2.4 | 2.8 | 2.7 | -0.08 | 0.074 | no clear trend |
| BANC | 2.6 | 3.2 | 3.1 | 2.6 | 2.9 | 2.6 | 2.5 | 2.3 | 2.1 | 2.4 | -0.10 | 0.007 | better |
| IID | 6.5 | 6.0 | 6.9 | 3.2 | 3.6 | 3.2 | 3.2 | 3.3 | 19.9 | 3.5 | -0.11 | 0.858 | no clear trend |
| SC | 4.5 | 4.6 | 4.0 |  |  | 2.8 | 2.9 | 3.4 | 3.8 | 3.4 | -0.11 | 0.386 | no clear trend |
| FMPP | 5.1 | 5.3 | 5.0 | 5.5 | 5.2 | 4.4 | 4.7 | 4.4 | 4.3 | 4.3 | -0.12 | 0.007 | better |
| PACE | 7.0 | 4.2 | 4.4 | 3.9 | 6.6 | 5.5 | 6.2 | 4.8 | 4.1 | 4.1 | -0.13 | 0.371 | no clear trend |
| PGE | 2.7 | 2.4 | 1.7 | 1.9 | 2.0 | 2.1 | 1.5 | 1.2 | 1.2 | 1.4 | -0.15 | 0.012 | better |
| HST | 7.3 | 9.7 | 7.2 | 6.5 | 8.7 | 8.0 | 6.9 | 6.8 | 6.7 | 6.5 | -0.15 | 0.049 | better |
| NWMT | 3.7 | 3.7 | 3.5 | 4.6 | 3.2 | 3.6 | 4.0 | 2.2 | 1.9 | 2.3 | -0.17 | 0.074 | no clear trend |
| **FPL** | 5.6 | 6.3 | 5.0 | 4.4 | 4.3 | 5.1 | 3.5 | 5.5 | 9.1 | 3.3 | -0.19 | 0.371 | no clear trend |
| SRP | 5.1 | 5.1 | 4.8 | 4.1 | 2.3 | 2.1 | 2.4 | 2.6 | 3.1 | 3.9 | -0.25 | 0.152 | no clear trend |
| AECI | 4.7 | 4.9 | 6.5 | 3.9 | 3.5 | 3.4 | 3.5 | 3.6 | 3.6 | 1.5 | -0.27 | 0.074 | no clear trend |
| JEA | 7.0 | 7.3 | 5.9 | 6.0 | 5.5 | 5.0 | 4.9 | 4.7 | 4.9 | 4.7 | -0.27 | 0.001 | better |
| **SOCO** | 4.0 | 3.9 | 3.6 | 3.9 | 3.8 | 3.0 | 2.1 | 2.0 | 1.9 | 1.2 | -0.31 | 0.001 | better |
| IPCO | 3.5 | 7.5 | 6.0 | 4.9 | 4.1 | 2.7 | 2.2 | 2.8 | 2.7 | 5.0 | -0.34 | 0.210 | no clear trend |
| DOPD | 9.6 | 9.5 | 9.0 | 8.6 | 9.6 | 5.1 | 4.8 | 6.6 | 10.0 | 6.5 | -0.35 | 0.283 | no clear trend |
| AVA | 10.4 | 9.2 | 10.3 | 2.8 | 3.2 | 1.9 | 2.0 | 1.9 | 1.7 | 1.7 | -0.93 | 0.001 | better |
| PSEI | 47.9 | 51.9 | 60.3 | 47.6 |  | 40.0 | 41.3 | 24.9 | 25.3 | 29.9 | -2.96 | 0.029 | better |
| TEPC | 11.2 | 7.2 | 33.2‡ | 28.4‡ | 19.9 | 43.0 | 13.5 | 7.9 | 3.0 | 2.5 | -3.49 | 0.152 | no clear trend |
| CHPD | 145.2‡ | 135.9‡ | 139.4‡ | 137.6‡ | 140.0‡ | 72.1‡ | 3.5 | 3.4 | 3.1 | 3.0 | -18.97 | 0.002 | better |

## Q3. When do forecasts miss most? (2016–2025)

All Q3 results use the usable hours of eligible BA-years, by local time.

### Season and hour of day

Each BA's MAPE per season, then the median across BAs. HE: local hour ending; the lowest and highest cells of the season's row of Figure 3 (`results/figures/q3_season_hour.png`, values in its CSV).

| Season | Median MAPE (%) | Lowest hour | Highest hour |
| :-- | --: | --: | --: |
| DJF | 4.01 | HE 19 (3.38) | HE 15 (4.72) |
| MAM | 4.12 | HE 4 (3.49) | HE 16 (4.85) |
| JJA | 4.29 | HE 7 (3.63) | HE 10 (4.99) |
| SON | 4.28 | HE 4 (3.79) | HE 11 (4.98) |

### Holidays

Each BA's MAPE over the holiday's days (all years, actual and observed dates) against the same weekday one and two weeks before and after, leaving out other holidays and the BA's event days. Ratio: holiday MAPE / comparison MAPE, median across BAs.

| Holiday | BAs | Median holiday MAPE (%) | Median comparison MAPE (%) | Median ratio | BAs with ratio > 1 |
| :-- | --: | --: | --: | --: | --: |
| New Year's Day | 55 | 4.73 | 3.99 | 1.16 | 38 |
| Memorial Day | 56 | 4.90 | 4.34 | 1.06 | 34 |
| Independence Day | 56 | 4.93 | 4.28 | 1.11 | 35 |
| Labor Day | 56 | 4.74 | 4.21 | 1.06 | 35 |
| Thanksgiving Day | 55 | 5.61 | 3.88 | 1.24 | 42 |
| Day after Thanksgiving | 55 | 4.95 | 4.01 | 1.21 | 43 |
| Christmas Eve | 55 | 4.97 | 4.26 | 1.17 | 40 |
| Christmas Day | 55 | 5.18 | 4.00 | 1.23 | 44 |
| New Year's Eve | 54 | 4.53 | 3.89 | 1.07 | 35 |

### Extreme-weather events

MAPE in the event window against the same BA's hours in the 14 days before and after (leaving out holidays and the BA's other events). Ratio: window MAPE / baseline MAPE; medians across the event's BAs with hours in both. Events and sources: `data/weather_events.csv`; the hurricane landfalls were checked against the NHC reports.

| # | Event | Window | BAs scored | Median window MAPE (%) | Median baseline MAPE (%) | Median ratio | BAs with ratio > 1 |
| :-- | :-- | :-- | --: | --: | --: | --: | --: |
| 1 | South Central US cold | 2018-01-16 to 01-18 | 3 of 4 | 2.70 | 2.84 | 1.21 | 2 |
| 2 | Polar vortex | 2019-01-29 to 02-01 | 4 of 4 | 3.49 | 2.88 | 1.05 | 2 |
| 3 | Winter Storm Uri | 2021-02-13 to 02-20 | 5 of 5 | 6.41 | 4.50 | 1.47 | 5 |
| 4 | California heat wave | 2020-08-13 to 08-16 | 5 of 5 | 3.43 | 3.79 | 0.76 | 2 |
| 5 | Pacific Northwest heat dome | 2021-06-27 to 07-01 | 10 of 10 | 6.00 | 3.87 | 1.51 | 8 |
| 6 | Western heat wave | 2022-09-05 to 09-07 | 5 of 5 | 4.02 | 3.88 | 1.53 | 4 |
| 7 | Winter Storm Elliott | 2022-12-21 to 12-26 | 14 of 14 | 4.34 | 3.21 | 1.35 | 13 |
| 8 | Texas heat | 2023-09-05 to 09-07 | 1 of 1 | 1.93 | 2.20 | 0.88 | 0 |
| 9 | Winter Storms Gerri and Heather | 2024-01-10 to 01-17 | 9 of 9 | 3.27 | 2.82 | 1.15 | 7 |
| 10 | Hurricane Harvey | 2017-08-24 to 08-28 | 2 of 2 | 2.95 | 2.33 | 1.33 | 1 |
| 11 | Hurricane Irma | 2017-09-09 to 09-13 | 10 of 10 | 29.72 | 6.54 | 4.62 | 9 |
| 12 | Hurricane Michael | 2018-10-09 to 10-13 | 4 of 4 | 59.28 | 12.71 | 1.51 | 3 |
| 13 | Hurricane Laura | 2020-08-26 to 08-30 | 1 of 1 | 4.60 | 2.94 | 1.57 | 1 |
| 14 | Hurricane Zeta | 2020-10-27 to 10-31 | 2 of 2 | 2.89 | 2.93 | 1.00 | 1 |
| 15 | Hurricane Ida | 2021-08-28 to 09-01 | 1 of 1 | 5.77 | 2.62 | 2.20 | 1 |
| 16 | Hurricane Ian | 2022-09-27 to 10-01 | 7 of 7 | 11.97 | 5.27 | 1.65 | 5 |
| 17 | Hurricane Idalia | 2023-08-29 to 09-02 | 6 of 6 | 7.52 | 7.17 | 0.90 | 2 |
| 18 | Hurricane Helene | 2024-09-25 to 09-29 | 12 of 12 | 8.75 | 4.47 | 1.59 | 7 |
| 19 | Hurricane Milton | 2024-10-08 to 10-12 | 8 of 8 | 8.00 | 6.94 | 1.16 | 4 |

Per event and BA (bias: Σe / Σ demand, %, positive is over-forecast):

| # | BA | Window hours | Window MAPE (%) | Window bias (%) | Baseline hours | Baseline MAPE (%) | Baseline bias (%) | Ratio |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |
| 1 | **MISO** | 72 | 1.69 | -0.30 | 672 | 2.84 | 0.51 | 0.59 |
| 1 | **SWPP** | – | – | – | 437 | 3.27 | 2.37 | – |
| 1 | **TVA** | 72 | 2.70 | -0.90 | 672 | 2.23 | -0.15 | 1.21 |
| 1 | AECI | 72 | 6.98 | -5.61 | 672 | 5.39 | -4.89 | 1.29 |
| 2 | **MISO** | 96 | 3.47 | 3.46 | 672 | 2.89 | 2.37 | 1.20 |
| 2 | **PJM** | 94 | 3.52 | -0.05 | 572 | 2.87 | -1.22 | 1.23 |
| 2 | **SWPP** | 96 | 2.27 | 0.27 | 672 | 2.53 | 0.70 | 0.90 |
| 2 | AECI | 96 | 4.02 | 2.53 | 672 | 5.24 | -1.98 | 0.77 |
| 3 | **ERCO** | 192 | 22.10 | 19.75 | 672 | 4.76 | 0.53 | 4.65 |
| 3 | **SWPP** | 192 | 6.41 | 5.74 | 663 | 4.36 | 2.50 | 1.47 |
| 3 | **MISO** | 192 | 4.52 | 1.85 | 672 | 2.11 | 1.20 | 2.14 |
| 3 | AECI | 192 | 5.98 | 1.67 | 672 | 4.50 | -0.66 | 1.33 |
| 3 | SPA | 192 | 12.47 | 5.02 | 672 | 12.03 | 6.27 | 1.04 |
| 4 | **CISO** | 44 | 1.73 | 0.10 | 396 | 3.20 | 1.90 | 0.54 |
| 4 | BANC | 92 | 4.51 | -3.38 | 623 | 3.59 | 1.00 | 1.26 |
| 4 | LDWP | 96 | 10.58 | -7.81 | 672 | 8.43 | -0.43 | 1.26 |
| 4 | IID | 96 | 2.87 | -2.13 | 647 | 3.79 | 0.96 | 0.76 |
| 4 | TIDC | 96 | 3.43 | -0.13 | 672 | 4.74 | 2.62 | 0.72 |
| 5 | AVA | 120 | 2.34 | -0.32 | 624 | 2.16 | 0.06 | 1.08 |
| 5 | BPAT | 120 | 3.12 | 0.31 | 624 | 1.93 | 0.56 | 1.62 |
| 5 | PSEI | 120 | 40.13 | -41.10 | 624 | 21.32 | -21.01 | 1.88 |
| 5 | SCL | 120 | 7.30 | -6.34 | 623 | 4.81 | -4.16 | 1.52 |
| 5 | TPWR | 120 | 5.81 | 1.50 | 624 | 2.90 | 0.90 | 2.00 |
| 5 | PGE | 120 | 7.78 | 7.52 | 624 | 2.39 | 0.27 | 3.26 |
| 5 | PACW | 120 | 4.20 | 2.69 | 624 | 3.82 | 2.93 | 1.10 |
| 5 | CHPD‡ | 120 | 117.04 | 113.35 | 624 | 125.57 | 117.86 | 0.93 |
| 5 | DOPD | 120 | 3.72 | 2.58 | 624 | 3.92 | 2.55 | 0.95 |
| 5 | GCPD | 120 | 6.19 | -5.83 | 624 | 4.14 | -3.65 | 1.49 |
| 6 | **CISO** | 71 | 4.02 | -2.46 | 647 | 3.88 | -1.02 | 1.04 |
| 6 | BANC | 72 | 3.59 | -1.19 | 672 | 2.07 | 0.50 | 1.73 |
| 6 | LDWP | 72 | 17.63 | -17.88 | 672 | 7.94 | -0.77 | 2.22 |
| 6 | IID | 72 | 6.13 | 1.61 | 670 | 4.00 | -0.30 | 1.53 |
| 6 | TIDC | 72 | 3.05 | -1.41 | 672 | 3.35 | -0.48 | 0.91 |
| 7 | **PJM** | 144 | 3.87 | -1.58 | 600 | 3.19 | -1.05 | 1.21 |
| 7 | **MISO** | 144 | 4.23 | 2.75 | 600 | 2.77 | 2.55 | 1.53 |
| 7 | **TVA** | 144 | 3.56 | 0.30 | 600 | 2.60 | 0.66 | 1.37 |
| 7 | DUK | 144 | 4.27 | -1.12 | 600 | 3.24 | 0.23 | 1.32 |
| 7 | CPLE | 144 | 6.29 | 3.25 | 600 | 3.35 | -0.54 | 1.88 |
| 7 | CPLW | 144 | 7.91 | -4.87 | 600 | 4.44 | 1.07 | 1.78 |
| 7 | **SOCO** | 144 | 1.57 | -1.07 | 600 | 1.71 | -1.19 | 0.92 |
| 7 | LGEE | 144 | 7.66 | -8.04 | 600 | 7.63 | -7.25 | 1.00 |
| 7 | SC | 144 | 5.70 | 4.40 | 600 | 2.96 | 1.66 | 1.92 |
| 7 | SCEG | 144 | 6.90 | -1.64 | 600 | 4.39 | -2.44 | 1.57 |
| 7 | AECI | 144 | 5.87 | -3.14 | 600 | 3.94 | -0.21 | 1.49 |
| 7 | **NYIS** | 144 | 3.46 | -3.27 | 600 | 2.72 | -2.67 | 1.27 |
| 7 | **ISNE** | 144 | 2.96 | -1.17 | 600 | 2.33 | -1.36 | 1.27 |
| 7 | **SWPP** | 144 | 4.40 | 1.60 | 600 | 4.03 | 3.05 | 1.09 |
| 8 | **ERCO** | 72 | 1.93 | -1.28 | 648 | 2.20 | 0.93 | 0.88 |
| 9 | **ERCO** | 192 | 3.96 | -0.17 | 624 | 3.78 | -0.30 | 1.05 |
| 9 | **SWPP** | 164 | 4.47 | -3.81 | 585 | 2.38 | -0.06 | 1.88 |
| 9 | **MISO** | 192 | 2.75 | 0.67 | 624 | 2.56 | 1.81 | 1.08 |
| 9 | **PJM** | 192 | 3.71 | -2.31 | 624 | 3.11 | -1.55 | 1.19 |
| 9 | **TVA** | 192 | 3.24 | 2.53 | 624 | 2.82 | 0.31 | 1.15 |
| 9 | AECI | 192 | 3.27 | -2.82 | 624 | 3.68 | -0.29 | 0.89 |
| 9 | BPAT | 192 | 3.50 | 0.96 | 624 | 1.92 | -0.49 | 1.82 |
| 9 | PGE | 192 | 1.65 | -0.68 | 624 | 1.15 | -0.20 | 1.43 |
| 9 | PACW | 192 | 3.10 | 0.02 | 624 | 4.04 | 3.08 | 0.77 |
| 10 | **ERCO** | 120 | 4.33 | 3.81 | 648 | 2.11 | 0.76 | 2.05 |
| 10 | **MISO** | 120 | 1.57 | 1.53 | 648 | 2.55 | 2.43 | 0.62 |
| 11 | **FPL** | 119 | 39.15 | 16.41 | 648 | 6.25 | -5.29 | 6.27 |
| 11 | FPC | 120 | 28.86 | -11.83 | 648 | 22.19 | -22.41 | 1.30 |
| 11 | TEC | 120 | 19.64 | 6.92 | 648 | 5.07 | 2.10 | 3.87 |
| 11 | JEA | 118 | 52.52 | 30.16 | 624 | 8.73 | 1.87 | 6.02 |
| 11 | FMPP | 120 | 30.59 | 19.08 | 647 | 5.70 | 1.81 | 5.37 |
| 11 | TAL | 120 | 16.49 | -1.16 | 648 | 4.89 | -4.12 | 3.37 |
| 11 | GVL | 120 | 24.93 | 12.52 | 648 | 6.84 | -4.48 | 3.64 |
| 11 | SEC | 74 | 403.20 | 58.30 | 621 | 38.13 | 17.38 | 10.57 |
| 11 | HST | 111 | 223.93 | 11.32 | 648 | 7.24 | 0.37 | 30.92 |
| 11 | **SOCO** | 96 | 4.32 | -3.00 | 648 | 4.82 | -4.06 | 0.90 |
| 12 | **SOCO** | 26 | 6.53 | -5.12 | 276 | 4.13 | -3.82 | 1.58 |
| 12 | TAL | 119 | 100.32 | 48.53 | 672 | 4.88 | -4.62 | 20.54 |
| 12 | AEC | 120 | 135.93 | 132.94 | 623 | 94.74 | 95.11 | 1.43 |
| 12 | FPC | 120 | 18.24 | -18.57 | 672 | 20.54 | -20.85 | 0.89 |
| 13 | **MISO** | 120 | 4.60 | 4.84 | 648 | 2.94 | 2.61 | 1.57 |
| 14 | **MISO** | 120 | 2.22 | 1.68 | 672 | 2.14 | 2.00 | 1.04 |
| 14 | **SOCO** | 120 | 3.56 | 0.77 | 673 | 3.72 | -3.08 | 0.96 |
| 15 | **MISO** | 120 | 5.77 | 5.75 | 647 | 2.62 | 2.47 | 2.20 |
| 16 | **FPL** | 120 | 3.99 | 2.20 | 672 | 2.85 | -1.14 | 1.40 |
| 16 | TEC | 120 | 34.65 | 19.23 | 672 | 4.95 | 1.54 | 7.00 |
| 16 | FPC | 120 | 16.46 | -12.54 | 672 | 22.46 | -22.74 | 0.73 |
| 16 | FMPP | 120 | 10.52 | 1.20 | 672 | 5.27 | 2.49 | 2.00 |
| 16 | SEC | 120 | 11.97 | -2.24 | 671 | 36.53 | -8.16 | 0.33 |
| 16 | JEA | 120 | 14.38 | 12.74 | 672 | 4.15 | 2.56 | 3.47 |
| 16 | GVL | 120 | 10.02 | 1.30 | 672 | 6.09 | -4.07 | 1.65 |
| 17 | FPC | 120 | 19.90 | -20.29 | 648 | 21.93 | -22.11 | 0.91 |
| 17 | TAL | 120 | 6.24 | 3.18 | 648 | 4.11 | -2.90 | 1.52 |
| 17 | SEC | 120 | 8.24 | -7.09 | 646 | 9.23 | -8.84 | 0.89 |
| 17 | GVL | 120 | 8.62 | -7.14 | 648 | 10.57 | -9.59 | 0.82 |
| 17 | JEA | 120 | 6.80 | 5.57 | 648 | 5.10 | 4.19 | 1.33 |
| 17 | **SOCO** | 120 | 1.79 | -1.53 | 648 | 2.20 | -1.73 | 0.81 |
| 18 | FPC | 120 | 20.32 | -20.53 | 552 | 23.45 | -23.63 | 0.87 |
| 18 | TAL | 120 | 8.59 | 3.82 | 672 | 3.76 | -2.80 | 2.28 |
| 18 | TEC | 120 | 7.86 | 4.68 | 552 | 4.59 | 1.61 | 1.71 |
| 18 | SEC | 119 | 9.53 | -5.16 | 551 | 9.99 | -9.11 | 0.95 |
| 18 | GVL | 120 | 14.07 | -3.64 | 552 | 9.49 | -6.48 | 1.48 |
| 18 | JEA | 120 | 8.02 | 7.27 | 552 | 4.71 | 2.92 | 1.70 |
| 18 | **SOCO** | 120 | 1.88 | -1.75 | 672 | 2.42 | -1.90 | 0.78 |
| 18 | DUK | 120 | 14.07 | 10.64 | 672 | 2.78 | -0.21 | 5.06 |
| 18 | CPLE | 120 | 2.77 | -1.01 | 672 | 3.06 | 0.57 | 0.91 |
| 18 | CPLW | 120 | 245.15 | 71.53 | 672 | 8.38 | 2.16 | 29.27 |
| 18 | SC | 120 | 8.91 | 8.56 | 672 | 4.15 | 3.50 | 2.15 |
| 18 | SCEG | 120 | 3.14 | -0.16 | 672 | 4.35 | -3.63 | 0.72 |
| 19 | FPC | 120 | 21.81 | -13.34 | 552 | 23.59 | -23.70 | 0.92 |
| 19 | TEC | 120 | 55.75 | 33.59 | 552 | 7.37 | -3.12 | 7.56 |
| 19 | **FPL** | 120 | 4.28 | 2.46 | 672 | 3.09 | 0.01 | 1.39 |
| 19 | FMPP | 120 | 3.35 | -1.66 | 672 | 4.25 | 0.64 | 0.79 |
| 19 | SEC | 115 | 8.12 | -6.05 | 551 | 9.65 | -9.31 | 0.84 |
| 19 | JEA | 120 | 7.24 | 5.46 | 552 | 3.87 | 2.17 | 1.87 |
| 19 | GVL | 120 | 7.88 | -7.61 | 552 | 8.42 | -8.35 | 0.94 |
| 19 | HST | 120 | 9.10 | 1.70 | 672 | 6.51 | 2.82 | 1.40 |

### Extreme-demand days (second check, demand only)

Days whose daily peak (over usable hours; days with at least 20) is above the BA's 99th percentile of daily peaks within that season of that season year (December counts with the next January and February): 2,135 BA-days out of 190,118. Each BA's MAPE on them against its other such days in the same seasons and years, then the median across BAs.

| Season | BAs | Median extreme-day MAPE (%) | Median other-day MAPE (%) | Median ratio | BAs with ratio > 1 |
| :-- | --: | --: | --: | --: | --: |
| All | 56 | 4.63 | 4.18 | 1.06 | 37 |
| DJF | 55 | 5.20 | 4.00 | 1.18 | 43 |
| MAM | 56 | 4.35 | 4.12 | 1.05 | 32 |
| JJA | 56 | 4.32 | 4.14 | 0.98 | 26 |
| SON | 56 | 4.56 | 4.24 | 1.01 | 28 |

## Q4. Did errors grow more where demand grew fastest?

49 BAs eligible in 2019 and 2025 (WACM, SPA left out for their footprint changes). x: mean demand over usable hours, 2025 / 2019 − 1. y: MAPE 2025 − MAPE 2019, percentage points.

- **Spearman ρ = -0.004, two-sided permutation p = 0.978** (10,000 permutations, seed 0).

Figure 4: `results/figures/q4_growth_vs_error.png`. ‡: published forecast inconsistent with demand in 2019 (see Notes).

| BA | Mean demand 2019 (MW) | Mean demand 2025 (MW) | Demand change (%) | MAPE 2019 (%) | MAPE 2025 (%) | MAPE change (pp) |
| :-- | --: | --: | --: | --: | --: | --: |
| DOPD | 208 | 278 | 33.8 | 8.60 | 6.48 | -2.12 |
| AZPS | 3,403 | 4,435 | 30.3 | 3.67 | 10.21 | 6.55 |
| **ERCO** | 43,798 | 55,744 | 27.3 | 2.35 | 2.46 | 0.11 |
| GCPD | 613 | 769 | 25.6 | 2.68 | 2.03 | -0.65 |
| SRP | 3,513 | 4,158 | 18.3 | 4.06 | 3.93 | -0.13 |
| TEPC‡ | 1,437 | 1,653 | 15.0 | 28.38 | 2.51 | -25.87 |
| **FPL** | 14,642 | 16,742 | 14.3 | 4.40 | 3.25 | -1.15 |
| PGE | 2,351 | 2,682 | 14.1 | 1.92 | 1.43 | -0.50 |
| LGEE | 3,961 | 4,422 | 11.6 | 5.03 | 7.73 | 2.70 |
| IPCO | 1,939 | 2,161 | 11.4 | 4.90 | 5.01 | 0.12 |
| **SWPP** | 30,962 | 34,110 | 10.2 | 3.44 | 7.77 | 4.33 |
| PACE | 5,566 | 6,119 | 9.9 | 3.90 | 4.11 | 0.22 |
| HST | 67 | 74 | 9.7 | 6.46 | 6.48 | 0.02 |
| BPAT | 6,376 | 6,977 | 9.4 | 1.90 | 2.00 | 0.10 |
| NEVP | 4,257 | 4,627 | 8.7 | 3.39 | 7.74 | 4.35 |
| FMPP | 2,041 | 2,211 | 8.4 | 5.55 | 4.27 | -1.28 |
| CHPD‡ | 209 | 226 | 8.1 | 137.65 | 2.97 | -134.67 |
| EPE | 975 | 1,046 | 7.3 | 2.96 | 3.13 | 0.17 |
| **TVA** | 18,197 | 19,490 | 7.1 | 2.28 | 2.31 | 0.03 |
| FPC | 6,230 | 6,642 | 6.6 | 21.75 | 23.27 | 1.52 |
| **PJM** | 91,169 | 96,493 | 5.8 | 3.65 | 3.44 | -0.21 |
| TIDC | 309 | 325 | 5.1 | 2.62 | 3.06 | 0.44 |
| PNM | 1,596 | 1,669 | 4.6 | 2.77 | 6.38 | 3.61 |
| TEC | 2,460 | 2,554 | 3.8 | 4.05 | 4.53 | 0.48 |
| **CISO** | 24,894 | 25,734 | 3.4 | 3.59 | 8.28 | 4.69 |
| IID | 422 | 436 | 3.2 | 3.16 | 3.47 | 0.31 |
| DUK | 12,193 | 12,542 | 2.9 | 2.67 | 2.57 | -0.10 |
| **MISO** | 74,149 | 75,708 | 2.1 | 3.22 | 2.38 | -0.84 |
| JEA | 1,546 | 1,578 | 2.1 | 6.01 | 4.72 | -1.29 |
| BANC | 1,966 | 2,007 | 2.1 | 2.59 | 2.40 | -0.19 |
| CPLE | 7,073 | 7,218 | 2.1 | 4.02 | 4.28 | 0.26 |
| GVL | 242 | 246 | 1.7 | 6.57 | 10.90 | 4.33 |
| AVA | 1,472 | 1,487 | 1.0 | 2.78 | 1.72 | -1.07 |
| TAL | 327 | 330 | 1.0 | 3.24 | 4.16 | 0.92 |
| SCEG | 2,812 | 2,838 | 0.9 | 4.51 | 4.89 | 0.38 |
| SCL | 1,077 | 1,082 | 0.4 | 2.43 | 3.39 | 0.96 |
| **SOCO** | 27,551 | 27,553 | 0.0 | 3.93 | 1.22 | -2.71 |
| PACW | 2,361 | 2,311 | -2.1 | 3.13 | 11.36 | 8.23 |
| **ISNE** | 13,503 | 13,159 | -2.5 | 2.42 | 2.52 | 0.10 |
| **NYIS** | 17,774 | 17,315 | -2.6 | 2.91 | 2.70 | -0.21 |
| WAUW | 94 | 91 | -3.7 | 6.26 | 14.14 | 7.88 |
| AECI | 2,680 | 2,548 | -4.9 | 3.88 | 1.55 | -2.34 |
| PSCO | 5,449 | 5,174 | -5.0 | 3.04 | 7.54 | 4.50 |
| WALC | 1,085 | 1,030 | -5.1 | 16.72 | 12.03 | -4.69 |
| CPLW | 583 | 552 | -5.3 | 4.14 | 4.22 | 0.08 |
| TPWR | 553 | 518 | -6.3 | 2.89 | 2.24 | -0.65 |
| NWMT | 1,439 | 1,344 | -6.6 | 4.63 | 2.30 | -2.34 |
| LDWP | 3,067 | 2,818 | -8.1 | 6.97 | 11.70 | 4.72 |
| PSEI | 3,384 | 2,838 | -16.1 | 47.64 | 29.90 | -17.74 |

## Q5. How many BAs lose to the naive forecast each year?

Skill below 0: the BA's forecast has a higher MAPE than demand 24 hours earlier, on the same hours. Sorted from the worst skill; the 10 largest BAs in bold; ‡: marked (see Notes).

| Year | Eligible BAs | Losing | Share (%) | BAs |
| :-- | --: | --: | --: | --: |
| 2016 | 56 | 20 | 35.7 | CHPD‡, AEC, PSEI, FPC, TEPC, AVA, SEC, DOPD, WALC, OVEC, PACE, GVL, WACM, WAUW, **FPL**, IID, HST, NWMT, SRP, NSB |
| 2017 | 55 | 17 | 30.9 | CHPD‡, AEC, PSEI, WALC, FPC, AVA, TEPC, DOPD, SEC, IPCO, GVL, **FPL**, PACW, SRP, WAUW, NWMT, PACE |
| 2018 | 54 | 13 | 24.1 | CHPD‡, PSEI, AEC, WALC, TEPC‡, FPC, AVA, DOPD, WACM, IPCO, NEVP, SRP, LDWP |
| 2019 | 53 | 12 | 22.6 | CHPD‡, AEC, PSEI, WALC, FPC, TEPC‡, DOPD, LDWP, WACM, IPCO, NWMT, WAUW |
| 2020 | 51 | 11 | 21.6 | CHPD‡, AEC, WALC, FPC, TEPC, DOPD, PACE, LDWP, WACM, HST, SPA |
| 2021 | 54 | 13 | 24.1 | CHPD‡, AEC, PSEI, WALC, WACM, TEPC, FPC, LDWP, PNM, PACE, HST, SPA, DOPD |
| 2022 | 53 | 10 | 18.9 | PSEI, FPC, WALC, TEPC, WACM, PNM, LDWP, PACE, NEVP, SPA |
| 2023 | 53 | 15 | 28.3 | SPA, PSEI, FPC, WACM, WALC, GVL, DOPD, PNM, TEPC, WAUW, NEVP, PACE, **CISO**, LDWP, LGEE |
| 2024 | 53 | 14 | 26.4 | WALC, PSEI, SPA, FPC, WACM, DOPD, NEVP, GVL, PNM, WAUW, **CISO**, LDWP, PACE, LGEE |
| 2025 | 53 | 19 | 35.8 | PSEI, FPC, SPA, WAUW, PACW, WACM, NEVP, WALC, AZPS, **SWPP**, **CISO**, GVL, DOPD, PNM, LDWP, PSCO, IPCO, PACE, LGEE |

### Checks inside EIA-930 for the 10 largest BAs that lose

Step 1 of the plan's checks. Repeated forecast: share of the BA-year's usable hours whose forecast repeats inside a run of 6+ equal hours. Shifted MAPE: the forecast moved by −24, −1, 0, +1, +24 hours (moved by +k: the value published for hour t − k is scored against demand at t), on the usable hours where all five exist; "best shift" is the lowest. R5: hours with both values R5 drops that year, and hours the exception rule gives back. Months and hours (local hour ending) where skill is below 0.

| BA-year | Skill | Repeated forecast (%) | MAPE shifted −24/−1/0/+1/+24 h (%) | Best shift | R5 drops | R5 given back | BA events | Months losing | Hours losing |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| CISO 2023 | -0.13 | 0.0 | 7.21 / 8.08 / 5.47 / 3.59 / 7.11 | +1 h | 213 (2.4%) | 0 | none | Jan, Feb, Mar, Apr, May, Jun, Jul, Sep, Nov, Dec | 14 of 24: 1-4, 6-7, 10-13, 18-19, 23-24 |
| CISO 2024 | -0.43 | 0.0 | 8.55 / 9.10 / 6.99 / 5.53 / 8.22 | +1 h | 225 (2.6%) | 41 | none | Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec | 14 of 24: 1-4, 6-7, 10-15, 23-24 |
| CISO 2025 | -0.78 | 0.0 | 9.43 / 9.91 / 8.27 / 7.20 / 9.35 | +1 h | 434 (5.0%) | 84 | none | Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec | 15 of 24: 1-4, 7, 9-16, 23-24 |
| FPL 2016 | -0.05 | 0.0 | 6.72 / 8.25 / 5.59 / 5.97 / 7.33 | none | 0 (0.0%) | 0 | none | Jun, Jul, Aug, Sep, Oct, Nov, Dec | 11 of 24: 1-4, 17, 19-24 |
| FPL 2017 | -0.08 | 0.0 | 7.08 / 8.70 / 6.24 / 6.58 / 8.48 | none | 7 (0.1%) | 0 | none | Jan, Feb, Mar, Jun, Jul, Nov, Dec | 13 of 24: 1-5, 17-24 |
| SWPP 2025 | -0.79 | 0.0 | 8.69 / 8.14 / 7.76 / 8.13 / 9.00 | none | 63 (0.7%) | 0 | none | May, Jun, Jul, Aug, Sep, Oct, Nov, Dec | 24 of 24: 1-24 |

Step 2 of the plan (comparing a few weeks against the operator's own published load and day-ahead forecast) needs downloads from outside EIA and has not been done; we ask before downloading anything.

## Robustness

Each variant re-runs the whole audit with one change. Eligibility, the panel and the Q4 BAs are recomputed for each variant (counts in the second table).

| Variant | Change from the main run | Median 2025 MAPE (%) | National 2025 WAPE (%) | Panel-median slope 2016–2025 (pp/yr) | BAs worse / better (Q2) | Spearman ρ (Q4) | BAs losing to naive in 2025 (Q5) |
| :-- | :-- | --: | --: | --: | --: | --: | --: |
| Main | — | 4.16 | 4.24 | 0.010 | 11 / 10 | -0.004 | 19 |
| EIA adjusted demand | Adjusted demand is the truth; all rules re-applied to it, except R4 | 4.16 | 4.23 | 0.020 | 10 / 9 | 0.011 | 19 |
| Without R5 | No energy-balance rule | 4.16 | 4.24 | -0.008 | 11 / 10 | -0.070 | 19 |
| R2 with N = 3 | Repeated-demand runs of 3 hours or more dropped | 4.16 | 4.24 | 0.010 | 11 / 9 | 0.005 | 19 |
| R2 with N = 12 | Only runs of 12 hours or more dropped | 4.16 | 4.24 | 0.010 | 11 / 10 | -0.004 | 19 |
| Repeated forecasts dropped | R2b (forecast runs of 6 hours or more) applied | 4.16 | 4.23 | 0.010 | 11 / 10 | 0.027 | 19 |

| Variant | Eligible BAs 2025 | Panel BAs | BAs tested for trend | Q4 BAs | Scored hours 2016–2025 |
| :-- | --: | --: | --: | --: | --: |
| Main | 53 | 50 | 52 | 49 | 4,582,331 |
| EIA adjusted demand | 53 | 50 | 52 | 49 | 4,599,581 |
| Without R5 | 53 | 51 | 53 | 50 | 4,658,548 |
| R2 with N = 3 | 53 | 50 | 52 | 49 | 4,574,117 |
| R2 with N = 12 | 53 | 50 | 52 | 49 | 4,582,454 |
| Repeated forecasts dropped | 53 | 50 | 52 | 49 | 4,574,441 |

## Notes

- ‡ Published forecast inconsistent with demand, not a forecasting failure (user, 2026-10-28): CHPD 2016-01 to 2021-06 (about 2.4x); TEPC 2018-10 to 2019-05 (1.2-2.2x). Their results stay in; yearly cells and events that overlap these months carry the mark.
- Local time is EIA's "Local Time at End of Hour". Some BAs report it in standard time all year (for example MISO, LGEE, EPE, PNM and WACM), so their hour of day does not follow daylight-saving time.
- Choices where the plan is silent:
  - MAPE, WAPE and bias use all usable hours; skill uses the usable hours that have a naive value, so the forecast and the naive forecast are scored on the same hours.
  - Holidays are the plan's table (pandas' rules for the six federal ones); the other federal holidays (Martin Luther King Jr. Day, Washington's Birthday, Juneteenth, Columbus Day, Veterans Day) are not in it and are treated as ordinary days. A BA's event days are left out of both its holiday and its comparison days.
  - Event windows are kept whole, holidays included (Winter Storm Elliott covers Christmas Eve and Day 2022). Bias is reported for the window and the baseline; the ratio is for MAPE only, because a bias near zero makes a ratio meaningless.
  - Extreme-demand days are compared with the BA's other days that also have at least 20 usable hours, pooled over all its seasons and years.
  - Mann–Kendall uses the normal approximation with the tie and continuity corrections. The permutation p-value counts the observed order: (b + 1) / (10,000 + 1).
  - In each robustness variant, eligibility, the panel and the Q4 BAs follow that variant's usable hours.
- Usable hours (R1, R2 with N = 6, R3a, R4, R5 with its exemptions, R3b): 5,038,714, as in `results/data_quality.md`.
- No result was used to change a rule, a threshold or the plan.
