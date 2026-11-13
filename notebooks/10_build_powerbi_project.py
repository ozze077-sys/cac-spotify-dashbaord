"""Phase 11 - Generate a ready-to-open Power BI project (PBIP) that mirrors the Dash dashboard.

Writes powerbi/:
  data/*.csv                              USD tables, the same numbers as dashboards/dashboard.py
  Spotify_Unit_Economics.pbip             open this in Power BI Desktop
  Spotify_Unit_Economics.SemanticModel/   TMDL model: CSV tables (Power Query), what-if tables, DAX measures
  Spotify_Unit_Economics.Report/          PBIR report: 12 pages, green / white / black theme

The model reads the CSVs from an absolute folder path (the DataFolder parameter). If the project is moved, change it in
Power BI Desktop: Transform data -> Edit parameters, or rerun this script.
"""

import json
import shutil
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT

sys.path.insert(0, str(ROOT / "dashboards"))
import dashboard as app  # noqa: E402  (reuses the USD conversion and the Monte Carlo engine)

OUT = ROOT / "powerbi"
NAME = "Spotify_Unit_Economics"
DATA = OUT / "data"
MODEL = OUT / f"{NAME}.SemanticModel"
REPORT = OUT / f"{NAME}.Report"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
GREEN, GREEN_DARK, BLACK, GREY, BORDER, PAGE_BG = "#1DB954", "#148A3E", "#121212", "#9E9E9E", "#E8E8E8", "#F7F7F7"
M = "_measures"  # table that holds every DAX measure

# ============================================================================= 1. data (USD)


def pct(s):
    """0-100 percentages from the pipeline -> fractions, so Power BI can format them as %."""
    return s / 100


def build_tables():
    a, r, s, p, ue = app.annual, app.rev, app.subs, app.prof, app.ue_years
    years = a.index
    t = {}
    t["year_selector"] = pd.DataFrame({"year": years, "year_label": years.astype(str)})

    t["fact_annual"] = pd.DataFrame({
        "year": years, "year_label": years.astype(str),
        "mau_m": a["mau_millions"], "premium_subs_m": a["premium_subscribers_millions"],
        "ad_mau_m": a["ad_supported_mau_millions"],
        "premium_rev_usd_m": a["premium_revenue_eur_millions"], "ad_rev_usd_m": a["ad_supported_revenue_eur_millions"],
        "total_rev_usd_m": a["total_revenue_eur_millions"], "gross_profit_usd_m": a["gross_profit_eur_millions"],
        "opex_usd_m": a["total_operating_expenses_eur_millions"], "op_income_usd_m": a["operating_income_eur_millions"],
        "fcf_usd_m": a["free_cash_flow_eur_millions"], "sm_usd_m": p["sales_marketing_expense_eur_millions"],
        "premium_net_adds_m": s["premium_net_adds_millions"],
        "arpu_monthly_usd": s["premium_arpu_monthly_eur"], "ad_rev_per_ad_mau_usd": s["ad_revenue_per_ad_mau_annual_eur"],
        "rev_per_mau_usd": s["revenue_per_mau_annual_eur"],
        "gross_margin": pct(p["gross_margin_calc_pct"]), "op_margin": pct(p["operating_margin_calc_pct"]),
        "fcf_margin": pct(p["fcf_margin_pct"]), "opex_ratio": pct(p["opex_ratio_pct"]),
        "sm_pct_rev": pct(p["sm_pct_of_revenue"]),
        "rev_growth": pct(r["total_revenue_growth_pct"]), "premium_rev_growth": pct(r["premium_revenue_growth_pct"]),
        "ad_rev_growth": pct(r["ad_supported_revenue_growth_pct"]),
        "premium_sub_growth": pct(s["premium_subscriber_growth_pct"]), "mau_growth": pct(s["mau_growth_pct"]),
        "premium_mix": pct(r["premium_mix_pct"]), "paying_share": pct(s["premium_share_of_mau_pct"]),
    })

    q = app.q
    t["fact_quarterly"] = pd.DataFrame({
        "period": q["period"], "quarter_index": range(1, len(q) + 1),
        "total_rev_usd_m": q["total_revenue_eur_millions"], "premium_rev_usd_m": q["premium_revenue_eur_millions"],
        "ad_rev_usd_m": q["ad_supported_revenue_eur_millions"],
        "gross_margin": pct(q["gross_margin_calc_pct"]), "op_margin": pct(q["operating_margin_calc_pct"]),
        "premium_net_adds_m": q["premium_net_adds_millions"], "arpu_monthly_usd": q["premium_arpu_monthly_eur"],
    })

    t["ue_by_year"] = pd.DataFrame({
        "year": ue.index, "year_label": ue.index.astype(str), "arpu_usd": ue["monthly_arpu_eur"],
        "ltv_usd": ue["ltv_eur"], "cac_net_usd": ue["cac_proxy_net_adds_eur"], "cac_gross_usd": ue["cac_proxy_gross_adds_eur"],
        "ltv_cac_net": ue["ltv_to_cac_net_adds"], "ltv_cac_gross": ue["ltv_to_cac_gross_adds"],
        "payback_net": ue["payback_months_net_adds"], "payback_gross": ue["payback_months_gross_adds"],
    })

    base = [app.usd_base(int(y)) for y in ue.index]
    t["base_inputs"] = pd.DataFrame({
        "year": ue.index, "arpu_usd": [b["arpu"] for b in base], "gross_margin": [b["gross_margin"] for b in base],
        "sm_usd_m": [b["sm_expense"] for b in base], "net_adds_m": [b["net_adds"] for b in base],
        "avg_subs_m": [b["avg_subs"] for b in base],
    })

    # What-if parameter tables (single-select slicers; measures fall back to the dashboard defaults).
    t["p_churn"] = pd.DataFrame({"churn": np.round(np.arange(0.01, 0.0801, 0.0025), 4)})
    t["p_arpu"] = pd.DataFrame({"arpu_change": np.round(np.arange(-0.30, 0.301, 0.05), 2)})
    t["p_gm"] = pd.DataFrame({"gm_change": np.round(np.arange(-0.05, 0.0501, 0.005), 3)})
    t["p_sm"] = pd.DataFrame({"sm_change": np.round(np.arange(-0.50, 0.501, 0.05), 2)})
    t["p_na"] = pd.DataFrame({"na_change": np.round(np.arange(-0.50, 0.501, 0.05), 2)})
    t["p_proxy"] = pd.DataFrame({"proxy": ["Realistic (gross adds)", "Simple (net adds)"]})

    # Axes for the churn curve, retention and sensitivity grids.
    t["churn_curve"] = pd.DataFrame({"churn": np.round(np.arange(0.01, 0.0801, 0.0025), 4)})
    rc = np.round(np.arange(0.01, 0.0601, 0.005), 4)
    t["grid_churn"] = pd.DataFrame({"churn": rc, "churn_label": [f"{c:.1%}" for c in rc]})
    t["grid_month"] = pd.DataFrame({"month": range(1, 13), "month_label": [f"M{m}" for m in range(1, 13)]})
    gm = np.arange(-4, 5)
    t["grid_gm"] = pd.DataFrame({"gm_change": gm / 100, "gm_label": [f"{g:+d}pp" if g else "0pp" for g in gm],
                                 "gm_order": range(len(gm))})

    # Monte Carlo: the dashboard's default ranges, 10,000 runs, fixed seed (identical to the Dash page).
    d = app.MC_DEFAULTS
    sim = app.mc_simulate(app.DEFAULTS, d["churn"], d["arpu"], d["gm"], d["sm"], d["na"], d["runs"])
    edges = np.round(np.arange(0, np.ceil(sim["ratio"].quantile(0.995) * 10) / 10 + 0.1, 0.1), 1)
    idx = np.clip(np.digitize(sim["ratio"], edges) - 1, 0, len(edges) - 2)
    t["mc_runs"] = pd.DataFrame({
        "run": range(1, len(sim) + 1), "churn": sim["Monthly churn %"] / 100, "arpu_usd": sim["ARPU $"],
        "gross_margin": sim["Gross margin %"] / 100, "sm_usd_m": sim["S&M $M"], "net_adds_m": sim["Net adds M"],
        "ltv_usd": sim["ltv"], "cac_usd": sim["cac"], "ltv_cac": sim["ratio"], "payback_months": sim["payback"],
        "bin_index": idx, "bin_label": [f"{edges[i]:.1f}x" for i in idx],
    })
    inputs = ["Monthly churn %", "ARPU $", "Gross margin %", "S&M $M", "Net adds M"]
    ranks = sim[inputs + ["ratio"]].rank()
    corr = ranks[inputs].corrwith(ranks["ratio"])
    t["mc_drivers"] = pd.DataFrame({"input": ["Monthly churn", "ARPU", "Gross margin", "Marketing spend (S&M)",
                                              "Net adds"], "correlation": corr.values, "abs_corr": corr.abs().values})
    pctl = lambda col, lo_good=True: [np.percentile(sim[col], 10 if lo_good else 90), sim[col].median(),
                                      np.percentile(sim[col], 90 if lo_good else 10), sim[col].mean()]
    t["mc_percentiles"] = pd.DataFrame(
        [["LTV:CAC (x)", *pctl("ratio")], ["LTV ($)", *pctl("ltv")], ["CAC ($)", *pctl("cac", False)],
         ["Payback (months)", *pctl("payback", False)]],
        columns=["metric", "p10_pessimistic", "p50_typical", "p90_optimistic", "mean"]).round(2)
    t["mc_percentiles"]["order"] = range(4)

    t["assumptions"] = pd.DataFrame([
        ["Monthly churn", "3.0%", "Share of paying subscribers who cancel each month. Spotify does not publish it.",
         "LTV, average stay, realistic CAC, payback"],
        ["ARPU change", "0%", "Raise or cut the base-year monthly revenue per subscriber.", "LTV, payback"],
        ["Gross margin change", "0pp", "Shift the base-year gross margin (royalties and delivery costs).", "LTV, payback"],
        ["Marketing spend change", "0%", "Raise or cut base-year sales & marketing spend.", "CAC, LTV:CAC, payback"],
        ["Net adds change", "0%", "Raise or cut base-year growth in paying subscribers.", "CAC, LTV:CAC"],
        ["CAC proxy", "Realistic (gross adds)", "Realistic counts subscribers won to replace cancellations; simple "
         "divides marketing by growth only.", "CAC, LTV:CAC, payback"],
        ["Base year", str(app.DEFAULTS["base_year"]), "Which year's actual numbers feed the model (2023 is the first "
         "year with marketing data).", "Every unit-economics figure"],
    ], columns=["assumption", "default", "what_it_is", "what_it_changes"])
    t["assumptions"]["order"] = range(len(t["assumptions"]))
    t["glossary"] = pd.DataFrame(app.GLOSSARY, columns=["term", "meaning"])
    t["formulas"] = pd.DataFrame([
        ["Growth", "(Current - Previous) / Previous"],
        ["Monthly premium ARPU", "Premium revenue / average subscribers / 12"],
        ["LTV", "Monthly ARPU x gross margin / monthly churn"],
        ["CAC proxy (simple)", "S&M / premium net adds"],
        ["CAC proxy (realistic)", "S&M / (net adds + average subscribers x churn x 12)"],
        ["LTV:CAC", "LTV / CAC"],
        ["Payback", "CAC / (monthly ARPU x gross margin)"],
        ["Cohort retention", "1,000 x (1 - monthly churn) ^ months"],
        ["Currency", "EUR converted to USD at the ECB average rate of each year / quarter"],
    ], columns=["metric", "formula"])
    t[M] = pd.DataFrame({"_": [""]})
    return t


# ============================================================================= 2. semantic model (TMDL)

FORMATS = {  # column -> format string; everything else gets a sensible default
    "churn": "0.00%", "arpu_change": "+0%;-0%;0%", "gm_change": "+0.0%;-0.0%;0.0%", "sm_change": "+0%;-0%;0%",
    "na_change": "+0%;-0%;0%", "ltv_cac": '0.00"x"', "correlation": "+0.00;-0.00;0.00",
}
HIDDEN = {"bin_index", "gm_order", "order", "_"}
SORT_BY = {("mc_runs", "bin_label"): "bin_index", ("grid_churn", "churn_label"): "churn",
           ("grid_month", "month_label"): "month", ("grid_gm", "gm_label"): "gm_order",
           ("mc_percentiles", "metric"): "order", ("assumptions", "assumption"): "order"}


def q(name):
    """Quote a TMDL / DAX object name when needed."""
    return name if name.replace("_", "").isalnum() else "'" + name.replace("'", "''") + "'"


def col_format(col, dtype):
    if col in FORMATS:
        return FORMATS[col]
    if col in ("year", "run", "month", "quarter_index", "bin_index", "gm_order", "order"):
        return "0"
    if col.endswith(("margin", "growth", "ratio", "mix", "share", "pct_rev")):
        return "0.0%"
    if col.endswith("_usd_m"):
        return "$#,0"
    if col.endswith("_usd"):
        return "$#,0.00"
    return "#,0.00" if dtype == "double" else "0"


def table_tmdl(name, df, measures=None):
    types = {}
    for c in df.columns:
        types[c] = ("int64" if pd.api.types.is_integer_dtype(df[c]) else
                    "double" if pd.api.types.is_float_dtype(df[c]) else "string")
    lines = [f"table {q(name)}", ""]
    for mname, expr, fmt in measures or []:
        lines += [f"\tmeasure {q(mname)} = {expr}"]
        if fmt:
            lines += [f"\t\tformatString: {fmt}"]
        lines += [""]
    for c in df.columns:
        lines += [f"\tcolumn {q(c)}", f"\t\tdataType: {types[c]}"]
        if types[c] != "string":
            lines += [f"\t\tformatString: {col_format(c, types[c])}"]
        if c in HIDDEN:
            lines += ["\t\tisHidden"]
        if (name, c) in SORT_BY:
            lines += [f"\t\tsortByColumn: {SORT_BY[(name, c)]}"]
        lines += ["\t\tsummarizeBy: none", f"\t\tsourceColumn: {c}", ""]
    mtype = {"int64": "Int64.Type", "double": "type number", "string": "type text"}
    typed = ", ".join(f'{{"{c}", {mtype[types[c]]}}}' for c in df.columns)
    lines += [
        f"\tpartition {q(name)} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t    Source = Csv.Document(File.Contents(DataFolder & "{name}.csv"), '
        '[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
        "\t\t\t\t    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),",
        f'\t\t\t\t    Typed = Table.TransformColumnTypes(Promoted, {{{typed}}}, "en-US")',
        "\t\t\t\tin",
        "\t\t\t\t    Typed",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- DAX measures: (name, expression, format string)
B = '$#,0.00"B"'
MS = '$#,0"M"'
USERS = '#,0"M"'
P1 = "0.0%"
USD2 = "$#,0.00"
X = '0.0"x"'
MO = '0.0" mo"'


def year_value(col, table="fact_annual"):
    return f"VAR y = [Sel Year] RETURN CALCULATE(SUM({table}[{col}]), {table}[year] = y)"


def delta(col, kind, table="fact_annual"):
    fmt = {"B": 'FORMAT(d / 1000, "+$#,0.00;-$#,0.00") & "B"', "M$": 'FORMAT(d, "+$#,0;-$#,0") & "M"',
           "Mu": 'FORMAT(d, "+#,0;-#,0") & "M"', "pct": 'FORMAT(d * 100, "+0.0;-0.0") & "pp"',
           "usd2": 'FORMAT(d, "+$0.00;-$0.00")', "x": 'FORMAT(d, "+0.0;-0.0") & "x"',
           "mo": 'FORMAT(d, "+0.0;-0.0") & " mo"'}[kind]
    return (f"VAR y = [Sel Year] VAR cur = CALCULATE(SUM({table}[{col}]), {table}[year] = y) "
            f"VAR prev = CALCULATE(SUM({table}[{col}]), {table}[year] = y - 1) VAR d = cur - prev "
            f'RETURN IF(ISBLANK(cur), "Not reported for " & y, IF(ISBLANK(prev), "First year in the data", '
            f'IF(d >= 0, "▲ ", "▼ ") & {fmt} & " vs " & (y - 1)))')


# KPI cards: (measure name, column, kind, table)
KPIS = [
    ("Revenue", "total_rev_usd_m", "B", "fact_annual"), ("Premium Revenue", "premium_rev_usd_m", "B", "fact_annual"),
    ("Ad Revenue", "ad_rev_usd_m", "B", "fact_annual"), ("Revenue Growth", "rev_growth", "pct", "fact_annual"),
    ("Premium Mix", "premium_mix", "pct", "fact_annual"),
    ("Premium Subscribers", "premium_subs_m", "Mu", "fact_annual"), ("MAU", "mau_m", "Mu", "fact_annual"),
    ("Ad MAU", "ad_mau_m", "Mu", "fact_annual"), ("Net Adds", "premium_net_adds_m", "Mu", "fact_annual"),
    ("Paying Share", "paying_share", "pct", "fact_annual"),
    ("ARPU", "arpu_monthly_usd", "usd2", "fact_annual"), ("Ad Revenue per Ad MAU", "ad_rev_per_ad_mau_usd", "usd2", "fact_annual"),
    ("Revenue per MAU", "rev_per_mau_usd", "usd2", "fact_annual"),
    ("Gross Margin", "gross_margin", "pct", "fact_annual"), ("Operating Income", "op_income_usd_m", "M$", "fact_annual"),
    ("Operating Margin", "op_margin", "pct", "fact_annual"), ("Free Cash Flow", "fcf_usd_m", "M$", "fact_annual"),
    ("Opex Ratio", "opex_ratio", "pct", "fact_annual"),
    ("LTV", "ltv_usd", "usd2", "ue_by_year"), ("CAC Realistic", "cac_gross_usd", "usd2", "ue_by_year"),
    ("CAC Simple", "cac_net_usd", "usd2", "ue_by_year"), ("LTV:CAC", "ltv_cac_gross", "x", "ue_by_year"),
    ("Payback", "payback_gross", "mo", "ue_by_year"),
]
KIND_FMT = {"B": B, "M$": MS, "Mu": USERS, "pct": P1, "usd2": USD2, "x": X, "mo": MO}


def measures():
    out = [("Sel Year", "SELECTEDVALUE(year_selector[year], MAX(year_selector[year]))", "0")]
    for name, col, kind, table in KPIS:
        expr = year_value(col, table)
        if kind == "B":
            expr = f"VAR y = [Sel Year] RETURN CALCULATE(SUM({table}[{col}]), {table}[year] = y) / 1000"
        out.append((f"{name} (Y)", expr, KIND_FMT[kind]))
        out.append((f"{name} (Y) Change", delta(col, kind, table), None))
    out.append(("Year Title", '"Key numbers for " & [Sel Year]', None))

    def s(name, table, col, fmt):
        # Money and people add up across years; ratios, per-user values and months are averaged instead.
        agg = "SUM" if fmt in (MS, USERS) else "AVERAGE"
        out.append((name, f"{agg}({table}[{col}])", fmt))

    for name, col, fmt in [
        ("Premium Revenue $M", "premium_rev_usd_m", MS), ("Ad Revenue $M", "ad_rev_usd_m", MS),
        ("Total Revenue $M", "total_rev_usd_m", MS), ("Gross Margin %", "gross_margin", P1),
        ("Operating Margin %", "op_margin", P1), ("Cash Margin %", "fcf_margin", P1), ("Opex Ratio %", "opex_ratio", P1),
        ("S&M % of Revenue", "sm_pct_rev", P1), ("Premium Mix %", "premium_mix", P1),
        ("Premium Revenue Growth %", "premium_rev_growth", P1), ("Ad Revenue Growth %", "ad_rev_growth", P1),
        ("Total Revenue Growth %", "rev_growth", P1), ("Subscriber Growth %", "premium_sub_growth", P1),
        ("MAU M", "mau_m", USERS), ("Ad MAU M", "ad_mau_m", USERS), ("Premium Subscribers M", "premium_subs_m", USERS),
        ("Net Adds M", "premium_net_adds_m", USERS), ("Paying Share %", "paying_share", P1),
        ("ARPU $", "arpu_monthly_usd", USD2), ("Ad Revenue per Ad MAU $", "ad_rev_per_ad_mau_usd", USD2),
        ("Operating Income $M", "op_income_usd_m", MS), ("Free Cash Flow $M", "fcf_usd_m", MS),
    ]:
        s(name, "fact_annual", col, fmt)
    for name, col, fmt in [
        ("Q Premium Revenue $M", "premium_rev_usd_m", MS), ("Q Ad Revenue $M", "ad_rev_usd_m", MS),
        ("Q Total Revenue $M", "total_rev_usd_m", MS), ("Q Gross Margin %", "gross_margin", P1),
        ("Q Operating Margin %", "op_margin", P1), ("Q Net Adds M", "premium_net_adds_m", USERS),
        ("Q ARPU $", "arpu_monthly_usd", USD2),
    ]:
        s(name, "fact_quarterly", col, fmt)
    for name, col, fmt in [
        ("CAC Simple $", "cac_net_usd", USD2), ("CAC Realistic $", "cac_gross_usd", USD2),
        ("Payback Simple (mo)", "payback_net", MO), ("Payback Realistic (mo)", "payback_gross", MO),
        ("LTV at 3% churn $", "ltv_usd", USD2), ("LTV:CAC Simple", "ltv_cac_net", X),
        ("LTV:CAC Realistic", "ltv_cac_gross", X),
    ]:
        s(name, "ue_by_year", col, fmt)

    base = "VAR y = [WI Base Year] RETURN CALCULATE(MAX(base_inputs[{c}]), base_inputs[year] = y)"
    out += [
        ("WI Churn", "SELECTEDVALUE(p_churn[churn], 0.03)", "0.00%"),
        ("WI ARPU Change", "SELECTEDVALUE(p_arpu[arpu_change], 0)", "+0%;-0%;0%"),
        ("WI GM Change", "SELECTEDVALUE(p_gm[gm_change], 0)", "+0.0%;-0.0%;0.0%"),
        ("WI S&M Change", "SELECTEDVALUE(p_sm[sm_change], 0)", "+0%;-0%;0%"),
        ("WI Net Adds Change", "SELECTEDVALUE(p_na[na_change], 0)", "+0%;-0%;0%"),
        ("WI Proxy", 'SELECTEDVALUE(p_proxy[proxy], "Realistic (gross adds)")', None),
        ("WI Base Year", f"SELECTEDVALUE(base_inputs[year], {app.DEFAULTS['base_year']})", "0"),
        ("Base ARPU", base.format(c="arpu_usd"), USD2),
        ("Base Gross Margin", base.format(c="gross_margin"), P1),
        ("Base S&M", base.format(c="sm_usd_m"), MS),
        ("Base Net Adds", base.format(c="net_adds_m"), '#,0.0"M"'),
        ("Base Avg Subscribers", base.format(c="avg_subs_m"), '#,0.0"M"'),
        ("WI ARPU", "[Base ARPU] * (1 + [WI ARPU Change])", USD2),
        ("WI Gross Margin", "[Base Gross Margin] + [WI GM Change]", P1),
        ("WI S&M", "[Base S&M] * (1 + [WI S&M Change])", MS),
        ("WI Net Adds", "[Base Net Adds] * (1 + [WI Net Adds Change])", '#,0.0"M"'),
        ("WI Avg Subscribers", "[Base Avg Subscribers] - [Base Net Adds] / 2 + [WI Net Adds] / 2", '#,0.0"M"'),
        ("WI Monthly Gross Profit", "[WI ARPU] * [WI Gross Margin]", USD2),
        ("WI Average Stay", "DIVIDE(1, [WI Churn])", MO),
        ("WI LTV", "DIVIDE([WI Monthly Gross Profit], [WI Churn])", USD2),
        ("WI CAC Simple", "DIVIDE([WI S&M], [WI Net Adds])", USD2),
        ("WI CAC Realistic", "DIVIDE([WI S&M], [WI Net Adds] + [WI Avg Subscribers] * [WI Churn] * 12)", USD2),
        ("WI CAC", 'IF([WI Proxy] = "Simple (net adds)", [WI CAC Simple], [WI CAC Realistic])', USD2),
        ("WI LTV:CAC", "DIVIDE([WI LTV], [WI CAC])", X),
        ("WI Payback", "DIVIDE([WI CAC], [WI Monthly Gross Profit])", MO),
        ("WI Status", 'IF([WI LTV:CAC] >= 3, "Healthy (3x or more)", "Weak (below 3x)")', None),
        ("WI Recovered", 'IF([WI Payback] < [WI Average Stay], "Cost earned back in time", "Cost NOT earned back")', None),
        ("Curve LTV", "DIVIDE([WI Monthly Gross Profit], SELECTEDVALUE(churn_curve[churn]))", USD2),
        ("Curve CAC Simple", "IF(NOT ISBLANK(SELECTEDVALUE(churn_curve[churn])), [WI CAC Simple])", USD2),
        ("Curve CAC Realistic", "VAR c = SELECTEDVALUE(churn_curve[churn]) RETURN "
                                "IF(NOT ISBLANK(c), DIVIDE([WI S&M], [WI Net Adds] + [WI Avg Subscribers] * c * 12))", USD2),
        ("Retained per 1,000", "VAR c = SELECTEDVALUE(grid_churn[churn]) VAR m = SELECTEDVALUE(grid_month[month]) "
                               "RETURN IF(NOT ISBLANK(c) && NOT ISBLANK(m), 1000 * POWER(1 - c, m))", "#,0"),
        ("Retained at Selected Churn", "VAR m = SELECTEDVALUE(grid_month[month]) RETURN "
                                       "IF(NOT ISBLANK(m), 1000 * POWER(1 - [WI Churn], m))", "#,0"),
        ("Cumulative Profit per Subscriber", "VAR m = SELECTEDVALUE(grid_month[month]) VAR c = [WI Churn] RETURN "
                                             "IF(NOT ISBLANK(m), [WI Monthly Gross Profit] * (1 - c) * (1 - POWER(1 - c, m)) / c)", USD2),
        ("Sensitivity LTV:CAC", "VAR c = SELECTEDVALUE(grid_churn[churn]) VAR g = SELECTEDVALUE(grid_gm[gm_change]) "
                                "VAR ltv = DIVIDE([WI ARPU] * ([Base Gross Margin] + g), c) "
                                'VAR cac = IF([WI Proxy] = "Simple (net adds)", [WI CAC Simple], '
                                "DIVIDE([WI S&M], [WI Net Adds] + [WI Avg Subscribers] * c * 12)) "
                                "RETURN IF(NOT ISBLANK(c) && NOT ISBLANK(g), DIVIDE(ltv, cac))", '0.00"x"'),
        ("MC Runs", "COUNTROWS(mc_runs)", "#,0"),
        ("MC Runs 3x or Better", "CALCULATE(COUNTROWS(mc_runs), mc_runs[ltv_cac] >= 3)", "#,0"),
        ("MC Runs Below 3x", "CALCULATE(COUNTROWS(mc_runs), mc_runs[ltv_cac] < 3)", "#,0"),
        ("MC Chance 3x", "DIVIDE([MC Runs 3x or Better], [MC Runs])", "0%"),
        ("MC P10 LTV:CAC", "PERCENTILE.INC(mc_runs[ltv_cac], 0.10)", X),
        ("MC P50 LTV:CAC", "MEDIAN(mc_runs[ltv_cac])", X),
        ("MC P90 LTV:CAC", "PERCENTILE.INC(mc_runs[ltv_cac], 0.90)", X),
        ("MC Range Text", 'FORMAT([MC P10 LTV:CAC], "0.0") & "x – " & FORMAT([MC P90 LTV:CAC], "0.0") & "x (P10–P90)"', None),
        ("MC P50 LTV", "MEDIAN(mc_runs[ltv_usd])", USD2),
        ("MC P50 CAC", "MEDIAN(mc_runs[cac_usd])", USD2),
        ("MC Payback in Time", "DIVIDE(COUNTROWS(FILTER(mc_runs, mc_runs[payback_months] < DIVIDE(1, mc_runs[churn]))), "
                               "[MC Runs])", "0%"),
        ("MC Positive Effect", "VAR v = SUM(mc_drivers[correlation]) RETURN IF(v >= 0, v)", "+0.00;-0.00;0.00"),
        ("MC Negative Effect", "VAR v = SUM(mc_drivers[correlation]) RETURN IF(v < 0, v)", "+0.00;-0.00;0.00"),
        ("Disclaimer", f'"{app.DISCLAIMER}"', None),
    ]
    return out


def write_model(tables):
    defn = MODEL / "definition"
    (defn / "tables").mkdir(parents=True)
    data_folder = str(DATA) + "\\"  # Power Query strings have no backslash escapes
    (MODEL / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    (MODEL / ".platform").write_text(json.dumps({
        "$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}}, indent=2), encoding="utf-8")
    (defn / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1600\n", encoding="utf-8")
    order = json.dumps(["DataFolder", *tables])
    (defn / "model.tmdl").write_text(
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: en-US\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_QueryOrder = {order}\n\nannotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        + "".join(f"ref table {q(n)}\n" for n in tables), encoding="utf-8")
    (defn / "expressions.tmdl").write_text(
        f'expression DataFolder = "{data_folder}" meta [IsParameterQuery = true, Type = "Text", '
        "IsParameterQueryRequired = true]\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    for name, df in tables.items():
        tm = table_tmdl(name, df, measures() if name == M else None)
        (defn / "tables" / f"{name}.tmdl").write_text(tm, encoding="utf-8")


# ============================================================================= 3. report (PBIR)


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


def color(hex_):
    return {"solid": {"color": lit(hex_)}}


def measure(name):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": name}},
            "queryRef": f"{M}.{name}", "nativeQueryRef": name}


def column(table, col):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": col}},
            "queryRef": f"{table}.{col}", "nativeQueryRef": col}


NAV_W = 200  # left sidebar with page buttons; page content is laid out on a 1280-wide grid to its right
PAGE_W = 1280 + NAV_W
MENU = {"overview": "Executive Overview", "revenue": "Revenue Analysis", "subscribers": "Subscriber Base",
        "arpu": "ARPU", "profitability": "Profitability & Margins", "cac": "CAC", "ltv": "LTV & LTV:CAC",
        "retention": "Retention & Churn", "sensitivity": "Sensitivity Analysis", "montecarlo": "Monte Carlo",
        "assumptions": "Model Assumptions", "data": "Data & Methodology"}


class Page:
    def __init__(self, key, title, subtitle):
        self.key, self.title, self.visuals = key, title, []
        self.textbox(0, 0, 1280, 64, [(title, 20, "#FFFFFF", True), ("   " + subtitle, 11, "#BFC7C2", False)],
                     bg=BLACK, name="header")

    def add(self, vtype, x, y, w, h, roles=None, title=None, sort=None, objects=None, vco=None, sync=None, name=None,
            nav=False):
        x = x if nav else x + NAV_W
        z = len(self.visuals) * 1000
        visual = {"visualType": vtype, "drillFilterOtherVisuals": True}
        if roles:
            visual["query"] = {"queryState": {role: {"projections": p} for role, p in roles.items()}}
            if sort:
                field, direction = sort
                visual["query"]["sortDefinition"] = {"sort": [{"field": field["field"], "direction": direction}]}
        if objects:
            visual["objects"] = objects
        vco = dict(vco or {})
        if title:
            vco["title"] = [{"properties": {"show": lit(True), "text": lit(title), "fontSize": lit(11),
                                            "bold": lit(True), "fontColor": color(BLACK)}}]
        if vco:
            visual["visualContainerObjects"] = vco
        if sync:
            visual["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
        self.visuals.append({
            "$schema": f"{SCHEMA}/item/report/definition/visualContainer/2.0.0/schema.json",
            "name": name or f"v{len(self.visuals):02d}{uuid.uuid4().hex[:14]}",
            "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
            "visual": visual})

    def textbox(self, x, y, w, h, runs, bg=None, name=None, nav=False, lines=None):
        """runs: one paragraph of (text, size, colour, bold); lines: several such paragraphs."""
        paragraphs = [{"textRuns": [{"value": text, "textStyle": {"fontSize": f"{size}pt", "color": col,
                                                                    **({"fontWeight": "bold"} if bold else {})}}
                                    for text, size, col, bold in para]} for para in (lines or [runs])]
        vco = {"background": [{"properties": {"show": lit(True), "color": color(bg), "transparency": lit(0)}}],
               "border": [{"properties": {"show": lit(False)}}]} if bg else \
              {"background": [{"properties": {"show": lit(False)}}], "border": [{"properties": {"show": lit(False)}}]}
        self.add("textbox", x, y, w, h, objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                 vco=vco, name=name, nav=nav)

    def sidebar(self):
        """Black left menu: brand, a Unit Economics badge and one page-navigation button per page."""
        self.textbox(0, 0, NAV_W, 720, None, bg=BLACK, name="nav_bg", nav=True, lines=[
            [("Spotify", 20, "#FFFFFF", True)], [("Financial Analysis", 9, "#8A8F98", False)]])
        self.textbox(14, 76, NAV_W - 28, 50, None, bg=GREEN, name="nav_badge", nav=True, lines=[
            [("UNIT ECONOMICS", 11, BLACK, True)], [("LTV · CAC · ARPU · Churn", 8, BLACK, False)]])
        # Button format: an un-scoped entry switches each part on/off; entries with a state selector style it.
        for i, (key, label) in enumerate(MENU.items()):
            active = key == self.key
            fills = {"default": GREEN if active else "#1A1A1A", "hover": GREEN if active else "#24402E"}
            inks = {"default": BLACK if active else "#D5D9DF", "hover": BLACK if active else "#FFFFFF"}
            text = [{"properties": {"show": lit(True)}}] + [
                {"properties": {"text": lit(label), "fontColor": color(inks[s]), "fontSize": lit(10),
                                "bold": lit(active), "horizontalAlignment": lit("left")}, "selector": {"id": s}}
                for s in fills]
            fill = [{"properties": {"show": lit(True)}}] + [
                {"properties": {"fillColor": color(fills[s]), "transparency": lit(0)}, "selector": {"id": s}}
                for s in fills]
            self.add("actionButton", 10, 140 + i * 46, NAV_W - 20, 40, name=f"nav_{key}", nav=True,
                     objects={"text": text, "fill": fill,
                              "icon": [{"properties": {"show": lit(False)}},
                                       {"properties": {"shapeType": lit("blank"), "placement": lit("left")},
                                        "selector": {"id": "default"}}],
                              "outline": [{"properties": {"show": lit(False)}}],
                              "shape": [{"properties": {"tileShape": lit("rectangleRounded"),
                                                        "roundEdge": {"expr": {"Literal": {"Value": "8L"}}}}}]},
                     vco={"visualLink": [{"properties": {"show": lit(True), "type": lit("PageNavigation"),
                                                         "navigationSection": lit(key)}}],
                          "background": [{"properties": {"show": lit(False)}}],
                          "border": [{"properties": {"show": lit(False)}}],
                          "title": [{"properties": {"show": lit(False)}}]})

    def note(self, x, y, w, h, text):
        self.textbox(x, y, w, h, [(text, 10, "#55595F", False)])

    def kpi(self, x, y, w, label, value_measure, change_measure=None):
        """KPI block: a card with the value and, under it, a card with the change text."""
        self.add("card", x, y, w, 82, roles={"Values": [measure(value_measure)]}, title=label,
                 objects={"labels": [{"properties": {"fontSize": lit(22), "color": color(BLACK), "labelDisplayUnits": lit(1)}}],
                          "categoryLabels": [{"properties": {"show": lit(False)}}]})
        if change_measure:
            self.add("card", x, y + 80, w, 34, roles={"Values": [measure(change_measure)]},
                     objects={"labels": [{"properties": {"fontSize": lit(10), "color": color(GREEN_DARK)}}],
                              "categoryLabels": [{"properties": {"show": lit(False)}}]},
                     vco={"border": [{"properties": {"show": lit(False)}}],
                          "background": [{"properties": {"show": lit(False)}}]})

    def kpi_row(self, items, y=76, change=True):
        gap, x0, w_total = 12, 16, 1248
        w = (w_total - gap * (len(items) - 1)) / len(items)
        for i, (label, m) in enumerate(items):
            self.kpi(x0 + i * (w + gap), y, w, label, m, f"{m} Change" if change else None)

    def chart(self, vtype, x, y, w, h, title, category, values, sort_asc=True, labels=False, colors=None,
              legend=True, extra_objects=None):
        objects = {"legend": [{"properties": {"show": lit(legend), "position": lit("Top")}}]}
        if labels:
            objects["labels"] = [{"properties": {"show": lit(True)}}]
        if colors:
            objects["dataPoint"] = [{"properties": {"fill": color(c)}, "selector": {"metadata": f"{M}.{m}"}}
                                    for m, c in zip(values, colors)]
        objects.update(extra_objects or {})
        self.add(vtype, x, y, w, h, roles={"Category": [category], "Y": [measure(v) for v in values]}, title=title,
                 sort=(category, "Ascending") if sort_asc else None, objects=objects)

    def table(self, x, y, w, h, title, fields, vtype="tableEx"):
        self.add(vtype, x, y, w, h, roles={"Values": fields}, title=title,
                 objects={"total": [{"properties": {"totals": lit(False)}}]})

    def slicer(self, x, y, w, h, title, field, sync=None):
        self.add("slicer", x, y, w, h, roles={"Values": [field]}, title=title, sync=sync,
                 objects={"data": [{"properties": {"mode": lit("Dropdown")}}],
                          "selection": [{"properties": {"singleSelect": lit(True)}}]})

    def year_slicer(self):
        self.slicer(1080, 8, 184, 50, "Year", column("year_selector", "year_label"), sync="year")

    def matrix(self, x, y, w, h, title, rows, cols, value, low, high):
        self.add("pivotTable", x, y, w, h, roles={"Rows": [rows], "Columns": [cols], "Values": [measure(value)]},
                 title=title, objects={
                     "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}],
                     "values": [{
                     "properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
                         "Input": measure(value)["field"],
                         "FillRule": {"linearGradient2": {
                             "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
                             "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
                             "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
                     "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{M}.{value}"}}]})


WHAT_IF = [("Monthly churn", "p_churn", "churn", "wi_churn"), ("ARPU change", "p_arpu", "arpu_change", "wi_arpu"),
           ("Gross margin change", "p_gm", "gm_change", "wi_gm"), ("Marketing spend change", "p_sm", "sm_change", "wi_sm"),
           ("Net adds change", "p_na", "na_change", "wi_na"), ("CAC proxy", "p_proxy", "proxy", "wi_proxy"),
           ("Base year", "base_inputs", "year", "wi_base")]


def what_if_slicers(page, x, y, w, per_row, h=56, gap=10):
    cw = (w - gap * (per_row - 1)) / per_row
    for i, (label, table, col, sync) in enumerate(WHAT_IF):
        r, c = divmod(i, per_row)
        page.slicer(x + c * (cw + gap), y + r * (h + gap), cw, h, label, column(table, col), sync=sync)


def build_pages():
    yl = column("fact_annual", "year_label")
    ql = column("fact_quarterly", "period")
    pages = []

    p = Page("overview", "Executive Overview", "Spotify unit economics, FY2021–FY2025, in US dollars")
    p.year_slicer()
    p.kpi_row([("Total revenue", "Revenue (Y)"), ("Premium subscribers", "Premium Subscribers (Y)"),
               ("Monthly active users", "MAU (Y)"), ("Gross margin", "Gross Margin (Y)"),
               ("Operating income", "Operating Income (Y)"), ("Free cash flow", "Free Cash Flow (Y)")])
    p.chart("columnChart", 16, 210, 616, 300, "Revenue: Premium vs ads ($ millions)", yl,
            ["Premium Revenue $M", "Ad Revenue $M"], colors=[GREEN, BLACK])
    p.chart("lineChart", 648, 210, 616, 300, "Profit margins (% of revenue kept)", yl,
            ["Gross Margin %", "Cash Margin %", "Operating Margin %"], colors=[GREEN, BLACK, GREY])
    p.textbox(16, 524, 1248, 180, [
        ("How to use this report  ", 12, BLACK, True),
        ("Pick a year at the top right to change the KPI cards. Use the pages on the left: Revenue, Subscribers, ARPU "
         "and Profitability show reported results; CAC, LTV, Retention, Sensitivity and Monte Carlo model the "
         "economics of one paying subscriber. Change the assumptions with the slicers on the LTV & LTV:CAC or "
         "Model Assumptions pages. " + app.DISCLAIMER, 10, "#55595F", False)])
    pages.append(p)

    p = Page("revenue", "Revenue Analysis", "How much money Spotify makes, and from where")
    p.year_slicer()
    p.kpi_row([("Total revenue", "Revenue (Y)"), ("Premium revenue", "Premium Revenue (Y)"),
               ("Ad revenue", "Ad Revenue (Y)"), ("Revenue growth", "Revenue Growth (Y)"),
               ("Share from Premium", "Premium Mix (Y)")])
    p.chart("columnChart", 16, 210, 410, 300, "Revenue by segment ($ millions)", yl,
            ["Premium Revenue $M", "Ad Revenue $M"], colors=[GREEN, BLACK])
    p.chart("clusteredColumnChart", 435, 210, 410, 300, "Revenue growth by segment (YoY)", yl,
            ["Premium Revenue Growth %", "Ad Revenue Growth %"], colors=[GREEN, BLACK], labels=True)
    p.chart("lineChart", 854, 210, 410, 300, "Share of revenue from Premium", yl, ["Premium Mix %"], colors=[GREEN],
            legend=False)
    p.chart("columnChart", 16, 520, 1248, 186, "Revenue each quarter ($ millions)", ql,
            ["Q Premium Revenue $M", "Q Ad Revenue $M"], colors=[GREEN, BLACK])
    pages.append(p)

    p = Page("subscribers", "Subscriber Base", "How many people use Spotify and how many pay")
    p.year_slicer()
    p.kpi_row([("Premium subscribers", "Premium Subscribers (Y)"), ("Monthly active users", "MAU (Y)"),
               ("Free (ad) users", "Ad MAU (Y)"), ("New paying subscribers", "Net Adds (Y)"),
               ("Paying share of users", "Paying Share (Y)")])
    p.chart("lineChart", 16, 210, 616, 300, "Users at year-end (millions)", yl,
            ["MAU M", "Ad MAU M", "Premium Subscribers M"], colors=[GREEN, BLACK, GREY])
    p.chart("clusteredColumnChart", 648, 210, 616, 300, "New paying subscribers per year (millions)", yl,
            ["Net Adds M"], colors=[GREEN], labels=True, legend=False)
    p.chart("lineChart", 16, 520, 616, 186, "Premium subscribers as % of MAU", yl, ["Paying Share %"], colors=[GREEN],
            legend=False)
    p.chart("clusteredColumnChart", 648, 520, 616, 186, "New paying subscribers per quarter (millions)", ql,
            ["Q Net Adds M"], colors=[GREEN], labels=True, legend=False)
    pages.append(p)

    p = Page("arpu", "ARPU (Average Revenue Per User)", "How much Spotify earns from each user")
    p.year_slicer()
    p.kpi_row([("Per paying subscriber / month", "ARPU (Y)"), ("Ad money per free user / year", "Ad Revenue per Ad MAU (Y)"),
               ("Revenue per user / year", "Revenue per MAU (Y)")])
    p.chart("lineChart", 16, 210, 616, 496, "Money from each paying subscriber, per month ($)", yl, ["ARPU $"],
            colors=[GREEN], legend=False, labels=True)
    p.chart("lineChart", 648, 210, 616, 240, "Ad money per free user, per year ($)", yl, ["Ad Revenue per Ad MAU $"],
            colors=[BLACK], legend=False, labels=True)
    p.chart("lineChart", 648, 466, 616, 240, "ARPU by quarter ($ per subscriber per month)", ql, ["Q ARPU $"],
            colors=[GREEN], legend=False, labels=True)
    pages.append(p)

    p = Page("profitability", "Profitability & Margins", "Is Spotify making money?")
    p.year_slicer()
    p.kpi_row([("Gross margin", "Gross Margin (Y)"), ("Operating income", "Operating Income (Y)"),
               ("Operating margin", "Operating Margin (Y)"), ("Free cash flow", "Free Cash Flow (Y)"),
               ("Costs as % of revenue", "Opex Ratio (Y)")])
    p.chart("lineChart", 16, 210, 410, 300, "Profit margins by year", yl,
            ["Gross Margin %", "Cash Margin %", "Operating Margin %"], colors=[GREEN, BLACK, GREY])
    p.chart("clusteredColumnChart", 435, 210, 410, 300, "Operating income ($ millions)", yl, ["Operating Income $M"],
            colors=[GREEN], labels=True, legend=False)
    p.chart("lineChart", 854, 210, 410, 300, "Costs as % of revenue (lower is better)", yl,
            ["Opex Ratio %", "S&M % of Revenue"], colors=[BLACK, GREY])
    p.table(16, 520, 1248, 186, "Profit & loss summary", [
        column("fact_annual", "year_label"), measure("Total Revenue $M"), measure("Operating Income $M"),
        measure("Free Cash Flow $M"), measure("Gross Margin %"), measure("Operating Margin %"), measure("Cash Margin %")])
    pages.append(p)

    p = Page("cac", "CAC (Customer Acquisition Cost)", "Marketing spend per new subscriber (estimated)")
    p.year_slicer()
    p.kpi_row([("CAC, realistic (3% churn)", "CAC Realistic (Y)"), ("CAC, simple", "CAC Simple (Y)"),
               ("LTV:CAC, realistic", "LTV:CAC (Y)"), ("Payback, realistic", "Payback (Y)")])
    ue = column("ue_by_year", "year_label")
    p.chart("clusteredColumnChart", 16, 210, 616, 380, "Estimated cost to win one subscriber ($)", ue,
            ["CAC Simple $", "CAC Realistic $"], colors=[GREEN, BLACK], labels=True)
    p.table(648, 210, 616, 380, "CAC proxies and payback at 3% churn", [
        ue, measure("CAC Simple $"), measure("CAC Realistic $"), measure("Payback Simple (mo)"),
        measure("Payback Realistic (mo)"), measure("LTV:CAC Realistic")])
    p.note(16, 600, 1248, 104, "Why two CAC proxies? Marketing ÷ net adds treats every new subscriber as growth, which "
           "implies zero churn and contradicts the churn used in LTV. The realistic proxy adds back the subscribers the "
           "assumed churn rate says must be replaced, so LTV and CAC rest on the same assumption. Sales & marketing data "
           "starts in 2023. " + app.DISCLAIMER)
    pages.append(p)

    p = Page("ltv", "LTV & LTV:CAC", "What one subscriber is worth versus what it costs to win them")
    what_if_slicers(p, 16, 72, 1248, 7)
    p.kpi_row([("LTV (value of a subscriber)", "WI LTV"), ("CAC (cost to win one)", "WI CAC"),
               ("LTV:CAC", "WI LTV:CAC"), ("Payback", "WI Payback"), ("Average stay", "WI Average Stay")],
              y=140, change=False)
    p.kpi(16, 232, 300, "Verdict", "WI Status")
    p.kpi(326, 232, 300, "Payback check", "WI Recovered")
    p.chart("lineChart", 16, 326, 1248, 380, "LTV vs CAC as churn changes ($ per subscriber)",
            column("churn_curve", "churn"), ["Curve LTV", "Curve CAC Simple", "Curve CAC Realistic"],
            colors=[GREEN, BLACK, GREY])
    pages.append(p)

    p = Page("retention", "Retention & Churn", "Modeled: how many of 1,000 new subscribers are still paying")
    p.slicer(1080, 8, 184, 50, "Monthly churn", column("p_churn", "churn"), sync="wi_churn")
    p.matrix(16, 76, 1248, 400, "Subscribers still paying, of 1,000 who joined (rows: monthly churn)",
             column("grid_churn", "churn_label"), column("grid_month", "month_label"), "Retained per 1,000",
             "#F6F8F7", "#18A048")
    p.chart("lineChart", 16, 486, 616, 220, "Retention at the selected churn (of 1,000)", column("grid_month", "month_label"),
            ["Retained at Selected Churn"], colors=[GREEN], legend=False)
    p.chart("lineChart", 648, 486, 616, 220, "Cumulative gross profit per subscriber ($)",
            column("grid_month", "month_label"), ["Cumulative Profit per Subscriber"], colors=[BLACK], legend=False)
    pages.append(p)

    p = Page("sensitivity", "Sensitivity Analysis", "LTV:CAC when churn and gross margin change together")
    p.slicer(1080, 8, 184, 50, "CAC proxy", column("p_proxy", "proxy"), sync="wi_proxy")
    p.matrix(16, 76, 1248, 520, "LTV:CAC by monthly churn (rows) and gross margin change (columns)",
             column("grid_churn", "churn_label"), column("grid_gm", "gm_label"), "Sensitivity LTV:CAC",
             "#F6F8F7", "#18A048")
    p.note(16, 606, 1248, 100, "Greener = better. 3x or more is usually considered healthy. The grid uses the ARPU, "
           "marketing and net adds settings from the LTV & LTV:CAC page.")
    pages.append(p)

    p = Page("montecarlo", "Monte Carlo Simulation", "10,000 simulated futures with uncertain inputs")
    p.kpi_row([("Chance LTV:CAC ≥ 3x", "MC Chance 3x"), ("Typical LTV:CAC (P50)", "MC P50 LTV:CAC"),
               ("Typical LTV (P50)", "MC P50 LTV"), ("Typical CAC (P50)", "MC P50 CAC"),
               ("Cost earned back in time", "MC Payback in Time")], change=False)
    p.kpi(16, 168, 400, "P10 – P90 range", "MC Range Text")
    p.chart("columnChart", 16, 262, 760, 330, "LTV:CAC across 10,000 simulated futures (number of runs)",
            column("mc_runs", "bin_label"), ["MC Runs Below 3x", "MC Runs 3x or Better"], colors=[GREY, GREEN])
    p.add("barChart", 788, 262, 476, 330, roles={"Category": [column("mc_drivers", "input")],
                                                 "Y": [measure("MC Positive Effect"), measure("MC Negative Effect")]},
          title="What drives the risk most? (rank correlation)",
          sort=(column("mc_drivers", "abs_corr"), "Descending"),
          objects={"legend": [{"properties": {"show": lit(False)}}], "labels": [{"properties": {"show": lit(True)}}],
                   "dataPoint": [{"properties": {"fill": color(GREEN)}, "selector": {"metadata": f"{M}.MC Positive Effect"}},
                                 {"properties": {"fill": color(BLACK)}, "selector": {"metadata": f"{M}.MC Negative Effect"}}]})
    p.table(16, 602, 760, 104, "Pessimistic / typical / optimistic results", [
        column("mc_percentiles", "metric"), column("mc_percentiles", "p10_pessimistic"),
        column("mc_percentiles", "p50_typical"), column("mc_percentiles", "p90_optimistic"), column("mc_percentiles", "mean")])
    p.note(788, 602, 476, 104, "Each run draws churn (2–5%), ARPU (±10%), gross margin (±2pp), marketing spend (±20%) and "
           "net adds (±25%) from triangular distributions, then computes LTV, CAC and payback. Same seed as the Python "
           "dashboard. To change the ranges, edit them there and rerun notebooks/10_build_powerbi_project.py.")
    pages.append(p)

    p = Page("assumptions", "Model Assumptions", "Every assumption in one place")
    what_if_slicers(p, 16, 76, 1248, 7)
    p.table(16, 146, 1248, 330, "What each assumption means", [
        column("assumptions", "assumption"), column("assumptions", "default"), column("assumptions", "what_it_is"),
        column("assumptions", "what_it_changes")])
    p.table(16, 486, 616, 220, "Base-year inputs (US dollars)", [
        column("base_inputs", "year"), column("base_inputs", "arpu_usd"), column("base_inputs", "gross_margin"),
        column("base_inputs", "sm_usd_m"), column("base_inputs", "net_adds_m"), column("base_inputs", "avg_subs_m")])
    for i, (label, m) in enumerate([("LTV", "WI LTV"), ("CAC", "WI CAC"), ("LTV:CAC", "WI LTV:CAC"),
                                    ("Payback", "WI Payback")]):
        p.kpi(648 + (i % 2) * 314, 486 + (i // 2) * 112, 302, label, m)
    pages.append(p)

    p = Page("data", "Data & Methodology", "Source numbers, formulas and definitions")
    p.table(16, 76, 1248, 250, "Annual reported data (US dollars)", [
        column("fact_annual", "year_label"), column("fact_annual", "total_rev_usd_m"),
        column("fact_annual", "premium_rev_usd_m"), column("fact_annual", "ad_rev_usd_m"),
        column("fact_annual", "premium_subs_m"), column("fact_annual", "mau_m"),
        column("fact_annual", "gross_margin"), column("fact_annual", "op_income_usd_m"), column("fact_annual", "fcf_usd_m")])
    p.table(16, 336, 616, 370, "Formulas", [column("formulas", "metric"), column("formulas", "formula")])
    p.table(648, 336, 616, 370, "Glossary", [column("glossary", "term"), column("glossary", "meaning")])
    pages.append(p)
    assert [pg.key for pg in pages] == list(MENU), "sidebar menu must list every page"
    for pg in pages:
        pg.sidebar()
    return pages


THEME = {
    "name": "Spotify Green",
    "dataColors": [GREEN, BLACK, GREY, GREEN_DARK, "#7EE2A8", "#535353", "#C9ECD6", "#2A2E35"],
    "background": "#FFFFFF", "foreground": BLACK, "tableAccent": GREEN,
    "good": GREEN, "neutral": GREY, "bad": BLACK, "maximum": GREEN, "center": "#C9ECD6", "minimum": "#F6F8F7",
    "textClasses": {
        "callout": {"fontFace": "Segoe UI Semibold", "color": BLACK},
        "title": {"fontFace": "Segoe UI Semibold", "color": BLACK, "fontSize": 11},
        "header": {"fontFace": "Segoe UI Semibold", "color": BLACK},
        "label": {"fontFace": "Segoe UI", "color": "#4B5058"},
    },
    "visualStyles": {
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": BORDER}}, "radius": 10}],
            "dropShadow": [{"show": False}],
            "title": [{"fontColor": {"solid": {"color": BLACK}}, "fontSize": 11, "bold": True}],
            "padding": [{"top": 8, "bottom": 8, "left": 10, "right": 10}],
        }},
        "page": {"*": {
            "background": [{"color": {"solid": {"color": PAGE_BG}}, "transparency": 0}],
            "outspace": [{"color": {"solid": {"color": PAGE_BG}}, "transparency": 0}],
        }},
        "slicer": {"*": {"items": [{"fontColor": {"solid": {"color": BLACK}}, "textSize": 10}]}},
        "tableEx": {"*": {"columnHeaders": [{"bold": True, "fontColor": {"solid": {"color": BLACK}}}]}},
    },
}


def write_report(pages):
    defn = REPORT / "definition"
    (defn / "pages").mkdir(parents=True)
    res = REPORT / "StaticResources"
    (res / "RegisteredResources").mkdir(parents=True)
    (res / "SharedResources" / "BaseThemes").mkdir(parents=True)
    shutil.copy(ROOT / "dashboards" / "powerbi_base_theme_CY24SU10.json",
                res / "SharedResources" / "BaseThemes" / "CY24SU10.json")
    (res / "RegisteredResources" / "SpotifyGreen.json").write_text(json.dumps(THEME, indent=2), encoding="utf-8")

    def dump(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    dump(REPORT / "definition.pbir", {
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    dump(REPORT / ".platform", {
        "$schema": f"{SCHEMA}/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": NAME},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())}})
    dump(defn / "version.json", {"$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json",
                                 "version": "2.0.0"})
    dump(defn / "report.json", {
        "$schema": f"{SCHEMA}/item/report/definition/report/1.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.61", "type": "SharedResources"},
            "customTheme": {"name": "SpotifyGreen.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}},
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources",
             "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": "SpotifyGreen.json", "path": "SpotifyGreen.json", "type": "CustomTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultDrillFilterOtherVisuals": True,
                     "allowChangeFilterTypes": True, "useEnhancedTooltips": True}})
    dump(defn / "pages" / "pages.json", {
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p.key for p in pages], "activePageName": pages[0].key})
    for p in pages:
        dump(defn / "pages" / p.key / "page.json", {
            "$schema": f"{SCHEMA}/item/report/definition/page/1.4.0/schema.json",
            "name": p.key, "displayName": p.title, "displayOption": "FitToPage", "height": 720, "width": PAGE_W})
        for v in p.visuals:
            dump(defn / "pages" / p.key / "visuals" / v["name"] / "visual.json", v)


def main():
    # Rebuild the generated parts only; Power BI's local cache (.pbi folders, cache.abf) is left alone.
    for path in (DATA, MODEL / "definition", REPORT / "definition", REPORT / "StaticResources"):
        if path.exists():
            shutil.rmtree(path)
    DATA.mkdir(parents=True)
    tables = build_tables()
    for name, df in tables.items():
        df.to_csv(DATA / f"{name}.csv", index=False)
    write_model(tables)
    pages = build_pages()
    write_report(pages)
    (OUT / f"{NAME}.pbip").write_text(json.dumps({
        "version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    n_visuals = sum(len(p.visuals) for p in pages)
    print(f"  pbip   -> powerbi/{NAME}.pbip ({len(tables)} tables, {len(measures())} measures, "
          f"{len(pages)} pages, {n_visuals} visuals)")


if __name__ == "__main__":
    main()
