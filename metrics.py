"""
metrics.py
----------
Takes the positions table (from data.py) and the live prices
(from prices.py) and calculates everything:

  - How much each position is worth today
  - How much the client gained or lost vs what they paid
  - How much each position moved today
  - What % of the total portfolio each stock represents
  - A summary block with totals, best/worst performer, etc.
"""

import pandas as pd


def calculate(df: pd.DataFrame, price_map: dict) -> dict:
    """
    df        : DataFrame with columns ticker, avg_cost, shares
    price_map : { "AAPL": { "live": 213.49, "prev": 212.10 }, ... }

    Returns a dict with:
      - positions : list of dicts, one per stock, ready for JSON
      - summary   : dict with portfolio-level totals
    """
    rows = []

    for _, row in df.iterrows():
        ticker   = row["ticker"]
        shares   = row["shares"]
        avg_cost = row["avg_cost"]
        prices   = price_map.get(ticker, {})
        live     = prices.get("live")
        prev     = prices.get("prev")

        # Skip if Yahoo Finance couldn't find this ticker
        if live is None:
            continue

        # ── Core calculations ────────────────────────────────────────────
        invested      = round(shares * avg_cost, 2)
        current_value = round(shares * live, 2)
        gain_loss     = round(current_value - invested, 2)
        gain_loss_pct = round((gain_loss / invested) * 100, 2) if invested else 0

        # Today's move
        day_pnl     = round((live - prev) * shares, 2) if prev else 0
        day_pnl_pct = round(((live - prev) / prev) * 100, 2) if prev else 0

        rows.append({
            "ticker":        ticker,
            "shares":        shares,
            "avg_cost":      avg_cost,
            "live_price":    live,
            "prev_close":    prev,
            "invested":      invested,
            "current_value": current_value,
            "gain_loss":     gain_loss,
            "gain_loss_pct": gain_loss_pct,
            "day_pnl":       day_pnl,
            "day_pnl_pct":   day_pnl_pct,
        })

    if not rows:
        return {"positions": [], "summary": {}}

    pdf = pd.DataFrame(rows)

    # ── Position weight ──────────────────────────────────────────────────
    total = pdf["current_value"].sum()
    pdf["weight_pct"] = ((pdf["current_value"] / total) * 100).round(2)

    # Sort by biggest position first
    pdf = pdf.sort_values("current_value", ascending=False)

    # ── Portfolio summary ────────────────────────────────────────────────
    total_invested = round(pdf["invested"].sum(), 2)
    total_value    = round(pdf["current_value"].sum(), 2)
    total_gain     = round(total_value - total_invested, 2)
    total_gain_pct = round((total_gain / total_invested) * 100, 2) if total_invested else 0
    total_day_pnl  = round(pdf["day_pnl"].sum(), 2)

    best    = pdf.loc[pdf["gain_loss_pct"].idxmax()]
    worst   = pdf.loc[pdf["gain_loss_pct"].idxmin()]
    biggest = pdf.loc[pdf["weight_pct"].idxmax()]

    return {
        "positions": pdf.to_dict(orient="records"),
        "summary": {
            "total_invested":  total_invested,
            "total_value":     total_value,
            "total_gain":      total_gain,
            "total_gain_pct":  total_gain_pct,
            "total_day_pnl":   total_day_pnl,
            "best_ticker":     best["ticker"],
            "best_pct":        best["gain_loss_pct"],
            "worst_ticker":    worst["ticker"],
            "worst_pct":       worst["gain_loss_pct"],
            "biggest_ticker":  biggest["ticker"],
            "biggest_weight":  biggest["weight_pct"],
            "num_positions":   len(pdf),
        }
    }
