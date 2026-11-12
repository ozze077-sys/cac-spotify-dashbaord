# Phase 8: Scenario & Sensitivity Analysis (2025 base, 3% churn)

Each scenario changes one lever (or a defined combination) and keeps everything else at the 2025 base.
Churn rates are hypothetical. CAC figures are proxies (see Phase 5).

| Scenario | LTV (EUR) | LTV vs base % | CAC net (EUR) | CAC gross (EUR) | LTV:CAC net | LTV:CAC gross | Payback gross (mo) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Base case | 49.32 | 0.00 | 52.81 | 11.27 | 0.93 | 4.38 | 7.62 |
| Optimistic churn (2%) | 73.97 | 50.00 | 52.81 | 15.27 | 1.40 | 4.84 | 10.32 |
| Moderate-risk churn (4%) | 36.99 | -25.00 | 52.81 | 8.93 | 0.70 | 4.14 | 6.03 |
| High-risk churn (5%) | 29.59 | -40.00 | 52.81 | 7.39 | 0.56 | 4.00 | 5.00 |
| Marketing spend +10% | 49.32 | 0.00 | 58.10 | 12.40 | 0.85 | 3.98 | 8.38 |
| Marketing spend +20% | 49.32 | 0.00 | 63.38 | 13.52 | 0.78 | 3.65 | 9.14 |
| Gross margin +1pp | 50.86 | 3.13 | 52.81 | 11.27 | 0.96 | 4.51 | 7.39 |
| Gross margin +2pp | 52.40 | 6.25 | 52.81 | 11.27 | 0.99 | 4.65 | 7.17 |
| Gross margin +3pp | 53.94 | 9.38 | 52.81 | 11.27 | 1.02 | 4.79 | 6.96 |
| Subscriber growth slowdown (net adds -25%) | 49.32 | 0.00 | 70.42 | 12.03 | 0.70 | 4.10 | 8.13 |
| Subscriber growth slowdown (net adds -50%) | 49.32 | 0.00 | 105.63 | 12.89 | 0.47 | 3.83 | 8.71 |
| Subscription revenue -10% (ARPU) | 44.38 | -10.00 | 52.81 | 11.27 | 0.84 | 3.94 | 8.46 |
| Subscription revenue -5% (ARPU) | 46.85 | -5.00 | 52.81 | 11.27 | 0.89 | 4.16 | 8.02 |
| Subscription revenue +5% (ARPU) | 51.78 | 5.00 | 52.81 | 11.27 | 0.98 | 4.59 | 7.25 |
| Subscription revenue +10% (ARPU) | 54.25 | 10.00 | 52.81 | 11.27 | 1.03 | 4.81 | 6.92 |
| Combined downside | 35.14 | -28.75 | 77.46 | 10.36 | 0.45 | 3.39 | 7.37 |
| Combined upside | 66.02 | 33.88 | 52.81 | 12.97 | 1.25 | 5.09 | 7.86 |

**Combined downside:** 4% churn, S&M +10%, net adds -25%, ARPU -5%. **Combined upside:** 2.5% churn, gross margin +2pp,
ARPU +5%.

## What the scenarios show

- **Churn dominates LTV.** LTV ranges from €30 to €74 across
  the churn scenarios. No other single lever comes close.
- **Gross margin is a low-risk lever.** Each +1pp of gross margin adds about
  3.1% to LTV. That matches a
  3.1% price increase without the churn risk of raising prices.
- **Marketing +10% / +20%** lowers LTV:CAC (gross-adds proxy) from 4.38x to
  3.98x / 3.65x.
  Extra spend has to produce extra subscribers to pay off.
- **Growth slowdown:** if net adds fall 50% while S&M stays flat, the net-adds CAC proxy doubles to
  €106. The gross-adds proxy only rises to
  €12.89, because replacement acquisitions dominate gross adds.
- **Biggest lever (tornado):** for the gross-adds proxy it is *S&M spend -20% / +20%* (LTV:CAC
  5.47x-3.65x). For the net-adds proxy it is *Monthly churn 2% / 4%*
  (1.40x-0.70x).
- **Combined downside** takes LTV:CAC to 3.39x (gross) /
  0.45x (net). **Combined upside** reaches
  5.09x / 1.25x.

Charts: `17_ltv_sensitivity_heatmap.png`, `18_ltv_cac_sensitivity_heatmap.png`, `19_tornado_ltv_cac.png`.
