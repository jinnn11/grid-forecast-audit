# Battery check: does the forecast gap track charging? (exploratory)

**Exploratory, not in the pre-registered plan** (`docs/step3_audit_plan.md`). Asked by the user on 2026-10-30 after the CISO check found that CAISO's actual load counts battery charging and its day-ahead forecast does not (`results/ciso_check.md`). Nothing here changes the audit. No new downloads: EIA-930's cached BALANCE files only.

## Findings

- 18 BAs report `Battery Storage` in EIA-930 in 2025; 4 of them never report charging (no value below 0): TVA, AZPS, ISNE, LDWP. CISO leaves that column blank; its row uses `Other Fuel Sources`, which matches CAISO's own battery output (`results/ciso_check.md`).
- Among BAs whose charging is at least 1% of demand, the forecast gap moves with charging as CISO's does (at least 0.5 MW per MW of charging; a reading, not a test) only for CISO. It does not for PNM, IID, PGE, IPCO, SRP, TEPC; for all of them taking charging out of demand makes the MAPE worse, which fits demand that already leaves charging out, as EIA's instructions ask.
- Too little charging to tell (under 1% of demand): PSCO, ERCO, DUK, MISO, SOCO, FPL, CPLE, FPC. ERCO reports charging as large as 5,101 MW but in only 266 of 8,688 hours, so its battery series is almost discharge only.

## Per BA

The audit's usable hours in 2025 (main run) that have a storage value. Charging: −(net generation from storage) where it is below 0. Gap: demand − forecast = a + b × charging + c × discharging, b / c (R²); b near 1 means the gap grows MW for MW with charging. Arrows: as published → against demand less charging. CISO's demand and storage column are moved back an hour where EIA-930 has them late.

| BA | Storage column | Hours | Hours charging | Peak charging (MW) | Charging (% of demand) | Gap b / c (R²) | Bias (%) | MAPE (%) |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |
| PNM | Battery storage | 8,014 | 4,134 | 704 | 6.54 | 0.09 / -0.02 (0.07) | -5.99 → 0.59 | 6.16 → 9.44 |
| CISO | Other fuel sources | 8,227 | 4,119 | 8,504 | 5.87 | 0.95 / -0.05 (0.90) | -6.59 → -0.76 | 7.10 → 2.38 |
| IID | Battery storage | 8,172 | 4,091 | 182 | 5.81 | -0.04 / 0.02 (0.01) | 0.40 → 6.59 | 3.47 → 12.79 |
| PGE | Battery storage | 8,760 | 5,491 | 489 | 2.27 | 0.02 / 0.02 (0.00) | 0.31 → 2.63 | 1.43 → 3.69 |
| IPCO | Battery storage | 8,640 | 5,166 | 419 | 2.11 | -0.21 / 0.03 (0.01) | -0.36 → 1.79 | 5.02 → 6.49 |
| SRP | Battery storage | 6,807 | 3,682 | 454 | 1.38 | -0.14 / 0.14 (0.01) | -2.24 → -0.87 | 3.79 → 4.19 |
| TEPC | Battery storage | 8,592 | 4,470 | 228 | 1.38 | -0.06 / 0.00 (0.00) | -0.14 → 1.25 | 2.50 → 3.88 |
| PSCO | Battery storage | 3,696 | 1,385 | 217 | 0.09 | 1.56 / 1.09 (0.27) | -7.60 → -7.51 | 8.00 → 7.95 |
| ERCO | Battery storage | 8,688 | 266 | 5,101 | 0.06 | 0.35 / 0.11 (0.01) | 1.19 → 1.25 | 2.46 → 2.51 |
| DUK | Battery storage | 1,824 | 414 | 50 | 0.06 | 1.64 / -3.72 (0.02) | 0.50 → 0.56 | 2.89 → 2.90 |
| MISO | Battery storage | 8,401 | 4,660 | 487 | 0.05 | 0.73 / -3.22 (0.02) | 2.02 → 2.07 | 2.42 → 2.46 |
| SOCO | Battery storage | 8,636 | 4,048 | 65 | 0.04 | -1.49 / 0.83 (0.01) | -0.96 → -0.92 | 1.21 → 1.17 |
| FPL | Battery storage | 3,216 | 1,194 | 68 | 0.03 | -6.34 / 0.72 (0.02) | -0.03 → 0.00 | 3.08 → 3.10 |
| CPLE | Battery storage | 6,912 | 389 | 102 | 0.02 | 0.71 / -1.29 (0.00) | 1.64 → 1.66 | 4.04 → 4.05 |
| FPC | Battery storage | 4,992 | 1,313 | 5 | 0.00 | -94.94 / 256.46 (0.06) | -23.00 → -23.00 | 22.85 → 22.84 |
| TVA | Battery storage | 7,081 | 0 | 0 | 0.00 | 0.00 / 0.00 (0.00) | 1.25 → 1.25 | 2.16 → 2.16 |
| AZPS | Battery storage | 6,888 | 0 | 0 | 0.00 | 0.00 / 0.11 (0.01) | -5.62 → -5.62 | 9.79 → 9.79 |
| ISNE | Battery storage | 8,758 | 0 | 0 | 0.00 | 0.00 / -2.30 (0.04) | -1.65 → -1.65 | 2.52 → 2.52 |
| LDWP | Battery storage | 8,243 | 0 | 0 | 0.00 | 0.00 / -13.34 (0.00) | -8.96 → -8.96 | 10.55 → 10.55 |
