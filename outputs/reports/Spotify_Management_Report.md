# Spotify Historical Financial & Unit Economics: Management Report

*Scope: 2021-2025 annual results and 2024-Q4 to 2025-Q4 quarterly results, from Spotify's published investor materials.
All currency is EUR. Churn and CAC figures are analyst scenarios and proxies, not company disclosures.*

## Executive summary

Spotify has moved from loss-making growth to profitable scale. Since 2021, revenue is up **78%** against
premium subscriber growth of 61%. Gross margin rose from 25.0% (2022) to
**32.0%**, and operating income went from a €659M loss
to a **€2,198M profit**. The 2025 watch-points are slowing top-line growth
(9.7%) and falling advertising revenue (-1.0%).
Subscriber lifetime value depends heavily on churn, which Spotify does not disclose.

## Key metrics (2025)

| Metric | Value | Basis |
| --- | --- | --- |
| Total revenue (EUR M) | 17,186 | Reported |
| Revenue growth YoY % | 9.65 | Calculated |
| Revenue CAGR 2021-2025 % | 15.47 | Calculated |
| Premium subscribers (M) | 290 | Reported |
| MAU (M) | 751 | Reported |
| Premium net adds (M) | 27.00 | Calculated |
| Monthly premium ARPU (EUR) | 4.63 | Analyst approximation |
| Gross margin % | 31.98 | Reported |
| Operating margin % | 12.79 | Reported |
| Operating income (EUR M) | 2,198 | Reported |
| Free cash flow (EUR M) | 2,874 | Reported (non-IFRS) |
| S&M % of revenue | 8.30 | Calculated |
| CAC proxy, net adds (EUR) | 52.81 | Analyst proxy - not CAC |
| CAC proxy, gross adds @3% churn (EUR) | 11.27 | Analyst proxy - not CAC |
| LTV @3% churn (EUR) | 49.32 | Scenario estimate |
| LTV:CAC, net-adds proxy (x) | 0.93 | Scenario estimate |
| LTV:CAC, gross-adds proxy (x) | 4.38 | Scenario estimate |
| Payback, gross-adds proxy (months) | 7.62 | Scenario estimate |

## Answers to the business questions

**1. Is revenue growing faster than the subscriber base?** Over the full period, yes: revenue +78% vs
subscribers +61%. Year by year it is mixed. Revenue outgrew subscribers in 2022 and 2024 and lagged
slightly in 2023 and 2025. In 2025 the lag came from ad revenue; premium revenue alone grew
11.1% vs subscribers 10.3%.

**2. Revenue per Premium subscriber?** About **€4.63 per month**
(€56 per year) in 2025, up from €4.44 in 2022.

**3. Is Spotify becoming more profitable?** Yes, decisively. Operating margin went from
-5.6% (2022) to 12.8% (2025), and FCF margin from
0.2% to 16.7%. Operating expenses fell in absolute terms in 2024 and 2025.
**55%** of 2025's incremental revenue reached operating income.

**4. How efficiently does Spotify spend on sales & marketing?** Increasingly efficiently. S&M fell from
11.6% to 8.3% of revenue (2023-2025). S&M per net premium add held
near €51, while gross profit per subscriber grew, so payback on that proxy shortened from
44 to 36 months.

**5. Estimated Premium LTV?** About **€49** of lifetime gross profit at an assumed 3% monthly churn
(€30-€74 across the 2-5% scenarios).

**6. How sensitive is LTV to churn?** Highly. LTV moves inversely with churn: cutting churn from 3% to 2% adds
€25 (+50%), and rising to 5% removes 40%. Churn is the largest LTV driver tested.

**7. How long to recover acquisition cost?** The answer depends on the proxy. Charging all S&M to *net* adds gives a
36-month payback, longer than the 33-month expected lifetime at 3% churn.
That proxy ignores the subscribers acquired to replace churned ones. The churn-consistent *gross-adds* proxy gives about
**8 months** and LTV:CAC of **4.4x**. The gross-adds view fits Spotify's rising
profitability better, but true CAC needs gross-add and churn data that Spotify does not publish.

**8. Strategies to improve profitability:** see recommendations below.

## Recommendations

1. **Make retention the top unit-economics priority.** Each 1pp reduction in monthly churn near the base case adds
   €12-€25 of LTV per subscriber, more than any pricing or
   margin move tested. Prioritise annual plans, family/duo bundling, and personalisation that raises engagement.
2. **Keep expanding gross margin.** Each +1pp of gross margin adds about 3.1% to LTV with
   no churn risk. The levers are a richer content mix (podcasts, audiobooks, marketplace) and favourable royalty terms.
3. **Price with care.** ARPU +5% lifts LTV by 5%, but only if churn holds. A price rise that adds 1pp of churn erases
   the gain many times over. Prefer tiering (premium add-ons) over blanket increases.
4. **Fix advertising monetisation.** Ad revenue per ad-supported MAU fell from €5.56 (2022) to
   €4.08 (2025) while the ad-supported audience kept growing. Better ad tech, programmatic and
   podcast ad yield are the clearest revenue-growth opportunities.
5. **Tie marketing spend to incremental subscribers.** S&M +20% without extra subscribers cuts LTV:CAC (gross proxy) from
   4.38x to 3.65x. Keep S&M near
   8% of revenue unless cohort data show payback inside the target window.
6. **Improve free-to-premium conversion.** Premium subscribers are 38.6% of MAU, down from
   44.3% in 2021. Users are joining faster on the free tier than they convert.
7. **Measure what this analysis had to assume.** Internally, track gross adds, monthly churn by cohort and market, and
   channel-level acquisition cost. Those three numbers replace every proxy in this report.

## Methodology & limitations

- Source: Spotify Q4 2025 Shareholder Deck, Form 20-F 2025, Spotify IR (`data/source_register.csv`).
  79 of 79 internal consistency checks pass (`data/processed/validation_checks.csv`).
- ARPU is an approximation (two-point average subscribers). It is not the company-reported metric.
- LTV uses **company-level** gross margin. Premium segment margin differs, and per-subscriber margin also varies by plan and market.
- Churn is **assumed** (2-5% monthly). Spotify does not disclose it.
- CAC proxies charge 100% of S&M to premium acquisition, overstating true CAC. The net-adds proxy also ignores churn
  replacement, which overstates it further.
- LTV is undiscounted and assumes constant ARPU, margin and churn.
- Only 4-5 annual observations: trends are descriptive, not statistically tested. Figures are in reported EUR, not constant currency.
