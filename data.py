"""
data.py — reads MK Stock Positions.xlsx
Works both locally in PyCharm and on Streamlit Cloud.
"""

import pandas as pd
from pathlib import Path

# This finds the Excel file relative to this script
# Works locally AND on Streamlit Cloud since the file is in the repo root
EXCEL_PATH   = Path(__file__).parent / "MK Stock Positions.xlsx"
CLIENTS      = ["Kunall", "Milind"]
SKIP_TICKERS = {"TOTAL", "NAN", "STOCK NAME", ""}


def load_client(sheet_name: str) -> pd.DataFrame:
    """
    Load one client's positions from their sheet.
    Columns: A = ticker, B = avg price paid, C = number of shares.
    """
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"\nCould not find: {EXCEL_PATH}\n"
            f"Make sure 'MK Stock Positions.xlsx' is in the same folder as data.py\n"
        )

    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, engine="openpyxl")

    # Take only the first 3 columns
    df = df.iloc[:, :3].copy()
    df.columns = ["ticker", "avg_cost", "shares"]

    # Clean
    df["ticker"]   = df["ticker"].astype(str).str.strip().str.upper()
    df["avg_cost"] = pd.to_numeric(df["avg_cost"], errors="coerce")
    df["shares"]   = pd.to_numeric(df["shares"],   errors="coerce")

    # Drop TOTAL row and empty rows
    df = df[~df["ticker"].isin(SKIP_TICKERS)]
    df = df.dropna(subset=["ticker", "avg_cost", "shares"])

    return df.reset_index(drop=True)
