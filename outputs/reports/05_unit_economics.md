# Phases 5-7: CAC Proxy, LTV, LTV:CAC & Payback (2025 base)

> **Read this first.** Spotify discloses neither customer acquisition cost nor churn. Every churn rate below is a
> hypothetical scenario, and every CAC figure is a company-level proxy. Use these numbers as **sensitivity
> analysis**, not as Spotify's actual unit economics.

## Inputs (2025)

| Input | Value | Basis |
| --- | --- | --- |
| Monthly premium ARPU | €4.63 | Premium revenue / avg subscribers / 12 (Phase 3) |
| Gross margin | 32.0% | Company-level reported gross margin (premium-only margin not in dataset) |
| Monthly gross profit per subscriber | €1.48 | ARPU x gross margin |
| Sales & marketing expense | €1,426M | Reported |
| Premium net adds | 27M | Change in year-end subscribers |
| Average premium subscribers | 276.5M | Avg of opening and closing |

## Phase 5: Marketing efficiency (CAC proxy)

Two proxies, both upper-bound estimates because they charge all S&M (brand, ad-tier, podcasts, audiobooks) to premium:

1. **Net-adds proxy (roadmap formula):** S&M / net premium adds. It treats every new subscriber as replacing nobody,
   which implicitly assumes zero churn and so **overstates CAC heavily**.
2. **Gross-adds proxy (churn-consistent):** S&M / (net adds + avg subscribers x monthly churn x 12). If you assume
   a churn rate for LTV, the same churn must also be replacing lost subscribers, so this proxy uses the same assumption.

| Year | ARPU (EUR/mo) | Gross margin % | CAC proxy, net adds (EUR) | CAC proxy, gross adds (EUR) | LTV @3% (EUR) | LTV:CAC (net) | LTV:CAC (gross) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 4.37 | 25.64 | 49.45 | 13.89 | 37.36 | 0.76 | 2.69 |
| 2024 | 4.62 | 30.14 | 51.56 | 11.92 | 46.37 | 0.90 | 3.89 |
| 2025 | 4.63 | 31.98 | 52.81 | 11.27 | 49.32 | 0.93 | 4.38 |

The net-adds proxy has stayed in a narrow €49-53
range (+6.8% from 2023 to 2025).
Monthly gross profit per subscriber grew faster (+32.0%),
so payback on this proxy shortened from 44 to 36 months.
**Q4 answer: marketing efficiency improved**, driven mainly by higher margin per subscriber rather than cheaper acquisition.

## Phase 6: LTV by churn scenario

LTV = monthly ARPU x gross margin / monthly churn

| Scenario | Churn %/mo | Lifetime (mo) | LTV (EUR) | CAC gross-adds (EUR) | LTV:CAC (net) | LTV:CAC (gross) | Payback net (mo) | Payback gross (mo) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Optimistic | 2.0 | 50.0 | 74.0 | 15.3 | 1.4 | 4.8 | 35.7 | 10.3 |
| Base case | 3.0 | 33.3 | 49.3 | 11.3 | 0.9 | 4.4 | 35.7 | 7.6 |
| Moderate risk | 4.0 | 25.0 | 37.0 | 8.9 | 0.7 | 4.1 | 35.7 | 6.0 |
| High risk | 5.0 | 20.0 | 29.6 | 7.4 | 0.6 | 4.0 | 35.7 | 5.0 |

**Q6. How sensitive is LTV to churn?** Very sensitive. LTV is inversely proportional to churn: moving from
2% to 5% monthly churn cuts LTV from €74 to €30 (-60%). Each
+1pp of churn near the base case removes about €12 of LTV.

## Phase 7: LTV:CAC and payback

**Q5. Estimated premium subscriber LTV:** about **€49** of gross profit at the 3% base case
(range €30-€74 across the scenarios).

**Q7. How long to recover acquisition cost?**

- With the net-adds proxy, payback is **36 months** in every scenario. That exceeds
  the 33-month expected lifetime at 3% churn, so LTV:CAC is
  0.93x and the economics look unattractive.
- With the churn-consistent gross-adds proxy, payback is **7.6 months** at 3% churn
  and LTV:CAC is **4.4x**. Across the four scenarios it ranges from
  4.0x to 4.8x
  (above the common 3x benchmark).
- **Interpretation:** the net-adds proxy contradicts the business's own trajectory (operating margin rising, S&M falling
  as a share of revenue). The gross-adds proxy is the more coherent estimate, but both depend on an assumed churn rate.
  Treat the proxy choice itself as the biggest uncertainty in this analysis. Phase 8 tests which lever moves the result most.
