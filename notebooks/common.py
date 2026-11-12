"""Shared paths, loaders, chart style and report helpers for the analysis scripts."""

import numbers
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
SOURCE_XLSX = DATA_RAW / "source" / "Spotify_Historical_Data.xlsx"
CHARTS = ROOT / "outputs" / "charts"
REPORTS = ROOT / "outputs" / "reports"
MODELS = ROOT / "outputs" / "financial_models"
POWERBI_DATA = ROOT / "dashboards" / "powerbi_data"

ANNUAL_RAW = DATA_RAW / "spotify_annual_reported_2021_2025.csv"
QUARTERLY_RAW = DATA_RAW / "spotify_quarterly_reported_2024Q4_2025.csv"
ANNUAL_CLEAN = DATA_PROCESSED / "annual_clean.csv"
QUARTERLY_CLEAN = DATA_PROCESSED / "quarterly_clean.csv"

for _d in (DATA_PROCESSED, CHARTS, REPORTS, MODELS, POWERBI_DATA):
    _d.mkdir(parents=True, exist_ok=True)

# Unit-economics assumptions shared by scripts 05-07 and the Excel model.
BASE_YEAR = 2025
CHURN_SCENARIOS = {"Optimistic": 0.02, "Base case": 0.03, "Moderate risk": 0.04, "High risk": 0.05}
BASE_CHURN = CHURN_SCENARIOS["Base case"]

# Chart palette (validated categorical order: blue, orange, aqua) and neutral ink.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"  # status colors: only for good/bad meaning
NEUTRAL = "#b9b8b2"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.titlepad": 14,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "text.color": INK,
    "font.size": 10,
    "legend.frameon": False,
    "lines.linewidth": 2,
    "lines.markersize": 7,
})


def unit_economics(arpu: float, gross_margin: float, churn: float, sm_expense: float,
                   net_adds: float, avg_subs: float) -> dict:
    """Simplified premium-subscriber unit economics (all per-subscriber values in EUR).

    arpu          monthly premium revenue per subscriber, EUR
    gross_margin  decimal (0.32 = 32%)
    churn         assumed monthly churn, decimal - a scenario, not a reported figure
    sm_expense    sales & marketing expense for the year, EUR millions
    net_adds      premium net additions for the year, millions
    avg_subs      average premium subscribers for the year, millions

    Two CAC proxies are returned:
      cac_net_adds    S&M / net adds - the roadmap proxy. Ignores churn, so it overstates true CAC.
      cac_gross_adds  S&M / (net adds + subscribers implied lost to churn) - consistent with the churn assumption.
    Both allocate 100% of S&M to premium acquisition, which also overstates true CAC.
    """
    monthly_gp = arpu * gross_margin
    ltv = monthly_gp / churn
    implied_churned = avg_subs * churn * 12
    gross_adds = net_adds + implied_churned
    cac_net = sm_expense / net_adds
    cac_gross = sm_expense / gross_adds
    return {
        "monthly_arpu_eur": arpu,
        "gross_margin_pct": gross_margin * 100,
        "monthly_churn_pct": churn * 100,
        "expected_lifetime_months": 1 / churn,
        "monthly_gross_profit_per_sub_eur": monthly_gp,
        "ltv_eur": ltv,
        "cac_proxy_net_adds_eur": cac_net,
        "implied_gross_adds_millions": gross_adds,
        "cac_proxy_gross_adds_eur": cac_gross,
        "ltv_to_cac_net_adds": ltv / cac_net,
        "ltv_to_cac_gross_adds": ltv / cac_gross,
        "payback_months_net_adds": cac_net / monthly_gp,
        "payback_months_gross_adds": cac_gross / monthly_gp,
    }


def base_inputs(year: int = BASE_YEAR) -> dict:
    """Unit-economics inputs for one year, read from the Phase 3-4 processed outputs."""
    subs = pd.read_csv(DATA_PROCESSED / "subscriber_analysis_annual.csv").set_index("year")
    prof = pd.read_csv(DATA_PROCESSED / "profitability_annual.csv").set_index("year")
    return {
        "arpu": subs.loc[year, "premium_arpu_monthly_eur"],
        "gross_margin": prof.loc[year, "gross_margin_calc_pct"] / 100,
        "sm_expense": prof.loc[year, "sales_marketing_expense_eur_millions"],
        "net_adds": subs.loc[year, "premium_net_adds_millions"],
        "avg_subs": subs.loc[year, "avg_premium_subscribers_millions"],
    }


def load_annual() -> pd.DataFrame:
    return pd.read_csv(ANNUAL_CLEAN if ANNUAL_CLEAN.exists() else ANNUAL_RAW)


def load_quarterly() -> pd.DataFrame:
    return pd.read_csv(QUARTERLY_CLEAN if QUARTERLY_CLEAN.exists() else QUARTERLY_RAW)


def pct_change(series: pd.Series) -> pd.Series:
    """(Current - Previous) / Previous x 100."""
    return series.pct_change() * 100


def save_chart(fig, name: str, note: str | None = None) -> Path:
    if note:
        fig.text(0.01, -0.04, note, fontsize=8, color=INK_2, ha="left", va="top")
    path = CHARTS / f"{name}.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  chart  -> {path.relative_to(ROOT)}")
    return path


def save_csv(df: pd.DataFrame, path: Path) -> Path:
    df.to_csv(path, index=False)
    print(f"  data   -> {path.relative_to(ROOT)}")
    return path


def write_report(name: str, text: str) -> Path:
    path = REPORTS / name
    path.write_text(text.strip() + "\n", encoding="utf-8")
    print(f"  report -> {path.relative_to(ROOT)}")
    return path


def md_table(df: pd.DataFrame, floatfmt: str = ",.1f") -> str:
    """Render a DataFrame as a GitHub markdown table without extra dependencies."""
    def fmt(v, col):
        if isinstance(v, bool):
            return "Yes" if v else "No"
        if isinstance(v, numbers.Integral):
            return str(int(v)) if str(col).lower() == "year" else format(int(v), ",")
        if isinstance(v, numbers.Real):
            return "n/a" if pd.isna(v) else format(float(v), floatfmt)
        return str(v)

    header = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(fmt(v, c) for v, c in zip(row, df.columns)) + " |" for row in df.itertuples(index=False)]
    return "\n".join([header, sep, *rows])
