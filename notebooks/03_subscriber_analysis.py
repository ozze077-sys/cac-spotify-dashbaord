"""Phase 3b - Subscriber economics: net adds, growth, ARPU and the revenue-growth decomposition.

Monthly premium ARPU (approx.) = premium revenue / average(opening, closing subscribers) / months in period.
This is an analyst approximation, not Spotify-reported ARPU.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    AQUA, BLUE, DATA_PROCESSED, INK_2, ORANGE, SURFACE, load_annual, load_quarterly, md_table, pct_change,
    save_chart, save_csv, write_report,
)


def annual_subscribers(annual: pd.DataFrame) -> pd.DataFrame:
    df = annual[["year", "mau_millions", "premium_subscribers_millions", "ad_supported_mau_millions",
                 "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions", "total_revenue_eur_millions"]].copy()
    df["premium_net_adds_millions"] = df["premium_subscribers_millions"].diff()
    df["mau_net_adds_millions"] = df["mau_millions"].diff()
    df["ad_mau_net_adds_millions"] = df["ad_supported_mau_millions"].diff()
    df["premium_subscriber_growth_pct"] = pct_change(df["premium_subscribers_millions"])
    df["mau_growth_pct"] = pct_change(df["mau_millions"])
    df["premium_share_of_mau_pct"] = df["premium_subscribers_millions"] / df["mau_millions"] * 100
    df["avg_premium_subscribers_millions"] = df["premium_subscribers_millions"].rolling(2).mean()
    df["avg_ad_mau_millions"] = df["ad_supported_mau_millions"].rolling(2).mean()
    df["avg_mau_millions"] = df["mau_millions"].rolling(2).mean()
    df["premium_arpu_monthly_eur"] = df["premium_revenue_eur_millions"] / df["avg_premium_subscribers_millions"] / 12
    df["premium_arpu_annual_eur"] = df["premium_arpu_monthly_eur"] * 12
    df["ad_revenue_per_ad_mau_annual_eur"] = df["ad_supported_revenue_eur_millions"] / df["avg_ad_mau_millions"]
    df["revenue_per_mau_annual_eur"] = df["total_revenue_eur_millions"] / df["avg_mau_millions"]
    df["premium_arpu_growth_pct"] = pct_change(df["premium_arpu_monthly_eur"])
    df["avg_premium_subscriber_growth_pct"] = pct_change(df["avg_premium_subscribers_millions"])
    df["premium_revenue_growth_pct"] = pct_change(df["premium_revenue_eur_millions"])
    df["total_revenue_growth_pct"] = pct_change(df["total_revenue_eur_millions"])
    # Revenue growth in excess of subscriber growth (percentage points) - the pricing / ARPU contribution.
    df["revenue_minus_subscriber_growth_pp"] = df["total_revenue_growth_pct"] - df["premium_subscriber_growth_pct"]
    return df


def quarterly_subscribers(quarterly: pd.DataFrame) -> pd.DataFrame:
    df = quarterly[["period", "mau_millions", "premium_subscribers_millions", "ad_supported_mau_millions",
                    "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions"]].copy()
    df["premium_net_adds_millions"] = df["premium_subscribers_millions"].diff()
    df["mau_net_adds_millions"] = df["mau_millions"].diff()
    df["avg_premium_subscribers_millions"] = df["premium_subscribers_millions"].rolling(2).mean()
    df["premium_arpu_monthly_eur"] = df["premium_revenue_eur_millions"] / df["avg_premium_subscribers_millions"] / 3
    return df


def charts(subs: pd.DataFrame, q: pd.DataFrame):
    s = subs.dropna(subset=["premium_net_adds_millions"])
    years = s["year"].astype(str)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(years, s["premium_net_adds_millions"], color=AQUA, width=0.55, edgecolor=SURFACE, linewidth=2)
    for yr, v in zip(years, s["premium_net_adds_millions"]):
        ax.text(yr, v + 0.5, f"+{v:.0f}M", ha="center", color=INK_2, fontsize=9)
    ax.set_ylabel("Premium net adds (millions)")
    ax.set_title("Premium subscriber net additions per year")
    save_chart(fig, "07_premium_net_adds", "Net adds = change in year-end subscribers. Gross adds and churn are not disclosed.")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(years, s["premium_arpu_monthly_eur"], marker="o", color=BLUE, label="Annual (avg of opening/closing subs)")
    qq = q.dropna(subset=["premium_arpu_monthly_eur"])
    ax.plot(["2025"], [qq["premium_arpu_monthly_eur"].mean()], marker="D", linestyle="none", color=ORANGE,
            label="2025 average of quarterly ARPU")
    for yr, v in zip(years, s["premium_arpu_monthly_eur"]):
        ax.annotate(f"€{v:.2f}", (yr, v), xytext=(0, 10), textcoords="offset points", ha="center", color=INK_2, fontsize=9)
    ax.set_ylim(4.0, 5.0)
    ax.set_ylabel("EUR per subscriber per month")
    ax.set_title("Approximate monthly premium revenue per subscriber")
    ax.legend(loc="lower right")
    save_chart(fig, "08_premium_arpu", "Analyst approximation; not Spotify-reported ARPU. Axis starts at EUR 4.00.")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(years))
    w = 0.38
    ax.bar(x - w / 2, s["premium_subscriber_growth_pct"], w, color=AQUA, label="Premium subscribers", edgecolor=SURFACE, linewidth=2)
    ax.bar(x + w / 2, s["total_revenue_growth_pct"], w, color=BLUE, label="Total revenue", edgecolor=SURFACE, linewidth=2)
    ax.set_xticks(x, years)
    ax.set_ylabel("YoY growth, %")
    ax.set_title("Revenue growth vs premium subscriber growth")
    ax.legend(loc="upper right")
    save_chart(fig, "09_revenue_vs_subscriber_growth")


def main():
    subs = annual_subscribers(load_annual())
    q = quarterly_subscribers(load_quarterly())
    save_csv(subs, DATA_PROCESSED / "subscriber_analysis_annual.csv")
    save_csv(q, DATA_PROCESSED / "subscriber_analysis_quarterly.csv")
    charts(subs, q)

    a = subs.set_index("year")
    table = subs.dropna(subset=["premium_net_adds_millions"])[[
        "year", "premium_subscribers_millions", "premium_net_adds_millions", "premium_subscriber_growth_pct",
        "total_revenue_growth_pct", "revenue_minus_subscriber_growth_pp", "premium_arpu_monthly_eur",
        "ad_revenue_per_ad_mau_annual_eur"]].rename(columns={
        "year": "Year", "premium_subscribers_millions": "Premium subs (M)", "premium_net_adds_millions": "Net adds (M)",
        "premium_subscriber_growth_pct": "Sub growth %", "total_revenue_growth_pct": "Revenue growth %",
        "revenue_minus_subscriber_growth_pp": "Gap (pp)", "premium_arpu_monthly_eur": "Monthly ARPU (EUR)",
        "ad_revenue_per_ad_mau_annual_eur": "Ad rev / ad MAU / yr (EUR)"})
    qtable = q.dropna(subset=["premium_arpu_monthly_eur"])[[
        "period", "premium_subscribers_millions", "premium_net_adds_millions", "premium_arpu_monthly_eur"]].rename(columns={
        "period": "Quarter", "premium_subscribers_millions": "Premium subs (M)",
        "premium_net_adds_millions": "Net adds (M)", "premium_arpu_monthly_eur": "Monthly ARPU (EUR)"})
    faster = (a["revenue_minus_subscriber_growth_pp"].dropna() > 0)

    write_report("03_subscriber_analysis.md", f"""
# Phase 3b: Revenue & Subscriber Economics

## Q1. Is revenue growing faster than the subscriber base?

{md_table(table, ",.2f")}

- **{'Mostly yes' if faster.sum() > len(faster) / 2 else 'Mixed'}:** revenue outgrew premium subscribers in
  {faster.sum()} of {len(faster)} years ({', '.join(str(y) for y in faster[faster].index)}).
- 2021-2025 cumulative: revenue {(a.loc[2025, 'total_revenue_eur_millions'] / a.loc[2021, 'total_revenue_eur_millions'] - 1) * 100:.0f}%
  vs premium subscribers {(a.loc[2025, 'premium_subscribers_millions'] / a.loc[2021, 'premium_subscribers_millions'] - 1) * 100:.0f}%
  vs MAU {(a.loc[2025, 'mau_millions'] / a.loc[2021, 'mau_millions'] - 1) * 100:.0f}%.
- In 2025, revenue growth ({a.loc[2025, 'total_revenue_growth_pct']:.1f}%) fell just below subscriber growth
  ({a.loc[2025, 'premium_subscriber_growth_pct']:.1f}%) because ad revenue declined. Premium revenue alone grew
  {a.loc[2025, 'premium_revenue_growth_pct']:.1f}%.

## Q2. How much revenue does Spotify generate per Premium subscriber?

- 2025 approximate monthly premium ARPU: **€{a.loc[2025, 'premium_arpu_monthly_eur']:.2f}**
  (€{a.loc[2025, 'premium_arpu_annual_eur']:.0f} per year), up from €{a.loc[2022, 'premium_arpu_monthly_eur']:.2f} in 2022.
- ARPU dipped in 2023 ({a.loc[2023, 'premium_arpu_growth_pct']:+.1f}%) and recovered in 2024
  ({a.loc[2024, 'premium_arpu_growth_pct']:+.1f}%), consistent with the 2023-2024 price increases.
  Subscriber mix (family, duo, student and emerging-market plans) and FX may also contribute; this dataset cannot
  separate the effects.
- Ad-supported monetisation is far lower: about €{a.loc[2025, 'ad_revenue_per_ad_mau_annual_eur']:.2f} per ad-supported MAU per **year**.

### Quarterly ARPU (2025)

{md_table(qtable, ",.2f")}

The 2025 average of the quarterly figures (€{qtable['Monthly ARPU (EUR)'].mean():.2f}) is close to the annual
approximation, which supports using the annual method.

## Method notes

- Monthly ARPU = premium revenue / average of opening and closing subscribers / 12 (or / 3 for quarters).
- A two-point average understates intra-year timing, so treat these figures as approximate.
- Premium ARPU covers premium revenue only. Ad revenue earned from free-tier users is excluded.
""")


if __name__ == "__main__":
    main()
