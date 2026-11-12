"""Phase 1 & 2 - Data quality validation and exploratory data analysis.

Validates the reported figures for internal consistency (segment sums, margins,
annual vs quarterly totals, stock reconciliation), re-derives the analyst columns,
writes clean datasets and produces the EDA charts and report.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    ANNUAL_CLEAN, ANNUAL_RAW, AQUA, BLUE, INK_2, ORANGE, QUARTERLY_CLEAN, QUARTERLY_RAW,
    ROOT, SURFACE, md_table, pct_change, save_chart, save_csv, write_report,
)

DERIVED_COLUMNS = [
    "sales_marketing_expense_eur_millions",  # reported, but only 2023-2025
    "premium_subscriber_net_adds_millions",
    "mau_net_adds_millions",
    "premium_revenue_per_avg_subscriber_per_month_eur_approx",
    "sales_marketing_per_net_added_premium_subscriber_eur_proxy",
]
FLOW_COLUMNS = [
    "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions", "total_revenue_eur_millions",
    "gross_profit_eur_millions", "total_operating_expenses_eur_millions", "operating_income_eur_millions",
    "operating_cash_flow_eur_millions", "free_cash_flow_eur_millions",
]
STOCK_COLUMNS = ["mau_millions", "premium_subscribers_millions", "ad_supported_mau_millions"]

checks: list[dict] = []


def check(name, period, expected, actual, tolerance):
    diff = actual - expected
    checks.append({
        "check": name, "period": str(period), "expected": round(float(expected), 3),
        "actual": round(float(actual), 3), "difference": round(float(diff), 3),
        "result": "PASS" if abs(diff) <= tolerance else "FAIL",
    })


def profile(df: pd.DataFrame, name: str) -> pd.DataFrame:
    return pd.DataFrame({
        "dataset": name,
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "non_null": df.notna().sum().values,
        "missing": df.isna().sum().values,
    })


def validate(annual: pd.DataFrame, quarterly: pd.DataFrame):
    for df, label_col in ((annual, "year"), (quarterly, "period")):
        for r in df.itertuples():
            p = getattr(r, label_col)
            check("Premium + ad-supported revenue = total revenue", p,
                  r.total_revenue_eur_millions, r.premium_revenue_eur_millions + r.ad_supported_revenue_eur_millions, 1)
            check("Gross profit / revenue = reported gross margin %", p,
                  r.gross_margin_pct, r.gross_profit_eur_millions / r.total_revenue_eur_millions * 100, 0.06)
            check("Gross profit - operating expenses = operating income", p,
                  r.operating_income_eur_millions, r.gross_profit_eur_millions - r.total_operating_expenses_eur_millions, 1)
            check("Operating income / revenue = reported operating margin %", p,
                  r.operating_margin_pct, r.operating_income_eur_millions / r.total_revenue_eur_millions * 100, 0.06)
            check("Free cash flow <= operating cash flow", p, 0,
                  max(0, r.free_cash_flow_eur_millions - r.operating_cash_flow_eur_millions), 0)

    # Quarterly flows for 2025 must add up to the 2025 annual figures.
    q2025 = quarterly[quarterly["period"].str.startswith("2025")]
    a2025 = annual.set_index("year").loc[2025]
    for col in FLOW_COLUMNS:
        check(f"Sum of 2025 quarters = annual 2025 ({col})", 2025, a2025[col], q2025[col].sum(), 1)

    # Year-end stocks must match the matching Q4 balance.
    for period, year in (("2024-Q4", 2024), ("2025-Q4", 2025)):
        q = quarterly.set_index("period").loc[period]
        a = annual.set_index("year").loc[year]
        for col in STOCK_COLUMNS:
            check(f"{period} = year-end {year} ({col})", year, a[col], q[col], 0)

    # Re-derive the analyst columns supplied in the source and compare.
    a = annual.set_index("year")
    net_adds = a["premium_subscribers_millions"].diff()
    mau_adds = a["mau_millions"].diff()
    avg_subs = a["premium_subscribers_millions"].rolling(2).mean()
    arpu = a["premium_revenue_eur_millions"] / avg_subs / 12
    cac_proxy = a["sales_marketing_expense_eur_millions"] / net_adds
    for year in a.index[1:]:
        check("Premium net adds re-derived", year, a.loc[year, "premium_subscriber_net_adds_millions"], net_adds[year], 0.001)
        check("MAU net adds re-derived", year, a.loc[year, "mau_net_adds_millions"], mau_adds[year], 0.001)
        check("Monthly premium ARPU re-derived", year,
              a.loc[year, "premium_revenue_per_avg_subscriber_per_month_eur_approx"], arpu[year], 0.001)
        if pd.notna(cac_proxy[year]):
            check("S&M per net premium add re-derived", year,
                  a.loc[year, "sales_marketing_per_net_added_premium_subscriber_eur_proxy"], cac_proxy[year], 0.001)


def clean(annual: pd.DataFrame, quarterly: pd.DataFrame):
    annual = annual.drop_duplicates().sort_values("year").reset_index(drop=True)
    quarterly = quarterly.drop_duplicates().sort_values("period").reset_index(drop=True)
    quarterly.insert(1, "year", quarterly["period"].str[:4].astype(int))
    quarterly.insert(2, "quarter", quarterly["period"].str[-2:])
    quarterly.insert(3, "quarter_end_date",
                     pd.PeriodIndex(quarterly["period"].str.replace("-", ""), freq="Q").end_time.date)
    return annual, quarterly


def eda_charts(annual: pd.DataFrame, quarterly: pd.DataFrame):
    years = annual["year"].astype(str)

    # 1. Revenue composition by year (stacked part-to-whole).
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(years, annual["premium_revenue_eur_millions"], color=BLUE, label="Premium", edgecolor=SURFACE, linewidth=2)
    ax.bar(years, annual["ad_supported_revenue_eur_millions"], bottom=annual["premium_revenue_eur_millions"],
           color=ORANGE, label="Ad-supported", edgecolor=SURFACE, linewidth=2)
    for x, total in zip(years, annual["total_revenue_eur_millions"]):
        ax.text(x, total + 250, f"€{total/1000:.1f}B", ha="center", color=INK_2, fontsize=9)
    ax.set_title("Total revenue grew 78% from 2021 to 2025")
    ax.set_ylabel("Revenue (EUR millions)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.legend(loc="upper left")
    save_chart(fig, "01_revenue_by_segment", "Source: Spotify Q4 2025 Shareholder Deck / Form 20-F")

    # 2. Users - MAU, ad-supported MAU and premium subscribers (same unit, one axis).
    fig, ax = plt.subplots(figsize=(8, 4.5))
    series = [("mau_millions", "Total MAU", BLUE), ("ad_supported_mau_millions", "Ad-supported MAU", ORANGE),
              ("premium_subscribers_millions", "Premium subscribers", AQUA)]
    for col, label, color in series:
        ax.plot(years, annual[col], marker="o", color=color, label=label)
        ax.annotate(f"{annual[col].iloc[-1]}M", (len(years) - 1, annual[col].iloc[-1]),
                    xytext=(8, 0), textcoords="offset points", va="center", color=INK_2, fontsize=9)
    ax.set_title("User base: MAU up 85%, premium subscribers up 61% (2021-2025)")
    ax.set_ylabel("Users (millions, year-end)")
    ax.set_ylim(0, None)
    ax.legend(loc="upper left")
    save_chart(fig, "02_user_growth", "Premium + ad-supported exceeds MAU because some users are counted in both during a month.")

    # 3. Quarterly revenue by segment.
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(quarterly["period"], quarterly["premium_revenue_eur_millions"], color=BLUE, label="Premium",
           edgecolor=SURFACE, linewidth=2)
    ax.bar(quarterly["period"], quarterly["ad_supported_revenue_eur_millions"],
           bottom=quarterly["premium_revenue_eur_millions"], color=ORANGE, label="Ad-supported",
           edgecolor=SURFACE, linewidth=2)
    for x, total in zip(quarterly["period"], quarterly["total_revenue_eur_millions"]):
        ax.text(x, total + 60, f"€{total:,}M", ha="center", color=INK_2, fontsize=9)
    ax.set_title("Quarterly revenue: Q4 is the seasonal high for advertising")
    ax.set_ylabel("Revenue (EUR millions)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
    ax.legend(loc="upper left", ncol=2)
    save_chart(fig, "03_quarterly_revenue")

    # 4. Subscriber growth vs revenue growth (n = 4, descriptive only).
    a = annual.set_index("year")
    growth = pd.DataFrame({
        "subs": pct_change(a["premium_subscribers_millions"]),
        "rev": pct_change(a["total_revenue_eur_millions"]),
    }).dropna()
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.grid(True, axis="both")
    lim = (0, max(growth.max()) + 4)
    ax.plot(lim, lim, color="#c3c2b7", linewidth=1, zorder=1)
    ax.text(lim[1] - 0.5, lim[1] - 3, "parity line\n(revenue growth =\nsubscriber growth)", ha="right", va="top",
            color=INK_2, fontsize=8)
    ax.scatter(growth["subs"], growth["rev"], s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
    for year, r in growth.iterrows():
        ax.annotate(str(year), (r["subs"], r["rev"]), xytext=(7, -3), textcoords="offset points", fontsize=9, color=INK_2)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Premium subscriber growth, YoY %")
    ax.set_ylabel("Total revenue growth, YoY %")
    slower = [str(y) for y, r in growth.iterrows() if r["rev"] < r["subs"]]
    ax.set_title(f"Revenue outgrew subscribers in {len(growth) - len(slower)} of {len(growth)} years\n"
                 f"(slower in {', '.join(slower)})")
    corr = growth["subs"].corr(growth["rev"])
    save_chart(fig, "04_subscriber_vs_revenue_growth",
               f"Pearson r = {corr:.2f} on only 4 data points: descriptive, not statistically meaningful.")
    return corr


def main():
    annual_raw = pd.read_csv(ANNUAL_RAW)
    quarterly_raw = pd.read_csv(QUARTERLY_RAW)

    profiles = pd.concat([profile(annual_raw, "annual"), profile(quarterly_raw, "quarterly")])
    dupes = {"annual": int(annual_raw.duplicated().sum()), "quarterly": int(quarterly_raw.duplicated().sum()),
             "annual (year key)": int(annual_raw["year"].duplicated().sum()),
             "quarterly (period key)": int(quarterly_raw["period"].duplicated().sum())}

    validate(annual_raw, quarterly_raw)
    results = pd.DataFrame(checks)
    save_csv(results, ROOT / "data" / "processed" / "validation_checks.csv")
    n_fail = (results["result"] == "FAIL").sum()
    if n_fail:
        print(results[results["result"] == "FAIL"].to_string())

    annual, quarterly = clean(annual_raw, quarterly_raw)
    save_csv(annual, ANNUAL_CLEAN)
    save_csv(quarterly, QUARTERLY_CLEAN)

    overlap = annual.assign(
        premium_plus_ad=annual["premium_subscribers_millions"] + annual["ad_supported_mau_millions"],
    )
    overlap["overlap_millions"] = overlap["premium_plus_ad"] - overlap["mau_millions"]

    corr = eda_charts(annual, quarterly)

    a = annual.set_index("year")
    cagr = lambda col: ((a[col].iloc[-1] / a[col].iloc[0]) ** (1 / (len(a) - 1)) - 1) * 100
    summary = pd.DataFrame({
        "Metric": ["Total revenue (EUR M)", "Premium subscribers (M)", "MAU (M)", "Gross margin %", "Operating income (EUR M)", "Free cash flow (EUR M)"],
        "2021": [a.loc[2021, c] for c in ["total_revenue_eur_millions", "premium_subscribers_millions", "mau_millions", "gross_margin_pct", "operating_income_eur_millions", "free_cash_flow_eur_millions"]],
        "2025": [a.loc[2025, c] for c in ["total_revenue_eur_millions", "premium_subscribers_millions", "mau_millions", "gross_margin_pct", "operating_income_eur_millions", "free_cash_flow_eur_millions"]],
    })
    summary["Change"] = summary["2025"] - summary["2021"]

    missing = profiles[profiles["missing"] > 0][["dataset", "column", "missing"]]
    catalog = pd.read_csv(ROOT / "data" / "data_dictionary.csv")[["field", "data_status"]]

    write_report("01_data_quality_and_eda_report.md", f"""
# Phase 1-2: Data Quality & Exploratory Data Analysis

## Dataset overview

| Dataset | Rows | Columns | Coverage |
| --- | --- | --- | --- |
| Annual | {annual.shape[0]} | {annual_raw.shape[1]} | {annual['year'].min()}-{annual['year'].max()} |
| Quarterly | {quarterly.shape[0]} | {quarterly_raw.shape[1]} | {quarterly['period'].iloc[0]} to {quarterly['period'].iloc[-1]} |

**Duplicates:** {', '.join(f'{k}: {v}' for k, v in dupes.items())}.

## Missing values

All reported financial fields are complete. Gaps only appear in derived or partially supplied columns:

{md_table(missing)}

- `sales_marketing_expense_eur_millions` is only supplied for 2023-2025, so the CAC proxy has 3 data points.
- Net-add and per-subscriber columns are blank for 2021 because they need a prior-year opening balance.

## Validation against reported totals

{len(results)} automated checks, **{(results['result'] == 'PASS').sum()} passed, {n_fail} failed**
(full log: `data/processed/validation_checks.csv`).

{md_table(results.groupby('check')['result'].agg(lambda s: f"{(s == 'PASS').sum()}/{len(s)} pass").reset_index())}

These checks confirm internal consistency: segment sums, margins, the P&L bridge, quarterly-to-annual totals and
year-end stocks. Before publishing, also spot-check the headline numbers against the Q4 2025 Shareholder Deck
(see `data/source_register.csv`).

### Observation: MAU overlap

Premium subscribers + ad-supported MAU exceed total MAU every year, by
{overlap['overlap_millions'].min()}-{overlap['overlap_millions'].max()}M. Spotify counts a user in both tiers if they
used both during the month, so **never add the two user counts together**.

## Reported vs calculated metrics

{md_table(catalog.rename(columns={'field': 'Field', 'data_status': 'Status'}))}

## EDA highlights

{md_table(summary, ",.1f")}

- Revenue CAGR 2021-2025: **{cagr('total_revenue_eur_millions'):.1f}%**; premium subscriber CAGR: **{cagr('premium_subscribers_millions'):.1f}%**;
  MAU CAGR: **{cagr('mau_millions'):.1f}%**.
- Premium is {a.loc[2025, 'premium_revenue_eur_millions'] / a.loc[2025, 'total_revenue_eur_millions'] * 100:.1f}% of 2025 revenue.
- Correlation between premium subscriber growth and revenue growth: r = {corr:.2f} (n = 4). The sample is too small for
  statistical inference; treat this as descriptive only.
- Q4 is the strongest quarter for advertising (Q4 2025 ad revenue: €{quarterly.iloc[-1]['ad_supported_revenue_eur_millions']}M
  vs €{quarterly.iloc[1]['ad_supported_revenue_eur_millions']}M in Q1).

Charts: `outputs/charts/01_*.png` through `04_*.png`.
""")


if __name__ == "__main__":
    main()
