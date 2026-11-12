"""Phase 3a - Revenue analysis: growth, segment growth, revenue mix and quarterly trends."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    BLUE, DATA_PROCESSED, INK_2, ORANGE, SURFACE, load_annual, load_quarterly, md_table, pct_change,
    save_chart, save_csv, write_report,
)


def annual_revenue(annual: pd.DataFrame) -> pd.DataFrame:
    df = annual[["year", "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions",
                 "total_revenue_eur_millions"]].copy()
    df["total_revenue_growth_pct"] = pct_change(df["total_revenue_eur_millions"])
    df["premium_revenue_growth_pct"] = pct_change(df["premium_revenue_eur_millions"])
    df["ad_supported_revenue_growth_pct"] = pct_change(df["ad_supported_revenue_eur_millions"])
    df["premium_mix_pct"] = df["premium_revenue_eur_millions"] / df["total_revenue_eur_millions"] * 100
    df["ad_supported_mix_pct"] = 100 - df["premium_mix_pct"]
    df["incremental_revenue_eur_millions"] = df["total_revenue_eur_millions"].diff()
    df["premium_share_of_incremental_revenue_pct"] = (
        df["premium_revenue_eur_millions"].diff() / df["incremental_revenue_eur_millions"] * 100
    )
    return df


def quarterly_revenue(quarterly: pd.DataFrame) -> pd.DataFrame:
    df = quarterly[["period", "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions",
                    "total_revenue_eur_millions"]].copy()
    df["total_revenue_qoq_pct"] = pct_change(df["total_revenue_eur_millions"])
    df["premium_revenue_qoq_pct"] = pct_change(df["premium_revenue_eur_millions"])
    df["ad_supported_revenue_qoq_pct"] = pct_change(df["ad_supported_revenue_eur_millions"])
    df["premium_mix_pct"] = df["premium_revenue_eur_millions"] / df["total_revenue_eur_millions"] * 100
    return df


def charts(rev: pd.DataFrame):
    g = rev.dropna(subset=["total_revenue_growth_pct"])
    years = g["year"].astype(str).to_numpy()
    x = np.arange(len(years))
    w = 0.38

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(x - w / 2, g["premium_revenue_growth_pct"], w, color=BLUE, label="Premium", edgecolor=SURFACE, linewidth=2)
    ax.bar(x + w / 2, g["ad_supported_revenue_growth_pct"], w, color=ORANGE, label="Ad-supported",
           edgecolor=SURFACE, linewidth=2)
    last = g.iloc[-1]
    ax.annotate(f"{last['ad_supported_revenue_growth_pct']:.1f}%", (x[-1] + w / 2, last["ad_supported_revenue_growth_pct"]),
                xytext=(0, -14), textcoords="offset points", ha="center", color=INK_2, fontsize=9)
    ax.annotate(f"{last['premium_revenue_growth_pct']:.1f}%", (x[-1] - w / 2, last["premium_revenue_growth_pct"]),
                xytext=(0, 4), textcoords="offset points", ha="center", color=INK_2, fontsize=9)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.set_xticks(x, years)
    ax.set_ylabel("YoY growth, %")
    ax.set_title("Advertising revenue stalled in 2025 while premium kept growing")
    ax.legend(loc="upper right")
    save_chart(fig, "05_revenue_growth_by_segment")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(rev["year"].astype(str), rev["premium_mix_pct"], marker="o", color=BLUE)
    for yr, v in zip(rev["year"].astype(str), rev["premium_mix_pct"]):
        ax.annotate(f"{v:.1f}%", (yr, v), xytext=(0, 9), textcoords="offset points", ha="center", color=INK_2, fontsize=9)
    ax.set_ylim(85, 92)
    ax.set_ylabel("Premium share of total revenue, %")
    ax.set_title("Premium revenue share of total revenue")
    save_chart(fig, "06_premium_revenue_mix", "Axis starts at 85% to show the change; the rest of revenue is ad-supported.")


def main():
    rev = annual_revenue(load_annual())
    q = quarterly_revenue(load_quarterly())
    save_csv(rev, DATA_PROCESSED / "revenue_analysis_annual.csv")
    save_csv(q, DATA_PROCESSED / "revenue_analysis_quarterly.csv")
    charts(rev)

    a = rev.set_index("year")
    cagr = lambda col: ((a[col].iloc[-1] / a[col].iloc[0]) ** 0.25 - 1) * 100
    q4_yoy = (q.iloc[-1]["total_revenue_eur_millions"] / q.iloc[0]["total_revenue_eur_millions"] - 1) * 100
    q4_ad_yoy = (q.iloc[-1]["ad_supported_revenue_eur_millions"] / q.iloc[0]["ad_supported_revenue_eur_millions"] - 1) * 100

    table = rev[["year", "total_revenue_eur_millions", "total_revenue_growth_pct", "premium_revenue_growth_pct",
                 "ad_supported_revenue_growth_pct", "premium_mix_pct"]].rename(columns={
        "year": "Year", "total_revenue_eur_millions": "Revenue (EUR M)", "total_revenue_growth_pct": "Total growth %",
        "premium_revenue_growth_pct": "Premium growth %", "ad_supported_revenue_growth_pct": "Ad growth %",
        "premium_mix_pct": "Premium mix %"})
    qtable = q[["period", "total_revenue_eur_millions", "total_revenue_qoq_pct", "ad_supported_revenue_qoq_pct",
                "premium_mix_pct"]].rename(columns={
        "period": "Quarter", "total_revenue_eur_millions": "Revenue (EUR M)", "total_revenue_qoq_pct": "QoQ %",
        "ad_supported_revenue_qoq_pct": "Ad QoQ %", "premium_mix_pct": "Premium mix %"})

    write_report("02_revenue_analysis.md", f"""
# Phase 3a: Revenue Analysis

## Annual revenue

{md_table(table)}

- Total revenue CAGR 2021-2025: **{cagr('total_revenue_eur_millions'):.1f}%** (premium {cagr('premium_revenue_eur_millions'):.1f}%,
  ad-supported {cagr('ad_supported_revenue_eur_millions'):.1f}%).
- Revenue growth slowed from {a.loc[2024, 'total_revenue_growth_pct']:.1f}% in 2024 to {a.loc[2025, 'total_revenue_growth_pct']:.1f}% in 2025.
- Ad-supported revenue **fell {abs(a.loc[2025, 'ad_supported_revenue_growth_pct']):.1f}%** in 2025, so premium delivered
  {a.loc[2025, 'premium_share_of_incremental_revenue_pct']:.0f}% of that year's incremental revenue.
- Premium mix rose from {a.loc[2021, 'premium_mix_pct']:.1f}% to {a.loc[2025, 'premium_mix_pct']:.1f}%. Spotify's revenue is
  increasingly concentrated in subscriptions.

## Quarterly trend (2024-Q4 to 2025-Q4)

{md_table(qtable)}

- Q4 2025 vs Q4 2024: total revenue **{q4_yoy:+.1f}%**; ad-supported revenue **{q4_ad_yoy:+.1f}%**.
- The Q1 drop in ad revenue is seasonal: Q4 is the peak advertising quarter.
- Reported growth is in EUR. Part of the 2025 slowdown may come from currency effects, but this dataset has no
  constant-currency figures. Check the shareholder deck before attributing the slowdown to demand.
""")


if __name__ == "__main__":
    main()
