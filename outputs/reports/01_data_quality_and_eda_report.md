# Phase 1-2: Data Quality & Exploratory Data Analysis

## Dataset overview

| Dataset | Rows | Columns | Coverage |
| --- | --- | --- | --- |
| Annual | 5 | 19 | 2021-2025 |
| Quarterly | 5 | 14 | 2024-Q4 to 2025-Q4 |

**Duplicates:** annual: 0, quarterly: 0, annual (year key): 0, quarterly (period key): 0.

## Missing values

All reported financial fields are complete. Gaps only appear in derived or partially supplied columns:

| dataset | column | missing |
| --- | --- | --- |
| annual | sales_marketing_expense_eur_millions | 2 |
| annual | premium_subscriber_net_adds_millions | 1 |
| annual | mau_net_adds_millions | 1 |
| annual | premium_revenue_per_avg_subscriber_per_month_eur_approx | 1 |
| annual | sales_marketing_per_net_added_premium_subscriber_eur_proxy | 2 |

- `sales_marketing_expense_eur_millions` is only supplied for 2023-2025, so the CAC proxy has 3 data points.
- Net-add and per-subscriber columns are blank for 2021 because they need a prior-year opening balance.

## Validation against reported totals

79 automated checks, **79 passed, 0 failed**
(full log: `data/processed/validation_checks.csv`).

| check | result |
| --- | --- |
| 2024-Q4 = year-end 2024 (ad_supported_mau_millions) | 1/1 pass |
| 2024-Q4 = year-end 2024 (mau_millions) | 1/1 pass |
| 2024-Q4 = year-end 2024 (premium_subscribers_millions) | 1/1 pass |
| 2025-Q4 = year-end 2025 (ad_supported_mau_millions) | 1/1 pass |
| 2025-Q4 = year-end 2025 (mau_millions) | 1/1 pass |
| 2025-Q4 = year-end 2025 (premium_subscribers_millions) | 1/1 pass |
| Free cash flow <= operating cash flow | 10/10 pass |
| Gross profit - operating expenses = operating income | 10/10 pass |
| Gross profit / revenue = reported gross margin % | 10/10 pass |
| MAU net adds re-derived | 4/4 pass |
| Monthly premium ARPU re-derived | 4/4 pass |
| Operating income / revenue = reported operating margin % | 10/10 pass |
| Premium + ad-supported revenue = total revenue | 10/10 pass |
| Premium net adds re-derived | 4/4 pass |
| S&M per net premium add re-derived | 3/3 pass |
| Sum of 2025 quarters = annual 2025 (ad_supported_revenue_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (free_cash_flow_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (gross_profit_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (operating_cash_flow_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (operating_income_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (premium_revenue_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (total_operating_expenses_eur_millions) | 1/1 pass |
| Sum of 2025 quarters = annual 2025 (total_revenue_eur_millions) | 1/1 pass |

These checks confirm internal consistency: segment sums, margins, the P&L bridge, quarterly-to-annual totals and
year-end stocks. Before publishing, also spot-check the headline numbers against the Q4 2025 Shareholder Deck
(see `data/source_register.csv`).

### Observation: MAU overlap

Premium subscribers + ad-supported MAU exceed total MAU every year, by
10-15M. Spotify counts a user in both tiers if they
used both during the month, so **never add the two user counts together**.

## Reported vs calculated metrics

| Field | Status |
| --- | --- |
| year | Actual reported |
| mau_millions | Actual reported |
| premium_subscribers_millions | Actual reported |
| ad_supported_mau_millions | Actual reported |
| premium_revenue_eur_millions | Actual reported |
| ad_supported_revenue_eur_millions | Actual reported |
| total_revenue_eur_millions | Actual reported |
| gross_profit_eur_millions | Actual reported |
| gross_margin_pct | Actual reported |
| total_operating_expenses_eur_millions | Actual reported |
| operating_income_eur_millions | Actual reported |
| operating_margin_pct | Actual reported |
| operating_cash_flow_eur_millions | Actual reported |
| free_cash_flow_eur_millions | Actual reported |
| sales_marketing_expense_eur_millions | Actual reported; only 2023-2025 included here |
| premium_subscriber_net_adds_millions | Calculated from reported subscriber counts |
| premium_revenue_per_avg_subscriber_per_month_eur_approx | Analyst calculation / approximation, not Spotify-reported ARPU |
| sales_marketing_per_net_added_premium_subscriber_eur_proxy | Analyst proxy, NOT CAC |

## EDA highlights

| Metric | 2021 | 2025 | Change |
| --- | --- | --- | --- |
| Total revenue (EUR M) | 9,668.0 | 17,186.0 | 7,518.0 |
| Premium subscribers (M) | 180.0 | 290.0 | 110.0 |
| MAU (M) | 406.0 | 751.0 | 345.0 |
| Gross margin % | 26.8 | 32.0 | 5.2 |
| Operating income (EUR M) | 94.0 | 2,198.0 | 2,104.0 |
| Free cash flow (EUR M) | 277.0 | 2,874.0 | 2,597.0 |

- Revenue CAGR 2021-2025: **15.5%**; premium subscriber CAGR: **12.7%**;
  MAU CAGR: **16.6%**.
- Premium is 89.3% of 2025 revenue.
- Correlation between premium subscriber growth and revenue growth: r = 0.33 (n = 4). The sample is too small for
  statistical inference; treat this as descriptive only.
- Q4 is the strongest quarter for advertising (Q4 2025 ad revenue: €518M
  vs €419M in Q1).

Charts: `outputs/charts/01_*.png` through `04_*.png`.
