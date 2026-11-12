"""Phases 5-7 - CAC proxy, LTV under churn scenarios, LTV:CAC and payback.

IMPORTANT: Spotify does not disclose CAC or churn. Every churn rate here is a hypothetical scenario, and every CAC
figure is a company-level proxy that allocates all sales & marketing spend to premium subscriber acquisition.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    AQUA, BASE_CHURN, BASE_YEAR, BLUE, CHURN_SCENARIOS, DATA_PROCESSED, INK_2, ORANGE, SURFACE, base_inputs,
    md_table, save_chart, save_csv, unit_economics, write_report,
)


def yearly_table() -> pd.DataFrame:
    """CAC proxy and base-churn unit economics for each year with S&M data."""
    prof = pd.read_csv(DATA_PROCESSED / "profitability_annual.csv")
    years = prof.dropna(subset=["sales_marketing_expense_eur_millions"])["year"]
    rows = [{"year": y, **unit_economics(churn=BASE_CHURN, **base_inputs(y))} for y in years]
    return pd.DataFrame(rows)


def churn_table(inputs: dict) -> pd.DataFrame:
    rows = [{"scenario": name, **unit_economics(churn=c, **inputs)} for name, c in CHURN_SCENARIOS.items()]
    return pd.DataFrame(rows)


def grouped_bars(ax, labels, series, fmt):
    x = np.arange(len(labels))
    w = 0.8 / len(series)
    for i, (values, label, color) in enumerate(series):
        pos = x - 0.4 + w / 2 + i * w
        ax.bar(pos, values, w, color=color, label=label, edgecolor=SURFACE, linewidth=2)
        for px, v in zip(pos, values):
            ax.text(px, v, fmt(v), ha="center", va="bottom", fontsize=8, color=INK_2)
    ax.set_xticks(x, labels)


def charts(yearly: pd.DataFrame, churn: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    grouped_bars(ax, yearly["year"].astype(str), [
        (yearly["cac_proxy_net_adds_eur"], "S&M / net adds (roadmap proxy)", BLUE),
        (yearly["cac_proxy_gross_adds_eur"], f"S&M / implied gross adds ({BASE_CHURN:.0%} churn)", ORANGE),
    ], lambda v: f"€{v:.0f}")
    ax.set_ylabel("EUR per subscriber added")
    ax.set_title("CAC proxy: the definition matters more than the trend")
    ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=2)
    save_chart(fig, "14_cac_proxy_trend", "Proxies, not true CAC: all S&M allocated to premium acquisition; churn is assumed.")

    labels = [f"{n}\n{c:.0%} churn" for n, c in CHURN_SCENARIOS.items()]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    grouped_bars(ax, labels, [
        (churn["ltv_eur"], "LTV (gross profit)", AQUA),
        (churn["cac_proxy_net_adds_eur"], "CAC proxy: S&M / net adds", BLUE),
        (churn["cac_proxy_gross_adds_eur"], "CAC proxy: S&M / implied gross adds", ORANGE),
    ], lambda v: f"€{v:.0f}")
    ax.set_ylabel("EUR per premium subscriber")
    ax.set_title(f"{BASE_YEAR} LTV vs CAC proxies by churn scenario")
    ax.legend(loc="upper right")
    save_chart(fig, "15_ltv_vs_cac_by_churn", "Churn rates are hypothetical scenarios, not Spotify-reported figures.")

    fig, ax = plt.subplots(figsize=(9, 4.8))
    grouped_bars(ax, labels, [
        (churn["expected_lifetime_months"], "Expected subscriber lifetime", AQUA),
        (churn["payback_months_net_adds"], "Payback: net-adds proxy", BLUE),
        (churn["payback_months_gross_adds"], "Payback: gross-adds proxy", ORANGE),
    ], lambda v: f"{v:.0f}")
    ax.set_ylabel("Months")
    ax.set_title("CAC payback vs expected subscriber lifetime")
    ax.legend(loc="upper right")
    save_chart(fig, "16_payback_vs_lifetime", "Payback is recovered only if it is shorter than the expected lifetime (1 / churn).")


def main():
    inputs = base_inputs(BASE_YEAR)
    yearly = yearly_table()
    churn = churn_table(inputs)
    save_csv(yearly, DATA_PROCESSED / "unit_economics_by_year.csv")
    save_csv(churn, DATA_PROCESSED / "unit_economics_churn_scenarios.csv")
    charts(yearly, churn)

    base = churn.set_index("scenario").loc["Base case"]
    ytable = yearly[["year", "monthly_arpu_eur", "gross_margin_pct", "cac_proxy_net_adds_eur", "cac_proxy_gross_adds_eur",
                     "ltv_eur", "ltv_to_cac_net_adds", "ltv_to_cac_gross_adds"]].rename(columns={
        "year": "Year", "monthly_arpu_eur": "ARPU (EUR/mo)", "gross_margin_pct": "Gross margin %",
        "cac_proxy_net_adds_eur": "CAC proxy, net adds (EUR)", "cac_proxy_gross_adds_eur": "CAC proxy, gross adds (EUR)",
        "ltv_eur": f"LTV @{BASE_CHURN:.0%} (EUR)", "ltv_to_cac_net_adds": "LTV:CAC (net)", "ltv_to_cac_gross_adds": "LTV:CAC (gross)"})
    ctable = churn[["scenario", "monthly_churn_pct", "expected_lifetime_months", "ltv_eur", "cac_proxy_gross_adds_eur",
                    "ltv_to_cac_net_adds", "ltv_to_cac_gross_adds", "payback_months_net_adds",
                    "payback_months_gross_adds"]].rename(columns={
        "scenario": "Scenario", "monthly_churn_pct": "Churn %/mo", "expected_lifetime_months": "Lifetime (mo)",
        "ltv_eur": "LTV (EUR)", "cac_proxy_gross_adds_eur": "CAC gross-adds (EUR)",
        "ltv_to_cac_net_adds": "LTV:CAC (net)", "ltv_to_cac_gross_adds": "LTV:CAC (gross)",
        "payback_months_net_adds": "Payback net (mo)", "payback_months_gross_adds": "Payback gross (mo)"})
    ltv2, ltv5 = churn["ltv_eur"].iloc[0], churn["ltv_eur"].iloc[-1]
    y0, y1 = yearly.iloc[0], yearly.iloc[-1]

    write_report("05_unit_economics.md", f"""
# Phases 5-7: CAC Proxy, LTV, LTV:CAC & Payback ({BASE_YEAR} base)

> **Read this first.** Spotify discloses neither customer acquisition cost nor churn. Every churn rate below is a
> hypothetical scenario, and every CAC figure is a company-level proxy. Use these numbers as **sensitivity
> analysis**, not as Spotify's actual unit economics.

## Inputs ({BASE_YEAR})

| Input | Value | Basis |
| --- | --- | --- |
| Monthly premium ARPU | €{inputs['arpu']:.2f} | Premium revenue / avg subscribers / 12 (Phase 3) |
| Gross margin | {inputs['gross_margin'] * 100:.1f}% | Company-level reported gross margin (premium-only margin not in dataset) |
| Monthly gross profit per subscriber | €{base['monthly_gross_profit_per_sub_eur']:.2f} | ARPU x gross margin |
| Sales & marketing expense | €{inputs['sm_expense']:,.0f}M | Reported |
| Premium net adds | {inputs['net_adds']:.0f}M | Change in year-end subscribers |
| Average premium subscribers | {inputs['avg_subs']:.1f}M | Avg of opening and closing |

## Phase 5: Marketing efficiency (CAC proxy)

Two proxies, both upper-bound estimates because they charge all S&M (brand, ad-tier, podcasts, audiobooks) to premium:

1. **Net-adds proxy (roadmap formula):** S&M / net premium adds. It treats every new subscriber as replacing nobody,
   which implicitly assumes zero churn and so **overstates CAC heavily**.
2. **Gross-adds proxy (churn-consistent):** S&M / (net adds + avg subscribers x monthly churn x 12). If you assume
   a churn rate for LTV, the same churn must also be replacing lost subscribers, so this proxy uses the same assumption.

{md_table(ytable, ",.2f")}

The net-adds proxy has stayed in a narrow €{yearly['cac_proxy_net_adds_eur'].min():.0f}-{yearly['cac_proxy_net_adds_eur'].max():.0f}
range ({(y1['cac_proxy_net_adds_eur'] / y0['cac_proxy_net_adds_eur'] - 1) * 100:+.1f}% from {y0['year']:.0f} to {y1['year']:.0f}).
Monthly gross profit per subscriber grew faster ({(y1['monthly_gross_profit_per_sub_eur'] / y0['monthly_gross_profit_per_sub_eur'] - 1) * 100:+.1f}%),
so payback on this proxy shortened from {y0['payback_months_net_adds']:.0f} to {y1['payback_months_net_adds']:.0f} months.
**Q4 answer: marketing efficiency improved**, driven mainly by higher margin per subscriber rather than cheaper acquisition.

## Phase 6: LTV by churn scenario

LTV = monthly ARPU x gross margin / monthly churn

{md_table(ctable, ",.1f")}

**Q6. How sensitive is LTV to churn?** Very sensitive. LTV is inversely proportional to churn: moving from
2% to 5% monthly churn cuts LTV from €{ltv2:.0f} to €{ltv5:.0f} (-{(1 - ltv5 / ltv2) * 100:.0f}%). Each
+1pp of churn near the base case removes about €{churn['ltv_eur'].iloc[1] - churn['ltv_eur'].iloc[2]:.0f} of LTV.

## Phase 7: LTV:CAC and payback

**Q5. Estimated premium subscriber LTV:** about **€{base['ltv_eur']:.0f}** of gross profit at the 3% base case
(range €{ltv5:.0f}-€{ltv2:.0f} across the scenarios).

**Q7. How long to recover acquisition cost?**

- With the net-adds proxy, payback is **{base['payback_months_net_adds']:.0f} months** in every scenario. That exceeds
  the {base['expected_lifetime_months']:.0f}-month expected lifetime at 3% churn, so LTV:CAC is
  {base['ltv_to_cac_net_adds']:.2f}x and the economics look unattractive.
- With the churn-consistent gross-adds proxy, payback is **{base['payback_months_gross_adds']:.1f} months** at 3% churn
  and LTV:CAC is **{base['ltv_to_cac_gross_adds']:.1f}x**. Across the four scenarios it ranges from
  {churn['ltv_to_cac_gross_adds'].min():.1f}x to {churn['ltv_to_cac_gross_adds'].max():.1f}x
  ({'above' if churn['ltv_to_cac_gross_adds'].min() > 3 else 'not always above'} the common 3x benchmark).
- **Interpretation:** the net-adds proxy contradicts the business's own trajectory (operating margin rising, S&M falling
  as a share of revenue). The gross-adds proxy is the more coherent estimate, but both depend on an assumed churn rate.
  Treat the proxy choice itself as the biggest uncertainty in this analysis. Phase 8 tests which lever moves the result most.
""")


if __name__ == "__main__":
    main()
