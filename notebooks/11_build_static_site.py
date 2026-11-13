"""Phase 12 - Build a static, fully client-side version of the dashboard for GitHub Pages.

Writes index.html (plus .nojekyll) at the project root. The page embeds the same US-dollar tables as the Dash
dashboard and the Power BI project, and recalculates LTV, CAC, payback, retention, sensitivity and Monte Carlo in
the browser, so it needs no Python server. Template: dashboards/static_template.html.
"""

import importlib.util
import json

from common import ROOT

spec = importlib.util.spec_from_file_location("pbi", ROOT / "notebooks" / "10_build_powerbi_project.py")
pbi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pbi)
app = pbi.app


def records(df):
    """DataFrame -> list of dicts with NaN as null (via pandas' JSON writer, which handles numpy types)."""
    return json.loads(df.to_json(orient="records", double_precision=10))


def main():
    t = pbi.build_tables()
    data = {
        "annual": records(t["fact_annual"]), "quarterly": records(t["fact_quarterly"]),
        "ue_by_year": records(t["ue_by_year"]), "base_inputs": records(t["base_inputs"]),
        "assumptions": records(t["assumptions"].drop(columns="order")), "glossary": records(t["glossary"]),
        "formulas": records(t["formulas"]), "disclaimer": app.DISCLAIMER,
        "default_base_year": int(app.DEFAULTS["base_year"]), "checks_pass": int(app.N_PASS),
        "checks_total": int(app.N_CHECKS),
    }
    template = (ROOT / "dashboards" / "static_template.html").read_text(encoding="utf-8")
    assert template.count("__DATA__") == 1
    html = template.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")  # serve index.html as-is, no Jekyll build
    print(f"  site   -> index.html ({len(html) / 1024:.0f} KB, open it in a browser or publish with GitHub Pages)")


if __name__ == "__main__":
    main()
