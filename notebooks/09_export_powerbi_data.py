"""Phase 10 - Export tidy, Power BI-ready tables to dashboards/powerbi_data/.

See dashboards/POWERBI_BUILD_GUIDE.md for the data model, DAX measures and page layouts.
"""

import shutil

import pandas as pd

from common import DATA_PROCESSED, POWERBI_DATA, REPORTS, save_csv


def main():
    rev = pd.read_csv(DATA_PROCESSED / "revenue_analysis_annual.csv")
    subs = pd.read_csv(DATA_PROCESSED / "subscriber_analysis_annual.csv")
    prof = pd.read_csv(DATA_PROCESSED / "profitability_annual.csv")
    ue = pd.read_csv(DATA_PROCESSED / "unit_economics_by_year.csv")

    annual = (
        subs.merge(rev.drop(columns=["premium_revenue_eur_millions", "ad_supported_revenue_eur_millions",
                                     "total_revenue_eur_millions"]), on="year", suffixes=("", "_rev"))
        .merge(prof.drop(columns=["total_revenue_eur_millions"]), on="year", suffixes=("", "_prof"))
        .merge(ue[["year", "cac_proxy_net_adds_eur", "cac_proxy_gross_adds_eur"]], on="year", how="left")
    )
    annual = annual.loc[:, ~annual.columns.str.endswith(("_rev", "_prof"))]
    save_csv(annual, POWERBI_DATA / "fact_annual.csv")

    q = pd.read_csv(DATA_PROCESSED / "profitability_quarterly.csv").merge(
        pd.read_csv(DATA_PROCESSED / "subscriber_analysis_quarterly.csv")[
            ["period", "premium_net_adds_millions", "mau_net_adds_millions", "premium_arpu_monthly_eur"]],
        on="period")
    q["quarter_index"] = range(1, len(q) + 1)
    save_csv(q, POWERBI_DATA / "fact_quarterly.csv")

    seg = annual.melt(id_vars="year", value_vars=["premium_revenue_eur_millions", "ad_supported_revenue_eur_millions"],
                      var_name="segment", value_name="revenue_eur_millions")
    seg["segment"] = seg["segment"].map({"premium_revenue_eur_millions": "Premium",
                                         "ad_supported_revenue_eur_millions": "Ad-supported"})
    save_csv(seg, POWERBI_DATA / "fact_revenue_by_segment_annual.csv")

    qseg = q.melt(id_vars=["period", "quarter_index"],
                  value_vars=["premium_revenue_eur_millions", "ad_supported_revenue_eur_millions"],
                  var_name="segment", value_name="revenue_eur_millions")
    qseg["segment"] = qseg["segment"].map({"premium_revenue_eur_millions": "Premium",
                                           "ad_supported_revenue_eur_millions": "Ad-supported"})
    save_csv(qseg, POWERBI_DATA / "fact_revenue_by_segment_quarterly.csv")

    # Base-year inputs for the DAX what-if model (single row).
    base = ue.iloc[[-1]][["year", "monthly_arpu_eur", "gross_margin_pct"]].copy()
    base["sm_expense_eur_millions"] = prof.set_index("year").loc[base["year"].iloc[0], "sales_marketing_expense_eur_millions"]
    s = subs.set_index("year").loc[base["year"].iloc[0]]
    base["net_adds_millions"] = s["premium_net_adds_millions"]
    base["avg_premium_subscribers_millions"] = s["avg_premium_subscribers_millions"]
    save_csv(base, POWERBI_DATA / "dim_unit_economics_base.csv")

    for name in ("unit_economics_churn_scenarios", "scenario_comparison", "sensitivity_grids_long",
                 "tornado_sensitivity", "unit_economics_by_year"):
        shutil.copy(DATA_PROCESSED / f"{name}.csv", POWERBI_DATA / f"{name}.csv")
        print(f"  data   -> dashboards/powerbi_data/{name}.csv")
    shutil.copy(REPORTS / "key_metrics_summary.csv", POWERBI_DATA / "kpi_summary.csv")
    print("  data   -> dashboards/powerbi_data/kpi_summary.csv")


if __name__ == "__main__":
    main()
