"""Phase 4 - Profitability: margins, operating expense ratio, S&M intensity, cash flow and operating leverage."""

import matplotlib.pyplot as plt
import pandas as pd

from common import (
    AQUA, BLUE, CRITICAL, DATA_PROCESSED, GOOD, INK_2, ORANGE, SURFACE, load_annual, load_quarterly,
    md_table, pct_change, save_chart, save_csv, write_report,
)


def add_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    rev = df["total_revenue_eur_millions"]
    df["gross_margin_calc_pct"] = df["gross_profit_eur_millions"] / rev * 100
    df["operating_margin_calc_pct"] = df["operating_income_eur_millions"] / rev * 100
    df["opex_ratio_pct"] = df["total_operating_expenses_eur_millions"] / rev * 100
    df["operating_cash_flow_margin_pct"] = df["operating_cash_flow_eur_millions"] / rev * 100
    df["fcf_margin_pct"] = df["free_cash_flow_eur_millions"] / rev * 100
    return df


def annual_profitability(annual: pd.DataFrame) -> pd.DataFrame:
    df = add_ratios(annual[[
        "year", "total_revenue_eur_millions", "gross_profit_eur_millions", "total_operating_expenses_eur_millions",
        "operating_income_eur_millions", "operating_cash_flow_eur_millions", "free_cash_flow_eur_millions",
        "sales_marketing_expense_eur_millions"]])
    df["sm_pct_of_revenue"] = df["sales_marketing_expense_eur_millions"] / df["total_revenue_eur_millions"] * 100
    df["sm_pct_of_opex"] = df["sales_marketing_expense_eur_millions"] / df["total_operating_expenses_eur_millions"] * 100
    df["revenue_growth_pct"] = pct_change(df["total_revenue_eur_millions"])
    df["gross_profit_growth_pct"] = pct_change(df["gross_profit_eur_millions"])
    df["opex_growth_pct"] = pct_change(df["total_operating_expenses_eur_millions"])
    df["sm_growth_pct"] = pct_change(df["sales_marketing_expense_eur_millions"])
    # Incremental operating margin: share of each extra euro of revenue that reached operating income.
    df["incremental_operating_margin_pct"] = (
        df["operating_income_eur_millions"].diff() / df["total_revenue_eur_millions"].diff() * 100
    )
    df["incremental_gross_margin_pct"] = (
        df["gross_profit_eur_millions"].diff() / df["total_revenue_eur_millions"].diff() * 100
    )
    return df


def charts(p: pd.DataFrame, q: pd.DataFrame):
    years = p["year"].astype(str)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for col, label, color in (("gross_margin_calc_pct", "Gross margin", BLUE),
                              ("fcf_margin_pct", "Free cash flow margin", AQUA),
                              ("operating_margin_calc_pct", "Operating margin", ORANGE)):
        ax.plot(years, p[col], marker="o", color=color, label=label)
        ax.annotate(f"{p[col].iloc[-1]:.1f}%", (len(years) - 1, p[col].iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", color=INK_2, fontsize=9)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.set_ylabel("% of revenue")
    ax.set_title("Every margin expanded from 2023 to 2025")
    ax.legend(loc="upper left")
    save_chart(fig, "10_margin_trends")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    colors = [GOOD if v >= 0 else CRITICAL for v in p["operating_income_eur_millions"]]
    ax.bar(years, p["operating_income_eur_millions"], color=colors, width=0.55, edgecolor=SURFACE, linewidth=2)
    for yr, v in zip(years, p["operating_income_eur_millions"]):
        ax.text(yr, v + (60 if v >= 0 else -60), f"{'Profit' if v >= 0 else 'Loss'} €{abs(v):,}M", ha="center",
                va="bottom" if v >= 0 else "top", color=INK_2, fontsize=9)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.set_ylabel("Operating income (EUR millions)")
    ax.set_title("Operating income: from losses in 2022-23 to €2.2B profit in 2025")
    ax.set_ylim(p["operating_income_eur_millions"].min() - 300, p["operating_income_eur_millions"].max() + 300)
    save_chart(fig, "11_operating_income")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(years, p["opex_ratio_pct"], marker="o", color=BLUE, label="Total operating expenses")
    sm = p.dropna(subset=["sm_pct_of_revenue"])
    ax.plot(sm["year"].astype(str), sm["sm_pct_of_revenue"], marker="o", color=ORANGE, label="Sales & marketing")
    for d, col in ((p, "opex_ratio_pct"), (sm, "sm_pct_of_revenue")):
        ax.annotate(f"{d[col].iloc[-1]:.1f}%", (str(d["year"].iloc[-1]), d[col].iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", color=INK_2, fontsize=9)
    ax.set_ylim(0, None)
    ax.set_ylabel("% of revenue")
    ax.set_title("Operating expenses fell from 31% (2022) to 19% of revenue")
    ax.legend(loc="upper right")
    save_chart(fig, "12_opex_ratio", "Sales & marketing expense available for 2023-2025 only.")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for col, label, color in (("gross_margin_calc_pct", "Gross margin", BLUE),
                              ("operating_margin_calc_pct", "Operating margin", ORANGE)):
        ax.plot(q["period"], q[col], marker="o", color=color, label=label)
    ax.set_ylim(0, 40)
    ax.set_ylabel("% of revenue")
    ax.set_title("Quarterly margins, 2024-Q4 to 2025-Q4")
    ax.legend(loc="lower right")
    save_chart(fig, "13_quarterly_margins")


def main():
    p = annual_profitability(load_annual())
    q = add_ratios(load_quarterly())
    save_csv(p, DATA_PROCESSED / "profitability_annual.csv")
    save_csv(q, DATA_PROCESSED / "profitability_quarterly.csv")
    charts(p, q)

    a = p.set_index("year")
    table = p[["year", "gross_margin_calc_pct", "operating_margin_calc_pct", "opex_ratio_pct", "sm_pct_of_revenue",
               "fcf_margin_pct", "incremental_operating_margin_pct"]].rename(columns={
        "year": "Year", "gross_margin_calc_pct": "Gross margin %", "operating_margin_calc_pct": "Operating margin %",
        "opex_ratio_pct": "Opex / revenue %", "sm_pct_of_revenue": "S&M / revenue %", "fcf_margin_pct": "FCF margin %",
        "incremental_operating_margin_pct": "Incremental op. margin %"})
    growth = p[["year", "revenue_growth_pct", "gross_profit_growth_pct", "opex_growth_pct", "sm_growth_pct"]].dropna(
        subset=["revenue_growth_pct"]).rename(columns={
        "year": "Year", "revenue_growth_pct": "Revenue %", "gross_profit_growth_pct": "Gross profit %",
        "opex_growth_pct": "Opex %", "sm_growth_pct": "S&M %"})
    qtable = q[["period", "gross_margin_calc_pct", "operating_margin_calc_pct", "opex_ratio_pct", "fcf_margin_pct"]].rename(
        columns={"period": "Quarter", "gross_margin_calc_pct": "Gross margin %", "operating_margin_calc_pct": "Op. margin %",
                 "opex_ratio_pct": "Opex / revenue %", "fcf_margin_pct": "FCF margin %"})

    write_report("04_profitability_analysis.md", f"""
# Phase 4: Profitability Analysis

## Q3. Is Spotify becoming more profitable? **Yes, clearly.**

{md_table(table)}

- Gross margin: {a.loc[2022, 'gross_margin_calc_pct']:.1f}% (2022 low) -> **{a.loc[2025, 'gross_margin_calc_pct']:.1f}%** (2025), +{a.loc[2025, 'gross_margin_calc_pct'] - a.loc[2022, 'gross_margin_calc_pct']:.1f}pp.
- Operating margin: {a.loc[2022, 'operating_margin_calc_pct']:.1f}% -> **{a.loc[2025, 'operating_margin_calc_pct']:.1f}%**;
  operating income swung from a €{abs(a.loc[2022, 'operating_income_eur_millions']):,}M loss to a €{a.loc[2025, 'operating_income_eur_millions']:,}M profit.
- Free cash flow: €{a.loc[2022, 'free_cash_flow_eur_millions']:,}M (2022) -> **€{a.loc[2025, 'free_cash_flow_eur_millions']:,}M** (2025),
  a {a.loc[2025, 'fcf_margin_pct']:.1f}% FCF margin.
- Operating leverage: in 2025, **{a.loc[2025, 'incremental_operating_margin_pct']:.0f}%** of incremental revenue reached
  operating income (in 2024 it was {a.loc[2024, 'incremental_operating_margin_pct']:.0f}%, helped by cost cuts). Total
  opex fell in absolute terms in both 2024 and 2025.

## Cost growth vs revenue growth (YoY %)

{md_table(growth)}

## Q4 (part 1). Is marketing spend growing faster than revenue? **No.**

- S&M fell from {a.loc[2023, 'sm_pct_of_revenue']:.1f}% of revenue (2023) to **{a.loc[2025, 'sm_pct_of_revenue']:.1f}%** (2025).
- 2025 S&M grew {a.loc[2025, 'sm_growth_pct']:.1f}% against revenue growth of {a.loc[2025, 'revenue_growth_pct']:.1f}%.
- S&M is {a.loc[2025, 'sm_pct_of_opex']:.0f}% of 2025 operating expenses, so it is a major lever on operating margin.

## Quarterly profitability

{md_table(qtable)}

- Q2 2025's operating margin dip ({q.iloc[2]['operating_margin_calc_pct']:.1f}%) came from higher operating expenses
  (€{q.iloc[2]['total_operating_expenses_eur_millions']}M). Gross margin was stable. Q4 2025 set the highs for both
  gross margin ({q.iloc[-1]['gross_margin_calc_pct']:.1f}%) and operating margin ({q.iloc[-1]['operating_margin_calc_pct']:.1f}%).
- Free cash flow is a non-IFRS, company-defined measure.
""")


if __name__ == "__main__":
    main()
