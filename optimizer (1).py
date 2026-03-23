"""
optimizer.py
------------
Phase 2 — Portfolio Optimization

1. Mean-variance optimization (Markowitz)
   - Finds the portfolio weights that maximize Sharpe ratio
   - Finds the minimum volatility portfolio

2. Risk-adjusted return analysis
   - Compares each holding's contribution to risk vs return

3. Rebalancing suggestions
   - Compares current weights vs optimal weights
   - Generates plain-English recommendations

4. New capital allocation
   - Given $X of new money, recommends where to put it
"""

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_returns(tickers: list, period: str = "1y") -> pd.DataFrame:
    """Download historical prices and return daily returns DataFrame."""
    raw = yf.download(tickers, period=period, interval="1d",
                      auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame(name=tickers[0])
    raw = raw[tickers] if all(t in raw.columns for t in tickers) else raw
    return raw.pct_change().dropna()


def _portfolio_stats(weights: np.ndarray, mean_returns: np.ndarray,
                     cov_matrix: np.ndarray, rf: float = 0.045) -> dict:
    """
    Given weights, return annualised return, volatility, Sharpe.
    cov_matrix must be ANNUALISED (already multiplied by 252).
    port_vol = sqrt(w @ cov_annual @ w)  -- no extra sqrt(252)
    port_return = mean_daily_returns @ w * 252
    sharpe = (port_return - rf) / port_vol
    """
    port_return = float(np.dot(weights, mean_returns) * 252)
    port_vol    = float(np.sqrt(weights @ cov_matrix @ weights))  # cov already annualised
    sharpe      = (port_return - rf) / port_vol if port_vol > 0 else 0
    return {"return": port_return, "volatility": port_vol, "sharpe": sharpe}


# ─────────────────────────────────────────────────────────────────────────────
# MEAN-VARIANCE OPTIMIZATION
# ─────────────────────────────────────────────────────────────────────────────

def run_optimization(tickers: list, current_weights: list,
                     period: str = "5y") -> dict:
    """
    Run Markowitz mean-variance optimization.
    Returns:
      - max_sharpe_weights  : weights that maximize Sharpe ratio
      - min_vol_weights     : weights that minimize volatility
      - current_stats       : stats for current portfolio
      - max_sharpe_stats    : stats for max Sharpe portfolio
      - min_vol_stats       : stats for min vol portfolio
      - efficient_frontier  : list of (vol, return) points
    """
    returns = _get_returns(tickers, period)
    valid   = [t for t in tickers if t in returns.columns]

    if len(valid) < 2:
        return {"error": "Need at least 2 tickers with price history."}

    returns      = returns[valid]
    mean_returns = returns.mean().values
    cov_matrix   = returns.cov().values * 252  # annualised — _portfolio_stats expects annual cov
    n            = len(valid)

    # Current portfolio stats
    w_current     = np.array([current_weights[tickers.index(t)] for t in valid])
    w_current     = w_current / w_current.sum()
    current_stats = _portfolio_stats(w_current, mean_returns, cov_matrix)

    # Constraints: weights sum to 1, each weight between 1% and 40%
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds      = tuple((0.01, 0.40) for _ in range(n))
    w0          = np.array([1 / n] * n)

    # ── Maximize Sharpe (minimize negative Sharpe) ───────────────────────
    def neg_sharpe(w):
        s = _portfolio_stats(w, mean_returns, cov_matrix)
        return -s["sharpe"]

    res_sharpe = minimize(neg_sharpe, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-9})

    # ── Minimize Volatility ──────────────────────────────────────────────
    def portfolio_vol(w):
        return float(np.sqrt(w @ cov_matrix @ w))  # cov already annualised

    res_vol = minimize(portfolio_vol, w0, method="SLSQP",
                       bounds=bounds, constraints=constraints,
                       options={"maxiter": 1000, "ftol": 1e-9})

    max_sharpe_w    = res_sharpe.x / res_sharpe.x.sum()
    min_vol_w       = res_vol.x   / res_vol.x.sum()
    max_sharpe_stats = _portfolio_stats(max_sharpe_w, mean_returns, cov_matrix)
    min_vol_stats    = _portfolio_stats(min_vol_w,    mean_returns, cov_matrix)

    # ── Efficient frontier (100 points) ──────────────────────────────────
    target_returns = np.linspace(
        min(mean_returns) * 252,
        max(mean_returns) * 252,
        60
    )
    frontier = []
    for target in target_returns:
        cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_returns) * 252 - t},
        ]
        r = minimize(portfolio_vol, w0, method="SLSQP",
                     bounds=bounds, constraints=cons,
                     options={"maxiter": 500})
        if r.success:
            frontier.append({
                "volatility": round(r.fun * 100, 2),
                "return":     round(target * 100, 2),
            })

    return {
        "tickers":           valid,
        "current_weights":   [round(float(w) * 100, 2) for w in w_current],
        "max_sharpe_weights": [round(float(w) * 100, 2) for w in max_sharpe_w],
        "min_vol_weights":   [round(float(w) * 100, 2) for w in min_vol_w],
        "current_stats":     {k: round(v * 100, 2) if k != "sharpe" else round(v, 2)
                              for k, v in current_stats.items()},
        "max_sharpe_stats":  {k: round(v * 100, 2) if k != "sharpe" else round(v, 2)
                              for k, v in max_sharpe_stats.items()},
        "min_vol_stats":     {k: round(v * 100, 2) if k != "sharpe" else round(v, 2)
                              for k, v in min_vol_stats.items()},
        "efficient_frontier": frontier,
    }


# ─────────────────────────────────────────────────────────────────────────────
# RISK-ADJUSTED RETURN PER HOLDING
# ─────────────────────────────────────────────────────────────────────────────

def risk_adjusted_analysis(tickers: list, period: str = "5y") -> list:
    """
    For each holding calculate:
      - Annualised return
      - Annualised volatility
      - Sharpe ratio
      - Max drawdown
    Lets you see which stocks are pulling their weight.
    """
    returns = _get_returns(tickers, period)
    rf_daily = 0.045 / 252

    results = []
    for ticker in tickers:
        if ticker not in returns.columns:
            continue
        r   = returns[ticker]
        ann_return = round(float(r.mean() * 252 * 100), 2)
        ann_vol    = round(float(r.std()  * np.sqrt(252) * 100), 2)
        sharpe     = round(float((r - rf_daily).mean() /
                                  (r - rf_daily).std() * np.sqrt(252)), 2)
        cum        = (1 + r).cumprod()
        drawdown   = round(float(((cum - cum.cummax()) / cum.cummax()).min() * 100), 2)

        results.append({
            "ticker":      ticker,
            "ann_return":  ann_return,
            "ann_vol":     ann_vol,
            "sharpe":      sharpe,
            "max_drawdown": drawdown,
            "verdict":     _verdict(sharpe, ann_vol),
        })

    return sorted(results, key=lambda x: x["sharpe"], reverse=True)


def _verdict(sharpe: float, vol: float) -> str:
    if sharpe > 1.5:  return "⭐ Strong"
    if sharpe > 0.8:  return "✅ Good"
    if sharpe > 0.3:  return "⚠️ Average"
    return "❌ Weak"


# ─────────────────────────────────────────────────────────────────────────────
# REBALANCING SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_rebalancing_suggestions(tickers: list, current_weights: list,
                                 optimal_weights: list,
                                 total_value: float,
                                 threshold: float = 2.0) -> list:
    """
    Compare current weights vs optimal weights.
    Only flag positions where the difference exceeds threshold %.
    Returns plain-English action items.
    """
    suggestions = []

    for ticker, current, optimal in zip(tickers, current_weights, optimal_weights):
        diff = optimal - current

        if abs(diff) < threshold:
            continue

        dollar_change = (diff / 100) * total_value
        action        = "Increase" if diff > 0 else "Reduce"
        direction     = "underweight vs optimal" if diff > 0 else "overweight vs optimal"

        suggestions.append({
            "ticker":        ticker,
            "current_pct":   round(current, 2),
            "optimal_pct":   round(optimal, 2),
            "diff_pct":      round(diff, 2),
            "dollar_change": round(dollar_change, 2),
            "action":        action,
            "direction":     direction,
            "message":       (
                f"{action} **{ticker}** by {abs(diff):.1f}% "
                f"({'+' if dollar_change > 0 else ''}${dollar_change:,.0f})  —  "
                f"{direction}"
            ),
        })

    return sorted(suggestions, key=lambda x: abs(x["diff_pct"]), reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# NEW CAPITAL ALLOCATION
# ─────────────────────────────────────────────────────────────────────────────

def allocate_new_capital(tickers: list, current_values: list,
                          optimal_weights: list, new_capital: float) -> list:
    """
    Given $X of new money, figure out where to put it
    to move the portfolio closer to the optimal allocation.

    Logic:
      new_total   = current_total + new_capital
      target_$    = new_total × optimal_weight
      to_buy_$    = target_$ - current_$
      Only buy (never sell) — allocate capital to underweight positions.
    """
    total_current = sum(current_values)
    new_total     = total_current + new_capital

    allocations = []
    remaining   = new_capital

    for ticker, cur_val, opt_w in zip(tickers, current_values, optimal_weights):
        target_val = new_total * (opt_w / 100)
        to_buy     = target_val - cur_val

        if to_buy > 0:
            allocations.append({
                "ticker":       ticker,
                "current_val":  round(cur_val, 2),
                "target_val":   round(target_val, 2),
                "to_buy":       round(min(to_buy, remaining), 2),
                "current_pct":  round((cur_val / total_current) * 100, 2),
                "optimal_pct":  round(opt_w, 2),
            })

    # Sort by biggest opportunity first
    allocations = sorted(allocations, key=lambda x: x["to_buy"], reverse=True)

    # Cap at available capital
    total_needed = sum(a["to_buy"] for a in allocations)
    if total_needed > new_capital:
        scale = new_capital / total_needed
        for a in allocations:
            a["to_buy"] = round(a["to_buy"] * scale, 2)

    return [a for a in allocations if a["to_buy"] > 0]
