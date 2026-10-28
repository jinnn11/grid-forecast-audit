# Schema check: EIA-930 BALANCE files

22 six-month files, each from `https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/` plus the file name. The download time is the file's modification time.

## Files

| File | Bytes | Downloaded (UTC) | SHA-256 |
| :-- | --: | --: | --: |
| EIA930_BALANCE_2015_Jul_Dec.csv | 30,973,894 | 2026-10-27 00:53 | `865870fbaeb8cc82081707ece53fb3f03b1ef78eab3e63143728c3ef671e629f` |
| EIA930_BALANCE_2016_Jan_Jun.csv | 30,566,131 | 2026-10-27 00:53 | `19e19e0becf86e9d3984d2e4199e8a77a33671a9cc27967562d383473a85cd10` |
| EIA930_BALANCE_2016_Jul_Dec.csv | 30,992,986 | 2026-10-27 00:53 | `9c5f376580ac794450d117e371e2694fbe6d53f75eacdf67e8ebe943b2003e5a` |
| EIA930_BALANCE_2017_Jan_Jun.csv | 30,416,510 | 2026-10-27 00:53 | `68abe29cd6196bc3c73d1b28531b8a77464615ecbff7e79282c32e52ddb5d981` |
| EIA930_BALANCE_2017_Jul_Dec.csv | 31,018,149 | 2026-10-27 00:53 | `2097bc2737ffc4e1689f6ed3c5a5f16814187cfafead3e7e672f8342b793d163` |
| EIA930_BALANCE_2018_Jan_Jun.csv | 30,287,937 | 2026-10-27 00:53 | `d8435a41ee74b7fa234014e3c749eb278fca86fc8dfcc3348a8f0a1607fda296` |
| EIA930_BALANCE_2018_Jul_Dec.csv | 44,213,835 | 2026-10-27 00:53 | `fadc93f9b574c2460594bc98e7c39014c942233eb1447455cb62c9b0a1a63fc1` |
| EIA930_BALANCE_2019_Jan_Jun.csv | 43,369,791 | 2026-10-27 00:53 | `02548d6bc49f3cffba1e66eb83a42e1d40194b1301f0f872baf2945e615af1b0` |
| EIA930_BALANCE_2019_Jul_Dec.csv | 44,134,576 | 2026-10-27 00:53 | `5ec5c85be997c6c56bdcf42be3443a4bb6eb0851d704065c11c02eac0d3c48d1` |
| EIA930_BALANCE_2020_Jan_Jun.csv | 42,970,027 | 2026-10-27 00:53 | `fff83ed20365e69933bdd6ebde06afaa8083930c613363c438844b0fd52034cf` |
| EIA930_BALANCE_2020_Jul_Dec.csv | 43,635,740 | 2026-10-27 00:53 | `47788a718c26eae5a2453e3471c2b9e7d1a11062a0de70e2dca803163de5a754` |
| EIA930_BALANCE_2021_Jan_Jun.csv | 43,073,764 | 2026-10-27 00:53 | `40b183f333e0f3edc1b9a2ed48b792eff00fd477915dae79ce5784e862380f7f` |
| EIA930_BALANCE_2021_Jul_Dec.csv | 43,438,192 | 2026-10-27 00:53 | `66afadcab6865f74cebd6db82e363a66976846241c040cba66baf240afcd669b` |
| EIA930_BALANCE_2022_Jan_Jun.csv | 42,567,904 | 2026-10-27 00:53 | `d3d315a0c29d9527a1c64cf6ddcdcc5c0b7281fddd99199bd70f06d242e503d5` |
| EIA930_BALANCE_2022_Jul_Dec.csv | 42,909,865 | 2026-10-27 00:53 | `267575c29ef40f386bcf3bc3993013b9ce13a3a154b89b702559a75dd742976d` |
| EIA930_BALANCE_2023_Jan_Jun.csv | 41,981,693 | 2026-10-27 00:54 | `a0e14e9c07ab4cc1de3e384c7be890b0c61d9de3fe04ad3ae5ec739f1f35ec1b` |
| EIA930_BALANCE_2023_Jul_Dec.csv | 42,574,041 | 2026-10-27 00:54 | `c719fc1b513eec8982ce209b6e3173fc64b2d0d243f83d3bf0d8d1adf6222de2` |
| EIA930_BALANCE_2024_Jan_Jun.csv | 41,742,812 | 2026-10-27 00:54 | `26768c495c3ba987e29d79df2e40d4e741f9dbcff086f53c12ff774465756a10` |
| EIA930_BALANCE_2024_Jul_Dec.csv | 47,928,993 | 2026-10-27 00:54 | `a602a8e577cfdd2fa3083413eaa4dd8ba7f0d2b26a2986f8f6d22917465ea49f` |
| EIA930_BALANCE_2025_Jan_Jun.csv | 47,565,054 | 2026-10-27 00:54 | `fac4bb991dfa1dab3b4b35300ccab54ac99be13a40ce91954db8ddafb2816242` |
| EIA930_BALANCE_2025_Jul_Dec.csv | 48,256,021 | 2026-10-27 00:54 | `1146158b972439db7c7f4cc7d0491e07644ddbf244d03b8ecb44cb2c833d10f1` |
| EIA930_BALANCE_2026_Jan_Jun.csv | 47,107,225 | 2026-10-27 00:33 | `1b3eaf7b0af08393f4d1593125b0c0f502f93e036d961b7dd6d50fc8e618582f` |

## Columns

Reference header: `EIA930_BALANCE_2026_Jan_Jun.csv` (65 columns).

All 22 files have the required columns ("Balancing Authority", "UTC Time at End of Hour", "Demand (MW)", "Demand Forecast (MW)", "Demand (MW) (Imputed)", "Demand (MW) (Adjusted)", "Net Generation (MW)", "Total Interchange (MW)").

### 2015 H2 to 2018 H1 (19 columns)

- Missing compared with the reference (46): `Net Generation (MW) from Coal`, `Net Generation (MW) from Natural Gas`, `Net Generation (MW) from Nuclear`, `Net Generation (MW) from All Petroleum Products`, `Net Generation (MW) from Hydropower Excluding Pumped Storage`, `Net Generation (MW) from Pumped Storage`, `Net Generation (MW) from Solar without Integrated Battery Storage`, `Net Generation (MW) from Solar with Integrated Battery Storage`, `Net Generation (MW) from Wind without Integrated Battery Storage`, `Net Generation (MW) from Wind with Integrated Battery Storage`, `Net Generation (MW) from Battery Storage`, `Net Generation (MW) from Other Energy Storage`, `Net Generation (MW) from Unknown Energy Storage`, `Net Generation (MW) from Geothermal`, `Net Generation (MW) from Other Fuel Sources`, `Net Generation (MW) from Unknown Fuel Sources`, `Net Generation (MW) from Coal (Imputed)`, `Net Generation (MW) from Natural Gas (Imputed)`, `Net Generation (MW) from Nuclear (Imputed)`, `Net Generation (MW) from All Petroleum Products (Imputed)`, `Net Generation (MW) from Hydropower Excluding Pumped Storage (Imputed)`, `Net Generation (MW) from Pumped Storage (Imputed)`, `Net Generation (MW) from Solar without Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Solar with Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Wind without Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Wind with Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Battery Storage (Imputed)`, `Net Generation (MW) from Other Energy Storage (Imputed)`, `Net Generation (MW) from Unknown Energy Storage (Imputed)`, `Net Generation (MW) from Geothermal (Imputed)`, `Net Generation (MW) from Other Fuel Sources (Imputed)`, `Net Generation (MW) from Coal (Adjusted)`, `Net Generation (MW) from Natural Gas (Adjusted)`, `Net Generation (MW) from Nuclear (Adjusted)`, `Net Generation (MW) from All Petroleum Products (Adjusted)`, `Net Generation (MW) from Hydropower Excluding Pumped Storage (Adjusted)`, `Net Generation (MW) from Pumped Storage  (Adjusted)`, `Net Generation (MW) from Solar without Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Solar witho Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Wind without Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Wind with Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Battery Storage (Adjusted)`, `Net Generation (MW) from Other Energy Storage (Adjusted)`, `Net Generation (MW) from Unknown Energy Storage (Adjusted)`, `Net Generation (MW) from Geothermal (Adjusted)`, `Net Generation (MW) from Other Fuel Sources (Adjusted)`
- Not in the reference (0): none

### 2018 H2 to 2024 H1 (44 columns)

- Missing compared with the reference (30): `Net Generation (MW) from Hydropower Excluding Pumped Storage`, `Net Generation (MW) from Pumped Storage`, `Net Generation (MW) from Solar without Integrated Battery Storage`, `Net Generation (MW) from Solar with Integrated Battery Storage`, `Net Generation (MW) from Wind without Integrated Battery Storage`, `Net Generation (MW) from Wind with Integrated Battery Storage`, `Net Generation (MW) from Battery Storage`, `Net Generation (MW) from Other Energy Storage`, `Net Generation (MW) from Unknown Energy Storage`, `Net Generation (MW) from Geothermal`, `Net Generation (MW) from Hydropower Excluding Pumped Storage (Imputed)`, `Net Generation (MW) from Pumped Storage (Imputed)`, `Net Generation (MW) from Solar without Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Solar with Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Wind without Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Wind with Integrated Battery Storage (Imputed)`, `Net Generation (MW) from Battery Storage (Imputed)`, `Net Generation (MW) from Other Energy Storage (Imputed)`, `Net Generation (MW) from Unknown Energy Storage (Imputed)`, `Net Generation (MW) from Geothermal (Imputed)`, `Net Generation (MW) from Hydropower Excluding Pumped Storage (Adjusted)`, `Net Generation (MW) from Pumped Storage  (Adjusted)`, `Net Generation (MW) from Solar without Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Solar witho Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Wind without Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Wind with Integrated Battery Storage (Adjusted)`, `Net Generation (MW) from Battery Storage (Adjusted)`, `Net Generation (MW) from Other Energy Storage (Adjusted)`, `Net Generation (MW) from Unknown Energy Storage (Adjusted)`, `Net Generation (MW) from Geothermal (Adjusted)`
- Not in the reference (9): `Net Generation (MW) from Hydropower and Pumped Storage`, `Net Generation (MW) from Solar`, `Net Generation (MW) from Wind`, `Net Generation (MW) from Hydropower and Pumped Storage (Imputed)`, `Net Generation (MW) from Solar (Imputed)`, `Net Generation (MW) from Wind (Imputed)`, `Net Generation (MW) from Hydropower and Pumped Storage (Adjusted)`, `Net Generation (MW) from Solar (Adjusted)`, `Net Generation (MW) from Wind (Adjusted)`

### 2024 H2 to 2026 H1 (65 columns)

- Missing compared with the reference (0): none
- Not in the reference (0): none

## Rows

| Half-year | Rows | BAs | BAs with demand | First hour (UTC) | Last hour (UTC) | Demand reported (%) | Adjusted demand reported (%) |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 2015 H2 | 293,717 | 67 | 56 | 2015-07-01 05:00 | 2016-01-01 08:00 | 80.1 | 81.1 |
| 2016 H1 | 288,235 | 66 | 56 | 2016-01-01 06:00 | 2016-07-01 07:00 | 82.8 | 84.0 |
| 2016 H2 | 291,509 | 66 | 56 | 2016-07-01 05:00 | 2017-01-01 08:00 | 83.7 | 84.4 |
| 2017 H1 | 286,651 | 66 | 56 | 2017-01-01 06:00 | 2017-07-01 07:00 | 83.7 | 84.2 |
| 2017 H2 | 291,509 | 66 | 56 | 2017-07-01 05:00 | 2018-01-01 08:00 | 83.9 | 84.3 |
| 2018 H1 | 285,235 | 66 | 56 | 2018-01-01 06:00 | 2018-07-01 07:00 | 83.8 | 84.6 |
| 2018 H2 | 290,046 | 66 | 56 | 2018-07-01 05:00 | 2019-01-01 08:00 | 81.8 | 82.7 |
| 2019 H1 | 282,307 | 65 | 55 | 2019-01-01 06:00 | 2019-07-01 07:00 | 84.0 | 84.3 |
| 2019 H2 | 287,093 | 65 | 55 | 2019-07-01 05:00 | 2020-01-01 08:00 | 84.2 | 84.4 |
| 2020 H1 | 279,668 | 66 | 55 | 2020-01-01 06:00 | 2020-07-01 07:00 | 82.6 | 82.8 |
| 2020 H2 | 282,676 | 64 | 54 | 2020-07-01 05:00 | 2021-01-01 08:00 | 82.0 | 82.8 |
| 2021 H1 | 277,964 | 64 | 54 | 2021-01-01 06:00 | 2021-07-01 07:00 | 84.0 | 84.1 |
| 2021 H2 | 279,747 | 64 | 54 | 2021-07-01 05:00 | 2022-01-01 08:00 | 84.2 | 84.2 |
| 2022 H1 | 273,621 | 63 | 53 | 2022-01-01 06:00 | 2022-07-01 07:00 | 83.8 | 84.1 |
| 2022 H2 | 275,330 | 63 | 53 | 2022-07-01 05:00 | 2023-01-01 08:00 | 85.0 | 85.0 |
| 2023 H1 | 269,278 | 62 | 53 | 2023-01-01 06:00 | 2023-07-01 07:00 | 85.5 | 85.5 |
| 2023 H2 | 272,378 | 62 | 53 | 2023-07-01 05:00 | 2024-01-01 08:00 | 85.8 | 85.9 |
| 2024 H1 | 266,398 | 61 | 53 | 2024-01-01 06:00 | 2024-07-01 07:00 | 86.8 | 86.9 |
| 2024 H2 | 269,426 | 61 | 53 | 2024-07-01 05:00 | 2025-01-01 08:00 | 86.8 | 86.9 |
| 2025 H1 | 264,934 | 62 | 53 | 2025-01-01 06:00 | 2025-07-01 07:00 | 86.8 | 86.9 |
| 2025 H2 | 267,218 | 61 | 53 | 2025-07-01 05:00 | 2026-01-01 08:00 | 87.4 | 87.6 |
| 2026 H1 | 260,590 | 62 | 55 | 2026-01-01 06:00 | 2026-07-01 07:00 | 87.5 | 87.6 |

## Duplicates

- Identical BA/hour rows in more than one file, dropped: 0
- BA/hour rows that disagree between files: none

## Units

- The columns we use have the same names in every file, so every file states them in MW: "Demand (MW)", "Demand Forecast (MW)", "Demand (MW) (Imputed)", "Demand (MW) (Adjusted)", "Net Generation (MW)", "Total Interchange (MW)".
- Magnitude check: BA half-years whose median positive demand is below 0.67 or above 1.50 times the BA's previous half-year. A shift can mean a footprint change, a unit change or bad data; these are reported, not corrected. 6 flagged.

| BA | Half-year | Previous median (MW) | Median (MW) | Ratio |
| :-- | --: | --: | --: | --: |
| CHPD | 2016 H1 | 415 | 172 | 0.41 |
| SEC | 2019 H1 | 205 | 136 | 0.67 |
| SEC | 2019 H2 | 136 | 65 | 0.48 |
| SEC | 2020 H1 | 65 | 318 | 4.89 |
| SEC | 2021 H1 | 367 | 199 | 0.54 |
| SPA | 2023 H2 | 64 | 23 | 0.36 |
