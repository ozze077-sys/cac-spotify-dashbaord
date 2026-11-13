"""Run the full analysis pipeline in order: raw extract -> analysis -> Excel model -> Power BI tables."""

import subprocess
import sys
from pathlib import Path

NOTEBOOKS = Path(__file__).resolve().parent / "notebooks"
STEPS = [
    "00_extract_raw_data.py",
    "01_data_quality_and_eda.py",
    "02_revenue_analysis.py",
    "03_subscriber_analysis.py",
    "04_profitability_analysis.py",
    "05_unit_economics.py",
    "06_scenario_analysis.py",
    "07_business_recommendations.py",
    "08_build_excel_model.py",
    "09_export_powerbi_data.py",
    "10_build_powerbi_project.py",
    "11_build_static_site.py",
]

for step in STEPS:
    print(f"\n=== {step}")
    subprocess.run([sys.executable, step], cwd=NOTEBOOKS, check=True)
print("\nPipeline complete.")
