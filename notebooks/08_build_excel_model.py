"""Phase 9 - Build the formula-driven Excel financial model.

Every analysis cell is a live Excel formula that traces back to Raw_Data. Inputs (blue text on yellow) on
LTV_Model and Scenario_Analysis drive all outputs, so the model recalculates when an assumption changes.
"""

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from common import BASE_CHURN, BASE_YEAR, CHURN_SCENARIOS, MODELS, load_annual, load_quarterly

OUT = MODELS / "Spotify_Unit_Economics_Model.xlsx"

YEARS = list(range(2021, 2026))
YCOLS = [get_column_letter(2 + i) for i in range(len(YEARS))]  # B..F
RAW_FIRST_ROW = 4  # Raw_Data annual rows 4..8

HEADER_FILL = PatternFill("solid", fgColor="1F2937")
SECTION_FILL = PatternFill("solid", fgColor="E5E7EB")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
OUTPUT_FILL = PatternFill("solid", fgColor="E2F0D9")
WHITE_BOLD = Font(bold=True, color="FFFFFF")
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
NOTE = Font(italic=True, size=9, color="52514E")
INPUT_FONT = Font(color="0000FF", bold=True)
THIN = Side(style="thin", color="D1D5DB")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

EUR_M = '#,##0;[Red]-#,##0'
EUR_2 = '"€"#,##0.00'
NUM_1 = '#,##0.0'
PCT_1 = '0.0%'
MULT = '0.00"x"'
MONTHS = '0.0" mo"'

RAW_COLS = {  # Raw_Data annual column letters
    "year": "A", "mau": "B", "subs": "C", "ad_mau": "D", "prem_rev": "E", "ad_rev": "F", "rev": "G",
    "gp": "H", "opex": "I", "opinc": "J", "ocf": "K", "fcf": "L", "sm": "M", "gm_rep": "N", "om_rep": "O",
}


def title(ws, text, subtitle=None):
    ws["A1"] = text
    ws["A1"].font = TITLE
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = NOTE


def header_row(ws, row, labels, start_col=1):
    for j, label in enumerate(labels):
        c = ws.cell(row=row, column=start_col + j, value=label)
        c.font = WHITE_BOLD
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def year_header(ws, row=4):
    ws.cell(row=row, column=1, value="EUR millions unless stated").font = WHITE_BOLD
    ws.cell(row=row, column=1).fill = HEADER_FILL
    for i, col in enumerate(YCOLS):
        c = ws[f"{col}{row}"]
        c.value = f"=Raw_Data!A{RAW_FIRST_ROW + i}"
        c.font = WHITE_BOLD
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center")


def section(ws, row, text, width=6):
    for j in range(1, width + 1):
        ws.cell(row=row, column=j).fill = SECTION_FILL
    ws.cell(row=row, column=1, value=text).font = BOLD


def year_row(ws, row, label, formula, fmt, skip_first=0):
    """formula(col, prev_col, raw_row) -> Excel formula string. skip_first leaves leading years as 'n/a'."""
    ws.cell(row=row, column=1, value=label)
    for i, col in enumerate(YCOLS):
        cell = ws[f"{col}{row}"]
        if i < skip_first:
            cell.value = "n/a"
            cell.alignment = Alignment(horizontal="right")
            cell.font = NOTE
        else:
            prev = YCOLS[i - 1] if i else None
            cell.value = formula(col, prev, RAW_FIRST_ROW + i)
            cell.number_format = fmt
        cell.border = BOX


def raw(key, r):
    return f"Raw_Data!{RAW_COLS[key]}{r}"


def by_year(sheet, row):
    """INDEX/MATCH a model row for the base year selected on LTV_Model."""
    return f"INDEX({sheet}!$B${row}:$F${row},MATCH(LTV_Model!$C$5,{sheet}!$B$4:$F$4,0))"


def input_cell(ws, ref, value, fmt):
    ws[ref] = value
    ws[ref].font = INPUT_FONT
    ws[ref].fill = INPUT_FILL
    ws[ref].number_format = fmt
    ws[ref].border = BOX


def label_value(ws, row, label, formula, fmt, note=None, col="C", out=False):
    ws[f"B{row}"] = label
    ws[f"{col}{row}"] = formula
    ws[f"{col}{row}"].number_format = fmt
    ws[f"{col}{row}"].border = BOX
    if out:
        ws[f"{col}{row}"].fill = OUTPUT_FILL
        ws[f"{col}{row}"].font = BOLD
    if note:
        ws[f"D{row}"] = note
        ws[f"D{row}"].font = NOTE


def widths(ws, mapping):
    for col, w in mapping.items():
        ws.column_dimensions[col].width = w


# --------------------------------------------------------------------------- sheets

def build_raw(wb):
    ws = wb.active
    ws.title = "Raw_Data"
    title(ws, "Raw Data: Spotify reported figures", "Source: Spotify Q4 2025 Shareholder Deck, Form 20-F 2025. "
          "Do not edit; every other sheet links here.")
    annual = load_annual()
    labels = ["Year", "MAU (M)", "Premium subs (M)", "Ad-supported MAU (M)", "Premium revenue", "Ad-supported revenue",
              "Total revenue", "Gross profit", "Operating expenses", "Operating income", "Operating cash flow",
              "Free cash flow", "Sales & marketing", "Gross margin % (reported)", "Operating margin % (reported)"]
    src = ["year", "mau_millions", "premium_subscribers_millions", "ad_supported_mau_millions",
           "premium_revenue_eur_millions", "ad_supported_revenue_eur_millions", "total_revenue_eur_millions",
           "gross_profit_eur_millions", "total_operating_expenses_eur_millions", "operating_income_eur_millions",
           "operating_cash_flow_eur_millions", "free_cash_flow_eur_millions", "sales_marketing_expense_eur_millions",
           "gross_margin_pct", "operating_margin_pct"]
    header_row(ws, 3, labels)
    for i, r in enumerate(annual.itertuples(index=False)):
        for j, col in enumerate(src):
            v = getattr(r, col)
            if v != v:  # NaN -> empty cell
                continue
            if col.endswith("_pct"):
                v = v / 100
            c = ws.cell(row=RAW_FIRST_ROW + i, column=j + 1, value=v)
            c.number_format = PCT_1 if col.endswith("_pct") else ("0" if col == "year" else EUR_M)
            c.border = BOX

    ws["A10"] = "Quarterly"
    ws["A10"].font = BOLD
    q = load_quarterly()
    qlabels = ["Period"] + labels[1:12]
    qsrc = ["period"] + src[1:12]
    header_row(ws, 11, qlabels)
    for i, r in enumerate(q.itertuples(index=False)):
        for j, col in enumerate(qsrc):
            c = ws.cell(row=12 + i, column=j + 1, value=getattr(r, col))
            c.number_format = EUR_M
            c.border = BOX
    ws["A18"] = ("Sales & marketing is available for 2023-2025 only. Premium + ad-supported MAU exceeds total MAU "
                 "because some users appear in both tiers within a month.")
    ws["A18"].font = NOTE
    widths(ws, {get_column_letter(c): 14 for c in range(1, 16)})
    ws.row_dimensions[3].height = 45
    ws.row_dimensions[11].height = 45
    ws.freeze_panes = "B4"


def build_revenue(wb):
    ws = wb.create_sheet("Revenue_Analysis")
    title(ws, "Revenue Analysis", "Growth = (Current - Previous) / Previous")
    year_header(ws)
    section(ws, 5, "Revenue")
    year_row(ws, 6, "Premium revenue", lambda c, p, r: f"={raw('prem_rev', r)}", EUR_M)
    year_row(ws, 7, "Ad-supported revenue", lambda c, p, r: f"={raw('ad_rev', r)}", EUR_M)
    year_row(ws, 8, "Total revenue", lambda c, p, r: f"={raw('rev', r)}", EUR_M)
    year_row(ws, 9, "Check: premium + ad - total (should be 0)", lambda c, p, r: f"={c}6+{c}7-{c}8", EUR_M)
    section(ws, 11, "Growth (YoY)")
    year_row(ws, 12, "Total revenue growth", lambda c, p, r: f"=({c}8-{p}8)/{p}8", PCT_1, 1)
    year_row(ws, 13, "Premium revenue growth", lambda c, p, r: f"=({c}6-{p}6)/{p}6", PCT_1, 1)
    year_row(ws, 14, "Ad-supported revenue growth", lambda c, p, r: f"=({c}7-{p}7)/{p}7", PCT_1, 1)
    year_row(ws, 15, "Incremental revenue", lambda c, p, r: f"={c}8-{p}8", EUR_M, 1)
    section(ws, 17, "Revenue mix")
    year_row(ws, 18, "Premium share of revenue", lambda c, p, r: f"={c}6/{c}8", PCT_1)
    year_row(ws, 19, "Ad-supported share of revenue", lambda c, p, r: f"={c}7/{c}8", PCT_1)
    ws["A21"] = "Total revenue CAGR 2021-2025"
    ws["B21"] = "=(F8/B8)^(1/(F4-B4))-1"
    ws["B21"].number_format = PCT_1
    ws["B21"].fill = OUTPUT_FILL
    ws["B21"].font = BOLD

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "stacked"
    chart.overlap = 100
    chart.title = "Revenue by segment (EUR M)"
    chart.add_data(Reference(ws, min_col=1, max_col=6, min_row=6, max_row=7), from_rows=True, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, max_col=6, min_row=4))
    chart.height, chart.width = 8, 16
    ws.add_chart(chart, "H4")
    widths(ws, {"A": 42, **{c: 12 for c in YCOLS}})
    ws.freeze_panes = "B5"


def build_subscribers(wb):
    ws = wb.create_sheet("Subscriber_Analysis")
    title(ws, "Subscriber Analysis", "Monthly ARPU (approx.) = premium revenue / average(opening, closing subscribers) / 12. "
          "Analyst approximation, not Spotify-reported ARPU.")
    year_header(ws)
    section(ws, 5, "Users (millions, year-end)")
    year_row(ws, 6, "Monthly active users", lambda c, p, r: f"={raw('mau', r)}", NUM_1)
    year_row(ws, 7, "Premium subscribers", lambda c, p, r: f"={raw('subs', r)}", NUM_1)
    year_row(ws, 8, "Ad-supported MAU", lambda c, p, r: f"={raw('ad_mau', r)}", NUM_1)
    section(ws, 10, "Growth")
    year_row(ws, 11, "Premium net adds (M)", lambda c, p, r: f"={c}7-{p}7", NUM_1, 1)
    year_row(ws, 12, "MAU net adds (M)", lambda c, p, r: f"={c}6-{p}6", NUM_1, 1)
    year_row(ws, 13, "Premium subscriber growth", lambda c, p, r: f"=({c}7-{p}7)/{p}7", PCT_1, 1)
    year_row(ws, 14, "MAU growth", lambda c, p, r: f"=({c}6-{p}6)/{p}6", PCT_1, 1)
    year_row(ws, 15, "Premium subscribers as % of MAU", lambda c, p, r: f"={c}7/{c}6", PCT_1)
    section(ws, 17, "Monetisation")
    year_row(ws, 18, "Average premium subscribers (M)", lambda c, p, r: f"=AVERAGE({p}7,{c}7)", NUM_1, 1)
    year_row(ws, 19, "Monthly premium ARPU (EUR, approx.)", lambda c, p, r: f"=Revenue_Analysis!{c}6/{c}18/12", EUR_2, 1)
    year_row(ws, 20, "Annual premium ARPU (EUR, approx.)", lambda c, p, r: f"={c}19*12", EUR_2, 1)
    year_row(ws, 21, "Ad revenue per avg ad-supported MAU (EUR / yr)",
             lambda c, p, r: f"=Revenue_Analysis!{c}7/AVERAGE({p}8,{c}8)", EUR_2, 1)
    year_row(ws, 22, "Revenue growth minus subscriber growth (pp)",
             lambda c, p, r: f"=Revenue_Analysis!{c}12-{c}13", PCT_1, 1)

    chart = LineChart()
    chart.title = "Users (millions)"
    chart.add_data(Reference(ws, min_col=1, max_col=6, min_row=6, max_row=8), from_rows=True, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, max_col=6, min_row=4))
    chart.height, chart.width = 8, 16
    ws.add_chart(chart, "H4")
    widths(ws, {"A": 46, **{c: 12 for c in YCOLS}})
    ws.freeze_panes = "B5"


def build_profitability(wb):
    ws = wb.create_sheet("Profitability")
    title(ws, "Profitability Analysis")
    year_header(ws)
    section(ws, 5, "Income statement & cash flow")
    year_row(ws, 6, "Total revenue", lambda c, p, r: f"=Revenue_Analysis!{c}8", EUR_M)
    year_row(ws, 7, "Gross profit", lambda c, p, r: f"={raw('gp', r)}", EUR_M)
    year_row(ws, 8, "Total operating expenses", lambda c, p, r: f"={raw('opex', r)}", EUR_M)
    year_row(ws, 9, "Operating income", lambda c, p, r: f"={raw('opinc', r)}", EUR_M)
    year_row(ws, 10, "Operating cash flow", lambda c, p, r: f"={raw('ocf', r)}", EUR_M)
    year_row(ws, 11, "Free cash flow (non-IFRS)", lambda c, p, r: f"={raw('fcf', r)}", EUR_M)
    year_row(ws, 12, "Sales & marketing expense", lambda c, p, r: f'=IF(ISNUMBER({raw("sm", r)}),{raw("sm", r)},"n/a")', EUR_M)
    year_row(ws, 13, "Check: GP - opex - operating income (should be 0)", lambda c, p, r: f"={c}7-{c}8-{c}9", EUR_M)
    section(ws, 15, "Margins & ratios")
    year_row(ws, 16, "Gross margin", lambda c, p, r: f"={c}7/{c}6", PCT_1)
    year_row(ws, 17, "Operating margin", lambda c, p, r: f"={c}9/{c}6", PCT_1)
    year_row(ws, 18, "Operating expense ratio", lambda c, p, r: f"={c}8/{c}6", PCT_1)
    year_row(ws, 19, "S&M as % of revenue", lambda c, p, r: f'=IF(ISNUMBER({c}12),{c}12/{c}6,"n/a")', PCT_1)
    year_row(ws, 20, "Operating cash flow margin", lambda c, p, r: f"={c}10/{c}6", PCT_1)
    year_row(ws, 21, "Free cash flow margin", lambda c, p, r: f"={c}11/{c}6", PCT_1)
    year_row(ws, 22, "Incremental operating margin", lambda c, p, r: f"=({c}9-{p}9)/({c}6-{p}6)", PCT_1, 1)
    section(ws, 24, "Cost growth vs revenue growth")
    year_row(ws, 25, "Revenue growth", lambda c, p, r: f"=Revenue_Analysis!{c}12", PCT_1, 1)
    year_row(ws, 26, "Operating expense growth", lambda c, p, r: f"=({c}8-{p}8)/{p}8", PCT_1, 1)
    year_row(ws, 27, "S&M growth", lambda c, p, r: f'=IF(AND(ISNUMBER({c}12),ISNUMBER({p}12)),({c}12-{p}12)/{p}12,"n/a")', PCT_1, 1)

    chart = LineChart()
    chart.title = "Margins"
    chart.add_data(Reference(ws, min_col=1, max_col=6, min_row=16, max_row=17), from_rows=True, titles_from_data=True)
    chart.add_data(Reference(ws, min_col=1, max_col=6, min_row=21, max_row=21), from_rows=True, titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, max_col=6, min_row=4))
    chart.y_axis.number_format = "0%"
    chart.height, chart.width = 8, 16
    ws.add_chart(chart, "H4")
    widths(ws, {"A": 46, **{c: 12 for c in YCOLS}})
    ws.freeze_panes = "B5"


def build_cac(wb):
    ws = wb.create_sheet("CAC_Analysis")
    title(ws, "CAC Proxy Analysis: NOT true CAC",
          "Spotify does not disclose CAC or churn. Both proxies charge 100% of S&M to premium acquisition. "
          "Churn comes from LTV_Model!C6.")
    year_header(ws)
    has_sm = lambda c: f"ISNUMBER(Profitability!{c}12)"
    section(ws, 5, "Inputs")
    year_row(ws, 6, "Sales & marketing expense", lambda c, p, r: f"=Profitability!{c}12", EUR_M)
    year_row(ws, 7, "Premium net adds (M)", lambda c, p, r: f"=Subscriber_Analysis!{c}11", NUM_1, 1)
    year_row(ws, 8, "Average premium subscribers (M)", lambda c, p, r: f"=Subscriber_Analysis!{c}18", NUM_1, 1)
    year_row(ws, 9, "Assumed monthly churn (from LTV_Model)", lambda c, p, r: "=LTV_Model!$C$6", PCT_1)
    year_row(ws, 10, "Implied subscribers lost to churn (M)", lambda c, p, r: f"={c}8*{c}9*12", NUM_1, 1)
    year_row(ws, 11, "Implied gross adds (M)", lambda c, p, r: f"={c}7+{c}10", NUM_1, 1)
    section(ws, 13, "CAC proxies (EUR per subscriber)")
    year_row(ws, 14, "Proxy 1: S&M / net adds (roadmap formula)", lambda c, p, r: f'=IF({has_sm(c)},{c}6/{c}7,"n/a")', EUR_2, 1)
    year_row(ws, 15, "Proxy 2: S&M / implied gross adds (churn-consistent)", lambda c, p, r: f'=IF({has_sm(c)},{c}6/{c}11,"n/a")', EUR_2, 1)
    year_row(ws, 16, "S&M as % of revenue", lambda c, p, r: f"=Profitability!{c}19", PCT_1)
    ws["A18"] = ("Proxy 1 assumes no subscriber is replaced (zero churn), so it overstates CAC. Proxy 2 adds back the "
                 "subscribers implied lost at the assumed churn rate, so it uses the same churn assumption as the LTV.")
    ws["A18"].font = NOTE
    widths(ws, {"A": 52, **{c: 12 for c in YCOLS}})
    ws.freeze_panes = "B5"


def build_ltv(wb):
    ws = wb.create_sheet("LTV_Model")
    title(ws, "LTV, LTV:CAC & Payback Model",
          "Yellow cells are inputs. LTV = ARPU x gross margin / churn. Payback = CAC / (ARPU x gross margin).")
    section(ws, 4, "1. Assumptions (edit the yellow cells)", 4)
    ws["B5"] = "Base year (2023-2025)"
    input_cell(ws, "C5", BASE_YEAR, "0")
    dv = DataValidation(type="list", formula1='"2023,2024,2025"', allow_blank=False)
    ws.add_data_validation(dv)
    dv.add("C5")
    ws["B6"] = "Assumed monthly churn"
    input_cell(ws, "C6", BASE_CHURN, PCT_1)
    ws["B7"] = "ARPU adjustment"
    input_cell(ws, "C7", 0, PCT_1)
    ws["B8"] = "Gross margin adjustment (pp, e.g. 1.0% = +1pp)"
    input_cell(ws, "C8", 0, PCT_1)
    ws["B9"] = "S&M spend adjustment"
    input_cell(ws, "C9", 0, PCT_1)
    ws["B10"] = "Net adds adjustment"
    input_cell(ws, "C10", 0, PCT_1)
    for r, note in zip(range(5, 11), ["Drives every INDEX/MATCH below and the Executive_Summary",
                                      "Hypothetical; Spotify does not report churn", "Subscription price / mix change",
                                      "Added to base gross margin", "Applied to base-year S&M",
                                      "Subscriber growth slowdown (negative) or acceleration"]):
        ws[f"D{r}"] = note
        ws[f"D{r}"].font = NOTE

    section(ws, 12, "2. Base-year inputs (linked)", 4)
    label_value(ws, 13, "Monthly premium ARPU (EUR)", f"={by_year('Subscriber_Analysis', 19)}", EUR_2)
    label_value(ws, 14, "Gross margin", f"={by_year('Profitability', 16)}", PCT_1)
    label_value(ws, 15, "Sales & marketing expense (EUR M)", f"={by_year('Profitability', 12)}", EUR_M)
    label_value(ws, 16, "Premium net adds (M)", f"={by_year('Subscriber_Analysis', 11)}", NUM_1)
    label_value(ws, 17, "Average premium subscribers (M)", f"={by_year('Subscriber_Analysis', 18)}", NUM_1)
    label_value(ws, 18, "Opening premium subscribers (M)", "=C17-C16/2", NUM_1)

    section(ws, 20, "3. Adjusted inputs", 4)
    label_value(ws, 21, "ARPU (EUR / month)", "=C13*(1+C7)", EUR_2)
    label_value(ws, 22, "Gross margin", "=C14+C8", PCT_1)
    label_value(ws, 23, "S&M expense (EUR M)", "=C15*(1+C9)", EUR_M)
    label_value(ws, 24, "Net adds (M)", "=C16*(1+C10)", NUM_1)
    label_value(ws, 25, "Average subscribers (M)", "=C18+C24/2", NUM_1)
    label_value(ws, 26, "Monthly churn", "=C6", PCT_1)

    section(ws, 28, "4. Outputs", 4)
    label_value(ws, 29, "Monthly gross profit per subscriber (EUR)", "=C21*C22", EUR_2, out=True)
    label_value(ws, 30, "Expected subscriber lifetime (months)", "=1/C26", MONTHS, out=True)
    label_value(ws, 31, "LTV (EUR, gross profit)", "=C29/C26", EUR_2, out=True)
    label_value(ws, 32, "Implied gross adds (M)", "=C24+C25*C26*12", NUM_1)
    label_value(ws, 33, "CAC proxy 1: S&M / net adds (EUR)", "=C23/C24", EUR_2, out=True)
    label_value(ws, 34, "CAC proxy 2: S&M / implied gross adds (EUR)", "=C23/C32", EUR_2, out=True)
    label_value(ws, 35, "LTV:CAC (proxy 1)", "=C31/C33", MULT, out=True)
    label_value(ws, 36, "LTV:CAC (proxy 2)", "=C31/C34", MULT, out=True)
    label_value(ws, 37, "Payback months (proxy 1)", "=C33/C29", MONTHS, out=True)
    label_value(ws, 38, "Payback months (proxy 2)", "=C34/C29", MONTHS, out=True)
    label_value(ws, 39, "Proxy 2 payback within expected lifetime?", '=IF(C38<C30,"Yes","No")', "@", out=True)

    section(ws, 41, "5. Churn scenarios (uses adjusted inputs above; edit churn in column C)", 11)
    cols = ["Scenario", "Monthly churn", "Lifetime (mo)", "LTV (EUR)", "Gross adds (M)", "CAC proxy 1", "CAC proxy 2",
            "LTV:CAC 1", "LTV:CAC 2", "Payback 1 (mo)", "Payback 2 (mo)"]
    header_row(ws, 42, cols, start_col=2)
    for i, (name, churn) in enumerate(CHURN_SCENARIOS.items()):
        r = 43 + i
        ws[f"B{r}"] = name
        input_cell(ws, f"C{r}", churn, PCT_1)
        f = {"D": f"=1/C{r}", "E": f"=$C$29/C{r}", "F": f"=$C$24+$C$25*C{r}*12", "G": "=$C$23/$C$24",
             "H": f"=$C$23/F{r}", "I": f"=E{r}/G{r}", "J": f"=E{r}/H{r}", "K": "=G{r}/$C$29".format(r=r),
             "L": f"=H{r}/$C$29"}
        fmts = {"D": MONTHS, "E": EUR_2, "F": NUM_1, "G": EUR_2, "H": EUR_2, "I": MULT, "J": MULT, "K": MONTHS, "L": MONTHS}
        for col, formula in f.items():
            ws[f"{col}{r}"] = formula
            ws[f"{col}{r}"].number_format = fmts[col]
            ws[f"{col}{r}"].border = BOX

    chart = BarChart()
    chart.type = "col"
    chart.title = "LTV vs CAC proxies by churn scenario (EUR)"
    for col in (5, 7, 8):  # LTV, CAC proxy 1, CAC proxy 2
        chart.add_data(Reference(ws, min_col=col, min_row=42, max_row=46), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=2, min_row=43, max_row=46))
    chart.height, chart.width = 8, 18
    ws.add_chart(chart, "B49")
    widths(ws, {"A": 3, "B": 46, "C": 14, "D": 14, **{get_column_letter(c): 13 for c in range(5, 13)}})


def build_scenarios(wb):
    ws = wb.create_sheet("Scenario_Analysis")
    title(ws, "Scenario & Sensitivity Analysis",
          "Each row applies its own adjustments (yellow) to the base year chosen on LTV_Model. Edit any yellow cell.")
    inputs = ["Scenario", "Monthly churn", "ARPU adj.", "Gross margin adj. (pp)", "S&M adj.", "Net adds adj."]
    outputs = ["ARPU (EUR)", "Gross margin", "S&M (EUR M)", "Net adds (M)", "Avg subs (M)", "Monthly GP / sub",
               "LTV (EUR)", "LTV vs base", "Gross adds (M)", "CAC proxy 1", "CAC proxy 2", "LTV:CAC 1", "LTV:CAC 2",
               "Payback 2 (mo)"]
    header_row(ws, 4, inputs + outputs)
    scenarios = [
        ("Base case", BASE_CHURN, 0, 0, 0, 0),
        ("Optimistic churn (2%)", 0.02, 0, 0, 0, 0),
        ("Moderate-risk churn (4%)", 0.04, 0, 0, 0, 0),
        ("High-risk churn (5%)", 0.05, 0, 0, 0, 0),
        ("Marketing spend +10%", BASE_CHURN, 0, 0, 0.10, 0),
        ("Marketing spend +20%", BASE_CHURN, 0, 0, 0.20, 0),
        ("Gross margin +1pp", BASE_CHURN, 0, 0.01, 0, 0),
        ("Gross margin +2pp", BASE_CHURN, 0, 0.02, 0, 0),
        ("Gross margin +3pp", BASE_CHURN, 0, 0.03, 0, 0),
        ("Subscriber growth slowdown (net adds -25%)", BASE_CHURN, 0, 0, 0, -0.25),
        ("Subscriber growth slowdown (net adds -50%)", BASE_CHURN, 0, 0, 0, -0.50),
        ("Subscription revenue -10% (ARPU)", BASE_CHURN, -0.10, 0, 0, 0),
        ("Subscription revenue -5% (ARPU)", BASE_CHURN, -0.05, 0, 0, 0),
        ("Subscription revenue +5% (ARPU)", BASE_CHURN, 0.05, 0, 0, 0),
        ("Subscription revenue +10% (ARPU)", BASE_CHURN, 0.10, 0, 0, 0),
        ("Combined downside", 0.04, -0.05, 0, 0.10, -0.25),
        ("Combined upside", 0.025, 0.05, 0.02, 0, 0),
    ]
    L = "LTV_Model!"
    for i, (name, churn, arpu, gm, sm, na) in enumerate(scenarios):
        r = 5 + i
        ws[f"A{r}"] = name
        for col, v in zip("BCDEF", (churn, arpu, gm, sm, na)):
            input_cell(ws, f"{col}{r}", v, PCT_1)
        formulas = {
            "G": (f"={L}$C$13*(1+C{r})", EUR_2),
            "H": (f"={L}$C$14+D{r}", PCT_1),
            "I": (f"={L}$C$15*(1+E{r})", EUR_M),
            "J": (f"={L}$C$16*(1+F{r})", NUM_1),
            "K": (f"={L}$C$18+J{r}/2", NUM_1),
            "L": (f"=G{r}*H{r}", EUR_2),
            "M": (f"=L{r}/B{r}", EUR_2),
            "N": (f"=M{r}/$M$5-1", PCT_1),
            "O": (f"=J{r}+K{r}*B{r}*12", NUM_1),
            "P": (f"=I{r}/J{r}", EUR_2),
            "Q": (f"=I{r}/O{r}", EUR_2),
            "R": (f"=M{r}/P{r}", MULT),
            "S": (f"=M{r}/Q{r}", MULT),
            "T": (f"=Q{r}/L{r}", MONTHS),
        }
        for col, (formula, fmt) in formulas.items():
            ws[f"{col}{r}"] = formula
            ws[f"{col}{r}"].number_format = fmt
            ws[f"{col}{r}"].border = BOX
    last = 4 + len(scenarios)

    # Two-way grid 1: LTV by churn x gross margin.
    g1 = last + 3
    section(ws, g1, "Sensitivity grid: LTV (EUR) by monthly churn (rows) and gross margin (columns)", 9)
    ws[f"A{g1 + 1}"] = "Churn \\ Gross margin"
    ws[f"A{g1 + 1}"].font = BOLD
    gm_deltas = [-0.04, -0.02, 0, 0.02, 0.04, 0.06, 0.08]
    churns = [0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06]
    for j, d in enumerate(gm_deltas):
        c = ws.cell(row=g1 + 1, column=2 + j, value=f"={L}$C$14+{d}")
        c.number_format = PCT_1
        c.font = WHITE_BOLD
        c.fill = HEADER_FILL
    for i, ch in enumerate(churns):
        r = g1 + 2 + i
        input_cell(ws, f"A{r}", ch, PCT_1)
        for j in range(len(gm_deltas)):
            col = get_column_letter(2 + j)
            ws[f"{col}{r}"] = f"={L}$C$13*{col}${g1 + 1}/$A{r}"
            ws[f"{col}{r}"].number_format = '"€"#,##0'
            ws[f"{col}{r}"].border = BOX

    # Two-way grid 2: LTV:CAC (proxy 2) by churn x S&M change.
    g2 = g1 + len(churns) + 4
    section(ws, g2, "Sensitivity grid: LTV:CAC (proxy 2, gross adds) by monthly churn (rows) and S&M change (columns)", 9)
    ws[f"A{g2 + 1}"] = "Churn \\ S&M change"
    ws[f"A{g2 + 1}"].font = BOLD
    sm_changes = [-0.20, -0.10, 0, 0.10, 0.20, 0.30]
    for j, d in enumerate(sm_changes):
        c = ws.cell(row=g2 + 1, column=2 + j, value=d)
        c.number_format = '+0%;-0%;0%'
        c.font = WHITE_BOLD
        c.fill = HEADER_FILL
    for i, ch in enumerate(churns):
        r = g2 + 2 + i
        input_cell(ws, f"A{r}", ch, PCT_1)
        for j in range(len(sm_changes)):
            col = get_column_letter(2 + j)
            ws[f"{col}{r}"] = (f"=({L}$C$13*{L}$C$14/$A{r})/({L}$C$15*(1+{col}${g2 + 1})"
                               f"/({L}$C$16+{L}$C$17*$A{r}*12))")
            ws[f"{col}{r}"].number_format = MULT
            ws[f"{col}{r}"].border = BOX

    widths(ws, {"A": 44, **{get_column_letter(c): 12 for c in range(2, 21)}})
    ws.row_dimensions[4].height = 45
    ws.freeze_panes = "B5"


def build_summary(wb):
    ws = wb.create_sheet("Executive_Summary", 0)
    title(ws, "Spotify Unit Economics: Executive Summary",
          "All figures link to the model. Change the base year or assumptions on LTV_Model.")
    ws["B4"] = "Base year"
    ws["C4"] = "=LTV_Model!C5"
    ws["C4"].font = BOLD
    ws["B5"] = "Assumed monthly churn"
    ws["C5"] = "=LTV_Model!C6"
    ws["C5"].number_format = PCT_1
    header_row(ws, 7, ["Metric", "Value", "Basis"], start_col=2)
    rows = [
        ("Total revenue (EUR M)", f"={by_year('Revenue_Analysis', 8)}", EUR_M, "Reported"),
        ("Revenue growth YoY", f"={by_year('Revenue_Analysis', 12)}", PCT_1, "Calculated"),
        ("Premium share of revenue", f"={by_year('Revenue_Analysis', 18)}", PCT_1, "Calculated"),
        ("Premium subscribers (M)", f"={by_year('Subscriber_Analysis', 7)}", NUM_1, "Reported"),
        ("Monthly active users (M)", f"={by_year('Subscriber_Analysis', 6)}", NUM_1, "Reported"),
        ("Premium net adds (M)", f"={by_year('Subscriber_Analysis', 11)}", NUM_1, "Calculated"),
        ("Monthly premium ARPU (EUR)", f"={by_year('Subscriber_Analysis', 19)}", EUR_2, "Analyst approximation"),
        ("Gross margin", f"={by_year('Profitability', 16)}", PCT_1, "Reported"),
        ("Operating income (EUR M)", f"={by_year('Profitability', 9)}", EUR_M, "Reported"),
        ("Operating margin", f"={by_year('Profitability', 17)}", PCT_1, "Reported"),
        ("Free cash flow (EUR M)", f"={by_year('Profitability', 11)}", EUR_M, "Reported (non-IFRS)"),
        ("S&M as % of revenue", f"={by_year('Profitability', 19)}", PCT_1, "Calculated"),
        ("LTV (EUR)", "=LTV_Model!C31", EUR_2, "Scenario estimate"),
        ("CAC proxy 1: S&M / net adds (EUR)", "=LTV_Model!C33", EUR_2, "Proxy, NOT CAC"),
        ("CAC proxy 2: S&M / implied gross adds (EUR)", "=LTV_Model!C34", EUR_2, "Proxy, NOT CAC"),
        ("LTV:CAC (proxy 1)", "=LTV_Model!C35", MULT, "Scenario estimate"),
        ("LTV:CAC (proxy 2)", "=LTV_Model!C36", MULT, "Scenario estimate"),
        ("Payback months (proxy 2)", "=LTV_Model!C38", MONTHS, "Scenario estimate"),
    ]
    for i, (label, formula, fmt, basis) in enumerate(rows):
        r = 8 + i
        ws[f"B{r}"] = label
        ws[f"C{r}"] = formula
        ws[f"C{r}"].number_format = fmt
        ws[f"C{r}"].font = BOLD
        ws[f"D{r}"] = basis
        ws[f"D{r}"].font = NOTE
        for col in "BCD":
            ws[f"{col}{r}"].border = BOX
    n = 8 + len(rows) + 1
    ws[f"B{n}"] = "Key findings (2025 base, 3% churn; text does not update with inputs)"
    ws[f"B{n}"].font = BOLD
    findings = [
        "Revenue grew 78% (2021-2025) vs premium subscribers +61%: monetisation per user improved.",
        "Operating margin improved from -5.6% (2022) to 12.8% (2025); opex fell in absolute terms in 2024 and 2025.",
        "S&M fell from 11.6% to 8.3% of revenue (2023-2025) while net adds held at ~27M a year.",
        "LTV is highly sensitive to churn: 2% -> 5% monthly churn cuts LTV by 60%.",
        "LTV:CAC depends on the CAC proxy; the churn-consistent proxy 2 is the more coherent estimate.",
        "Ad revenue per ad-supported MAU is falling: ad monetisation is the clearest growth gap.",
    ]
    for i, text in enumerate(findings):
        ws[f"B{n + 1 + i}"] = f"- {text}"
    ws[f"B{n + 8}"] = ("Limitations: churn is hypothetical; CAC figures are proxies; ARPU is approximated; gross margin is "
                       "company-level. See the management report for methodology.")
    ws[f"B{n + 8}"].font = NOTE
    widths(ws, {"A": 3, "B": 46, "C": 16, "D": 24})


def main():
    wb = Workbook()
    build_raw(wb)
    build_revenue(wb)
    build_subscribers(wb)
    build_profitability(wb)
    build_cac(wb)
    build_ltv(wb)
    build_scenarios(wb)
    build_summary(wb)
    order = ["Raw_Data", "Revenue_Analysis", "Subscriber_Analysis", "Profitability", "CAC_Analysis", "LTV_Model",
             "Scenario_Analysis", "Executive_Summary"]
    wb._sheets = [wb[name] for name in order]
    wb.active = wb.sheetnames.index("Executive_Summary")
    wb.calculation.fullCalcOnLoad = True
    wb.save(OUT)
    print(f"  model  -> {OUT}")


if __name__ == "__main__":
    main()
