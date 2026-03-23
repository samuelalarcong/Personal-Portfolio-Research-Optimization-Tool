"""
analytics.py
------------
All advanced calculations:
  - Performance vs benchmark (SPY)
  - Risk metrics: volatility, Sharpe ratio, max drawdown, beta
  - Sector exposure
  - Correlation matrix between holdings
"""

import numpy as np
import pandas as pd
import yfinance as yf


# ─────────────────────────────────────────────────────────────────────────────
# BENCHMARK PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

def get_performance_vs_benchmark(tickers: list, weights: list, benchmark: str = "SPY", period: str = "5y") -> dict:
    """
    Compare portfolio cumulative return vs benchmark over a given period.
    Returns daily cumulative returns for both portfolio and benchmark.
    """
    all_tickers = list(set(tickers + [benchmark]))

    raw = yf.download(all_tickers, period=period, interval="1d", auto_adjust=True, progress=False)["Close"]

    if isinstance(raw, pd.Series):
        raw = raw.to_frame()

    raw = raw.dropna(how="all")

    # Daily returns
    returns = raw.pct_change().dropna()

    # Portfolio daily return = weighted sum of individual returns
    portfolio_tickers = [t for t in tickers if t in returns.columns]
    w = np.array([weights[tickers.index(t)] for t in portfolio_tickers])
    w = w / w.sum()  # normalize

    portfolio_returns = returns[portfolio_tickers].dot(w)
    benchmark_returns = returns[benchmark] if benchmark in returns.columns else None

    # Cumulative returns
    portfolio_cum = (1 + portfolio_returns).cumprod() - 1
    benchmark_cum = (1 + benchmark_returns).cumprod() - 1 if benchmark_returns is not None else None

    return {
        "dates":          portfolio_cum.index.strftime("%Y-%m-%d").tolist(),
        "portfolio":      (portfolio_cum * 100).round(2).tolist(),
        "benchmark":      (benchmark_cum * 100).round(2).tolist() if benchmark_cum is not None else [],
        "benchmark_name": benchmark,
        "portfolio_total_return": round(float(portfolio_cum.iloc[-1]) * 100, 2),
        "benchmark_total_return": round(float(benchmark_cum.iloc[-1]) * 100, 2) if benchmark_cum is not None else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RISK METRICS
# ─────────────────────────────────────────────────────────────────────────────

def get_risk_metrics(tickers: list, weights: list, benchmark: str = "SPY", period: str = "5y") -> dict:
    """
    Calculate:
      - Annualised volatility
      - Sharpe ratio (risk-free rate = 4.5%)
      - Max drawdown
      - Beta vs benchmark
    """
    all_tickers = list(set(tickers + [benchmark]))
    raw = yf.download(all_tickers, period=period, interval="1d", auto_adjust=True, progress=False)["Close"]

    if isinstance(raw, pd.Series):
        raw = raw.to_frame()

    returns = raw.pct_change().dropna()

    portfolio_tickers = [t for t in tickers if t in returns.columns]
    w = np.array([weights[tickers.index(t)] for t in portfolio_tickers])
    w = w / w.sum()

    port_returns = returns[portfolio_tickers].dot(w)

    # ── Volatility (annualised) ──────────────────────────────────────────
    volatility = round(float(port_returns.std() * np.sqrt(252) * 100), 2)

    # ── Sharpe Ratio ─────────────────────────────────────────────────────
    risk_free_daily = 0.045 / 252
    excess = port_returns - risk_free_daily
    sharpe = round(float(excess.mean() / excess.std() * np.sqrt(252)), 2)

    # ── Max Drawdown ─────────────────────────────────────────────────────
    cum = (1 + port_returns).cumprod()
    rolling_max = cum.cummax()
    drawdown = (cum - rolling_max) / rolling_max
    max_drawdown = round(float(drawdown.min() * 100), 2)

    # ── Beta vs Benchmark ────────────────────────────────────────────────
    beta = None
    if benchmark in returns.columns:
        bench_ret = returns[benchmark]
        aligned = pd.concat([port_returns, bench_ret], axis=1).dropna()
        aligned.columns = ["portfolio", "benchmark"]
        cov = aligned.cov()
        beta = round(float(cov.loc["portfolio", "benchmark"] / cov.loc["benchmark", "benchmark"]), 2)

    # ── Drawdown series for chart ────────────────────────────────────────
    drawdown_series = (drawdown * 100).round(2)

    return {
        "volatility":    volatility,
        "sharpe":        sharpe,
        "max_drawdown":  max_drawdown,
        "beta":          beta,
        "dates":         drawdown_series.index.strftime("%Y-%m-%d").tolist(),
        "drawdown_series": drawdown_series.tolist(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR EXPOSURE
# ─────────────────────────────────────────────────────────────────────────────

def get_sector_exposure(tickers: list, weights: list) -> dict:
    """
    Fetch sector for each ticker from Yahoo Finance.
    ETFs don't have a sector — we use a manual mapping for the most common ones.
    Returns sector weights as % of portfolio.
    """

    # Manual mapping for common ETFs that Yahoo Finance returns no sector for
    ETF_SECTOR_MAP = {
        # Broad market
        "SPY":  "Broad Market ETF",
        "IVV":  "Broad Market ETF",
        "VOO":  "Broad Market ETF",
        "VTI":  "Broad Market ETF",
        "ITOT": "Broad Market ETF",
        # Tech / Growth
        "QQQ":  "Technology ETF",
        "QQQM": "Technology ETF",
        "VGT":  "Technology ETF",
        "XLK":  "Technology ETF",
        # Dividends
        "SCHD": "Dividend ETF",
        "VYM":  "Dividend ETF",
        "DVY":  "Dividend ETF",
        # Real estate
        "VNQI": "Real Estate ETF",
        "VNQ":  "Real Estate ETF",
        "XLRE": "Real Estate ETF",
        # Commodities
        "GLD":  "Gold / Commodities",
        "IAU":  "Gold / Commodities",
        "SLV":  "Silver / Commodities",
        "USO":  "Oil / Commodities",
        "GSG":  "Oil / Commodities",
        # Bonds
        "BND":  "Bonds ETF",
        "AGG":  "Bonds ETF",
        "TLT":  "Bonds ETF",
        "LQD":  "Bonds ETF",
        # International
        "EFA":  "International ETF",
        "VEA":  "International ETF",
        "EEM":  "Emerging Markets ETF",
        "VWO":  "Emerging Markets ETF",
        # Small / Mid cap
        "IJR":  "Small Cap ETF",
        "IWM":  "Small Cap ETF",
        "VO":   "Mid Cap ETF",
    }

    sector_weights = {}

    for ticker, weight in zip(tickers, weights):
        # Check manual ETF map first
        if ticker in ETF_SECTOR_MAP:
            sector = ETF_SECTOR_MAP[ticker]
        else:
            # Try Yahoo Finance for individual stocks
            try:
                info   = yf.Ticker(ticker).info
                sector = info.get("sector") or info.get("quoteType", "Unknown")
                # quoteType returns ETF/EQUITY/etc — clean it up
                if sector == "ETF":
                    sector = f"{ticker} ETF"
                elif not sector or sector == "Unknown":
                    sector = "Other"
            except Exception:
                sector = "Other"

        sector_weights[sector] = sector_weights.get(sector, 0) + weight

    # Normalize to 100%
    total = sum(sector_weights.values())
    sector_pct = {k: round((v / total) * 100, 2) for k, v in sector_weights.items()}

    # Sort by weight descending
    sector_pct = dict(sorted(sector_pct.items(), key=lambda x: x[1], reverse=True))

    return sector_pct


# ─────────────────────────────────────────────────────────────────────────────
# CORRELATION MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def get_correlation_matrix(tickers: list, period: str = "5y") -> dict:
    """
    Calculate correlation between all holdings based on daily returns.
    Returns a dict with tickers and the correlation matrix values.
    """
    raw = yf.download(tickers, period=period, interval="1d", auto_adjust=True, progress=False)["Close"]

    if isinstance(raw, pd.Series):
        raw = raw.to_frame(name=tickers[0])

    returns = raw.pct_change().dropna()

    # Keep only tickers we have data for
    valid = [t for t in tickers if t in returns.columns]
    corr  = returns[valid].corr().round(2)

    return {
        "tickers": valid,
        "matrix":  corr.values.tolist(),
    }
