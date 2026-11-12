"""Phase 8 - Scenario and sensitivity analysis on the base-year unit economics.

Tests churn, marketing spend, gross margin, subscriber-growth slowdown and subscription revenue (ARPU) changes,
individually and combined, plus two-way sensitivity grids and a tornado chart.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from common import (
    BASE_CHURN, BASE_YEAR, BLUE, DATA_PROCESSED, INK_2, ORANGE, SURFACE, base_inputs, md_table, save_chart,
    save_csv, unit_economics, write_report,
)

BASE = base_inputs(BASE_YEAR)
OPENING_SUBS = BASE["avg_subs"] - BASE["net_adds"] / 2


def run(churn=BASE_CHURN, gm_pp=0.0, arpu_chg=0.0, sm_chg=0.0, net_adds_chg=0.0) -> dict:
    """Unit economics with adjustments applied to the base-year inputs."""
    net_adds = BASE["net_adds"] * (1 + net_adds_chg)
    return unit_economics(
        arpu=BASE["arpu"] * (1 + arpu_chg),
        gross_margin=BASE["gross_margin"] + gm_pp / 100,
        churn=churn,
        sm_expense=BASE["sm_expense"] * (1 + sm_chg),
        net_adds=net_adds,
        avg_subs=OPENING_SUBS + net_adds / 2,
    )


SCENARIOS = [
    ("Base case", "Base", {}),
    ("Optimistic churn (2%)", "Churn", {"churn": 0.02}),
    ("Moderate-risk churn (4%)", "Churn", {"churn": 0.04}),
    ("High-risk churn (5%)", "Churn", {"churn": 0.05}),
    ("Marketing spend +10%", "Marketing", {"sm_chg": 0.10}),
    ("Marketing spend +20%", "Marketing", {"sm_chg": 0.20}),
    ("Gross margin +1pp", "Gross margin", {"gm_pp": 1}),
    ("Gross margin +2pp", "Gross margin", {"gm_pp": 2}),
    ("Gross margin +3pp", "Gross margin", {"gm_pp": 3}),
    ("Subscriber growth slowdown (net adds -25%)", "Growth", {"net_adds_chg": -0.25}),
    ("Subscriber growth slowdown (net adds -50%)", "Growth", {"net_adds_chg": -0.50}),
    ("Subscription revenue -10% (ARPU)", "Revenue", {"arpu_chg": -0.10}),
    ("Subscription revenue -5% (ARPU)", "Revenue", {"arpu_chg": -0.05}),
    ("Subscription revenue +5% (ARPU)", "Revenue", {"arpu_chg": 0.05}),
    ("Subscription revenue +10% (ARPU)", "Revenue", {"arpu_chg": 0.10}),
    ("Combined downside", "Combined", {"churn": 0.04, "sm_chg": 0.10, "net_adds_chg": -0.25, "arpu_chg": -0.05}),
    ("Combined upside", "Combined", {"churn": 0.025, "gm_pp": 2, "arpu_chg": 0.05}),
]

# Tornado levers: (label, low-case kwargs, high-case kwargs)
LEVERS = [
    ("Monthly churn 2% / 4%", {"churn": 0.02}, {"churn": 0.04}),
    ("Gross margin -2pp / +2pp", {"gm_pp": -2}, {"gm_pp": 2}),
    ("ARPU -10% / +10%", {"arpu_chg": -0.10}, {"arpu_chg": 0.10}),
    ("S&M spend -20% / +20%", {"sm_chg": -0.20}, {"sm_chg": 0.20}),
    ("Net adds -25% / +25%", {"net_adds_chg": -0.25}, {"net_adds_chg": 0.25}),
]


def scenario_table() -> pd.DataFrame:
    rows = []
    for name, group, kw in SCENARIOS:
        rows.append({"scenario": name, "lever": group, "churn_assumption_pct": kw.get("churn", BASE_CHURN) * 100,
                     "sm_change_pct": kw.get("sm_chg", 0) * 100, "gross_margin_change_pp": kw.get("gm_pp", 0),
                     "net_adds_change_pct": kw.get("net_adds_chg", 0) * 100, "arpu_change_pct": kw.get("arpu_chg", 0) * 100,
                     **run(**kw)})
    df = pd.DataFrame(rows)
    base_ltv = df.loc[0, "ltv_eur"]
    df["ltv_change_vs_base_pct"] = (df["ltv_eur"] / base_ltv - 1) * 100
    return df


def grid(metric: str, rows: dict, cols: dict) -> pd.DataFrame:
    """Two-way sensitivity grid. rows/cols map a display label to run() kwargs."""
    data = {c_label: [run(**{**r_kw, **c_kw})[metric] for r_kw in rows.values()] for c_label, c_kw in cols.items()}
    return pd.DataFrame(data, index=list(rows))


def heatmap(df: pd.DataFrame, title: str, xlabel: str, ylabel: str, fmt: str, name: str, note: str):
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    sns.heatmap(df, annot=True, fmt=fmt, cmap="Blues", linewidths=2, linecolor=SURFACE, cbar_kws={"shrink": 0.8},
                annot_kws={"fontsize": 9}, ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(length=0)
    ax.tick_params(axis="y", rotation=0)
    save_chart(fig, name, note)


def tornado(metric: str) -> pd.DataFrame:
    base = run()[metric]
    rows = []
    for label, lo, hi in LEVERS:
        rows.append({"metric": metric, "lever": label, "base": base, "low_case": run(**lo)[metric], "high_case": run(**hi)[metric]})
    df = pd.DataFrame(rows)
    df["swing"] = (df["high_case"] - df["low_case"]).abs()
    return df.sort_values("swing").reset_index(drop=True)


def tornado_chart(panels: list[tuple[pd.DataFrame, str]]):
    fig, axes = plt.subplots(1, len(panels), figsize=(12, 4.6), sharey=False)
    for ax, (df, title) in zip(axes, panels):
        base = df["base"].iloc[0]
        y = np.arange(len(df))
        ax.barh(y, df["low_case"] - base, left=base, color=BLUE, height=0.55, label="Lever at low value", edgecolor=SURFACE, linewidth=2)
        ax.barh(y, df["high_case"] - base, left=base, color=ORANGE, height=0.55, label="Lever at high value", edgecolor=SURFACE, linewidth=2)
        ax.axvline(base, color=INK_2, linewidth=1)
        ax.set_yticks(y, df["lever"])
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.set_title(f"{title}\n(base {base:.2f}x)", fontsize=11)
        ax.set_xlabel("LTV:CAC (x)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.suptitle("What moves LTV:CAC most? Tornado sensitivity on the 2025 base", x=0.01, ha="left",
                 fontweight="bold", fontsize=13)
    fig.tight_layout()
    fig.legend(handles, labels, loc="upper right", ncol=2, fontsize=9, bbox_to_anchor=(0.99, 1.0))
    save_chart(fig, "19_tornado_ltv_cac", "Bar ends show LTV:CAC with one lever moved and all others at base (3% churn).")


def main():
    scen = scenario_table()
    save_csv(scen, DATA_PROCESSED / "scenario_comparison.csv")

    churn_rows = {f"{c:.1f}%": {"churn": c / 100} for c in np.arange(1.5, 6.01, 0.5)}
    gm_cols = {f"{BASE['gross_margin'] * 100 + d:.0f}%": {"gm_pp": d} for d in range(-4, 9, 2)}
    sm_cols = {f"{d:+d}%": {"sm_chg": d / 100} for d in range(-20, 31, 10)}
    ltv_grid = grid("ltv_eur", churn_rows, gm_cols)
    ratio_grid = grid("ltv_to_cac_gross_adds", churn_rows, sm_cols)
    ratio_net_grid = grid("ltv_to_cac_net_adds", churn_rows, sm_cols)

    heatmap(ltv_grid, "LTV (EUR) by monthly churn and gross margin", "Gross margin", "Monthly churn", ".0f",
            "17_ltv_sensitivity_heatmap", f"2025 ARPU €{BASE['arpu']:.2f}/month. Churn rates are hypothetical.")
    heatmap(ratio_grid, "LTV:CAC (gross-adds proxy) by churn and S&M spend change", "Change in S&M spend vs 2025",
            "Monthly churn", ".1f", "18_ltv_cac_sensitivity_heatmap", "CAC proxy = S&M / (net adds + churn-implied replacements).")

    long = pd.concat([
        ltv_grid.rename_axis("monthly_churn").reset_index().melt("monthly_churn", var_name="column_value", value_name="value").assign(metric="LTV (EUR)", column_dimension="Gross margin"),
        ratio_grid.rename_axis("monthly_churn").reset_index().melt("monthly_churn", var_name="column_value", value_name="value").assign(metric="LTV:CAC gross-adds proxy", column_dimension="S&M change"),
        ratio_net_grid.rename_axis("monthly_churn").reset_index().melt("monthly_churn", var_name="column_value", value_name="value").assign(metric="LTV:CAC net-adds proxy", column_dimension="S&M change"),
    ])
    save_csv(long, DATA_PROCESSED / "sensitivity_grids_long.csv")

    t_gross = tornado("ltv_to_cac_gross_adds")
    t_net = tornado("ltv_to_cac_net_adds")
    save_csv(pd.concat([t_gross, t_net]), DATA_PROCESSED / "tornado_sensitivity.csv")
    tornado_chart([(t_gross, "Gross-adds CAC proxy"), (t_net, "Net-adds CAC proxy")])

    table = scen[["scenario", "ltv_eur", "ltv_change_vs_base_pct", "cac_proxy_net_adds_eur", "cac_proxy_gross_adds_eur",
                  "ltv_to_cac_net_adds", "ltv_to_cac_gross_adds", "payback_months_gross_adds"]].rename(columns={
        "scenario": "Scenario", "ltv_eur": "LTV (EUR)", "ltv_change_vs_base_pct": "LTV vs base %",
        "cac_proxy_net_adds_eur": "CAC net (EUR)", "cac_proxy_gross_adds_eur": "CAC gross (EUR)",
        "ltv_to_cac_net_adds": "LTV:CAC net", "ltv_to_cac_gross_adds": "LTV:CAC gross",
        "payback_months_gross_adds": "Payback gross (mo)"})
    top_gross, top_net = t_gross.iloc[-1], t_net.iloc[-1]
    s = scen.set_index("scenario")

    write_report("06_scenario_analysis.md", f"""
# Phase 8: Scenario & Sensitivity Analysis ({BASE_YEAR} base, {BASE_CHURN:.0%} churn)

Each scenario changes one lever (or a defined combination) and keeps everything else at the {BASE_YEAR} base.
Churn rates are hypothetical. CAC figures are proxies (see Phase 5).

{md_table(table, ",.2f")}

**Combined downside:** 4% churn, S&M +10%, net adds -25%, ARPU -5%. **Combined upside:** 2.5% churn, gross margin +2pp,
ARPU +5%.

## What the scenarios show

- **Churn dominates LTV.** LTV ranges from €{s.loc['High-risk churn (5%)', 'ltv_eur']:.0f} to €{s.loc['Optimistic churn (2%)', 'ltv_eur']:.0f} across
  the churn scenarios. No other single lever comes close.
- **Gross margin is a low-risk lever.** Each +1pp of gross margin adds about
  {s.loc['Gross margin +1pp', 'ltv_change_vs_base_pct']:.1f}% to LTV. That matches a
  {s.loc['Gross margin +1pp', 'ltv_change_vs_base_pct']:.1f}% price increase without the churn risk of raising prices.
- **Marketing +10% / +20%** lowers LTV:CAC (gross-adds proxy) from {s.loc['Base case', 'ltv_to_cac_gross_adds']:.2f}x to
  {s.loc['Marketing spend +10%', 'ltv_to_cac_gross_adds']:.2f}x / {s.loc['Marketing spend +20%', 'ltv_to_cac_gross_adds']:.2f}x.
  Extra spend has to produce extra subscribers to pay off.
- **Growth slowdown:** if net adds fall 50% while S&M stays flat, the net-adds CAC proxy doubles to
  €{s.loc['Subscriber growth slowdown (net adds -50%)', 'cac_proxy_net_adds_eur']:.0f}. The gross-adds proxy only rises to
  €{s.loc['Subscriber growth slowdown (net adds -50%)', 'cac_proxy_gross_adds_eur']:.2f}, because replacement acquisitions dominate gross adds.
- **Biggest lever (tornado):** for the gross-adds proxy it is *{top_gross['lever']}* (LTV:CAC
  {top_gross['low_case']:.2f}x-{top_gross['high_case']:.2f}x). For the net-adds proxy it is *{top_net['lever']}*
  ({top_net['low_case']:.2f}x-{top_net['high_case']:.2f}x).
- **Combined downside** takes LTV:CAC to {s.loc['Combined downside', 'ltv_to_cac_gross_adds']:.2f}x (gross) /
  {s.loc['Combined downside', 'ltv_to_cac_net_adds']:.2f}x (net). **Combined upside** reaches
  {s.loc['Combined upside', 'ltv_to_cac_gross_adds']:.2f}x / {s.loc['Combined upside', 'ltv_to_cac_net_adds']:.2f}x.

Charts: `17_ltv_sensitivity_heatmap.png`, `18_ltv_cac_sensitivity_heatmap.png`, `19_tornado_ltv_cac.png`.
""")


if __name__ == "__main__":
    main()
