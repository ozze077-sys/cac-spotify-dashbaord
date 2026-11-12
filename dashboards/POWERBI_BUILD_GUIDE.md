# Power BI Dashboard: Build Guide

`spotify_dashboard.pbix` has to be built in Power BI Desktop, which is a Windows GUI. Everything it needs is already in
this folder:

| File | Purpose |
| --- | --- |
| `powerbi_data/*.csv` | Model tables (regenerate with `python run_pipeline.py`) |
| `powerbi_measures.dax` | Every DAX measure, including the what-if unit economics |
| `spotify_dashboard_theme.json` | Colour-blind-validated theme (View -> Themes -> Browse for themes) |

Estimated build time: 60-90 minutes.

## 1. Load data

Home -> Get data -> Text/CSV, load each file in `powerbi_data/`:

| Table | Grain | Used on |
| --- | --- | --- |
| `fact_annual` | 1 row per year (2021-2025) | Pages 1-3 |
| `fact_quarterly` | 1 row per quarter (2024-Q4 to 2025-Q4) | Pages 2-3 |
| `fact_revenue_by_segment_annual` | year x segment | Page 2 stacked columns |
| `fact_revenue_by_segment_quarterly` | quarter x segment | Page 2 |
| `unit_economics_by_year` | 1 row per year (2023-2025) | Page 3 |
| `dim_unit_economics_base` | 1 row (2025 base inputs) | Page 4 what-if |
| `unit_economics_churn_scenarios` | 1 row per churn scenario | Page 4 |
| `scenario_comparison` | 1 row per scenario | Page 4 |
| `sensitivity_grids_long` | churn x column value x metric | Page 4 matrix heatmap |
| `tornado_sensitivity` | lever x metric | Page 4 |
| `kpi_summary` | metric list | Optional table visual |

In Power Query, set `year` to **Whole number** and the `*_pct` columns to **Decimal**. Note that `*_pct` columns are
stored as 0-100, not 0-1. DAX ratio measures return 0-1, so format those as Percentage.

## 2. Relationships (Model view)

- `fact_annual[year]` 1 -> * `fact_revenue_by_segment_annual[year]`
- `fact_annual[year]` 1 -> 1 `unit_economics_by_year[year]` (cross-filter: both)
- `fact_quarterly[period]` 1 -> * `fact_revenue_by_segment_quarterly[period]`
- The scenario tables stand alone; they are static outputs of the Python model.

Sort `unit_economics_churn_scenarios[scenario]` by `monthly_churn_pct` and `fact_quarterly[period]` by `quarter_index`
(Column tools -> Sort by column).

## 3. Measures and what-if parameters

1. Home -> Enter data -> create an empty table `_Measures`.
2. Create the five numeric-range parameters listed in `powerbi_measures.dax` (Modeling -> New parameter).
3. Paste each measure from `powerbi_measures.dax` (Modeling -> New measure). Formats:
   - `%` measures: Percentage, 1 decimal.
   - `ARPU`, `LTV`, `CAC`: Currency EUR, 2 decimals.
   - `LTV to CAC`: Decimal with suffix "x".
   - `Payback`: Decimal, 1 decimal.
4. Check: with every parameter at its default (churn 3%, other changes 0), `WI LTV` should read **€49.32**,
   `WI CAC Proxy Gross` **€11.27** and `WI LTV to CAC Gross` **4.38x**. These match the Python and Excel models.

## 4. Pages

Canvas 1280 x 720. Put a single-select **year slicer** (`fact_annual[year]`, default 2025) at the top of pages 1-3, and
add the `[Proxy Disclaimer]` measure as a text card on pages 3-4.

### Page 1: Executive Overview
- **KPI cards (top row):** `Total Revenue`, `Premium Subscribers`, `MAU`, `Gross Margin %`, `Operating Income`,
  `Revenue Growth %`.
- **Clustered column:** `Total Revenue` by year. Title: "Revenue 2021-2025".
- **Line chart:** `Gross Margin %`, `Operating Margin %`, `FCF Margin %` by year (one % axis, no secondary axis).
- **Text box:** three headline findings from `outputs/reports/Spotify_Management_Report.md`.

### Page 2: Revenue & Subscriber Analytics
- **Stacked column:** `fact_revenue_by_segment_annual` revenue by year, legend = segment.
- **Line chart:** `premium_subscribers_millions`, `ad_supported_mau_millions`, `mau_millions` by year.
- **Line chart:** `Monthly Premium ARPU` by year.
- **Stacked column:** quarterly revenue by segment (`fact_revenue_by_segment_quarterly`).
- **Clustered column:** `Revenue Growth %` vs `Subscriber Growth %` by year.

### Page 3: Profitability & Marketing
- **Waterfall or column chart:** `Operating Income` by year. Conditional colour: red when negative, green when positive.
- **Line chart:** `Opex Ratio %` and `S&M % of Revenue` by year.
- **Clustered column:** `unit_economics_by_year` `cac_proxy_net_adds_eur` and `cac_proxy_gross_adds_eur` by year.
- **Table:** year, `S&M Expense`, `Premium Net Adds`, `CAC Proxy (Net Adds)`.
- **Line chart:** quarterly `gross_margin_calc_pct` and `operating_margin_calc_pct` by period.

### Page 4: Unit Economics & Scenarios
- **Slicers (left rail):** the five what-if parameters.
- **KPI cards:** `WI LTV`, `WI CAC Proxy Gross`, `WI LTV to CAC Gross`, `WI Payback Months Gross`, `WI Payback Status`.
  Also add `WI LTV to CAC Net` as a secondary card labelled "Net-adds proxy".
- **Clustered column:** `unit_economics_churn_scenarios`, axis = scenario, values = `ltv_eur`,
  `cac_proxy_net_adds_eur`, `cac_proxy_gross_adds_eur`.
- **Matrix heatmap:** `sensitivity_grids_long` filtered to metric = "LTV (EUR)". Rows = `monthly_churn`,
  columns = `column_value`, values = `value`. Use background-colour conditional formatting with a single-hue blue
  gradient.
- **Tornado:** clustered bar from `tornado_sensitivity` (filter metric = `ltv_to_cac_gross_adds`). Axis = lever,
  values = `low_case` and `high_case`; add a constant line at `base`.
- **Table:** `scenario_comparison` (scenario, `ltv_eur`, `ltv_to_cac_net_adds`, `ltv_to_cac_gross_adds`,
  `payback_months_gross_adds`).

## 5. Finish
- Apply `spotify_dashboard_theme.json`.
- Save as `dashboards/spotify_dashboard.pbix`.
- Export each page (File -> Export -> PDF, or screenshots) to `outputs/charts/powerbi_page_N.png` for the README.
