"""Phase 0 - Export the source workbook's sheets to the raw CSV files used by the pipeline."""

import pandas as pd

from common import ANNUAL_RAW, QUARTERLY_RAW, ROOT, SOURCE_XLSX, save_csv

SHEETS = {
    "Annual_2021_2025": ANNUAL_RAW,
    "Quarterly_2024Q4_2025": QUARTERLY_RAW,
    "Data_Dictionary": ROOT / "data" / "data_dictionary.csv",
    "Source_Register": ROOT / "data" / "source_register.csv",
}


def main():
    print(f"Reading {SOURCE_XLSX.relative_to(ROOT)}")
    workbook = pd.ExcelFile(SOURCE_XLSX)
    missing = set(SHEETS) - set(workbook.sheet_names)
    if missing:
        raise ValueError(f"Source workbook is missing sheets: {sorted(missing)}")
    for sheet, target in SHEETS.items():
        save_csv(workbook.parse(sheet), target)


if __name__ == "__main__":
    main()
