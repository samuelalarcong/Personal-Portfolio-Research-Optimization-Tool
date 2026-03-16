"""
prices.py
---------
Fetches today's live price and yesterday's closing price
from Yahoo Finance for every ticker in the portfolio.
"""

import yfinance as yf


def fetch_prices(tickers: list) -> dict:
    """
    For each ticker, fetch:
      - live  : today's latest closing price
      - prev  : yesterday's closing price (used to calculate today's move)

    Returns:
      {
        "AAPL": { "live": 213.49, "prev": 212.10 },
        "MSFT": { "live": 415.20, "prev": 418.30 },
        ...
      }
    """
    result = {}

    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="2d", interval="1d").dropna()

            live = round(float(hist["Close"].iloc[-1]), 2)
            prev = round(float(hist["Close"].iloc[-2]), 2) if len(hist) >= 2 else live

            result[ticker] = {"live": live, "prev": prev}

        except Exception:
            # If Yahoo Finance can't find the ticker, store None
            result[ticker] = {"live": None, "prev": None}

    return result
