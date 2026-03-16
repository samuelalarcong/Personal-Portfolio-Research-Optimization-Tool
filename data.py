"""
data.py — reads the Excel file from the project root
"""
import pandas as pd
from pathlib import Path

# Excel file is in the project root (same level as main.py)
# C:\Users\samue\Desktop\Respaldo\Upwork clients\Millid\MK Stock Positions.xlsx
EXCEL_PATH = Path(__file__).parent / "MK Stock Positions.xlsx"

CLIENTS      = ["Kunall", "Milind"]
SKIP_TICKERS = {"TOTAL", "NAN", "STOCK NAME", ""}


def load_client(sheet_name: str) -> pd.DataFrame:
    """
    Read one client's positions from their sheet in the local Excel file.

    Columns in the Excel:
        A → Stock name       (ticker symbol)
        B → Average price    (price paid per share)
        C → Number of stocks (how many shares)
    """
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(
            f"\nExcel file not found at: {EXCEL_PATH}\n"
            f"Make sure 'MK Stock Positions.xlsx' is in the same folder as main.py\n"
        )

    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, engine="openpyxl")

    # Keep only columns A, B, C — everything else we recalculate live
    df = df.iloc[:, :3].copy()
    df.columns = ["ticker", "avg_cost", "shares"]

    # Clean
    df["ticker"]   = df["ticker"].astype(str).str.strip().str.upper()
    df["avg_cost"] = pd.to_numeric(df["avg_cost"], errors="coerce")
    df["shares"]   = pd.to_numeric(df["shares"],   errors="coerce")

    # Drop TOTAL row and any empty rows
    df = df[~df["ticker"].isin(SKIP_TICKERS)]
    df = df.dropna(subset=["ticker", "avg_cost", "shares"])

    return df.reset_index(drop=True)
