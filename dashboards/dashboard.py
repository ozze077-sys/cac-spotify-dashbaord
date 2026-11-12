"""Interactive Python dashboard built with Plotly Dash - layout, styling and callbacks are all plain Python.

Layout: dark navigation sidebar, a gradient top bar, a page header (Assumptions link, download,
currency and period chips), underlined sub-tabs, and cohort-style heat tables with dropdown controls.

Run from the project root:
    python run_pipeline.py              # once, to build data/processed
    python dashboards/dashboard.py      # then open http://127.0.0.1:8050
"""

import sys
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Dash, Input, Output, State, ctx, dash_table, dcc, html
from dash.exceptions import PreventUpdate

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "notebooks"))
from common import (  # noqa: E402
    CHURN_SCENARIOS, DATA_PROCESSED, INK, INK_2, ROOT, base_inputs, unit_economics,
)

# Theme: green, white and black.
GREEN, GREEN_DARK, BLACK, GREY = "#1db954", "#148a3e", "#121212", "#9e9e9e"
BLUE, ORANGE, AQUA = GREEN, BLACK, GREY  # chart series slots 1-3
GOOD, CRITICAL = GREEN, BLACK  # profit / loss bars (always text-labelled)

DISCLAIMER = ("Churn is a hypothetical assumption and CAC figures are proxies (all sales & marketing spend / "
              "subscribers added). Spotify does not disclose either.")

# ----------------------------------------------------------------------------- data

FILES = {
    "annual": "annual_clean.csv", "quarterly": "quarterly_clean.csv", "rev": "revenue_analysis_annual.csv",
    "subs": "subscriber_analysis_annual.csv", "prof": "profitability_annual.csv",
    "prof_q": "profitability_quarterly.csv", "subs_q": "subscriber_analysis_quarterly.csv",
    "ue": "unit_economics_by_year.csv", "scen": "scenario_comparison.csv", "checks": "validation_checks.csv",
}
_missing = [f for f in FILES.values() if not (DATA_PROCESSED / f).exists()]
if _missing:
    sys.exit(f"Processed data not found ({', '.join(_missing)}). Run `python run_pipeline.py` first.")
D = {k: pd.read_csv(DATA_PROCESSED / f) for k, f in FILES.items()}

# ----------------------------------------------------------------------------- currency: EUR -> USD
# Spotify reports in EUR. The dashboard shows US dollars, converting each period at its ECB average
# EUR/USD rate (data/raw/fx_eur_usd_ecb.csv). Column names keep their "_eur" suffix but hold USD values.
FX = pd.read_csv(ROOT / "data" / "raw" / "fx_eur_usd_ecb.csv", dtype={"period": str})
FX_YEAR = {int(p): r for p, r in FX.loc[FX["frequency"] == "annual", ["period", "usd_per_eur"]].values}
FX_QUARTER = dict(FX.loc[FX["frequency"] == "quarterly", ["period", "usd_per_eur"]].values)


def to_usd(df, rate):
    """Multiply every money column (name contains 'eur') by a per-row USD/EUR rate."""
    df = df.copy()
    money = [c for c in df.columns if "eur" in c]
    df[money] = df[money].mul(rate.values, axis=0)
    return df


def growth(s):
    return s.pct_change() * 100


for key in ("annual", "rev", "subs", "prof", "ue"):
    D[key] = to_usd(D[key], D[key]["year"].map(FX_YEAR))
for key in ("quarterly", "prof_q", "subs_q"):
    D[key] = to_usd(D[key], D[key]["period"].map(FX_QUARTER))
D["scen"] = to_usd(D["scen"], pd.Series(FX_YEAR[2025], index=D["scen"].index))

# Growth rates and incremental figures must be recomputed in USD (ratios such as margins are unchanged).
_r, _s, _p = D["rev"], D["subs"], D["prof"]
for col in ("total_revenue", "premium_revenue", "ad_supported_revenue"):
    _r[f"{col}_growth_pct"] = growth(_r[f"{col}_eur_millions"])
_r["incremental_revenue_eur_millions"] = _r["total_revenue_eur_millions"].diff()
_r["premium_share_of_incremental_revenue_pct"] = (_r["premium_revenue_eur_millions"].diff()
                                                  / _r["incremental_revenue_eur_millions"] * 100)
_s["premium_revenue_growth_pct"] = growth(_s["premium_revenue_eur_millions"])
_s["total_revenue_growth_pct"] = growth(_s["total_revenue_eur_millions"])
_s["premium_arpu_growth_pct"] = growth(_s["premium_arpu_monthly_eur"])
_s["revenue_minus_subscriber_growth_pp"] = _s["total_revenue_growth_pct"] - _s["premium_subscriber_growth_pct"]
_p["revenue_growth_pct"] = growth(_p["total_revenue_eur_millions"])
_p["gross_profit_growth_pct"] = growth(_p["gross_profit_eur_millions"])
_p["opex_growth_pct"] = growth(_p["total_operating_expenses_eur_millions"])
_p["sm_growth_pct"] = growth(_p["sales_marketing_expense_eur_millions"])
_p["incremental_operating_margin_pct"] = (_p["operating_income_eur_millions"].diff()
                                          / _p["total_revenue_eur_millions"].diff() * 100)

annual = D["annual"].set_index("year")
rev, subs, prof = (D[k].set_index("year") for k in ("rev", "subs", "prof"))
ue_years = D["ue"].set_index("year")
q = D["prof_q"].merge(D["subs_q"][["period", "premium_net_adds_millions", "premium_arpu_monthly_eur"]], on="period")
YEARS = annual.index.tolist()
N_PASS, N_CHECKS = int((D["checks"]["result"] == "PASS").sum()), len(D["checks"])

# ----------------------------------------------------------------------------- navigation model

# page key -> (menu label, page title, info text, [(subtab value, subtab label)], download file)
PAGES = {
    "dashboard": ("Executive Overview", "Executive Overview", "Start with the big picture, then open any report from the menu on the left.",
                  [("overview", "Overview")], "annual"),
    "revenue": ("Revenue Analysis", "Revenue Analysis", "How much money Spotify makes, and from where: Premium subscriptions or ads.",
                [("segment", "Where money comes from"), ("growth", "Growth"), ("quarterly", "By quarter")],
                "rev"),
    "subscribers": ("Subscriber Base", "Subscriber Base", "How many people use Spotify and how many pay for Premium.",
                    [("users", "Users"), ("netadds", "New paying subscribers")], "subs"),
    "arpu": ("ARPU", "ARPU (Average Revenue Per User)", "How much money Spotify earns from each user. ARPU = Average Revenue Per User.",
             [("premium", "Paying subscribers"), ("ads", "Free users (ads)")], "subs"),
    "profitability": ("Profitability & Margins", "Profitability & Margins", "Is Spotify making money? Margins show how many cents of each dollar are kept.",
                      [("margins", "Margins"), ("opinc", "Profit or loss"), ("pnl", "Full table")],
                      "prof"),
    "cac": ("CAC", "CAC (Customer Acquisition Cost)", "CAC = Customer Acquisition Cost: marketing spend per new subscriber. " + DISCLAIMER,
            [("proxies", "Estimates by year")],
            "ue"),
    "ltv": ("LTV & LTV:CAC", "LTV (Customer Lifetime Value) & LTV:CAC", "LTV = Lifetime Value: the profit one subscriber brings in before cancelling. Change the assumptions on the Assumptions page.",
            [("unit", "Value vs cost"), ("drivers", "What matters most")], "scen"),
    "retention": ("Retention & Churn", "Cohort Retention & Churn",
                  "Modeled: how many of 1,000 new subscribers are still paying each month. Spotify does not publish this.",
                  [("subs", "Subscribers still paying"), ("gp", "Profit earned per subscriber")],
                  "scen"),
    "sensitivity": ("Sensitivity Analysis", "Sensitivity Analysis", "See how results change when two assumptions change at once.",
                    [("grid", "What-if table")], "scen"),
    "montecarlo": ("Monte Carlo", "Monte Carlo Simulation",
                   "Thousands of simulated futures with uncertain churn, price, margin and marketing, instead of one guess.",
                   [("sim", "Simulation"), ("method", "How it works")], "scen"),
    "assumptions": ("Model Assumptions", "Model Assumptions", "Every assumption in one place: change it here, see what it means, and follow the step-by-step maths.",
                    [("set", "Set assumptions"), ("how", "How results are calculated"), ("fixed", "Fixed data choices")], "fx"),
    "data": ("Data & Methodology", "Data & Methodology", "The source numbers, data checks, formulas and plain-English definitions.",
             [("glossary", "Glossary"), ("reported", "Reported data"), ("validation", "Data checks"), ("method", "Formulas")],
             "annual"),
}
REPORT_PAGES = ["revenue", "subscribers", "arpu", "profitability", "cac", "ltv", "retention", "sensitivity", "montecarlo"]
NAV_ORDER = ["dashboard", *REPORT_PAGES, "assumptions", "data"]

# ----------------------------------------------------------------------------- styles

FONT = "'Plus Jakarta Sans', Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
NAV_BG = "linear-gradient(180deg, #050505 0%, #06120b 55%, #0b2415 100%)"
NAV_ACTIVE, NAV_ACCENT = "rgba(29,185,84,0.18)", GREEN
BORDER, PAGE_BG, LINK = "#e8e8e8", "#f7f7f7", GREEN_DARK
INK_3 = "#8a8f98"
SHADOW = "0 1px 2px rgba(16,24,40,0.04), 0 4px 16px rgba(16,24,40,0.05)"

PAGE = {"fontFamily": FONT, "backgroundColor": PAGE_BG, "color": INK, "margin": 0, "minHeight": "100vh",
        "display": "flex"}
SIDEBAR = {"width": "272px", "flexShrink": 0, "background": NAV_BG, "color": "#e8eaed", "minHeight": "100vh",
           "paddingBottom": "24px", "boxSizing": "border-box", "position": "sticky", "top": 0, "alignSelf": "flex-start",
           "height": "100vh", "overflowY": "auto"}
NAV_ITEM = {"padding": "12px 16px", "margin": "4px 14px", "fontSize": "15px", "cursor": "pointer", "color": "#b9c4bd",
            "borderRadius": "14px", "display": "flex", "alignItems": "center", "gap": "14px", "fontWeight": 600,
            "border": "1px solid transparent"}
ACTIVE = {"background": "linear-gradient(90deg, rgba(29,185,84,0.30) 0%, rgba(29,185,84,0.08) 100%)", "color": "#ffffff",
          "border": "1px solid rgba(29,185,84,0.40)", "boxShadow": "0 8px 24px rgba(29,185,84,0.18)"}
SUB_ITEM = {**NAV_ITEM, "paddingLeft": "44px", "fontSize": "13.5px", "fontWeight": 400}
TOPBAR = {"minHeight": "92px", "background": "linear-gradient(100deg, #050505 0%, #07160d 45%, #0d2c19 75%, #14532d 100%)",
          "display": "flex", "alignItems": "center", "justifyContent": "space-between", "padding": "14px 40px",
          "position": "sticky", "top": 0, "zIndex": 10, "boxSizing": "border-box", "flexWrap": "wrap", "gap": "12px",
          "boxShadow": "0 10px 30px rgba(0,0,0,0.18)"}
CHIP = {"backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "borderRadius": "999px", "padding": "5px 12px",
        "fontSize": "12px", "color": INK, "whiteSpace": "nowrap", "fontWeight": 500,
        "boxShadow": "0 1px 2px rgba(16,24,40,0.05)"}
ICON_BTN = {**CHIP, "cursor": "pointer", "fontWeight": 700}
FILTER_BTN = {"backgroundColor": "#e8f7ee", "color": GREEN_DARK, "border": "1px solid #c9ecd6", "borderRadius": "999px",
              "padding": "10px 18px", "fontSize": "13.5px", "fontWeight": 700, "cursor": "pointer", "fontFamily": FONT}
CARD = {"backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "borderRadius": "18px", "padding": "16px 18px 10px",
        "minWidth": 0, "boxShadow": SHADOW, "boxSizing": "border-box", "overflow": "hidden"}
PANEL = {"backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "borderRadius": "18px", "padding": "12px",
         "flex": "1 1 460px", "minWidth": "320px", "boxShadow": SHADOW, "boxSizing": "border-box"}
ROW = {"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginBottom": "16px"}
LABEL = {"fontSize": "11px", "fontWeight": 600, "color": INK_3, "marginBottom": "6px", "textTransform": "uppercase",
         "letterSpacing": "0.06em"}
NOTE = {"fontSize": "12px", "color": INK_3, "lineHeight": 1.5}
SUBTAB = {"padding": "6px 2px", "marginRight": "24px", "fontSize": "13px", "color": "#4b5058", "border": "none",
          "borderBottom": "2px solid transparent", "backgroundColor": "transparent", "width": "auto", "flex": "none"}
SUBTAB_ON = {**SUBTAB, "color": LINK, "borderBottom": f"2px solid {LINK}", "fontWeight": 600}
BOX_COLORS = {"info": ("#effaf3", GREEN), "good": ("#effaf3", GREEN_DARK), "warn": ("#f2f2f2", BLACK)}
TH = {"padding": "12px 12px", "fontSize": "12px", "fontWeight": 700, "textAlign": "center", "whiteSpace": "nowrap",
      "borderBottom": f"1px solid {BORDER}", "backgroundColor": "#ffffff", "position": "sticky", "top": 0,
      "color": "#2a2e35"}
TD = {"padding": "10px 12px", "fontSize": "13px", "textAlign": "center", "whiteSpace": "nowrap",
      "borderRight": "1px solid rgba(255,255,255,0.6)", "borderBottom": "1px solid rgba(255,255,255,0.6)",
      "fontVariantNumeric": "tabular-nums"}

# Global CSS for what inline styles cannot express (font, hover states, focus rings, scrollbars).
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
body { margin: 0; font-family: 'Plus Jakarta Sans', Inter, 'Segoe UI', sans-serif; -webkit-font-smoothing: antialiased; }
.nav-item { transition: background .15s ease, color .15s ease, border-color .15s ease; }
.nav-item:hover { background-color: rgba(255,255,255,0.06); color: #ffffff !important; }
.dark-slider .rc-slider-rail { background-color: rgba(255,255,255,0.18) !important; }
.dark-slider .rc-slider-handle { background: #ffffff !important; border: 3px solid #1db954 !important;
  box-shadow: 0 0 0 4px rgba(29,185,84,0.25) !important; }
.cta { transition: transform .15s ease, box-shadow .15s ease; }
.cta:hover { transform: translateY(-2px); box-shadow: 0 10px 28px rgba(0,0,0,0.25); }
.float { animation: float 6s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
.lift { transition: transform .15s ease, box-shadow .15s ease; }
.lift:hover { transform: translateY(-2px); box-shadow: 0 2px 4px rgba(16,24,40,.06), 0 12px 28px rgba(16,24,40,.09) !important; }
.btn { transition: filter .15s ease, transform .1s ease; }
.btn:hover { filter: brightness(0.96); }
.btn:active { transform: scale(0.98); }
.heat td { transition: filter .12s ease; }
.heat td:hover { filter: brightness(1.06) saturate(1.1); }
.Select-control, .dash-dropdown .Select-control { border-radius: 8px !important; border-color: #e9ebef !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.05); }
.dash-slider-range, .rc-slider-track { background: #1db954 !important; }
.dash-slider-thumb, .rc-slider-handle { background: #ffffff !important; border: 3px solid #1db954 !important; }
.dash-slider-track { background-color: #e3e6e4 !important; }
.dark-slider .dash-slider-track { background-color: rgba(255,255,255,0.18) !important; }
.dark-slider .dash-slider-thumb { box-shadow: 0 0 0 5px rgba(29,185,84,0.25) !important; }
input[type=radio], input[type=checkbox] { accent-color: #1db954; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #d4d7dd; border-radius: 10px; border: 2px solid #f6f7f9; }
"""

# ----------------------------------------------------------------------------- generic components


def style(fig, title, y_title=None, height=360, legend=True):
    fig.update_layout(
        title=dict(text=title, x=0.015, xanchor="left", y=0.96, font=dict(size=15, color="#1d2127", family=FONT, weight=600)),
        template="plotly_white", height=height, margin=dict(l=56, r=20, t=64, b=40),
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff", font=dict(family=FONT, color=INK_3, size=12),
        colorway=[BLUE, ORANGE, AQUA], hovermode="x unified", showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#4b5058")),
        hoverlabel=dict(bgcolor="#1d2127", font=dict(color="#ffffff", family=FONT), bordercolor="#1d2127"),
        bargap=0.3, bargroupgap=0.1, barcornerradius=5,
    )
    fig.update_xaxes(showgrid=False, type="category", linecolor=BORDER, ticks="", tickfont=dict(color="#6b7079"))
    fig.update_yaxes(title=y_title, gridcolor="#f0f1f4", zerolinecolor="#d4d7dd", tickfont=dict(color="#6b7079"),
                     title_font=dict(size=12, color=INK_3))
    return fig


def line(df, cols, title, y_title=None, x=None, fmt=":,.1f", suffix=""):
    fig = go.Figure()
    xs = [str(v) for v in (df.index if x is None else df[x])]
    single = len(cols) == 1
    for (col, label), color in zip(cols, [BLUE, ORANGE, AQUA]):
        fig.add_trace(go.Scatter(
            x=xs, y=df[col], name=label, mode="lines+markers", line=dict(width=3, shape="spline", color=color),
            marker=dict(size=8, color=color, line=dict(width=2, color="#ffffff")),
            fill="tozeroy" if single else None, fillcolor="rgba(29,185,84,0.10)" if single else None,
            hovertemplate=f"%{{y{fmt}}}{suffix}"))
    return style(fig, title, y_title)


def sparkline(values, color):
    vals = [v for v in values if pd.notna(v)]
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    fig = go.Figure(go.Scatter(y=vals, mode="lines", line=dict(width=2, color=color, shape="spline"), fill="tozeroy",
                               fillcolor=f"rgba({r},{g},{b},0.10)", hoverinfo="skip"))
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.15 or 1
    fig.update_layout(height=42, margin=dict(l=0, r=0, t=4, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, range=[lo - pad, hi + pad])
    return dcc.Graph(figure=fig, config={"staticPlot": True}, style={"height": "42px", "marginTop": "6px"})


def bars(df, cols, title, y_title=None, x=None, mode="group", fmt=":,.1f", suffix="", text=False):
    fig = go.Figure()
    xs = [str(v) for v in (df.index if x is None else df[x])]
    for col, label in cols:
        fig.add_trace(go.Bar(x=xs, y=df[col], name=label, hovertemplate=f"%{{y{fmt}}}{suffix}",
                             texttemplate=f"%{{y{fmt}}}{suffix}" if text else None, textposition="outside",
                             cliponaxis=False))
    fig.update_layout(barmode=mode)
    return style(fig, title, y_title)


def graph(fig, note=None):
    children = [dcc.Graph(figure=fig, style={"height": f"{fig.layout.height or 360}px"},
                          config={"displayModeBar": False, "responsive": True})]
    if note:
        children.append(html.Div(note, style={**NOTE, "padding": "0 12px 8px"}))
    return html.Div(children, style=PANEL, className="lift")


def row(*children):
    return html.Div(list(children), style=ROW)


def kpi_row(*cards):
    return html.Div(list(cards), style={"display": "grid", "gap": "16px", "marginBottom": "16px",
                                        "gridTemplateColumns": "repeat(auto-fit, minmax(175px, 1fr))"})


def eur_m(v, signed=False):
    sign = "-" if v < 0 else ("+" if signed else "")
    return f"{sign}${abs(v):,.0f}M"


def card(label, value, delta=None, positive=None, spark=None, icon=None, color=BLUE):
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    head = html.Div([
        html.Div(label, style={"fontSize": "12px", "color": INK_3, "fontWeight": 600, "textTransform": "uppercase",
                               "letterSpacing": "0.05em"}),
        html.Div(icon, style={"width": "28px", "height": "28px", "borderRadius": "8px", "display": "flex",
                              "alignItems": "center", "justifyContent": "center", "fontSize": "14px", "color": color,
                              "backgroundColor": f"rgba({r},{g},{b},0.10)"}) if icon else None,
    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"})
    kids = [head, html.Div(value, style={"fontSize": "26px", "fontWeight": 700, "marginTop": "6px",
                                         "letterSpacing": "-0.02em", "color": "#14171c"})]
    if delta:
        if positive is None:
            pill = {"color": "#4b5058", "backgroundColor": "#f0f1f4"}
            arrow = ""
        else:
            pill = {"color": GREEN_DARK, "backgroundColor": "#e8f7ee"} if positive else {"color": "#ffffff", "backgroundColor": BLACK}
            arrow = "▲ " if positive else "▼ "
        kids.append(html.Span(arrow + delta, style={**pill, "fontSize": "11.5px", "fontWeight": 600, "padding": "3px 8px",
                                                    "borderRadius": "999px", "display": "inline-block", "marginTop": "6px"}))
    if spark is not None:
        kids.append(sparkline(spark, color))
    return html.Div(kids, style=CARD, className="lift")


def callout(kind, title, text):
    bg, accent = BOX_COLORS[kind]
    return html.Div([
        html.Div(title, style={"fontWeight": 700, "fontSize": "13.5px", "color": "#14171c", "marginBottom": "4px"}),
        html.Div(text, style={"color": "#4b5058"}),
    ], style={"backgroundColor": bg, "borderLeft": f"4px solid {accent}", "borderRadius": "12px", "padding": "14px 16px",
              "flex": "1 1 280px", "fontSize": "13px", "lineHeight": 1.55}, className="lift")


def table(df, fmt="{:,.2f}"):
    df = df.reset_index()
    shown = df.copy()
    for col in shown.columns[1:]:
        shown[col] = shown[col].map(
            lambda v: "n/a" if pd.isna(v) else (fmt.format(v) if isinstance(v, (int, float, np.number)) else v))
    return dash_table.DataTable(
        data=shown.to_dict("records"), columns=[{"name": str(c), "id": str(c)} for c in shown.columns],
        style_table={"overflowX": "auto"}, style_as_list_view=True,
        style_header={"fontWeight": 700, "backgroundColor": "#ffffff", "color": INK, "border": "none",
                      "whiteSpace": "normal", "height": "auto", "lineHeight": "1.3",
                      "borderBottom": f"1px solid {BORDER}"},
        style_cell={"fontFamily": FONT, "fontSize": "13px", "padding": "9px 12px", "textAlign": "right",
                    "border": "none", "borderBottom": f"1px solid {BORDER}"},
        style_cell_conditional=[{"if": {"column_id": str(shown.columns[0])}, "textAlign": "left", "fontWeight": 600}],
        page_size=25,
    )


def panel(title, body):
    return html.Div([html.Div(title, style={"fontWeight": 600, "fontSize": "15px", "padding": "8px 8px 12px",
                                            "color": "#1d2127"}), body], style=PANEL)


def toolbar_select(id_, options, value, width="150px"):
    return dcc.Dropdown(id=id_, options=[{"label": label, "value": v} for v, label in options], value=value,
                        clearable=False, searchable=False, persistence=True, persistence_type="memory",
                        style={"width": width, "fontSize": "13px"})

# ----------------------------------------------------------------------------- heat table (cohort style)

# Sequential heat: near-white (worse) -> green (better).
HEAT_STOPS = [(0.0, (246, 248, 247)), (0.5, (150, 220, 176)), (1.0, (24, 160, 72))]


def heat_color(t):
    t = min(max(t, 0.0), 1.0)
    for (t0, c0), (t1, c1) in zip(HEAT_STOPS, HEAT_STOPS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return "rgb({},{},{})".format(*(round(a + (b - a) * f) for a, b in zip(c0, c1)))
    return "rgb({},{},{})".format(*HEAT_STOPS[-1][1])


def heat_table(row_labels, fixed_cols, col_labels, values, fmt, higher_is_better=True, highlight_row=None, marks=None):
    """Cohort-style table: label column + fixed info columns + heat-coloured value grid.

    marks: optional boolean grid; marked cells get a bold outline (e.g. the CAC payback period)."""
    arr = np.array(values, dtype=float)
    lo, hi = np.nanmin(arr), np.nanmax(arr)
    span = (hi - lo) or 1.0
    header = html.Tr([html.Th(fixed_cols[0][0], style={**TH, "textAlign": "left", "left": 0, "zIndex": 2})]
                     + [html.Th(name, style=TH) for name, _ in fixed_cols[1:]]
                     + [html.Th(c, style=TH) for c in col_labels])
    body = []
    for i, label in enumerate(row_labels):
        bold = {"fontWeight": 700} if i == highlight_row else {}
        cells = [html.Td(label, style={**TD, "textAlign": "left", "fontWeight": 700, "backgroundColor": "#ffffff",
                                       "borderBottom": f"1px solid {BORDER}", "position": "sticky", "left": 0})]
        cells += [html.Td(vals[i], style={**TD, "backgroundColor": "#ffffff", "borderBottom": f"1px solid {BORDER}", **bold})
                  for _, vals in fixed_cols[1:]]
        for j, v in enumerate(arr[i]):
            if np.isnan(v):
                cells.append(html.Td("", style={**TD, "backgroundColor": "#ffffff"}))
                continue
            t = (v - lo) / span
            mark = {"fontWeight": 800, "boxShadow": "inset 0 0 0 2px #14171c"} if marks is not None and marks[i][j] else {}
            cells.append(html.Td(fmt(v), title=f"{label} · {col_labels[j]}",
                                 style={**TD, **bold, **mark, "color": "#ffffff" if (t if higher_is_better else 1 - t) > 0.7 else BLACK,
                                        "backgroundColor": heat_color(t if higher_is_better else 1 - t)}))
        body.append(html.Tr(cells))
    legend = html.Div([
        html.Span("Worse", style=NOTE),
        html.Div(style={"width": "160px", "height": "10px", "borderRadius": "5px", "margin": "0 8px",
                        "background": f"linear-gradient(90deg, {heat_color(0)}, {heat_color(0.5)}, {heat_color(1)})"}),
        html.Span("Better", style=NOTE),
    ], style={"display": "flex", "alignItems": "center", "padding": "10px 4px 2px"})
    return html.Div([
        html.Div(html.Table([html.Thead(header), html.Tbody(body)], className="heat",
                            style={"borderCollapse": "collapse", "width": "100%", "fontFamily": FONT}),
                 style={"overflow": "auto", "maxHeight": "580px", "border": f"1px solid {BORDER}", "borderRadius": "10px"}),
        legend,
    ])


def table_card(toolbar, body_id, note):
    return html.Div([
        html.Div(toolbar, style={"display": "flex", "justifyContent": "flex-end", "gap": "8px", "padding": "6px 6px 12px",
                                 "flexWrap": "wrap"}),
        html.Div(id=body_id),
        html.Div(note, style={**NOTE, "padding": "8px 6px 4px"}),
    ], style={**PANEL, "padding": "12px 14px"})

# ----------------------------------------------------------------------------- unit economics


def usd_base(base_year):
    """Base-year unit-economics inputs with the money values (ARPU, S&M) converted to USD."""
    base = base_inputs(base_year)
    rate = FX_YEAR[base_year]
    return {**base, "arpu": base["arpu"] * rate, "sm_expense": base["sm_expense"] * rate}


def make_runner(base_year, churn, arpu_chg, gm_pp, sm_chg, na_chg):
    base = usd_base(base_year)
    opening = base["avg_subs"] - base["net_adds"] / 2

    def run(churn=churn, arpu_chg=arpu_chg, gm_pp=gm_pp, sm_chg=sm_chg, na_chg=na_chg):
        net_adds = base["net_adds"] * (1 + na_chg)
        return unit_economics(arpu=base["arpu"] * (1 + arpu_chg), gross_margin=base["gross_margin"] + gm_pp / 100,
                              churn=churn, sm_expense=base["sm_expense"] * (1 + sm_chg), net_adds=net_adds,
                              avg_subs=opening + net_adds / 2)
    return run, base


def runner_from(f):
    return make_runner(int(f["base_year"]), f["churn"] / 100, f["arpu"] / 100, f["gm"], f["sm"] / 100, f["na"] / 100)

# ----------------------------------------------------------------------------- page content


def section_title(text, sub=None):
    return html.Div([
        html.Div(text, style={"fontSize": "22px", "fontWeight": 700, "color": BLACK, "letterSpacing": "-0.01em"}),
        html.Div(sub, style={"fontSize": "14px", "color": "#6b7079", "marginTop": "2px"}) if sub else None,
    ], style={"margin": "30px 0 16px"})


def hero(y):
    rev_b = annual.loc[y, "total_revenue_eur_millions"] / 1000
    om = prof.loc[y, "operating_margin_calc_pct"]
    grow = rev.loc[y, "total_revenue_growth_pct"]
    grow_txt = "first year in the data" if pd.isna(grow) else f"{grow:+.1f}% vs last year"
    grow = 0 if pd.isna(grow) else grow
    cta = {"borderRadius": "999px", "padding": "10px 20px", "fontSize": "13.5px", "fontWeight": 700,
           "textDecoration": "none", "display": "inline-block"}
    left = html.Div([
        html.Div([html.Span("●", style={"color": GREEN, "marginRight": "8px"}), "SPOTIFY UNIT ECONOMICS"], style={
            "display": "inline-block", "fontSize": "11px", "fontWeight": 800, "letterSpacing": "0.16em", "color": "#e6efe9",
            "border": "1px solid rgba(255,255,255,0.22)", "borderRadius": "999px", "padding": "6px 14px",
            "backgroundColor": "rgba(255,255,255,0.05)"}),
        html.Div([
            "See how Spotify turns listeners into profit, ",
            html.Span("year by year.", style={
                "backgroundImage": f"linear-gradient(90deg, {GREEN} 0%, #9ff0c0 100%)", "WebkitBackgroundClip": "text",
                "backgroundClip": "text", "color": "transparent"}),
        ], style={"fontSize": "28px", "fontWeight": 800, "color": "#ffffff", "lineHeight": 1.2, "letterSpacing": "-0.025em",
                  "margin": "14px 0 10px", "maxWidth": "760px"}),
        html.Div("This dashboard uses Spotify's official results (2021-2025) to show where the money comes from, whether "
                 "the business is profitable, and how much each subscriber is worth, explained in plain words.",
                 style={"fontSize": "14.5px", "color": "#cfdad3", "lineHeight": 1.55, "maxWidth": "640px"}),
        html.Div([
            dcc.Link("See subscriber value →", href="/ltv", className="cta",
                     style={**cta, "backgroundColor": "#ffffff", "color": BLACK, "boxShadow": "0 8px 24px rgba(0,0,0,0.25)"}),
            dcc.Link("Explore revenue", href="/revenue", className="cta",
                     style={**cta, "color": "#ffffff", "border": "1px solid rgba(255,255,255,0.35)",
                            "backgroundColor": "rgba(255,255,255,0.05)"}),
        ], style={"display": "flex", "gap": "12px", "marginTop": "20px", "flexWrap": "wrap"}),
    ], style={"flex": "1 1 520px", "minWidth": 0})
    floats = html.Div([
        html.Div([
            html.Div(f"Revenue {y}", style={"fontSize": "13px", "color": "#cfe9d9"}),
            html.Div(f"${rev_b:.1f}B", style={"fontSize": "26px", "fontWeight": 800, "color": "#ffffff", "margin": "4px 0 8px"}),
            html.Div(html.Div(style={"width": f"{min(max(grow, 0) * 5, 100):.0f}%", "height": "6px", "borderRadius": "6px",
                                     "background": f"linear-gradient(90deg, {GREEN}, #9ff0c0)"}),
                     style={"backgroundColor": "rgba(255,255,255,0.15)", "borderRadius": "6px", "width": "130px"}),
            html.Div(grow_txt, style={"fontSize": "13px", "color": "#cfe9d9", "marginTop": "10px"}),
        ], className="float", style={
            "background": "linear-gradient(145deg, rgba(29,185,84,0.55) 0%, rgba(20,83,45,0.85) 100%)",
            "border": "1px solid rgba(255,255,255,0.22)", "borderRadius": "16px", "padding": "14px 18px", "width": "170px",
            "boxShadow": "0 20px 40px rgba(0,0,0,0.35)", "backdropFilter": "blur(6px)"}),
        html.Div([
            html.Div("Kept as profit", style={"fontSize": "13px", "color": "#6b7079"}),
            html.Div(f"{om:.1f}%", style={"fontSize": "26px", "fontWeight": 800, "color": GREEN_DARK, "margin": "4px 0 2px"}),
            html.Div("of every dollar earned", style={"fontSize": "13px", "color": "#6b7079"}),
        ], className="float", style={
            "backgroundColor": "#ffffff", "borderRadius": "16px", "padding": "14px 18px", "width": "160px",
            "boxShadow": "0 24px 48px rgba(0,0,0,0.35)", "marginTop": "10px", "marginLeft": "50px",
            "animationDelay": "1.5s"}),
    ], style={"flex": "0 0 auto", "display": "flex", "flexDirection": "column", "padding": "6px 10px 0 0"})
    banner = html.Div([left, floats], style={
        "display": "flex", "gap": "30px", "alignItems": "center", "flexWrap": "wrap", "borderRadius": "22px",
        "padding": "28px 36px", "position": "relative", "overflow": "hidden", "boxShadow": "0 24px 60px rgba(5,20,12,0.28)",
        "background": "radial-gradient(circle at 85% 15%, rgba(29,185,84,0.40) 0%, rgba(29,185,84,0) 42%), "
                      "radial-gradient(circle at 10% 110%, rgba(29,185,84,0.22) 0%, rgba(29,185,84,0) 40%), "
                      "linear-gradient(130deg, #050505 0%, #0a1d12 50%, #14532d 100%)"})

    def step(n, title, text):
        return html.Div([
            html.Div(str(n), style={"width": "46px", "height": "46px", "borderRadius": "50%", "display": "flex",
                                    "alignItems": "center", "justifyContent": "center", "fontWeight": 800, "fontSize": "18px",
                                    "color": GREEN_DARK, "backgroundColor": "#e8f7ee", "flexShrink": 0}),
            html.Div([html.Div(title, style={"fontSize": "18px", "fontWeight": 700, "color": BLACK}),
                      html.Div(text, style={"fontSize": "15px", "color": "#5b6168", "lineHeight": 1.6, "marginTop": "8px"})]),
        ], className="lift", style={**CARD, "display": "flex", "gap": "18px", "padding": "26px 26px", "flex": "1 1 300px"})

    steps = html.Div([
        step(1, "Collect official numbers", "Revenue, users, costs and profit from Spotify's published results for "
                                            f"2021-2025, checked with {N_CHECKS} automatic tests."),
        step(2, "Turn them into simple metrics", "Growth, profit margins, money per subscriber, the cost to win a "
                                                 "subscriber and how much each one is worth."),
        step(3, "Test 'what if?'", "Move the sliders to see what happens if more people cancel, prices change or "
                                   "marketing spend rises."),
    ], style={"display": "flex", "gap": "18px", "flexWrap": "wrap"})
    return [banner, section_title("How it works"), steps]


def view_dashboard(year):
    a, p = annual.loc[year], prof.loc[year]
    prev = year - 1 if year - 1 in annual.index else None

    def delta(col, src=annual):
        return None if prev is None else src.loc[year, col] - src.loc[prev, col]

    def pos(v):
        return None if v is None else v >= 0

    hist = annual.loc[:year]
    phist = prof.loc[:year]
    cards = kpi_row(
        card("Total revenue", f"${a['total_revenue_eur_millions'] / 1000:.2f}B",
             None if prev is None else f"{rev.loc[year, 'total_revenue_growth_pct']:+.1f}% YoY", pos(delta("total_revenue_eur_millions")),
             hist["total_revenue_eur_millions"], "$", BLUE),
        card("Premium subscribers", f"{a['premium_subscribers_millions']:.0f}M",
             None if prev is None else f"{delta('premium_subscribers_millions'):+.0f}M", pos(delta("premium_subscribers_millions")),
             hist["premium_subscribers_millions"], "★", GREEN),
        card("Monthly active users", f"{a['mau_millions']:.0f}M",
             None if prev is None else f"{delta('mau_millions'):+.0f}M", pos(delta("mau_millions")),
             hist["mau_millions"], "◉", BLUE),
        card("Gross margin", f"{p['gross_margin_calc_pct']:.1f}%",
             None if prev is None else f"{delta('gross_margin_calc_pct', prof):+.1f}pp", pos(delta("gross_margin_calc_pct", prof)),
             phist["gross_margin_calc_pct"], "%", GREEN),
        card("Operating income", eur_m(a["operating_income_eur_millions"]),
             None if prev is None else eur_m(delta("operating_income_eur_millions"), True), pos(delta("operating_income_eur_millions")),
             hist["operating_income_eur_millions"], "▲", GREEN),
        card("Free cash flow", eur_m(a["free_cash_flow_eur_millions"]),
             None if prev is None else eur_m(delta("free_cash_flow_eur_millions"), True), pos(delta("free_cash_flow_eur_millions")),
             hist["free_cash_flow_eur_millions"], "◆", BLUE),
    )
    cum_rev = (annual.loc[2025, "total_revenue_eur_millions"] / annual.loc[2021, "total_revenue_eur_millions"] - 1) * 100
    cum_sub = (annual.loc[2025, "premium_subscribers_millions"] / annual.loc[2021, "premium_subscribers_millions"] - 1) * 100
    return [
        *hero(year),
        section_title(f"Key numbers for {year}", "Pills show the change from the year before. Pick another year with the "
                                                 "Year filter at the top."),
        cards,
        row(graph(bars(annual, [("premium_revenue_eur_millions", "Premium"), ("ad_supported_revenue_eur_millions", "Ads (free users)")],
                       "Revenue: Premium vs ads ($ millions)", "$ millions", mode="stack", fmt=":,.0f")),
            graph(line(prof, [("gross_margin_calc_pct", "Gross margin"), ("fcf_margin_pct", "Cash margin"),
                              ("operating_margin_calc_pct", "Operating margin")], "Profit margins (% of revenue kept)", "% of revenue", suffix="%"))),
        row(
            callout("info", "Growth is monetising.", f"Revenue +{cum_rev:.0f}% vs premium subscribers +{cum_sub:.0f}% (2021-2025)."),
            callout("good", "Profitable at scale.", f"Operating margin {prof.loc[2022, 'operating_margin_calc_pct']:.1f}% (2022) → "
                    f"{prof.loc[2025, 'operating_margin_calc_pct']:.1f}% (2025); FCF ${annual.loc[2025, 'free_cash_flow_eur_millions']:,.0f}M."),
            callout("warn", "Ads are the gap.", f"Ad revenue {rev.loc[2025, 'ad_supported_revenue_growth_pct']:+.1f}% in 2025; revenue per "
                    f"ad-supported MAU ${subs['ad_revenue_per_ad_mau_annual_eur'].dropna().iloc[0]:.2f} → "
                    f"${subs.loc[2025, 'ad_revenue_per_ad_mau_annual_eur']:.2f} a year."),
        ),
    ]


def view_revenue(sub):
    if sub == "growth":
        rg = rev.dropna(subset=["total_revenue_growth_pct"])
        g = subs.dropna(subset=["premium_subscriber_growth_pct"])
        return [row(graph(bars(rg, [("premium_revenue_growth_pct", "Premium"), ("ad_supported_revenue_growth_pct", "Ads (free users)")],
                               "Revenue growth by segment (YoY %)", "YoY %", suffix="%", text=True)),
                    graph(bars(g, [("premium_subscriber_growth_pct", "Premium subscribers"), ("total_revenue_growth_pct", "Total revenue")],
                               "Revenue growth vs subscriber growth (YoY %)", "YoY %", suffix="%", text=True)))]
    if sub == "quarterly":
        qt = q.set_index("period")[["total_revenue_eur_millions", "premium_revenue_eur_millions",
                                     "ad_supported_revenue_eur_millions"]]
        qt.columns = ["Total revenue", "Premium", "Ad-supported"]
        return [row(graph(bars(q, [("premium_revenue_eur_millions", "Premium"), ("ad_supported_revenue_eur_millions", "Ads (free users)")],
                               "Revenue each quarter ($ millions)", "$ millions", x="period", mode="stack", fmt=":,.0f"))),
                row(panel("Quarterly revenue ($ millions)", table(qt, "{:,.0f}")))]
    mix = line(rev, [("premium_mix_pct", "Premium share of revenue")], "Share of revenue from Premium (%)", "%", suffix="%")
    mix.update_layout(showlegend=False)
    mix.update_yaxes(range=[85, 92])
    return [row(graph(bars(annual, [("premium_revenue_eur_millions", "Premium"), ("ad_supported_revenue_eur_millions", "Ads (free users)")],
                           "Revenue: Premium vs ads ($ millions)", "$ millions", mode="stack", fmt=":,.0f")),
                graph(mix, "Axis is zoomed to show the change."))]


def view_subscribers(sub):
    if sub == "netadds":
        n = subs.dropna(subset=["premium_net_adds_millions"])
        adds = bars(n, [("premium_net_adds_millions", "Net adds")], "New paying subscribers per year (millions, after cancellations)", "Millions",
                    fmt=":.0f", suffix="M", text=True)
        adds.update_traces(marker_color=GREEN)
        adds.update_layout(showlegend=False)
        qa = q.dropna(subset=["premium_net_adds_millions"])
        qadds = bars(qa, [("premium_net_adds_millions", "Net adds")], "New paying subscribers per quarter (millions)",
                     "Millions", x="period", fmt=":.0f", suffix="M", text=True)
        qadds.update_traces(marker_color=GREEN)
        qadds.update_layout(showlegend=False)
        return [row(graph(adds, "Net adds = change in year-end subscribers. Gross adds and churn are not disclosed."), graph(qadds))]
    share = line(subs, [("premium_share_of_mau_pct", "Premium subscribers as % of MAU")], "Premium subscribers as % of MAU", "%", suffix="%")
    share.update_layout(showlegend=False)
    return [row(graph(line(annual, [("mau_millions", "Total MAU"), ("ad_supported_mau_millions", "Ad-supported MAU"),
                                    ("premium_subscribers_millions", "Premium subscribers")],
                           "Users at year-end (millions)", "Millions", fmt=":,.0f", suffix="M"),
                      "Premium + ad-supported exceeds MAU: users on both tiers within a month are counted in each."),
                graph(share, "Free users are growing faster than conversions to premium."))]


def view_arpu(sub):
    if sub == "ads":
        s = subs.dropna(subset=["ad_revenue_per_ad_mau_annual_eur"])
        fig = line(s, [("ad_revenue_per_ad_mau_annual_eur", "Ad revenue per ad-supported MAU")],
                   "Ad money earned per free user, per year ($)", "$ per user per year", fmt=":.2f")
        fig.update_layout(showlegend=False)
        fig.update_yaxes(rangemode="tozero", tickprefix="$")
        return [row(graph(fig, "Ad-supported monetisation fell every year while the free audience grew."))]
    s = subs.dropna(subset=["premium_arpu_monthly_eur"])
    fig = line(s, [("premium_arpu_monthly_eur", "Annual method")], "Money from each paying subscriber, per month ($)",
               "$ / subscriber / month", fmt=":.2f")
    fig.update_yaxes(range=[4.0, 5.0], tickprefix="$")
    qa = q.dropna(subset=["premium_arpu_monthly_eur"])
    qfig = line(qa, [("premium_arpu_monthly_eur", "Quarterly")], "Money per paying subscriber per month, 2025 quarters ($)",
                "$ / subscriber / month", x="period", fmt=":.2f")
    qfig.update_layout(showlegend=False)
    qfig.update_yaxes(range=[4.0, 5.0], tickprefix="$")
    return [row(graph(fig, "Axis starts at $4."), graph(qfig, "Axis starts at $4."))]


def view_profitability(sub):
    if sub == "opinc":
        oi = annual["operating_income_eur_millions"]
        op = go.Figure(go.Bar(x=[str(y) for y in oi.index], y=oi, marker_color=[GOOD if v >= 0 else CRITICAL for v in oi],
                              text=[f"{'Profit' if v >= 0 else 'Loss'} ${abs(v):,.0f}M" for v in oi], textposition="outside",
                              cliponaxis=False, hovertemplate="$%{y:,.0f}M", name="Operating income"))
        style(op, "Profit or loss from operations ($ millions)", "$ millions", legend=False)
        op.update_yaxes(range=[oi.min() - 450, oi.max() + 450])
        ratios = line(prof, [("opex_ratio_pct", "Total operating expenses"), ("sm_pct_of_revenue", "Sales & marketing")],
                      "Costs as % of revenue (lower is better)", "% of revenue", suffix="%")
        ratios.update_yaxes(rangemode="tozero")
        return [row(graph(op), graph(ratios, "Sales & marketing expense is available for 2023-2025 only."))]
    if sub == "pnl":
        tbl = prof[["total_revenue_eur_millions", "gross_profit_eur_millions", "total_operating_expenses_eur_millions",
                    "sales_marketing_expense_eur_millions", "operating_income_eur_millions", "free_cash_flow_eur_millions",
                    "gross_margin_calc_pct", "operating_margin_calc_pct", "incremental_operating_margin_pct"]].copy()
        tbl.columns = ["Revenue", "Gross profit", "Opex", "S&M", "Operating income", "FCF", "Gross margin %",
                       "Operating margin %", "Incremental op. margin %"]
        tbl.index.name = "Year"
        return [row(panel("Profit & loss summary ($ millions)", table(tbl, "{:,.1f}")))]
    qm = line(q, [("gross_margin_calc_pct", "Gross margin"), ("operating_margin_calc_pct", "Operating margin")],
              "Profit margins by quarter (%)", "% of revenue", x="period", suffix="%")
    qm.update_yaxes(range=[0, 40])
    return [row(graph(line(prof, [("gross_margin_calc_pct", "Gross margin"), ("fcf_margin_pct", "Cash margin"),
                                  ("operating_margin_calc_pct", "Operating margin")], "Profit margins by year (%)",
                           "% of revenue", suffix="%")), graph(qm))]


def view_cac():
    t = ue_years[["cac_proxy_net_adds_eur", "cac_proxy_gross_adds_eur", "payback_months_net_adds",
                  "payback_months_gross_adds"]].copy()
    t.columns = ["CAC proxy, net adds ($)", "CAC proxy, gross adds ($)", "Payback, net (mo)", "Payback, gross (mo)"]
    t.index.name = "Year"
    return [
        row(graph(bars(ue_years, [("cac_proxy_net_adds_eur", "S&M / net adds"),
                                  ("cac_proxy_gross_adds_eur", "S&M / implied gross adds (3% churn)")],
                       "Estimated cost to win one subscriber ($)", "$ per subscriber", fmt=":.2f", text=True), DISCLAIMER),
            panel("CAC proxies and payback at 3% churn", table(t))),
        row(callout("info", "Why two CAC proxies?", "S&M ÷ net adds treats every new subscriber as growth, which implies "
                    "zero churn and contradicts the churn used in LTV. The gross-adds proxy adds back the subscribers the "
                    "assumed churn rate implies must be replaced, so LTV and CAC rest on the same assumption.")),
    ]


def view_ltv(sub, f):
    run, _ = runner_from(f)
    proxy = f["proxy"]
    r = run()
    churn = f["churn"] / 100
    lifetime, payback = r["expected_lifetime_months"], r[f"payback_months_{proxy}"]
    recovered = payback < lifetime
    ratio = r[f"ltv_to_cac_{proxy}"]
    cards = kpi_row(
        card("Value of a subscriber", f"${r['ltv_eur']:.2f}", "profit over their lifetime"),
        card("Cost to win one", f"${r[f'cac_proxy_{proxy}_eur']:.2f}", "marketing per subscriber"),
        card("Value ÷ cost", f"{ratio:.1f}x", "healthy (3x or more)" if ratio >= 3 else "weak (below 3x)", ratio >= 3),
        card("Months to earn back cost", f"{payback:.1f} mo"),
        card("Average stay", f"{lifetime:.1f} mo", "cost earned back in time" if recovered else "cost NOT earned back", recovered),
    )
    if sub == "drivers":
        key = f"ltv_to_cac_{proxy}"
        levers = [("Churn ±1pp", {"churn": max(churn - 0.01, 0.005)}, {"churn": churn + 0.01}),
                  ("Gross margin ∓2pp", {"gm_pp": f["gm"] - 2}, {"gm_pp": f["gm"] + 2}),
                  ("ARPU ∓10%", {"arpu_chg": f["arpu"] / 100 - 0.10}, {"arpu_chg": f["arpu"] / 100 + 0.10}),
                  ("S&M spend ∓20%", {"sm_chg": f["sm"] / 100 - 0.20}, {"sm_chg": f["sm"] / 100 + 0.20}),
                  ("Net adds ∓25%", {"na_chg": f["na"] / 100 - 0.25}, {"na_chg": f["na"] / 100 + 0.25})]
        t = pd.DataFrame([{"lever": n, "low": run(**lo)[key], "high": run(**hi)[key]} for n, lo, hi in levers])
        t = t.assign(swing=(t["high"] - t["low"]).abs()).sort_values("swing")
        tor = go.Figure()
        for col, label, color in (("low", "Assumption lowered", BLUE), ("high", "Assumption raised", ORANGE)):
            tor.add_trace(go.Bar(y=t["lever"], x=t[col] - ratio, base=ratio, orientation="h", name=label,
                                 marker_color=color, customdata=t[col],
                                 hovertemplate=f"%{{customdata:.2f}}x<extra>{label}</extra>"))
        tor.add_vline(x=ratio, line_width=1, line_color=INK_2)
        style(tor, f"Which assumption changes the value-to-cost ratio most? (now {ratio:.1f}x)", height=400)
        tor.update_layout(barmode="overlay", hovermode="closest")
        tor.update_xaxes(type="linear", title="Value-to-cost ratio (x)", showgrid=True, gridcolor="#eeeeea")
        tor.update_yaxes(type="category", showgrid=False)
        return [cards, row(graph(tor, "Each bar moves one lever from the current filter settings, holding the others fixed."))]

    sweep = pd.DataFrame([{"churn": ch * 100, **run(churn=ch)} for ch in np.round(np.arange(0.01, 0.0801, 0.0025), 4)])
    sw = go.Figure()
    for col, label, color in (("ltv_eur", "Value of a subscriber", GREEN), ("cac_proxy_net_adds_eur", "Cost to win (simple estimate)", BLACK),
                              ("cac_proxy_gross_adds_eur", "Cost to win (realistic estimate)", GREY)):
        sw.add_trace(go.Scatter(x=sweep["churn"], y=sweep[col], name=label, line=dict(width=2.5, color=color),
                                hovertemplate="$%{y:.2f}"))
    sw.add_vline(x=churn * 100, line_width=1, line_color=INK_2, annotation_text=f"selected {churn:.1%}",
                 annotation_position="top right")
    style(sw, "Value of a subscriber vs cost to win one ($)", "$ per subscriber")
    sw.update_xaxes(type="linear", title="% of subscribers who cancel each month (churn)", ticksuffix="%")
    sw.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="left", x=0), margin=dict(b=110), height=430)
    ct = pd.DataFrame([{"Scenario": f"{n} ({c:.0%})", **run(churn=c)} for n, c in CHURN_SCENARIOS.items()]).set_index("Scenario")
    ct = ct[["ltv_eur", "cac_proxy_gross_adds_eur", "ltv_to_cac_net_adds", "ltv_to_cac_gross_adds",
             "payback_months_gross_adds"]]
    ct.columns = ["Value $", "Cost to win $", "Value ÷ cost (simple)", "Value ÷ cost (realistic)", "Months to earn back"]
    return [cards, row(graph(sw, "Cancellation rates are assumptions; Spotify does not publish them."), panel("If more or fewer people cancel (uses your assumptions)", table(ct)))]


def view_retention(sub):
    is_gp = sub == "gp"
    toolbar = [
        toolbar_select("rt-value", [("gp", "Profit earned $"), ("pct", "Percent"), ("subs", "People (of 1,000)")] if is_gp
                       else [("pct", "Percent"), ("subs", "People (of 1,000)"), ("gp", "Profit earned $")],
                       "gp" if is_gp else "pct", "170px"),
        toolbar_select("rt-mode", [("retained", "Still paying"), ("churned", "Cancelled")], "retained", "140px"),
        toolbar_select("rt-start", [("start", "Since joining"), ("prev", "Vs previous period")], "start", "170px"),
        toolbar_select("rt-period", [("month", "Month"), ("quarter", "Quarter"), ("year", "Year")], "month", "120px"),
    ]
    note = ("Each row follows 1,000 people who just subscribed, assuming a fixed % cancel every month (row label). "
            "Greener = more people still paying. The bold row is the rate set on the Assumptions page. In 'Profit earned $', the "
            "outlined cell is when the profit from one subscriber has paid back the cost of winning them. "
            "This is a model: Spotify does not publish this data.")
    return [row(table_card(toolbar, "rt-body", note))]


def view_sensitivity():
    toolbar = [
        toolbar_select("sg-metric", [("ltv_eur", "Value of a subscriber $"), ("ltv_to_cac_gross_adds", "Value ÷ cost (realistic)"),
                                     ("ltv_to_cac_net_adds", "Value ÷ cost (simple)"),
                                     ("payback_months_gross_adds", "Months to earn back cost")], "ltv_eur", "220px"),
        toolbar_select("sg-cols", [("gm", "vs profit margin"), ("arpu", "vs price change"), ("sm", "vs marketing spend"),
                                   ("na", "vs new subscribers")], "gm", "190px"),
    ]
    note = ("Rows: % of subscribers who cancel each month (an assumption). Columns: the second assumption you picked. "
            "Greener = better. The bold row is the cancellation rate set on the Assumptions page.")
    return [row(table_card(toolbar, "sg-body", note))]


def view_data(sub, year=None):
    if sub == "glossary":
        g = pd.DataFrame(GLOSSARY, columns=["Term", "What it means"]).set_index("Term")
        return [row(panel("Glossary: the terms used in this dashboard", table(g)))]
    if sub == "validation":
        return [row(panel(f"Data validation: {N_PASS}/{N_CHECKS} checks passed", table(D["checks"].set_index("check"), "{:,.3f}")))]
    if sub == "method":
        formulas = pd.DataFrame({
            "Metric": ["Growth", "Monthly premium ARPU", "LTV", "CAC proxy (net adds)", "CAC proxy (gross adds)", "Payback",
                       "Modeled cohort retention"],
            "Formula": ["(Current - Previous) / Previous", "Premium revenue / avg(opening, closing subscribers) / 12",
                        "Monthly ARPU × gross margin / monthly churn", "S&M / net premium additions",
                        "S&M / (net adds + avg subscribers × churn × 12)", "CAC proxy / (monthly ARPU × gross margin)",
                        "(1 - monthly churn) ^ months"],
        }).set_index("Metric")
        return [row(panel("Formulas", table(formulas))), row(callout("warn", "Limitations.", DISCLAIMER + " ARPU is "
                    "approximated, gross margin is company-level, and LTV is undiscounted."))]
    an, qd = D["annual"], D["quarterly"]
    if year is not None:
        an, qd = an[an["year"] == year], qd[qd["year"] == year]
    label = f" for {year}" if year is not None else ""
    quarterly = (table(qd.set_index("period"), "{:,.1f}") if len(qd) else
                 html.Div(f"Spotify's quarterly figures in this data start in Q4 2024, so there are none for {year}.",
                          style={**NOTE, "padding": "4px 8px 10px"}))
    return [row(panel(f"Annual reported data{label} ($ millions, users in millions)", table(an.set_index("year"), "{:,.1f}"))),
            row(panel(f"Quarterly reported data{label}", quarterly))]


# ----------------------------------------------------------------------------- plain-English guide

GLOSSARY = [
    ("MAU", "Monthly active users: everyone who used Spotify in the month, free or paying."),
    ("Premium subscriber", "A person paying for Spotify Premium."),
    ("Ad-supported (free) user", "A person using free Spotify; Spotify earns money from ads they hear."),
    ("Revenue", "All the money Spotify earns, before costs."),
    ("US dollars ($)", "Spotify reports in euros; amounts here are converted to dollars at each year's average ECB exchange rate."),
    ("Gross margin", "The % of revenue left after paying music royalties and delivery costs."),
    ("Operating income", "Profit after all running costs (staff, marketing, offices). Negative = loss."),
    ("Free cash flow", "Cash the business actually generated in the year after investments."),
    ("ARPU", "Average Revenue Per User: money earned from one user per month."),
    ("Churn", "The % of subscribers who cancel each month. Spotify does not publish this, so we assume it."),
    ("CAC", "Customer Acquisition Cost: marketing money spent to win one new subscriber (estimated here)."),
    ("LTV", "Lifetime Value: the profit one subscriber brings in before they cancel."),
    ("LTV ÷ CAC", "How many times a subscriber pays back what it cost to win them. 3x or more is usually healthy."),
    ("Payback", "Months until a subscriber's profit covers the cost of winning them."),
    ("Simple vs realistic estimate", "Simple divides marketing by growth only. Realistic also counts people won to "
                                     "replace those who cancelled, so it is lower and more believable."),
]

GUIDE_BOX = {"backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "borderLeft": f"5px solid {GREEN}",
             "borderRadius": "12px", "padding": "14px 18px", "marginBottom": "16px", "boxShadow": SHADOW}


def explain(headline, how):
    return html.Div([
        html.Div([html.Span("💡", style={"marginRight": "8px"}), html.Span("What this means", style={
            "fontSize": "11px", "fontWeight": 700, "letterSpacing": "0.08em", "color": GREEN_DARK})]),
        html.Div(headline, style={"fontSize": "15.5px", "fontWeight": 600, "color": BLACK, "margin": "6px 0 4px",
                                  "lineHeight": 1.45}),
        html.Div([html.B("How to read it: "), how], style={"fontSize": "13px", "color": "#55595f", "lineHeight": 1.5}),
    ], style=GUIDE_BOX)


def guide(page, sub, f):
    """(headline, how-to-read) for each view, written in plain language with the key numbers."""
    a = annual
    rev_up = (a.loc[2025, "total_revenue_eur_millions"] / a.loc[2021, "total_revenue_eur_millions"] - 1) * 100
    if page == "dashboard":
        y = chosen_year(f) or YEARS[-1]
        return (f"In {y} Spotify earned ${a.loc[y, 'total_revenue_eur_millions'] / 1000:.1f} billion, had "
                f"{a.loc[y, 'premium_subscribers_millions']} million paying subscribers and "
                f"{'made a profit' if a.loc[y, 'operating_income_eur_millions'] >= 0 else 'made a loss'} of "
                f"${abs(a.loc[y, 'operating_income_eur_millions']):,.0f} million.",
                "Each card shows the number for the chosen year; the pill shows the change from the year before "
                "(green = up, black = down). The small line shows the trend since 2021. Change the year on the Assumptions page.")
    if page == "revenue":
        if sub == "growth":
            return (f"Revenue grew {rev.loc[2025, 'total_revenue_growth_pct']:.1f}% in 2025. Premium kept growing, but "
                    f"ad money fell {abs(rev.loc[2025, 'ad_supported_revenue_growth_pct']):.1f}%.",
                    "Each bar is growth versus the year before. Taller bar = faster growth; below zero = shrinking.")
        if sub == "quarterly":
            return ("Revenue is steady through the year and jumps in Q4 (October-December), when advertisers spend most.",
                    "Each bar is three months of revenue: green = Premium subscriptions, black = ads.")
        return (f"Revenue grew {rev_up:.0f}% from 2021 to 2025. About {rev.loc[2025, 'premium_mix_pct']:.0f}% of it "
                "comes from Premium subscriptions; the rest comes from ads.",
                "Each bar is one year's revenue. The green part is Premium, the black part is ads.")
    if page == "subscribers":
        if sub == "netadds":
            return (f"Spotify gains roughly {subs['premium_net_adds_millions'].dropna().iloc[-1]:.0f} million extra paying "
                    "subscribers a year, after subtracting those who cancelled.",
                    "Each bar is the growth in paying subscribers over the period.")
        return (f"Spotify has {a.loc[2025, 'mau_millions']} million users; {a.loc[2025, 'premium_subscribers_millions']} "
                f"million ({subs.loc[2025, 'premium_share_of_mau_pct']:.0f}%) pay for Premium.",
                "Lines show user counts at year-end. Some people use both free and Premium in a month, so the two "
                "groups add up to slightly more than total users.")
    if page == "arpu":
        if sub == "ads":
            return (f"Each free user earned Spotify only about ${subs.loc[2025, 'ad_revenue_per_ad_mau_annual_eur']:.2f} "
                    "a year from ads in 2025, and this is falling.",
                    "The line shows ad money divided by free users. Lower = each free user is worth less.")
        return (f"Each paying subscriber brings in about ${subs.loc[2025, 'premium_arpu_monthly_eur']:.2f} a month "
                "(after family, student and regional discounts).",
                "The line shows average money per paying subscriber per month. Up = Spotify earns more per person.")
    if page == "profitability":
        if sub == "opinc":
            return ("Spotify lost money in 2022 and 2023 and turned profitable in 2024. In 2025 it made "
                    f"${a.loc[2025, 'operating_income_eur_millions']:,.0f} million.",
                    "Green bars are profit, black bars are loss. The right chart shows costs shrinking as a share of revenue.")
        if sub == "pnl":
            return ("The full yearly numbers behind the profit charts.",
                    "Read across a row for one year. All money is in $ millions; % columns are shares of revenue.")
        return (f"Spotify now keeps {prof.loc[2025, 'gross_margin_calc_pct']:.0f} cents of every dollar after paying for "
                f"music, and {prof.loc[2025, 'operating_margin_calc_pct']:.0f} cents after all costs.",
                "Each line is a margin: the % of revenue kept. Higher lines = more profitable.")
    if page == "cac":
        return (f"Spotify spends roughly ${ue_years['cac_proxy_gross_adds_eur'].iloc[-1]:.0f} (realistic estimate) to "
                f"${ue_years['cac_proxy_net_adds_eur'].iloc[-1]:.0f} (simple estimate) on marketing for each new subscriber.",
                "These are estimates: Spotify does not publish this number. The realistic one is lower because it "
                "counts everyone Spotify had to win, including people replacing those who cancelled.")
    if page == "ltv":
        run, _ = runner_from(f)
        r = run()
        ratio = r[f"ltv_to_cac_{f['proxy']}"]
        if sub == "drivers":
            return ("Longer bars matter more. The top bar is the assumption that changes the result the most.",
                    "Green shows the result if that assumption goes down, black if it goes up. The middle line is today.")
        return (f"A subscriber is worth about ${r['ltv_eur']:.0f} in profit and costs about "
                f"${r[f'cac_proxy_{f['proxy']}_eur']:.0f} to win, so they pay back {ratio:.1f}x their cost "
                f"({'healthy' if ratio >= 3 else 'weak'}).",
                f"This assumes {f['churn']:.1f}% of subscribers cancel each month. Open the Assumptions page and move the sliders "
                "to see how the numbers change.")
    if page == "retention":
        c = f["churn"] / 100
        if sub == "gp":
            return ("Profit from a subscriber builds up every month they stay. The outlined cell shows when it has paid "
                    "back the cost of winning them.",
                    "Each row is a cancellation rate. Read left to right to see profit build up over time.")
        return (f"If {f['churn']:.1f}% cancel each month, about {(1 - c) ** 12 * 100:.0f}% of new subscribers are still "
                "paying after a year.",
                "Each row follows 1,000 new subscribers. Read left to right: greener cells = more people still paying.")
    if page == "montecarlo":
        if sub == "method":
            return ("Monte Carlo means running the same calculation thousands of times with randomly drawn inputs.",
                    "Each run picks a churn rate, price, margin, marketing spend and growth from the ranges you set, "
                    "then works out LTV, CAC and payback. The spread of results shows how sure we can be.")
        return ("Instead of betting on one churn rate, this runs thousands of possible futures and counts how often "
                "Spotify's subscribers are still worth more than 3x what they cost to win.",
                "Set how uncertain each input is on the left. The chart shows every simulated LTV:CAC; the dark line "
                "is the 3x 'healthy' mark. Bars to the right of it are good outcomes.")
    if page == "sensitivity":
        return ("Use this table to answer 'what if?' questions, e.g. what if fewer people cancel AND margins improve?",
                "Pick what to measure and what to compare in the dropdowns. Find your row (cancellation rate) and "
                "column. Greener = better.")
    if page == "assumptions":
        if sub == "how":
            return ("Here is exactly how the subscriber numbers are worked out, step by step, using your current assumptions.",
                    "Read top to bottom: each step uses the result of the steps above. The green number on the right is the result.")
        if sub == "fixed":
            return ("These choices are built into the data and cannot be changed with a slider, including how euros become dollars.",
                    "Read each row to see how that part of the data is handled and why.")
        return ("Every assumption the dashboard uses is on this page. Change one and every page updates.",
                "Each card explains what the assumption is, why it starts at its default, and which results it changes. "
                "The dark bar shows the results with your current settings.")
    if sub == "glossary":
        return ("Plain-English meanings of every term on this dashboard.", "Look up any word you're unsure about.")
    return (f"All numbers come from Spotify's official reports. {N_PASS} of {N_CHECKS} automatic checks passed.",
            "Use these tables if you want the exact figures behind the charts.")


# ----------------------------------------------------------------------------- assumptions page

DEFAULTS = {"year": "all", "base_year": int(ue_years.index[-1]), "churn": 3, "arpu": 0, "gm": 0, "sm": 0, "na": 0,
            "proxy": "gross_adds"}


def chosen_year(f):
    """The year picked in the header Year filter, or None for 'All years'."""
    return None if f.get("year", "all") == "all" else int(f["year"])


def a_id(name, where="page"):
    """Pattern id shared by every assumption control; `name@where` lets one assumption appear in two places."""
    return {"type": "a", "key": f"{name}@{where}"}


def assumption_card(title, control, what, default, effect):
    def line(label, text):
        return html.Div([html.Span(label, style={"fontWeight": 700, "color": BLACK}), " ", text],
                        style={"fontSize": "13.5px", "color": "#55595f", "lineHeight": 1.55, "marginTop": "8px"})
    return html.Div([
        html.Div(title, style={"fontSize": "16px", "fontWeight": 700, "color": BLACK, "marginBottom": "14px"}),
        control,
        html.Div([line("What it is:", what), line("Default & why:", default), line("What it changes:", effect)],
                 style={"marginTop": "14px", "paddingTop": "6px", "borderTop": f"1px solid {BORDER}"}),
    ], className="lift", style={**CARD, "padding": "22px 24px 20px"})


def view_assumptions(sub, f):
    base = usd_base(int(f["base_year"]))
    by = int(f["base_year"])
    if sub == "how":
        return [calc_steps(f)]
    if sub == "fixed":
        choices = pd.DataFrame([
            ("Currency", "Spotify reports in euros. Every amount here is in US dollars, converted at the European "
                         "Central Bank's average EUR→USD rate for that year or quarter (table below). Growth rates are "
                         "worked out in dollars, so they can differ slightly from Spotify's euro growth."),
            ("Revenue per subscriber", "Premium revenue ÷ the average of paying subscribers at the start and end of the "
                                       "year ÷ 12. An approximation: Spotify's own figure may differ."),
            ("Profit margin", "Spotify's company-wide gross margin is used for each subscriber; the Premium-only margin "
                              "is not in this data."),
            ("Marketing", "All sales & marketing spend is counted as the cost of winning paying subscribers. Some of it "
                          "really goes to free users and brand, so the cost to win is an upper estimate."),
            ("Cancellations (churn)", "Not published by Spotify. The default 3% a month is an assumption; the reports "
                                      "test 2%, 3%, 4% and 5%."),
            ("Subscriber value", "Not discounted for the time value of money, and inputs are held constant over the "
                                 "subscriber's lifetime."),
            ("Source data", f"Spotify Q4 2025 Shareholder Deck and 2025 Form 20-F, 2021-2025. {N_PASS} of {N_CHECKS} "
                            "automatic consistency checks pass."),
        ], columns=["Choice", "How it is handled"]).set_index("Choice")
        fx = FX[["period", "frequency", "usd_per_eur"]].rename(columns={
            "period": "Period", "frequency": "Type", "usd_per_eur": "US$ per €1"}).set_index("Period")
        return [row(panel("Fixed data choices (not adjustable)", table(choices))),
                row(panel("Exchange rates used (ECB average of period)", table(fx, "{:.4f}")),
                    panel("Why average rates?", html.Div(
                        "Revenue and costs are earned through the year, so each year's figures are converted at that "
                        "year's average rate, the usual way to translate an income statement. Quarterly figures use "
                        "each quarter's average, so four converted quarters do not add up exactly to the converted year.",
                        style={"fontSize": "14px", "color": "#55595f", "lineHeight": 1.6, "padding": "4px 8px"})))]

    def sld(name, lo, hi, step, marks, suffix=""):
        return dcc.Slider(id=a_id(name), min=lo, max=hi, step=step, value=f[name],
                          marks={m: f"{m:g}{suffix}" for m in marks}, tooltip={"placement": "bottom"})

    cards = [
        assumption_card("% of subscribers who cancel each month (churn)", sld("churn", 1, 8, 0.5, [1, 2, 3, 4, 5, 6, 7, 8], "%"),
                        "The share of paying subscribers who stop paying in a month. Also in the sidebar.",
                        "3%. Spotify does not publish this; 3% is a middle-of-the-road value for a subscription app, "
                        "and the reports also test 2%-5%.",
                        "How long a subscriber stays (1 ÷ churn), the value of a subscriber, and the realistic cost to win."),
        assumption_card("Price per subscriber change", sld("arpu", -20, 20, 1, [-20, -10, 0, 10, 20], "%"),
                        f"A change to the ${base['arpu']:.2f} a month each paying subscriber brought in during {by}.",
                        f"0% = Spotify's actual {by} figure.",
                        "Money and profit per subscriber, so the value of a subscriber."),
        assumption_card("Profit margin change (percentage points)", sld("gm", -5, 10, 0.5, [-5, 0, 5, 10], " pt"),
                        f"Points added to Spotify's {by} gross margin of {base['gross_margin'] * 100:.1f}% (money left after "
                        "music royalties and delivery).",
                        f"0 = the actual {by} margin.",
                        "Profit per subscriber, so the value of a subscriber and months to earn back cost."),
        assumption_card("Marketing spend change", sld("sm", -30, 50, 5, [-30, 0, 25, 50], "%"),
                        f"A change to the ${base['sm_expense']:,.0f} million Spotify spent on sales & marketing in {by}.",
                        f"0% = the actual {by} spend.",
                        "The cost to win one subscriber (both estimates)."),
        assumption_card("New subscribers change", sld("na", -50, 50, 5, [-50, -25, 0, 25, 50], "%"),
                        f"A change to the {base['net_adds']:.0f} million extra paying subscribers Spotify gained in {by}.",
                        f"0% = the actual {by} growth.",
                        "The cost to win one subscriber: fewer new subscribers for the same spend = higher cost each."),
        assumption_card("Cost-to-win estimate", dcc.RadioItems(
            id=a_id("proxy"), value=f["proxy"], labelStyle={"display": "block", "fontSize": "14px", "marginBottom": "6px"},
            options=[{"label": " Realistic: marketing ÷ everyone won (incl. replacing cancellations)", "value": "gross_adds"},
                     {"label": " Simple: marketing ÷ growth in subscribers only", "value": "net_adds"}]),
                        "Spotify does not publish what it costs to win a subscriber, so it is estimated two ways.",
                        "Realistic, because the cancellations assumed above must be replaced too.",
                        "Cost to win, value ÷ cost and months to earn back cost."),
        assumption_card("Base year for estimates", dcc.Dropdown(
            id=a_id("base_year"), value=f["base_year"], clearable=False, searchable=False,
            options=[{"label": str(y), "value": int(y)} for y in ue_years.index[::-1]]),
                        "Which year's actual Spotify numbers feed the subscriber value and cost estimates.",
                        f"{DEFAULTS['base_year']}, the latest year. 2023 is the earliest with marketing data.",
                        "Every subscriber-value, cost-to-win and retention figure."),
    ]
    reset = html.Button("↺  Reset all to defaults", id={"type": "reset", "key": "all"}, n_clicks=0, className="btn",
                        style={**FILTER_BTN, "backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "color": BLACK})
    return [
        html.Div([html.Div(id="assump-live", style={"flex": 1}), reset],
                 style={"display": "flex", "gap": "14px", "alignItems": "center", "flexWrap": "wrap", "marginBottom": "18px"}),
        html.Div(cards, style={"display": "grid", "gap": "18px", "gridTemplateColumns": "repeat(auto-fit, minmax(340px, 1fr))"}),
    ]


def calc_steps(f):
    """Step-by-step worked calculation of the subscriber-value results with the current assumptions."""
    run, base = runner_from(f)
    r = run()
    by = int(f["base_year"])
    churn = f["churn"] / 100
    arpu = r["monthly_arpu_eur"]
    gm = r["gross_margin_pct"] / 100
    na = base["net_adds"] * (1 + f["na"] / 100)
    avg_subs = base["avg_subs"] - base["net_adds"] / 2 + na / 2
    sm = base["sm_expense"] * (1 + f["sm"] / 100)
    proxy = f["proxy"]
    cac = r[f"cac_proxy_{proxy}_eur"]
    steps = [
        ("Money per paying subscriber, per month",
         f"Premium revenue ÷ average paying subscribers ÷ 12 in {by} = ${base['arpu']:.2f}; adjusted by your price change "
         f"of {f['arpu']:+.0f}%.", f"${base['arpu']:.2f} × (1 {f['arpu']:+.0f}%)", f"${arpu:.2f}"),
        ("Profit margin", f"Spotify's {by} gross margin {base['gross_margin'] * 100:.1f}% plus your change of {f['gm']:+.1f} points.",
         f"{base['gross_margin'] * 100:.1f}% {f['gm']:+.1f} pt", f"{gm * 100:.1f}%"),
        ("Profit per subscriber, per month", "Money per subscriber × profit margin.",
         f"${arpu:.2f} × {gm * 100:.1f}%", f"${r['monthly_gross_profit_per_sub_eur']:.2f}"),
        ("How long a subscriber stays", f"If {churn:.1%} cancel each month, the average subscriber stays 1 ÷ churn months.",
         f"1 ÷ {churn:.1%}", f"{r['expected_lifetime_months']:.1f} months"),
        ("Value of a subscriber (LTV)", "Profit per month × months they stay.",
         f"${r['monthly_gross_profit_per_sub_eur']:.2f} × {r['expected_lifetime_months']:.1f}", f"${r['ltv_eur']:.2f}"),
        ("Marketing spend", f"Spotify's {by} sales & marketing spend, adjusted by your change of {f['sm']:+.0f}%.",
         f"${base['sm_expense']:,.0f}M × (1 {f['sm']:+.0f}%)", f"${sm:,.0f}M"),
        ("Subscribers Spotify had to win", "Growth in subscribers plus everyone won to replace cancellations "
         "(average subscribers × churn × 12 months).",
         f"{na:.1f}M + {avg_subs:.1f}M × {churn:.1%} × 12", f"{r['implied_gross_adds_millions']:.1f}M"),
        ("Cost to win one subscriber (CAC)",
         "Realistic = marketing ÷ everyone won. Simple = marketing ÷ growth only. You are using: "
         + ("Realistic." if proxy == "gross_adds" else "Simple."),
         (f"${sm:,.0f}M ÷ {r['implied_gross_adds_millions']:.1f}M" if proxy == "gross_adds" else f"${sm:,.0f}M ÷ {na:.1f}M"),
         f"${cac:.2f}"),
        ("Value ÷ cost", "How many times a subscriber pays back what it cost to win them. 3x or more is healthy.",
         f"${r['ltv_eur']:.2f} ÷ ${cac:.2f}", f"{r[f'ltv_to_cac_{proxy}']:.1f}x"),
        ("Months to earn back the cost", "Cost to win ÷ profit per month. It should be shorter than how long they stay.",
         f"${cac:.2f} ÷ ${r['monthly_gross_profit_per_sub_eur']:.2f}", f"{r[f'payback_months_{proxy}']:.1f} months"),
    ]
    items = []
    for i, (title, text, formula, result) in enumerate(steps, 1):
        items.append(html.Div([
            html.Div(str(i), style={"width": "38px", "height": "38px", "borderRadius": "50%", "display": "flex",
                                    "alignItems": "center", "justifyContent": "center", "fontWeight": 800,
                                    "color": GREEN_DARK, "backgroundColor": "#e8f7ee", "flexShrink": 0}),
            html.Div([html.Div(title, style={"fontSize": "16px", "fontWeight": 700, "color": BLACK}),
                      html.Div(text, style={"fontSize": "13.5px", "color": "#5b6168", "lineHeight": 1.55, "marginTop": "4px"})],
                     style={"flex": "1 1 320px"}),
            html.Div(formula, style={"fontFamily": "Consolas, 'Courier New', monospace", "fontSize": "13.5px",
                                     "backgroundColor": "#f4f6f5", "border": f"1px solid {BORDER}", "borderRadius": "10px",
                                     "padding": "8px 12px", "color": "#2a2e35", "whiteSpace": "nowrap"}),
            html.Div(result, style={"fontSize": "20px", "fontWeight": 800, "color": GREEN_DARK, "minWidth": "120px",
                                    "textAlign": "right"}),
        ], style={"display": "flex", "alignItems": "center", "gap": "18px", "flexWrap": "wrap", "padding": "16px 20px",
                  "borderBottom": f"1px solid {BORDER}" if i < len(steps) else "none"}))
    return html.Div(items, style={**CARD, "padding": "6px 0"})


def live_results(f):
    run, _ = runner_from(f)
    r = run()
    proxy = f["proxy"]
    ratio = r[f"ltv_to_cac_{proxy}"]

    def chip(label, value):
        return html.Div([html.Div(label, style={"fontSize": "12px", "color": "#cfdad3"}),
                         html.Div(value, style={"fontSize": "20px", "fontWeight": 800, "color": "#ffffff"})])
    return html.Div([
        html.Div("Results with these assumptions", style={"fontSize": "13px", "fontWeight": 700, "color": GREEN,
                                                          "letterSpacing": "0.04em", "marginRight": "10px"}),
        chip("Value of a subscriber", f"${r['ltv_eur']:.2f}"),
        chip("Cost to win one", f"${r[f'cac_proxy_{proxy}_eur']:.2f}"),
        chip("Value ÷ cost", f"{ratio:.1f}x {'✓' if ratio >= 3 else '✗'}"),
        chip("Months to earn back", f"{r[f'payback_months_{proxy}']:.1f}"),
        chip("Average stay", f"{r['expected_lifetime_months']:.1f} mo"),
    ], style={"display": "flex", "gap": "34px", "alignItems": "center", "flexWrap": "wrap", "padding": "18px 26px",
              "borderRadius": "18px", "boxShadow": "0 12px 30px rgba(5,20,12,0.22)",
              "background": "linear-gradient(120deg, #050505 0%, #0a1d12 55%, #14532d 100%)"})


# Cards shown above each page when one year is picked: (label, frame, column, format, higher is better).
SNAPSHOT = {
    "revenue": [("Total revenue", "annual", "total_revenue_eur_millions", "b", True),
                ("Premium revenue", "annual", "premium_revenue_eur_millions", "b", True),
                ("Ad revenue", "annual", "ad_supported_revenue_eur_millions", "b", True),
                ("Revenue growth", "rev", "total_revenue_growth_pct", "pct", True),
                ("Share from Premium", "rev", "premium_mix_pct", "pct", None)],
    "subscribers": [("Premium subscribers", "annual", "premium_subscribers_millions", "users", True),
                    ("Monthly active users", "annual", "mau_millions", "users", True),
                    ("Free (ad) users", "annual", "ad_supported_mau_millions", "users", True),
                    ("New paying subscribers", "subs", "premium_net_adds_millions", "users", True),
                    ("Paying share of users", "subs", "premium_share_of_mau_pct", "pct", True)],
    "arpu": [("Per paying subscriber / month", "subs", "premium_arpu_monthly_eur", "usd2", True),
             ("Ad money per free user / year", "subs", "ad_revenue_per_ad_mau_annual_eur", "usd2", True),
             ("Revenue per user / year", "subs", "revenue_per_mau_annual_eur", "usd2", True)],
    "profitability": [("Gross margin", "prof", "gross_margin_calc_pct", "pct", True),
                      ("Operating income", "annual", "operating_income_eur_millions", "m", True),
                      ("Operating margin", "prof", "operating_margin_calc_pct", "pct", True),
                      ("Free cash flow", "annual", "free_cash_flow_eur_millions", "m", True),
                      ("Costs as % of revenue", "prof", "opex_ratio_pct", "pct", False)],
}
UE_SNAPSHOT = [("Value of a subscriber", "ltv_eur", "usd2", True),
               ("Cost to win one (realistic)", "cac_proxy_gross_adds_eur", "usd2", False),
               ("Value ÷ cost", "ltv_to_cac_gross_adds", "x", True),
               ("Months to earn back cost", "payback_months_gross_adds", "mo", False)]


def fmt_value(v, kind):
    return {"b": f"${v / 1000:.2f}B", "m": eur_m(v), "pct": f"{v:.1f}%", "users": f"{v:,.0f}M", "usd2": f"${v:,.2f}",
            "x": f"{v:.1f}x", "mo": f"{v:.1f} mo"}[kind]


def fmt_delta(d, kind):
    return {"b": eur_m(d, True), "m": eur_m(d, True), "pct": f"{d:+.1f}pp", "users": f"{d:+,.0f}M",
            "usd2": f"{'-' if d < 0 else '+'}${abs(d):,.2f}", "x": f"{d:+.1f}x", "mo": f"{d:+.1f} mo"}[kind]


def snapshot_card(label, frame, col, kind, better, year):
    v = frame[col].get(year)
    if v is None or pd.isna(v):
        return card(label, "n/a", "not reported this year")
    prev = frame[col].get(year - 1)
    if prev is None or pd.isna(prev):
        return card(label, fmt_value(v, kind), "first year in the data")
    d = v - prev
    return card(label, fmt_value(v, kind), f"{fmt_delta(d, kind)} vs {year - 1}",
                None if better is None else (d >= 0) == better)


def year_snapshot(page, year):
    """Key numbers for the chosen year, shown above the page's charts."""
    frames = {"annual": annual, "rev": rev, "subs": subs, "prof": prof}
    if page in SNAPSHOT:
        cards = [snapshot_card(label, frames[fr], col, kind, better, year) for label, fr, col, kind, better in SNAPSHOT[page]]
        sub = "Pills show the change from the year before."
    elif page in ("cac", "ltv", "retention", "sensitivity"):
        if year not in ue_years.index:
            return [callout("warn", f"No marketing data for {year}.", "Spotify only reports sales & marketing spend for "
                            f"{ue_years.index[0]}-{ue_years.index[-1]}, so subscriber value and cost to win start in "
                            f"{ue_years.index[0]}. The charts below use the base year set on the Assumptions page.")]
        cards = [snapshot_card(label, ue_years, col, kind, better, year) for label, col, kind, better in UE_SNAPSHOT]
        sub = "At the default 3% monthly cancellation rate. Charts below use your Assumptions settings."
    else:
        return []
    return [html.Div([
        html.Div(f"{year} at a glance", style={"fontSize": "16px", "fontWeight": 700, "color": BLACK}),
        html.Div(sub, style={"fontSize": "13px", "color": "#6b7079"}),
    ], style={"display": "flex", "alignItems": "baseline", "gap": "12px", "flexWrap": "wrap", "marginBottom": "10px"}),
        kpi_row(*cards)]


def highlight_year(node, year):
    """Shade the chosen year on every category-axis chart inside a view."""
    if isinstance(node, (list, tuple)):
        for child in node:
            highlight_year(child, year)
        return
    if isinstance(node, dcc.Graph):
        fig = node.figure
        if fig is None or not fig.data or fig.layout.xaxis.type != "category":
            return
        xs = [str(x) for x in (fig.data[0].x or [])]
        hits = [i for i, x in enumerate(xs) if str(year) in x]
        if hits:
            fig.add_vrect(x0=min(hits) - 0.5, x1=max(hits) + 0.5, fillcolor="rgba(29,185,84,0.13)", line_width=0,
                          layer="below")
        return
    children = getattr(node, "children", None)
    if children is not None and not isinstance(children, str):
        highlight_year(children, year)

# ----------------------------------------------------------------------------- Monte Carlo simulation

MC_DEFAULTS = {"churn": [2, 5], "arpu": 10, "gm": 2, "sm": 20, "na": 25, "runs": 10000}
MC_SEED = 42  # fixed seed: the same settings always give the same answer


def mc_control(title, control, help_text):
    control.persistence, control.persistence_type = True, "memory"  # keep settings when the page re-renders
    return html.Div([
        html.Div(title, style={"fontSize": "14px", "fontWeight": 700, "color": BLACK}),
        html.Div(help_text, style={**NOTE, "margin": "2px 0 4px"}),
        html.Div(control, style={"margin": "0 -14px"}),
    ], style={"marginBottom": "18px"})


def mc_simulate(f, churn_range, arpu_pct, gm_pp, sm_pct, na_pct, runs):
    """Vectorised Monte Carlo of the subscriber unit economics.

    Every input is drawn from a triangular distribution: the base-year value (or the middle of the churn range)
    is the most likely, the edges of the range are the least likely."""
    rng = np.random.default_rng(MC_SEED)
    base = usd_base(int(f["base_year"]))
    lo, hi = sorted(churn_range)
    hi = hi if hi > lo else lo + 0.01
    churn = rng.triangular(lo, (lo + hi) / 2, hi, runs) / 100

    def spread(width):
        return rng.triangular(-width, 0, width, runs) if width > 0 else np.zeros(runs)

    arpu = base["arpu"] * (1 + spread(arpu_pct / 100))
    gm = base["gross_margin"] + spread(gm_pp / 100)
    sm = base["sm_expense"] * (1 + spread(sm_pct / 100))
    net_adds = base["net_adds"] * (1 + spread(na_pct / 100))
    avg_subs = base["avg_subs"] - base["net_adds"] / 2 + net_adds / 2

    monthly_gp = arpu * gm
    ltv = monthly_gp / churn
    cac = sm / (net_adds + avg_subs * churn * 12) if f["proxy"] == "gross_adds" else sm / net_adds
    return pd.DataFrame({"Monthly churn %": churn * 100, "ARPU $": arpu, "Gross margin %": gm * 100,
                         "S&M $M": sm, "Net adds M": net_adds,
                         "ltv": ltv, "cac": cac, "ratio": ltv / cac, "payback": cac / monthly_gp})


def mc_results(f, churn_range, arpu_pct, gm_pp, sm_pct, na_pct, runs):
    sim = mc_simulate(f, churn_range, arpu_pct, gm_pp, sm_pct, na_pct, int(runs))
    ratio = sim["ratio"]
    p_ok = (ratio >= 3).mean() * 100
    p10, p50, p90 = np.percentile(ratio, [10, 50, 90])
    payback_ok = (sim["payback"] < 1 / (sim["Monthly churn %"] / 100)).mean() * 100

    cards = kpi_row(
        card("Chance LTV:CAC ≥ 3x", f"{p_ok:.0f}%", "healthy in most futures" if p_ok >= 70 else
             "risky: often below 3x", p_ok >= 70),
        card("Typical LTV:CAC (P50)", f"{p50:.1f}x", f"range {p10:.1f}x – {p90:.1f}x (P10–P90)"),
        card("Typical LTV (P50)", f"${sim['ltv'].median():,.2f}", "profit per subscriber"),
        card("Typical CAC (P50)", f"${sim['cac'].median():,.2f}", "realistic proxy" if f["proxy"] == "gross_adds"
             else "simple proxy"),
        card("Cost earned back in time", f"{payback_ok:.0f}%", "of simulations: payback < average stay",
             payback_ok >= 70),
    )
    cards.style = {**cards.style, "gridTemplateColumns": "repeat(auto-fit, minmax(128px, 1fr))", "gap": "12px"}

    # Histogram of LTV:CAC, binned with numpy so the chart carries 60 bars rather than every simulated value.
    # Bins below 3x are grey, 3x and above use the accent colour.
    top = float(np.percentile(ratio, 99.5))
    counts, edges = np.histogram(ratio.clip(upper=top), bins=60, range=(0, top))
    mids = (edges[:-1] + edges[1:]) / 2
    hist = go.Figure()
    for mask, color, label in ((mids < 3, GREY, "Below 3x"), (mids >= 3, GREEN, "3x or better")):
        hist.add_trace(go.Bar(x=mids[mask], y=counts[mask], width=(edges[1] - edges[0]) * 0.92, marker_color=color,
                              name=label, customdata=np.c_[edges[:-1][mask], edges[1:][mask]],
                              hovertemplate="LTV:CAC %{customdata[0]:.2f}x – %{customdata[1]:.2f}x"
                                            "<br>%{y:,} simulations<extra></extra>"))
    style(hist, f"LTV:CAC across {int(runs):,} simulated futures", "Number of simulations", height=400)
    hist.update_layout(barmode="overlay", hovermode="closest",
                       legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0), margin=dict(b=80))
    hist.update_xaxes(type="linear", title="LTV:CAC (x)", range=[0, top], ticksuffix="x")
    hist.add_vline(x=3, line_width=2, line_color=BLACK, annotation_text="3x healthy", annotation_position="top left")
    for v, lab in ((p10, "P10"), (p50, "P50"), (p90, "P90")):
        hist.add_vline(x=v, line_width=1, line_dash="dot", line_color=INK_2, annotation_text=lab,
                       annotation_position="top right", annotation_font_size=11)

    # Which uncertain input moves LTV:CAC most (rank correlation, -1 to 1).
    inputs = ["Monthly churn %", "ARPU $", "Gross margin %", "S&M $M", "Net adds M"]
    ranks = sim[inputs + ["ratio"]].rank()
    with np.errstate(invalid="ignore", divide="ignore"):  # an input with zero uncertainty has no correlation
        corr = ranks[inputs].corrwith(ranks["ratio"]).fillna(0).sort_values(key=abs)
    drivers = go.Figure(go.Bar(x=corr.values, y=corr.index, orientation="h",
                               marker_color=[GREEN if v >= 0 else BLACK for v in corr.values],
                               text=[f"{v:+.2f}" for v in corr.values], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x:+.2f}<extra></extra>"))
    style(drivers, "What drives the risk most?", height=400, legend=False)
    drivers.update_layout(hovermode="closest")
    drivers.update_xaxes(type="linear", range=[-1.15, 1.15], title="Effect on LTV:CAC (rank correlation)",
                         zeroline=True, zerolinecolor=INK_2)
    drivers.update_yaxes(type="category", showgrid=False)

    pct = pd.DataFrame({
        "Metric": ["LTV:CAC (x)", "LTV ($)", "CAC ($)", "Payback (months)"],
        "P10 (pessimistic)": [p10, *np.percentile(sim["ltv"], [10]), *np.percentile(sim["cac"], [90]),
                              *np.percentile(sim["payback"], [90])],
        "P50 (typical)": [p50, sim["ltv"].median(), sim["cac"].median(), sim["payback"].median()],
        "P90 (optimistic)": [p90, *np.percentile(sim["ltv"], [90]), *np.percentile(sim["cac"], [10]),
                             *np.percentile(sim["payback"], [10])],
        "Mean": [ratio.mean(), sim["ltv"].mean(), sim["cac"].mean(), sim["payback"].mean()],
    }).set_index("Metric")
    return [
        cards,
        row(graph(hist, "Each bar counts how many simulated futures landed on that LTV:CAC. Dotted lines mark the "
                        "pessimistic (P10), typical (P50) and optimistic (P90) results."),
            graph(drivers, "Longer bar = that input matters more. Positive means a higher input raises LTV:CAC; "
                           "negative means it lowers it.")),
        row(panel("Pessimistic / typical / optimistic results", table(pct)),
            callout("info", "How to read P10 / P50 / P90.", "P10 is a bad-case result: only 10% of simulations were "
                    "worse. P50 is the middle result. P90 is a good case: only 10% did better. For CAC and payback, "
                    "lower is better, so their pessimistic column shows the high values.")),
    ]


def view_montecarlo(sub, f):
    if sub == "method":
        steps = pd.DataFrame({
            "Step": ["1. Draw inputs", "2. Calculate", "3. Repeat", "4. Summarise"],
            "What happens": [
                "Pick a random monthly churn, ARPU, gross margin, S&M spend and net adds from the ranges you set. "
                "Values near the base year (or the middle of the churn range) are most likely (triangular distribution).",
                "LTV = ARPU × gross margin ÷ churn. CAC = S&M ÷ subscribers won. Payback = CAC ÷ monthly gross profit.",
                "Do this thousands of times (you choose how many). A fixed random seed means the same settings "
                "always give the same answer.",
                "Count how often LTV:CAC is 3x or better, and report the P10 / P50 / P90 of every metric."],
        }).set_index("Step")
        base = usd_base(int(f["base_year"]))
        start = pd.DataFrame({
            "Input": ["Monthly ARPU", "Gross margin", "S&M spend", "Premium net adds", "Average subscribers"],
            f"Base year {f['base_year']}": [f"${base['arpu']:.2f}", f"{base['gross_margin'] * 100:.1f}%",
                                            f"${base['sm_expense']:,.0f}M", f"{base['net_adds']:.1f}M",
                                            f"{base['avg_subs']:.1f}M"],
        }).set_index("Input")
        return [row(panel("How the simulation works", table(steps))),
                row(panel("Starting values (change the base year on the Model Assumptions page)", table(start)),
                    callout("warn", "Still a model.", DISCLAIMER + " The simulation shows how uncertain the answer "
                            "is; it does not make the inputs more accurate."))]

    controls = html.Div([
        html.Div("Uncertainty ranges", style={"fontSize": "16px", "fontWeight": 700, "color": BLACK, "marginBottom": "14px"}),
        mc_control("Monthly churn range", dcc.RangeSlider(
            id="mc-churn", min=1, max=8, step=0.25, value=MC_DEFAULTS["churn"], marks={m: f"{m}%" for m in (1, 2, 4, 6, 8)},
            tooltip={"placement": "bottom"}), "Spotify does not publish churn, so it is drawn between these two values."),
        mc_control("ARPU uncertainty (±%)", slider("mc-arpu", 0, 30, 1, MC_DEFAULTS["arpu"], [0, 10, 20, 30], "%"),
                   "How far price per subscriber could move from the base year."),
        mc_control("Gross margin uncertainty (± points)", slider("mc-gm", 0, 5, 0.5, MC_DEFAULTS["gm"], [0, 1, 2, 3, 4, 5], "pp"),
                   "Royalty and delivery costs could shift the margin."),
        mc_control("Marketing spend uncertainty (±%)", slider("mc-sm", 0, 50, 5, MC_DEFAULTS["sm"], [0, 25, 50], "%"),
                   "Sales & marketing spend drives CAC."),
        mc_control("Net adds uncertainty (±%)", slider("mc-na", 0, 50, 5, MC_DEFAULTS["na"], [0, 25, 50], "%"),
                   "How many more subscribers Spotify wins in a year."),
        html.Div([
            html.Div("Number of simulations", style={"fontSize": "14px", "fontWeight": 700, "color": BLACK,
                                                     "marginBottom": "6px"}),
            dcc.Dropdown(id="mc-runs", value=MC_DEFAULTS["runs"], clearable=False, searchable=False,
                         options=[{"label": f"{n:,}", "value": n} for n in (1000, 5000, 10000, 25000, 50000)],
                         persistence=True, persistence_type="memory"),
        ]),
        html.Div(f"Uses base year {f['base_year']} and the "
                 f"{'realistic' if f['proxy'] == 'gross_adds' else 'simple'} CAC proxy from Model Assumptions.",
                 style={**NOTE, "marginTop": "14px"}),
    ], style={**CARD, "padding": "20px 22px", "flex": "0 0 330px", "alignSelf": "flex-start", "boxSizing": "border-box"})
    out = dcc.Loading(html.Div(id="mc-out"), type="dot", color=GREEN)
    return [html.Div([controls, html.Div(out, style={"flex": "1 1 600px", "minWidth": 0})],
                     style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "alignItems": "flex-start"})]


def render_view(page, sub, f):
    if page == "assumptions":
        return view_assumptions(sub, f)
    if page == "dashboard":
        return view_dashboard(chosen_year(f) or YEARS[-1])
    if page == "revenue":
        return view_revenue(sub)
    if page == "subscribers":
        return view_subscribers(sub)
    if page == "arpu":
        return view_arpu(sub)
    if page == "profitability":
        return view_profitability(sub)
    if page == "cac":
        return view_cac()
    if page == "ltv":
        return view_ltv(sub, f)
    if page == "retention":
        return view_retention(sub)
    if page == "sensitivity":
        return view_sensitivity()
    if page == "montecarlo":
        return view_montecarlo(sub, f)
    return view_data(sub, chosen_year(f))

# ----------------------------------------------------------------------------- heat-table builders


def retention_table(value, mode, start, period, f):
    run, _ = runner_from(f)
    step, n, prefix = {"month": (1, 12, "M"), "quarter": (3, 8, "Q"), "year": (12, 5, "Y")}[period]
    churns = np.round(np.arange(0.01, 0.0601, 0.005), 4)
    months = np.arange(1, n + 1) * step
    selected = f["churn"] / 100
    rows, values, lifetimes, cacs, marks = [], [], [], [], []
    for c in churns:
        r = run(churn=c)
        surv = (1 - c) ** months
        if value == "gp":
            # cumulative gross profit per original subscriber after m months
            vals = r["monthly_gross_profit_per_sub_eur"] * (1 - (1 - c) ** months) / c
            covered = vals >= r[f"cac_proxy_{f['proxy']}_eur"]
            first = int(np.argmax(covered)) if covered.any() else -1
            marks.append([j == first for j in range(len(vals))])
        else:
            if start == "prev":
                prev_surv = (1 - c) ** (months - step)
                base = surv / prev_surv
            else:
                base = surv
            vals = base if mode == "retained" else 1 - base
            vals = vals * (100 if value == "pct" else 1000)
        rows.append(f"{c:.1%} cancel / mo")
        values.append(vals)
        lifetimes.append(f"{1 / c:.0f} mo")
        cacs.append(f"${r[f'cac_proxy_{f['proxy']}_eur']:.2f}")
    highlight = int(np.argmin(np.abs(churns - selected)))
    if value == "gp":
        fixed = [("Cancel rate", rows), ("Avg stay", lifetimes), ("Cost to win", cacs)]
        return heat_table(rows, fixed, [f"{prefix}{i}" for i in range(1, n + 1)], values, lambda v: f"${v:,.2f}",
                          True, highlight, marks)
    fmt = (lambda v: f"{v:.1f}%") if value == "pct" else (lambda v: f"{v:,.0f}")
    fixed = [("Cancel rate", rows), ("Start", ["1,000"] * len(rows)), ("Avg stay", lifetimes)]
    return heat_table(rows, fixed, [f"{prefix}{i}" for i in range(1, n + 1)], values, fmt, mode == "retained", highlight)


def sensitivity_table(metric, cols, f):
    run, base = runner_from(f)
    churns = np.round(np.arange(0.015, 0.0601, 0.005), 4)
    if cols == "gm":
        steps = np.arange(-4, 9, 2)
        labels = [f"{base['gross_margin'] * 100 + f['gm'] + s:.0f}%" for s in steps]
        kw = [{"gm_pp": f["gm"] + s} for s in steps]
    elif cols == "arpu":
        steps = np.arange(-20, 21, 5)
        labels = [f"{s:+d}%" for s in steps]
        kw = [{"arpu_chg": f["arpu"] / 100 + s / 100} for s in steps]
    elif cols == "sm":
        steps = np.arange(-30, 51, 10)
        labels = [f"{s:+d}%" for s in steps]
        kw = [{"sm_chg": f["sm"] / 100 + s / 100} for s in steps]
    else:
        steps = np.arange(-50, 51, 25)
        labels = [f"{s:+d}%" for s in steps]
        kw = [{"na_chg": f["na"] / 100 + s / 100} for s in steps]
    values = [[run(churn=c, **k)[metric] for k in kw] for c in churns]
    fmt = {"ltv_eur": lambda v: f"${v:,.0f}", "payback_months_gross_adds": lambda v: f"{v:.1f}"}.get(metric, lambda v: f"{v:.2f}x")
    rows = [f"{c:.1%}" for c in churns]
    highlight = int(np.argmin(np.abs(churns - f["churn"] / 100)))
    fixed = [("Cancel rate / mo", rows), ("Avg stay", [f"{1 / c:.0f} mo" for c in churns])]
    return heat_table(rows, fixed, labels, values, fmt, metric != "payback_months_gross_adds", highlight)

# ----------------------------------------------------------------------------- layout

# Line icons (Lucide-style paths, 24x24) rendered as inline SVG images.
ICON_PATHS = {
    "dashboard": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
                 '<rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    "revenue": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "subscribers": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                   '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "arpu": '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>'
            '<path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    "profitability": '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/>'
                     '<line x1="6" y1="20" x2="6" y2="16"/>',
    "cac": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "ltv": '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2'
           'A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    "retention": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    "montecarlo": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8.5" cy="8.5" r="1.2"/>'
                  '<circle cx="15.5" cy="15.5" r="1.2"/><circle cx="15.5" cy="8.5" r="1.2"/><circle cx="8.5" cy="15.5" r="1.2"/>'
                  '<circle cx="12" cy="12" r="1.2"/>',
    "sensitivity": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/>'
                   '<line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
                   '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>',
    "assumptions": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6'
                   'a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 14l2 2 4-4"/>',
    "data": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/>'
                '<line x1="12" y1="15" x2="12" y2="3"/>',
    "filter": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "spark": '<path d="M12 3l1.9 5.8L20 10l-6.1 1.9L12 18l-1.9-6.1L4 10l6.1-1.2Z"/>',
}


def icon(name, color="#c9d3cc", size=20):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICON_PATHS[name]}</svg>')
    return html.Img(src="data:image/svg+xml;utf8," + quote(svg), style={"width": f"{size}px", "height": f"{size}px",
                                                                        "flexShrink": 0, "display": "block"})


def nav_item(page):
    return html.Div([icon(page), html.Span(PAGES[page][0])], id={"type": "nav", "page": page}, n_clicks=0,
                    className="nav-item", style=NAV_ITEM)


def nav_style(page, active):
    return {**NAV_ITEM, **ACTIVE} if page == active else NAV_ITEM


def slider(id_, lo, hi, step, value, marks, suffix):
    return dcc.Slider(id=id_, min=lo, max=hi, step=step, value=value,
                      marks={m: f"{m:g}{suffix}" for m in marks}, tooltip={"placement": "bottom"})


def filter_field(label, control, width="220px"):
    return html.Div([html.Div(label, style=LABEL), control], style={"width": width})


GLASS = {"backgroundColor": "rgba(255,255,255,0.04)", "border": "1px solid rgba(255,255,255,0.08)", "borderRadius": "16px"}

sidebar = html.Div([
    html.Div([
        html.Div(icon("revenue", "#ffffff", 20), style={
            "width": "40px", "height": "40px", "borderRadius": "12px", "display": "flex", "alignItems": "center",
            "justifyContent": "center", "background": f"linear-gradient(135deg, {GREEN} 0%, {GREEN_DARK} 100%)",
            "boxShadow": "0 8px 24px rgba(29,185,84,0.45)"}),
        html.Div([html.Div("Spotify", style={"fontWeight": 800, "fontSize": "22px", "lineHeight": 1.05,
                                             "letterSpacing": "-0.02em"}),
                  html.Div("Financial Analysis", style={"fontSize": "11.5px", "fontWeight": 500, "color": "#8fa397",
                                                        "marginTop": "2px"})]),
    ], style={"padding": "26px 24px 14px", "display": "flex", "alignItems": "center", "gap": "12px", "color": "#ffffff"}),
    html.Div([
        html.Div("UNIT ECONOMICS", className="ue-badge", style={
            "fontSize": "15px", "fontWeight": 800, "letterSpacing": "0.14em", "color": "#04110a"}),
        html.Div("LTV · CAC · ARPU · Churn · Payback", style={
            "fontSize": "11px", "fontWeight": 600, "color": "#0b3a1d", "marginTop": "3px", "letterSpacing": "0.02em"}),
    ], style={"margin": "0 18px 18px", "padding": "11px 14px", "borderRadius": "12px", "textAlign": "center",
              "background": f"linear-gradient(120deg, {GREEN} 0%, #7ee2a8 100%)",
              "boxShadow": "0 8px 26px rgba(29,185,84,0.40), inset 0 1px 0 rgba(255,255,255,0.35)"}),
    *[nav_item(p) for p in NAV_ORDER],
    html.Div([
        html.Div("Churn Scenario", style={"fontWeight": 700, "fontSize": "15px", "color": "#ffffff"}),
        html.Div("Adjust the monthly churn rate. LTV, CAC payback and LTV:CAC update live.",
                 style={"fontSize": "12.5px", "color": "#a9b4ad", "lineHeight": 1.5, "margin": "6px 0 14px"}),
        html.Div([html.Span("Monthly churn", style={"color": "#d6ded9"}),
                  html.Span(id="churn-readout", style={"color": "#ffffff", "fontWeight": 700})],
                 style={"display": "flex", "justifyContent": "space-between", "fontSize": "13px"}),
        html.Div(dcc.Slider(id=a_id("churn", "side"), min=1, max=8, step=0.5, value=DEFAULTS["churn"], marks=None,
                            tooltip={"placement": "bottom"}), className="dark-slider", style={"margin": "6px -14px 4px"}),
        html.Div(id="quick-ratio", style={"marginTop": "6px"}),
    ], style={**GLASS, "margin": "26px 16px 0", "padding": "18px 18px 16px"}),
    html.Div([
        html.Span("●", style={"color": GREEN, "marginRight": "8px"}),
        f"{N_PASS}/{N_CHECKS} data checks passed · Q4 2025",
    ], style={"fontSize": "12px", "color": "#a9b4ad", "margin": "16px 24px 0"}),
], id="sidebar", style=SIDEBAR)

ROUND_BTN = {"width": "44px", "height": "44px", "borderRadius": "50%", "border": "1px solid rgba(255,255,255,0.18)",
             "backgroundColor": "rgba(255,255,255,0.04)", "color": "#ffffff", "display": "flex", "alignItems": "center",
             "justifyContent": "center", "cursor": "pointer", "fontSize": "16px", "fontWeight": 700,
             "textDecoration": "none", "padding": 0}
SEG = {"border": "none", "borderRadius": "999px", "padding": "9px 18px", "fontSize": "14px", "fontWeight": 600,
       "cursor": "pointer", "backgroundColor": "transparent", "color": "#c9d3cc", "fontFamily": FONT}
SEG_ON = {**SEG, "background": f"linear-gradient(135deg, {GREEN} 0%, {GREEN_DARK} 100%)", "color": "#ffffff",
          "boxShadow": "0 4px 14px rgba(29,185,84,0.4)"}

topbar = html.Div([
    html.Div([
        html.Button("☰", id="burger", n_clicks=0, className="btn", style={**ROUND_BTN, "fontSize": "18px"}),
        html.Div(id="page-title", style={"fontSize": "30px", "fontWeight": 700, "color": "#ffffff",
                                         "letterSpacing": "-0.02em"}),
    ], style={"display": "flex", "alignItems": "center", "gap": "18px"}),
    html.Div([
        html.Span(f"{annual['premium_subscribers_millions'].iloc[-1]}M subscribers · FY2021-FY2025", style={
            "fontSize": "14px", "color": "#d6ded9", "border": "1px solid rgba(255,255,255,0.18)", "borderRadius": "999px",
            "padding": "11px 18px", "backgroundColor": "rgba(255,255,255,0.03)"}),
        html.Div([html.Button("Simple", id="mode-simple", n_clicks=0, style=SEG_ON),
                  html.Button("Detailed", id="mode-detailed", n_clicks=0, style=SEG)],
                 title="Simple shows a plain-English summary on every page; Detailed hides it.",
                 style={"display": "flex", "padding": "4px", "borderRadius": "999px",
                        "border": "1px solid rgba(255,255,255,0.18)", "backgroundColor": "rgba(255,255,255,0.03)"}),
        dcc.Link("?", href="/data", title="Glossary: what every term means", className="btn", style=ROUND_BTN),
        html.Button(icon("download", "#ffffff", 18), id="dl-btn", n_clicks=0, className="btn",
                    title="Download this page's data (CSV)", style=ROUND_BTN),
    ], style={"display": "flex", "alignItems": "center", "gap": "12px"}),
], style=TOPBAR)

chip_box = html.Div([
    html.Span("USD $", style={"fontWeight": 700, "color": GREEN_DARK}),
    html.Span(style={"width": "1px", "height": "14px", "backgroundColor": BORDER}),
    html.Span("Year", style={"color": "#6b7079"}),
    dcc.Dropdown(id=a_id("year", "top"), value=DEFAULTS["year"], clearable=False, searchable=False, className="year-filter",
                 options=[{"label": "All years (2021–2025)", "value": "all"}]
                 + [{"label": str(y), "value": y} for y in YEARS[::-1]],
                 style={"width": "170px", "fontSize": "12px"}),
], style={"display": "flex", "alignItems": "center", "gap": "10px", "fontSize": "12px", "color": INK,
          "whiteSpace": "nowrap", "backgroundColor": "#ffffff", "border": f"1px solid {BORDER}", "borderRadius": "8px",
          "padding": "4px 12px", "boxShadow": "0 1px 2px rgba(16,24,40,0.05)"})

app = Dash(__name__, title="Spotify Unit Economics", suppress_callback_exceptions=True)
app.index_string = app.index_string.replace("{%css%}", "{%css%}<style>" + CSS + "</style>")
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="page", data="dashboard"),
    dcc.Store(id="mode", data="simple"),
    dcc.Store(id="assump", data=DEFAULTS),
    dcc.Download(id="download"),
    sidebar,
    html.Div([
        topbar,
        html.Div([
            html.Div([
                dcc.Tabs(id="subtab", value="overview", children=[], style={"height": "auto"},
                         parent_style={"flex": 1, "minWidth": 0}),
                chip_box,
            ], style={"display": "flex", "alignItems": "center", "gap": "12px", "borderBottom": f"1px solid {BORDER}",
                      "marginBottom": "12px"}),
            dcc.Loading(html.Div(id="view"), type="dot", color=GREEN),
            html.Div(f"Source: Spotify Q4 2025 Shareholder Deck & Form 20-F · {N_PASS}/{N_CHECKS} validation checks passed",
                     style={**NOTE, "marginTop": "10px"}),
        ], style={"padding": "6px 40px 32px", "maxWidth": "1480px"}),
    ], style={"flex": 1, "minWidth": 0}),
], style=PAGE)

ASSUMP = Input("assump", "data")

# ----------------------------------------------------------------------------- callbacks


@app.callback(Output("page", "data"), Output({"type": "nav", "page": ALL}, "style"), Output("url", "pathname"),
              Input({"type": "nav", "page": ALL}, "n_clicks"), Input("url", "pathname"), State("page", "data"))
def navigate(_, path, current):
    """Sidebar clicks and the URL path (e.g. /retention) both select the page; the URL mirrors the selection."""
    if isinstance(ctx.triggered_id, dict):
        page = ctx.triggered_id["page"]
    else:
        page = (path or "").strip("/") or current
        page = page if page in PAGES else "dashboard"
    return page, [nav_style(p, page) for p in NAV_ORDER], f"/{page}"


@app.callback(Output("page-title", "children"), Output("subtab", "children"), Output("subtab", "value"),
              Input("page", "data"))
def set_page(page):
    _, title, _, subtabs, _ = PAGES[page]
    tabs = [dcc.Tab(label=label, value=value, style=SUBTAB, selected_style=SUBTAB_ON) for value, label in subtabs]
    return title, tabs, subtabs[0][0]


@app.callback(Output("mode", "data"), Output("mode-simple", "style"), Output("mode-detailed", "style"),
              Input("mode-simple", "n_clicks"), Input("mode-detailed", "n_clicks"), State("mode", "data"))
def set_mode(_s, _d, current):
    mode = {"mode-simple": "simple", "mode-detailed": "detailed"}.get(ctx.triggered_id, current)
    return mode, (SEG_ON if mode == "simple" else SEG), (SEG_ON if mode == "detailed" else SEG)


@app.callback(Output("view", "children"), Input("page", "data"), Input("subtab", "value"), Input("mode", "data"),
              ASSUMP)
def show_view(page, sub, mode, f):
    valid = [v for v, _ in PAGES[page][3]]
    sub = sub if sub in valid else valid[0]
    if page == "assumptions" and sub == "set" and ctx.triggered_id == "assump":
        raise PreventUpdate  # keep the sliders in place while dragging; assump-live updates instead
    body = render_view(page, sub, f)
    year = chosen_year(f)
    if year is not None and page not in ("dashboard", "assumptions"):
        highlight_year(body, year)
        if page != "data":
            body = year_snapshot(page, year) + body
    if page == "dashboard" or mode == "detailed":
        return body
    return [explain(*guide(page, sub, f))] + body


@app.callback(Output("churn-readout", "children"), Output("quick-ratio", "children"), ASSUMP)
def quick_what_if(f):
    run, _ = runner_from(f)
    r = run()
    ratio = r[f"ltv_to_cac_{f['proxy']}"]
    good = ratio >= 3
    return f"{f['churn']:.1f}%", html.Div([
        html.Div([html.Span("LTV"), html.B(f"${r['ltv_eur']:.0f}")],
                 style={"display": "flex", "justifyContent": "space-between"}),
        html.Div([html.Span("LTV:CAC"), html.B(f"{ratio:.1f}x")],
                 style={"display": "flex", "justifyContent": "space-between", "marginTop": "4px"}),
        html.Div("Healthy (3x or more)" if good else "Weak (below 3x)", style={
            "marginTop": "10px", "textAlign": "center", "borderRadius": "999px", "padding": "6px 0", "fontWeight": 700,
            "fontSize": "12.5px", "color": "#04110a" if good else "#ffffff",
            "background": f"linear-gradient(90deg, {GREEN}, #7ee2a8)" if good else "linear-gradient(90deg, #3a3a3a, #555)"}),
    ], style={"fontSize": "13px", "color": "#d6ded9"})


@app.callback(Output("rt-body", "children"), Input("rt-value", "value"), Input("rt-mode", "value"),
              Input("rt-start", "value"), Input("rt-period", "value"), ASSUMP)
def update_retention(value, mode, start, period, f):
    return retention_table(value, mode, start, period, f)


@app.callback(Output("sg-body", "children"), Input("sg-metric", "value"), Input("sg-cols", "value"), ASSUMP)
def update_sensitivity(metric, cols, f):
    return sensitivity_table(metric, cols, f)


@app.callback(Output("assump-live", "children"), ASSUMP)
def update_live(f):
    return live_results(f)


@app.callback(Output("assump", "data"), Output({"type": "a", "key": ALL}, "value"),
              Input({"type": "a", "key": ALL}, "value"), Input({"type": "reset", "key": ALL}, "n_clicks"),
              State("assump", "data"))
def sync_assumptions(values, _resets, store):
    """One store holds every assumption; all controls (sidebar + Assumptions page) read from and write to it."""
    store = {**DEFAULTS, **(store or {})}
    keys = [item["id"]["key"] for item in ctx.inputs_list[0]]
    trig = ctx.triggered_id
    if isinstance(trig, dict) and trig.get("type") == "reset":
        store = dict(DEFAULTS)
    elif isinstance(trig, dict) and trig.get("type") == "a":
        value = values[keys.index(trig["key"])]
        if value is not None:
            store[trig["key"].split("@")[0]] = value
    return store, [store[k.split("@")[0]] for k in keys]


@app.callback(Output("sidebar", "style"), Input("burger", "n_clicks"))
def toggle_sidebar(n):
    return {**SIDEBAR, "display": "none"} if n and n % 2 else SIDEBAR


@app.callback(Output("mc-out", "children"), Input("mc-churn", "value"), Input("mc-arpu", "value"),
              Input("mc-gm", "value"), Input("mc-sm", "value"), Input("mc-na", "value"), Input("mc-runs", "value"), ASSUMP)
def update_montecarlo(churn_range, arpu_pct, gm_pp, sm_pct, na_pct, runs, f):
    return mc_results(f, churn_range, arpu_pct, gm_pp, sm_pct, na_pct, runs)


@app.callback(Output("download", "data"), Input("dl-btn", "n_clicks"), State("page", "data"), prevent_initial_call=True)
def download(_, page):
    key = PAGES[page][4]
    df = FX if key == "fx" else D[key]
    return dcc.send_data_frame(df.to_csv, f"spotify_{page}_usd.csv", index=False)


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
