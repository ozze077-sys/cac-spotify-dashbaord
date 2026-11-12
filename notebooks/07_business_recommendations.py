"""Phase 11 - Management report: answers the eight business questions and turns them into recommendations.

Reads only the processed outputs of scripts 01-06, so it must run after them.
"""

import pandas as pd

from common import BASE_CHURN, BASE_YEAR, DATA_PROCESSED, ROOT, md_table, save_csv, write_report


def main():
    subs = pd.read_csv(DATA_PROCESSED / "subscriber_analysis_annual.csv").set_index("year")
    rev = pd.read_csv(DATA_PROCESSED / "revenue_analysis_annual.csv").set_index("year")
    prof = pd.read_csv(DATA_PROCESSED / "profitability_annual.csv").set_index("year")
    yearly = pd.read_csv(DATA_PROCESSED / "unit_economics_by_year.csv").set_index("year")
    churn = pd.read_csv(DATA_PROCESSED / "unit_economics_churn_scenarios.csv").set_index("scenario")
    scen = pd.read_csv(DATA_PROCESSED / "scenario_comparison.csv").set_index("scenario")
    checks = pd.read_csv(DATA_PROCESSED / "validation_checks.csv")

    y0, y1 = 2021, BASE_YEAR
    base = churn.loc["Base case"]
    kpis = pd.DataFrame([
        ("Total revenue (EUR M)", rev.loc[y1, "total_revenue_eur_millions"], "Reported"),
        ("Revenue growth YoY %", rev.loc[y1, "total_revenue_growth_pct"], "Calculated"),
        (f"Revenue CAGR {y0}-{y1} %", ((rev.loc[y1, 'total_revenue_eur_millions'] / rev.loc[y0, 'total_revenue_eur_millions']) ** 0.25 - 1) * 100, "Calculated"),
        ("Premium subscribers (M)", subs.loc[y1, "premium_subscribers_millions"], "Reported"),
        ("MAU (M)", subs.loc[y1, "mau_millions"], "Reported"),
        ("Premium net adds (M)", subs.loc[y1, "premium_net_adds_millions"], "Calculated"),
        ("Monthly premium ARPU (EUR)", subs.loc[y1, "premium_arpu_monthly_eur"], "Analyst approximation"),
        ("Gross margin %", prof.loc[y1, "gross_margin_calc_pct"], "Reported"),
        ("Operating margin %", prof.loc[y1, "operating_margin_calc_pct"], "Reported"),
        ("Operating income (EUR M)", prof.loc[y1, "operating_income_eur_millions"], "Reported"),
        ("Free cash flow (EUR M)", prof.loc[y1, "free_cash_flow_eur_millions"], "Reported (non-IFRS)"),
        ("S&M % of revenue", prof.loc[y1, "sm_pct_of_revenue"], "Calculated"),
        ("CAC proxy, net adds (EUR)", base["cac_proxy_net_adds_eur"], "Analyst proxy - not CAC"),
        (f"CAC proxy, gross adds @{BASE_CHURN:.0%} churn (EUR)", base["cac_proxy_gross_adds_eur"], "Analyst proxy - not CAC"),
        (f"LTV @{BASE_CHURN:.0%} churn (EUR)", base["ltv_eur"], "Scenario estimate"),
        ("LTV:CAC, net-adds proxy (x)", base["ltv_to_cac_net_adds"], "Scenario estimate"),
        ("LTV:CAC, gross-adds proxy (x)", base["ltv_to_cac_gross_adds"], "Scenario estimate"),
        ("Payback, gross-adds proxy (months)", base["payback_months_gross_adds"], "Scenario estimate"),
    ], columns=["metric", "value", "basis"])
    kpis.insert(0, "year", y1)
    save_csv(kpis, ROOT / "outputs" / "reports" / "key_metrics_summary.csv")

    rev_cum = (rev.loc[y1, "total_revenue_eur_millions"] / rev.loc[y0, "total_revenue_eur_millions"] - 1) * 100
    sub_cum = (subs.loc[y1, "premium_subscribers_millions"] / subs.loc[y0, "premium_subscribers_millions"] - 1) * 100
    churn_gain = churn.loc["Optimistic", "ltv_eur"] - base["ltv_eur"]
    ad_per_mau_first = subs["ad_revenue_per_ad_mau_annual_eur"].dropna().iloc[0]
    ad_per_mau_first_year = subs["ad_revenue_per_ad_mau_annual_eur"].dropna().index[0]

    write_report("Spotify_Management_Report.md", f"""
# Spotify Historical Financial & Unit Economics: Management Report

*Scope: {y0}-{y1} annual results and 2024-Q4 to 2025-Q4 quarterly results, from Spotify's published investor materials.
All currency is EUR. Churn and CAC figures are analyst scenarios and proxies, not company disclosures.*

## Executive summary

Spotify has moved from loss-making growth to profitable scale. Since {y0}, revenue is up **{rev_cum:.0f}%** against
premium subscriber growth of {sub_cum:.0f}%. Gross margin rose from {prof.loc[2022, 'gross_margin_calc_pct']:.1f}% (2022) to
**{prof.loc[y1, 'gross_margin_calc_pct']:.1f}%**, and operating income went from a €{abs(prof.loc[2022, 'operating_income_eur_millions']):,.0f}M loss
to a **€{prof.loc[y1, 'operating_income_eur_millions']:,.0f}M profit**. The {y1} watch-points are slowing top-line growth
({rev.loc[y1, 'total_revenue_growth_pct']:.1f}%) and falling advertising revenue ({rev.loc[y1, 'ad_supported_revenue_growth_pct']:+.1f}%).
Subscriber lifetime value depends heavily on churn, which Spotify does not disclose.

## Key metrics ({y1})

{md_table(kpis.assign(value=kpis['value'].map(lambda v: f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"))[['metric', 'value', 'basis']].rename(columns=str.title))}

## Answers to the business questions

**1. Is revenue growing faster than the subscriber base?** Over the full period, yes: revenue +{rev_cum:.0f}% vs
subscribers +{sub_cum:.0f}%. Year by year it is mixed. Revenue outgrew subscribers in 2022 and 2024 and lagged
slightly in 2023 and {y1}. In {y1} the lag came from ad revenue; premium revenue alone grew
{rev.loc[y1, 'premium_revenue_growth_pct']:.1f}% vs subscribers {subs.loc[y1, 'premium_subscriber_growth_pct']:.1f}%.

**2. Revenue per Premium subscriber?** About **€{subs.loc[y1, 'premium_arpu_monthly_eur']:.2f} per month**
(€{subs.loc[y1, 'premium_arpu_annual_eur']:.0f} per year) in {y1}, up from €{subs.loc[2022, 'premium_arpu_monthly_eur']:.2f} in 2022.

**3. Is Spotify becoming more profitable?** Yes, decisively. Operating margin went from
{prof.loc[2022, 'operating_margin_calc_pct']:.1f}% (2022) to {prof.loc[y1, 'operating_margin_calc_pct']:.1f}% ({y1}), and FCF margin from
{prof.loc[2022, 'fcf_margin_pct']:.1f}% to {prof.loc[y1, 'fcf_margin_pct']:.1f}%. Operating expenses fell in absolute terms in 2024 and {y1}.
**{prof.loc[y1, 'incremental_operating_margin_pct']:.0f}%** of {y1}'s incremental revenue reached operating income.

**4. How efficiently does Spotify spend on sales & marketing?** Increasingly efficiently. S&M fell from
{prof.loc[2023, 'sm_pct_of_revenue']:.1f}% to {prof.loc[y1, 'sm_pct_of_revenue']:.1f}% of revenue (2023-{y1}). S&M per net premium add held
near €{yearly['cac_proxy_net_adds_eur'].mean():.0f}, while gross profit per subscriber grew, so payback on that proxy shortened from
{yearly['payback_months_net_adds'].iloc[0]:.0f} to {yearly['payback_months_net_adds'].iloc[-1]:.0f} months.

**5. Estimated Premium LTV?** About **€{base['ltv_eur']:.0f}** of lifetime gross profit at an assumed {BASE_CHURN:.0%} monthly churn
(€{churn['ltv_eur'].min():.0f}-€{churn['ltv_eur'].max():.0f} across the 2-5% scenarios).

**6. How sensitive is LTV to churn?** Highly. LTV moves inversely with churn: cutting churn from 3% to 2% adds
€{churn_gain:.0f} (+50%), and rising to 5% removes 40%. Churn is the largest LTV driver tested.

**7. How long to recover acquisition cost?** The answer depends on the proxy. Charging all S&M to *net* adds gives a
{base['payback_months_net_adds']:.0f}-month payback, longer than the {base['expected_lifetime_months']:.0f}-month expected lifetime at 3% churn.
That proxy ignores the subscribers acquired to replace churned ones. The churn-consistent *gross-adds* proxy gives about
**{base['payback_months_gross_adds']:.0f} months** and LTV:CAC of **{base['ltv_to_cac_gross_adds']:.1f}x**. The gross-adds view fits Spotify's rising
profitability better, but true CAC needs gross-add and churn data that Spotify does not publish.

**8. Strategies to improve profitability:** see recommendations below.

## Recommendations

1. **Make retention the top unit-economics priority.** Each 1pp reduction in monthly churn near the base case adds
   €{churn.loc['Base case', 'ltv_eur'] - churn.loc['Moderate risk', 'ltv_eur']:.0f}-€{churn_gain:.0f} of LTV per subscriber, more than any pricing or
   margin move tested. Prioritise annual plans, family/duo bundling, and personalisation that raises engagement.
2. **Keep expanding gross margin.** Each +1pp of gross margin adds about {scen.loc['Gross margin +1pp', 'ltv_change_vs_base_pct']:.1f}% to LTV with
   no churn risk. The levers are a richer content mix (podcasts, audiobooks, marketplace) and favourable royalty terms.
3. **Price with care.** ARPU +5% lifts LTV by 5%, but only if churn holds. A price rise that adds 1pp of churn erases
   the gain many times over. Prefer tiering (premium add-ons) over blanket increases.
4. **Fix advertising monetisation.** Ad revenue per ad-supported MAU fell from €{ad_per_mau_first:.2f} ({ad_per_mau_first_year:.0f}) to
   €{subs.loc[y1, 'ad_revenue_per_ad_mau_annual_eur']:.2f} ({y1}) while the ad-supported audience kept growing. Better ad tech, programmatic and
   podcast ad yield are the clearest revenue-growth opportunities.
5. **Tie marketing spend to incremental subscribers.** S&M +20% without extra subscribers cuts LTV:CAC (gross proxy) from
   {scen.loc['Base case', 'ltv_to_cac_gross_adds']:.2f}x to {scen.loc['Marketing spend +20%', 'ltv_to_cac_gross_adds']:.2f}x. Keep S&M near
   {prof.loc[y1, 'sm_pct_of_revenue']:.0f}% of revenue unless cohort data show payback inside the target window.
6. **Improve free-to-premium conversion.** Premium subscribers are {subs.loc[y1, 'premium_share_of_mau_pct']:.1f}% of MAU, down from
   {subs.loc[y0, 'premium_share_of_mau_pct']:.1f}% in {y0}. Users are joining faster on the free tier than they convert.
7. **Measure what this analysis had to assume.** Internally, track gross adds, monthly churn by cohort and market, and
   channel-level acquisition cost. Those three numbers replace every proxy in this report.

## Methodology & limitations

- Source: Spotify Q4 {y1} Shareholder Deck, Form 20-F {y1}, Spotify IR (`data/source_register.csv`).
  {(checks['result'] == 'PASS').sum()} of {len(checks)} internal consistency checks pass (`data/processed/validation_checks.csv`).
- ARPU is an approximation (two-point average subscribers). It is not the company-reported metric.
- LTV uses **company-level** gross margin. Premium segment margin differs, and per-subscriber margin also varies by plan and market.
- Churn is **assumed** (2-5% monthly). Spotify does not disclose it.
- CAC proxies charge 100% of S&M to premium acquisition, overstating true CAC. The net-adds proxy also ignores churn
  replacement, which overstates it further.
- LTV is undiscounted and assumes constant ARPU, margin and churn.
- Only 4-5 annual observations: trends are descriptive, not statistically tested. Figures are in reported EUR, not constant currency.
""")


if __name__ == "__main__":
    main()
