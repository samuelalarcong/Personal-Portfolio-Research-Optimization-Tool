"""
app.py — Phase 1 + Phase 2 Portfolio Dashboard
===============================================
RUN:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data      import load_client, CLIENTS
from prices    import fetch_prices
from metrics   import calculate
from analytics import (
    get_performance_vs_benchmark,
    get_risk_metrics,
    get_sector_exposure,
    get_correlation_matrix,
)
from optimizer import (
    run_optimization,
    risk_adjusted_analysis,
    get_rebalancing_suggestions,
    allocate_new_capital,
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Portfolio Dashboard", page_icon="📈", layout="wide")

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.4rem; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Portfolio")
    st.divider()
    client    = st.selectbox("Client",    CLIENTS)
    benchmark = st.selectbox("Benchmark", ["SPY", "QQQ", "IVV", "VTI"])
    period    = st.selectbox("Period",    ["3mo", "6mo", "1y", "2y", "5y"], index=2)
    st.divider()
    refresh = st.button("🔄 Refresh all data", use_container_width=True)
    st.caption("Data from Yahoo Finance")


# ─────────────────────────────────────────────────────────────────────────────
# CACHED DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Fetching live prices...")
def get_portfolio(client_name):
    df        = load_client(client_name)
    price_map = fetch_prices(df["ticker"].tolist())
    return calculate(df, price_map)

@st.cache_data(ttl=300, show_spinner="Loading performance data...")
def get_perf(tickers, weights, bench, per):
    return get_performance_vs_benchmark(list(tickers), list(weights), bench, per)

@st.cache_data(ttl=300, show_spinner="Calculating risk metrics...")
def get_risk(tickers, weights, bench, per):
    return get_risk_metrics(list(tickers), list(weights), bench, per)

@st.cache_data(ttl=300, show_spinner="Fetching sector data...")
def get_sectors(tickers, weights):
    return get_sector_exposure(list(tickers), list(weights))

@st.cache_data(ttl=300, show_spinner="Calculating correlations...")
def get_corr(tickers, per):
    return get_correlation_matrix(list(tickers), per)


if refresh:
    st.cache_data.clear()

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

data      = get_portfolio(client)
summary   = data["summary"]
positions = pd.DataFrame(data["positions"])
tickers   = tuple(positions["ticker"].tolist())
weights   = tuple(positions["weight_pct"].tolist())


# ─────────────────────────────────────────────────────────────────────────────
# TOP METRIC CARDS
# ─────────────────────────────────────────────────────────────────────────────

st.subheader(f"{client}'s Portfolio")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Portfolio Value",   f"${summary['total_value']:,.2f}")
c2.metric("Total Invested",    f"${summary['total_invested']:,.2f}")
c3.metric("Total Gain / Loss", f"${summary['total_gain']:,.2f}",    f"{summary['total_gain_pct']:+.2f}%")
c4.metric("Today's P&L",       f"${summary['total_day_pnl']:,.2f}")
c5.metric("Positions",          summary["num_positions"])

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊  Holdings",
    "📈  Performance",
    "⚠️  Risk",
    "🏭  Sectors",
    "🔗  Correlation",
    "🎯  Optimization",
    "⚖️  Rebalancing",
    "💰  New Capital",
])

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#e2e8f0"),
    margin=dict(t=20, b=20),
    yaxis=dict(gridcolor="#2a2d3e"),
    hovermode="x unified",
)


# ══════════════════════════════════════════════════════
# TAB 1 — HOLDINGS
# ══════════════════════════════════════════════════════

with tab1:
    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.markdown("#### Holdings")
        disp = positions[[
            "ticker","shares","avg_cost","live_price",
            "current_value","gain_loss","gain_loss_pct",
            "day_pnl","day_pnl_pct","weight_pct"
        ]].copy()
        disp.columns = [
            "Ticker","Shares","Avg Cost","Live $",
            "Value","Gain/Loss $","Gain/Loss %",
            "Today $","Today %","Weight %"
        ]
        def clr(v):
            if isinstance(v, (int, float)):
                return f"color: {'#34d399' if v >= 0 else '#f87171'}"
            return ""
        styled = disp.style\
            .format({
                "Avg Cost":"${:.2f}","Live $":"${:.2f}","Value":"${:,.2f}",
                "Gain/Loss $":"${:,.2f}","Gain/Loss %":"{:+.2f}%",
                "Today $":"${:,.2f}","Today %":"{:+.2f}%","Weight %":"{:.1f}%",
            })\
            .applymap(clr, subset=["Gain/Loss $","Gain/Loss %","Today $","Today %"])
        st.dataframe(styled, use_container_width=True, hide_index=True)

    with col_r:
        st.markdown("#### Allocation")
        fig = px.pie(positions, names="ticker", values="weight_pct", hole=0.6,
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=0,b=0,l=0,r=0),
                          legend=dict(font=dict(size=11)))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Gain / Loss per position")
    colors = ["#34d399" if v >= 0 else "#f87171" for v in positions["gain_loss_pct"]]
    fig2 = go.Figure(go.Bar(
        x=positions["ticker"], y=positions["gain_loss_pct"],
        marker_color=colors,
        text=positions["gain_loss_pct"].apply(lambda x: f"{x:+.1f}%"),
        textposition="outside",
    ))
    fig2.update_layout(**CHART_LAYOUT, yaxis_title="Gain / Loss %")
    st.plotly_chart(fig2, use_container_width=True)

    b1, b2, b3 = st.columns(3)
    b1.success(f"**Best:** {summary['best_ticker']}  {summary['best_pct']:+.2f}%")
    b2.error(  f"**Worst:** {summary['worst_ticker']}  {summary['worst_pct']:+.2f}%")
    b3.info(   f"**Biggest:** {summary['biggest_ticker']}  {summary['biggest_weight']:.1f}%")


# ══════════════════════════════════════════════════════
# TAB 2 — PERFORMANCE VS BENCHMARK
# ══════════════════════════════════════════════════════

with tab2:
    st.markdown(f"#### Portfolio vs {benchmark}  —  {period}")
    perf = get_perf(tickers, weights, benchmark, period)

    p1, p2, p3 = st.columns(3)
    port_ret  = perf["portfolio_total_return"]
    bench_ret = perf["benchmark_total_return"]
    alpha     = round(port_ret - bench_ret, 2) if bench_ret is not None else None

    p1.metric("Portfolio return",       f"{port_ret:+.2f}%")
    p2.metric(f"{benchmark} return",    f"{bench_ret:+.2f}%" if bench_ret else "—")
    p3.metric("Alpha vs benchmark",     f"{alpha:+.2f}%" if alpha else "—")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=perf["dates"], y=perf["portfolio"], name="Portfolio",
        line=dict(color="#6366f1", width=2),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.1)",
    ))
    if perf["benchmark"]:
        fig3.add_trace(go.Scatter(
            x=perf["dates"], y=perf["benchmark"], name=benchmark,
            line=dict(color="#94a3b8", width=1.5, dash="dash"),
        ))
    fig3.add_hline(y=0, line_color="#334155", line_width=1)
    fig3.update_layout(**CHART_LAYOUT, yaxis_title="Cumulative Return %",
                       legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 3 — RISK METRICS
# ══════════════════════════════════════════════════════

with tab3:
    st.markdown("#### Risk metrics")
    risk = get_risk(tickers, weights, benchmark, period)

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Volatility (ann.)",      f"{risk['volatility']}%")
    r2.metric("Sharpe Ratio",           f"{risk['sharpe']}")
    r3.metric("Max Drawdown",           f"{risk['max_drawdown']}%")
    r4.metric(f"Beta vs {benchmark}",   f"{risk['beta']}" if risk['beta'] else "—")

    st.markdown(f"""
    > **Volatility {risk['volatility']}%** — how much the portfolio swings per year.
    > **Sharpe {risk['sharpe']}** — return per unit of risk. Above 1.0 is good, above 2.0 is great.
    > **Max Drawdown {risk['max_drawdown']}%** — worst peak-to-trough loss in this period.
    > **Beta {risk['beta']}** — sensitivity to {benchmark}. Above 1.0 = more volatile than market.
    """)

    st.markdown("#### Drawdown over time")
    fig4 = go.Figure(go.Scatter(
        x=risk["dates"], y=risk["drawdown_series"],
        fill="tozeroy", fillcolor="rgba(248,113,113,0.15)",
        line=dict(color="#f87171", width=1.5), name="Drawdown",
    ))
    fig4.update_layout(**CHART_LAYOUT, yaxis_title="Drawdown %")
    st.plotly_chart(fig4, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 4 — SECTOR EXPOSURE
# ══════════════════════════════════════════════════════

with tab4:
    st.markdown("#### Sector exposure")
    sectors = get_sectors(tickers, weights)

    s1, s2 = st.columns(2)

    with s1:
        fig5 = go.Figure(go.Bar(
            x=list(sectors.values()), y=list(sectors.keys()),
            orientation="h", marker_color="#6366f1",
            text=[f"{v:.1f}%" for v in sectors.values()],
            textposition="outside",
        ))
        fig5.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"),
            xaxis_title="Weight %",
            margin=dict(t=10, b=20, l=10, r=60),
            xaxis=dict(gridcolor="#2a2d3e"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig5, use_container_width=True)

    with s2:
        fig6 = px.pie(names=list(sectors.keys()), values=list(sectors.values()),
                      hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig6.update_traces(textposition="inside", textinfo="percent+label")
        fig6.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=0,b=0,l=0,r=0), showlegend=False)
        st.plotly_chart(fig6, use_container_width=True)

    top_name = list(sectors.keys())[0]
    top_val  = list(sectors.values())[0]
    if top_val > 40:
        st.warning(f"⚠️ High concentration: **{top_name}** is {top_val:.1f}% of the portfolio.")
    else:
        st.success("✅ Portfolio is reasonably diversified across sectors.")


# ══════════════════════════════════════════════════════
# TAB 5 — CORRELATION
# ══════════════════════════════════════════════════════

with tab5:
    st.markdown("#### Correlation between holdings")
    st.caption("1.0 = move together perfectly  |  0 = no relationship  |  -1.0 = move in opposite directions")

    corr = get_corr(tickers, period)

    fig7 = go.Figure(go.Heatmap(
        z=corr["matrix"], x=corr["tickers"], y=corr["tickers"],
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr["matrix"]],
        texttemplate="%{text}", textfont=dict(size=10),
    ))
    fig7.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"),
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig7, use_container_width=True)

    st.markdown("#### Highly correlated pairs  (> 0.80)")
    mat   = corr["matrix"]
    tkrs  = corr["tickers"]
    pairs = []
    for i in range(len(tkrs)):
        for j in range(i+1, len(tkrs)):
            v = mat[i][j]
            if abs(v) > 0.80:
                pairs.append({
                    "Pair":        f"{tkrs[i]} — {tkrs[j]}",
                    "Correlation": round(v, 2),
                    "Meaning":     "Move together" if v > 0 else "Move opposite",
                })
    if pairs:
        st.dataframe(pd.DataFrame(pairs), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No highly correlated pairs. Good diversification.")


# ══════════════════════════════════════════════════════
# TAB 6 — OPTIMIZATION
# ══════════════════════════════════════════════════════

with tab6:
    st.markdown("#### Mean-variance portfolio optimization")
    st.caption("Finds the weights that maximize risk-adjusted return (Sharpe ratio) and minimum volatility.")

    with st.spinner("Running Markowitz optimization..."):
        opt = run_optimization(list(tickers), list(weights), period)

    if "error" in opt:
        st.error(opt["error"])
    else:
        # ── Stats comparison ─────────────────────────────────────────────
        st.markdown("#### Current vs Optimized portfolios")
        o1, o2, o3 = st.columns(3)

        with o1:
            st.markdown("**Current portfolio**")
            st.metric("Return",     f"{opt['current_stats']['return']}%")
            st.metric("Volatility", f"{opt['current_stats']['volatility']}%")
            st.metric("Sharpe",     f"{opt['current_stats']['sharpe']}")

        with o2:
            st.markdown("**Max Sharpe (best risk/return)**")
            delta_r = round(opt['max_sharpe_stats']['return']     - opt['current_stats']['return'], 2)
            delta_v = round(opt['max_sharpe_stats']['volatility'] - opt['current_stats']['volatility'], 2)
            delta_s = round(opt['max_sharpe_stats']['sharpe']     - opt['current_stats']['sharpe'], 2)
            st.metric("Return",     f"{opt['max_sharpe_stats']['return']}%",     f"{delta_r:+.2f}%")
            st.metric("Volatility", f"{opt['max_sharpe_stats']['volatility']}%", f"{delta_v:+.2f}%")
            st.metric("Sharpe",     f"{opt['max_sharpe_stats']['sharpe']}",      f"{delta_s:+.2f}")

        with o3:
            st.markdown("**Min Volatility (safest)**")
            delta_r2 = round(opt['min_vol_stats']['return']     - opt['current_stats']['return'], 2)
            delta_v2 = round(opt['min_vol_stats']['volatility'] - opt['current_stats']['volatility'], 2)
            delta_s2 = round(opt['min_vol_stats']['sharpe']     - opt['current_stats']['sharpe'], 2)
            st.metric("Return",     f"{opt['min_vol_stats']['return']}%",     f"{delta_r2:+.2f}%")
            st.metric("Volatility", f"{opt['min_vol_stats']['volatility']}%", f"{delta_v2:+.2f}%")
            st.metric("Sharpe",     f"{opt['min_vol_stats']['sharpe']}",      f"{delta_s2:+.2f}")

        st.divider()

        # ── Weight comparison bar chart ──────────────────────────────────
        st.markdown("#### Current vs optimal weights per position")
        weight_df = pd.DataFrame({
            "Ticker":       opt["tickers"],
            "Current %":    opt["current_weights"],
            "Max Sharpe %": opt["max_sharpe_weights"],
            "Min Vol %":    opt["min_vol_weights"],
        })
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(name="Current",    x=weight_df["Ticker"], y=weight_df["Current %"],    marker_color="#94a3b8"))
        fig_w.add_trace(go.Bar(name="Max Sharpe", x=weight_df["Ticker"], y=weight_df["Max Sharpe %"], marker_color="#6366f1"))
        fig_w.add_trace(go.Bar(name="Min Vol",    x=weight_df["Ticker"], y=weight_df["Min Vol %"],    marker_color="#34d399"))
        fig_w.update_layout(
            barmode="group", yaxis_title="Weight %",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e2e8f0"), margin=dict(t=20, b=20),
            yaxis=dict(gridcolor="#2a2d3e"),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig_w, use_container_width=True)

        # ── Efficient frontier ───────────────────────────────────────────
        if opt["efficient_frontier"]:
            st.markdown("#### Efficient frontier")
            st.caption("Each dot is a possible portfolio. The curve shows the best return for each level of risk.")
            ef = pd.DataFrame(opt["efficient_frontier"])
            fig_ef = go.Figure()
            fig_ef.add_trace(go.Scatter(
                x=ef["volatility"], y=ef["return"],
                mode="lines", name="Efficient frontier",
                line=dict(color="#6366f1", width=2),
            ))
            # Plot current portfolio
            fig_ef.add_trace(go.Scatter(
                x=[opt["current_stats"]["volatility"]],
                y=[opt["current_stats"]["return"]],
                mode="markers", name="Current",
                marker=dict(color="#f59e0b", size=12, symbol="star"),
            ))
            # Plot max Sharpe
            fig_ef.add_trace(go.Scatter(
                x=[opt["max_sharpe_stats"]["volatility"]],
                y=[opt["max_sharpe_stats"]["return"]],
                mode="markers", name="Max Sharpe",
                marker=dict(color="#34d399", size=12, symbol="diamond"),
            ))
            # Plot min vol
            fig_ef.add_trace(go.Scatter(
                x=[opt["min_vol_stats"]["volatility"]],
                y=[opt["min_vol_stats"]["return"]],
                mode="markers", name="Min Volatility",
                marker=dict(color="#f87171", size=12, symbol="circle"),
            ))
            fig_ef.update_layout(
                xaxis_title="Annualised Volatility %",
                yaxis_title="Annualised Return %",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"), margin=dict(t=20, b=20),
                xaxis=dict(gridcolor="#2a2d3e"), yaxis=dict(gridcolor="#2a2d3e"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_ef, use_container_width=True)

        # ── Risk-adjusted per holding ────────────────────────────────────
        st.markdown("#### Risk-adjusted return per holding")
        with st.spinner("Analysing each position..."):
            ra = risk_adjusted_analysis(list(tickers), period)
        ra_df = pd.DataFrame(ra)
        ra_df.columns = ["Ticker", "Ann. Return %", "Ann. Vol %", "Sharpe", "Max DD %", "Verdict"]

        def color_sharpe(val):
            if isinstance(val, float):
                if val > 1.5: return "color: #34d399"
                if val > 0.8: return "color: #6366f1"
                if val > 0.3: return "color: #f59e0b"
                return "color: #f87171"
            return ""

        styled_ra = ra_df.style\
            .format({"Ann. Return %": "{:+.2f}%", "Ann. Vol %": "{:.2f}%",
                     "Sharpe": "{:.2f}", "Max DD %": "{:.2f}%"})\
            .applymap(color_sharpe, subset=["Sharpe"])
        st.dataframe(styled_ra, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════
# TAB 7 — REBALANCING (broker-ready share counts)
# ══════════════════════════════════════════════════════

with tab7:
    st.markdown("#### ⚖️ Rebalancing — broker-ready orders")
    st.caption("⚠️ Prices from Yahoo Finance last close. Verify in your broker before executing.")

    with st.spinner("Running optimization for rebalancing..."):
        opt_reb = run_optimization(list(tickers), list(weights), period)

    if "error" in opt_reb:
        st.error(opt_reb["error"])
    else:
        rebal_type = st.radio(
            "Optimize for",
            ["Max Sharpe (best return/risk)", "Min Volatility (safest)"],
            horizontal=True,
        )
        optimal_w  = opt_reb["max_sharpe_weights"] if "Sharpe" in rebal_type else opt_reb["min_vol_weights"]
        tkrs_reb   = opt_reb["tickers"]
        total_val  = summary["total_value"]
        pos_lookup = positions.set_index("ticker")

        sells = []
        buys  = []

        for ticker, cur_w, opt_w_val in zip(tkrs_reb, opt_reb["current_weights"], optimal_w):
            diff = opt_w_val - cur_w
            if abs(diff) < 2.0:
                continue
            try:
                price      = float(pos_lookup.loc[ticker, "live_price"])
                cur_shares = float(pos_lookup.loc[ticker, "shares"])
                cur_val    = float(pos_lookup.loc[ticker, "current_value"])
            except Exception:
                continue
            if price <= 0:
                continue

            dollar_change = (diff / 100) * total_val
            shares_count  = int(abs(dollar_change) // price)
            if shares_count < 1:
                continue

            actual_cost  = round(shares_count * price, 2)
            shares_after = int(cur_shares + shares_count) if diff > 0 else int(cur_shares - shares_count)
            w_after      = round(((cur_val + (actual_cost if diff > 0 else -actual_cost)) / total_val) * 100, 2)

            order = {
                "ticker":        ticker,
                "action":        "BUY" if diff > 0 else "SELL",
                "shares_count":  shares_count,
                "price":         round(price, 2),
                "actual_cost":   actual_cost,
                "shares_before": int(cur_shares),
                "shares_after":  shares_after,
                "w_before":      round(cur_w, 2),
                "w_after":       w_after,
                "w_delta":       round(diff, 2),
                "optimal_w":     round(opt_w_val, 2),
            }
            if diff > 0:
                buys.append(order)
            else:
                sells.append(order)

        if not sells and not buys:
            st.success("✅ Portfolio is already close to optimal. No rebalancing needed.")
        else:
            # ── SELL CARDS ─────────────────────────────────────────────
            if sells:
                st.markdown("#### 🔴 Sell orders")
                cols_s = st.columns(min(len(sells), 4))
                for i, o in enumerate(sells):
                    with cols_s[i % len(cols_s)]:
                        st.markdown(f"""
<div style="background:#1a1d27;border:1px solid #f87171;border-radius:10px;padding:14px 16px;margin-bottom:10px">
  <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px">{o['ticker']}</div>
  <div style="font-size:28px;font-weight:700;color:#f87171;margin-bottom:8px">−{o['shares_count']} shares</div>
  <div style="font-size:12px;color:#94a3b8">@ ${o['price']:,.2f} per share</div>
  <div style="font-size:14px;font-weight:600;color:#fff;margin-top:6px">${o['actual_cost']:,.2f} proceeds</div>
  <hr style="border-color:#2a2d3e;margin:10px 0">
  <div style="font-size:12px;color:#94a3b8">Shares: {o['shares_before']} → <b style="color:#fff">{o['shares_after']}</b></div>
  <div style="font-size:12px;color:#94a3b8;margin-top:3px">Weight: {o['w_before']}% → <b style="color:#f87171">{o['w_after']}%</b></div>
  <div style="font-size:11px;color:#64748b;margin-top:3px">Target: {o['optimal_w']}%</div>
</div>
""", unsafe_allow_html=True)

            # ── BUY CARDS ──────────────────────────────────────────────
            if buys:
                st.markdown("#### 🟢 Buy orders")
                cols_b = st.columns(min(len(buys), 4))
                for i, o in enumerate(buys):
                    with cols_b[i % len(cols_b)]:
                        st.markdown(f"""
<div style="background:#1a1d27;border:1px solid #34d399;border-radius:10px;padding:14px 16px;margin-bottom:10px">
  <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px">{o['ticker']}</div>
  <div style="font-size:28px;font-weight:700;color:#34d399;margin-bottom:8px">+{o['shares_count']} shares</div>
  <div style="font-size:12px;color:#94a3b8">@ ${o['price']:,.2f} per share</div>
  <div style="font-size:14px;font-weight:600;color:#fff;margin-top:6px">${o['actual_cost']:,.2f} total</div>
  <hr style="border-color:#2a2d3e;margin:10px 0">
  <div style="font-size:12px;color:#94a3b8">Shares: {o['shares_before']} → <b style="color:#fff">{o['shares_after']}</b></div>
  <div style="font-size:12px;color:#94a3b8;margin-top:3px">Weight: {o['w_before']}% → <b style="color:#34d399">{o['w_after']}%</b></div>
  <div style="font-size:11px;color:#64748b;margin-top:3px">Target: {o['optimal_w']}%</div>
</div>
""", unsafe_allow_html=True)

            # ── Summary metrics ─────────────────────────────────────────
            st.divider()
            sell_total = sum(o["actual_cost"] for o in sells)
            buy_total  = sum(o["actual_cost"] for o in buys)
            net        = round(sell_total - buy_total, 2)

            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Sell orders",   len(sells))
            sm2.metric("Buy orders",    len(buys))
            sm3.metric("Sell proceeds", f"${sell_total:,.2f}")
            sm4.metric("Net cash", f"${abs(net):,.2f}",
                       "released" if net > 0 else "needed")

            # ── Full detail table ───────────────────────────────────────
            st.divider()
            st.markdown("#### Full order table")
            all_orders = sells + buys
            ord_df = pd.DataFrame(all_orders)[[
                "action", "ticker", "shares_count", "price", "actual_cost",
                "shares_before", "shares_after", "w_before", "w_after", "w_delta"
            ]]
            ord_df.columns = [
                "Action", "Ticker", "Shares", "Price $", "Total $",
                "Before", "After", "Weight Before", "Weight After", "Weight Δ"
            ]

            def clr_action(val):
                if val == "SELL": return "color: #f87171"
                if val == "BUY":  return "color: #34d399"
                return ""

            def clr_wdelta(val):
                if isinstance(val, float):
                    return f"color: {'#34d399' if val > 0 else '#f87171'}"
                return ""

            styled_ord = ord_df.style.format({
                "Price $":       "${:,.2f}",
                "Total $":       "${:,.2f}",
                "Weight Before": "{:.2f}%",
                "Weight After":  "{:.2f}%",
                "Weight Δ":      "{:+.2f}%",
            }).applymap(clr_action, subset=["Action"]).applymap(clr_wdelta, subset=["Weight Δ"])
            st.dataframe(styled_ord, use_container_width=True, hide_index=True)

            # ── Before vs after chart ───────────────────────────────────
            st.divider()
            st.markdown("#### Before vs after weights")
            fig_reb = go.Figure()
            fig_reb.add_trace(go.Bar(
                name="Before", x=tkrs_reb,
                y=opt_reb["current_weights"], marker_color="#94a3b8",
            ))
            fig_reb.add_trace(go.Bar(
                name="Target", x=tkrs_reb,
                y=optimal_w, marker_color="#6366f1",
            ))
            fig_reb.update_layout(
                barmode="group", yaxis_title="Weight %",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e2e8f0"), margin=dict(t=20, b=20),
                yaxis=dict(gridcolor="#2a2d3e"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_reb, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 8 — NEW CAPITAL ALLOCATION (deep version)
# ══════════════════════════════════════════════════════

with tab8:
    st.markdown("#### 💰 New capital allocation")
    st.caption("Enter the amount you want to invest. Get exact share counts at today's price — ready to execute.")

    # ── Inputs ───────────────────────────────────────────────────────────
    i1, i2, i3 = st.columns([1, 1, 1])
    with i1:
        new_capital = st.number_input(
            "Capital to deploy ($)",
            min_value=100.0, max_value=10_000_000.0,
            value=5000.0, step=500.0, format="%.2f",
        )
    with i2:
        optimize_for = st.radio("Strategy", ["Max Sharpe", "Min Volatility"], horizontal=True)
    with i3:
        st.markdown("&nbsp;")
        run_btn = st.button("▶  Calculate", use_container_width=True)

    # ── Portfolio context ────────────────────────────────────────────────
    ctx1, ctx2, ctx3 = st.columns(3)
    ctx1.metric("Current portfolio",  f"${summary['total_value']:,.2f}")
    ctx2.metric("New capital",        f"${new_capital:,.2f}")
    ctx3.metric("Portfolio after",    f"${summary['total_value'] + new_capital:,.2f}")

    st.divider()

    if run_btn:
        with st.spinner("Running optimization and calculating share counts..."):
            opt_cap = run_optimization(list(tickers), list(weights), period)

        if "error" in opt_cap:
            st.error(opt_cap["error"])
        else:
            optimal_w_cap = (
                opt_cap["max_sharpe_weights"]
                if optimize_for == "Max Sharpe"
                else opt_cap["min_vol_weights"]
            )

            tkrs_opt    = opt_cap["tickers"]
            cur_vals    = positions.set_index("ticker").reindex(tkrs_opt)["current_value"].fillna(0).tolist()
            cur_shares  = positions.set_index("ticker").reindex(tkrs_opt)["shares"].fillna(0).tolist()
            prices_now  = positions.set_index("ticker").reindex(tkrs_opt)["live_price"].fillna(0).tolist()
            total_cur   = sum(cur_vals)
            new_total   = total_cur + new_capital

            # ── Calculate exact share counts ──────────────────────────────
            orders      = []
            deployed    = 0.0

            for ticker, cur_val, cur_sh, price, opt_w in zip(
                tkrs_opt, cur_vals, cur_shares, prices_now, optimal_w_cap
            ):
                if price <= 0:
                    continue

                target_val   = new_total * (opt_w / 100)
                gap          = target_val - cur_val

                if gap <= 0:
                    continue

                budget        = min(gap, new_capital - deployed)
                shares_to_buy = int(budget // price)

                if shares_to_buy < 1:
                    continue

                cost           = round(shares_to_buy * price, 2)
                deployed      += cost
                new_shares     = cur_sh + shares_to_buy
                w_before       = round((cur_val / total_cur) * 100, 2)
                w_after        = round(((cur_val + cost) / new_total) * 100, 2)

                orders.append({
                    "ticker":        ticker,
                    "shares_to_buy": shares_to_buy,
                    "price":         round(price, 2),
                    "cost":          cost,
                    "shares_before": int(cur_sh),
                    "shares_after":  int(new_shares),
                    "w_before":      w_before,
                    "w_after":       w_after,
                    "w_delta":       round(w_after - w_before, 2),
                    "target_w":      round(opt_w, 2),
                    "pct_of_new":    round((cost / new_capital) * 100, 2),
                })

                if deployed >= new_capital * 0.99:
                    break

            leftover = round(new_capital - deployed, 2)

            if not orders:
                st.success("✅ Portfolio is already at optimal weights. No buying needed.")
            else:
                # ── BROKER-READY ORDER CARDS ──────────────────────────────
                st.markdown("#### 🛒 Buy orders — ready to execute")
                st.caption("⚠️ Share counts based on Yahoo Finance last closing price. Always verify the live price in your broker before executing — intraday prices may differ slightly.")

                cols = st.columns(min(len(orders), 4))
                for i, o in enumerate(orders):
                    with cols[i % len(cols)]:
                        st.markdown(f"""
<div style="background:#1a1d27;border:1px solid #2a2d3e;border-radius:10px;padding:14px 16px;margin-bottom:10px">
  <div style="font-size:18px;font-weight:700;color:#fff;margin-bottom:2px">{o['ticker']}</div>
  <div style="font-size:28px;font-weight:700;color:#34d399;margin-bottom:8px">+{o['shares_to_buy']} shares</div>
  <div style="font-size:12px;color:#94a3b8">@ ${o['price']:,.2f} per share</div>
  <div style="font-size:14px;font-weight:600;color:#fff;margin-top:6px">${o['cost']:,.2f} total</div>
  <hr style="border-color:#2a2d3e;margin:10px 0">
  <div style="font-size:12px;color:#94a3b8">You own: {o['shares_before']} → <b style="color:#fff">{o['shares_after']} shares</b></div>
  <div style="font-size:12px;color:#94a3b8;margin-top:3px">Weight: {o['w_before']}% → <b style="color:#6366f1">{o['w_after']}%</b></div>
  <div style="font-size:11px;color:#475569;margin-top:3px">{o['pct_of_new']:.1f}% of new capital</div>
</div>
""", unsafe_allow_html=True)

                # ── Cash summary ──────────────────────────────────────────
                st.divider()
                s1, s2, s3 = st.columns(3)
                s1.metric("Total deployed",  f"${deployed:,.2f}")
                s2.metric("Leftover cash",   f"${leftover:,.2f}",
                          "hold or add next month" if leftover > 0 else None)
                s3.metric("Orders",          len(orders))

                # ── Full detail table ─────────────────────────────────────
                st.divider()
                st.markdown("#### Full order table")

                order_df = pd.DataFrame(orders)[[
                    "ticker", "shares_to_buy", "price", "cost",
                    "shares_before", "shares_after",
                    "w_before", "w_after", "w_delta", "target_w"
                ]]
                order_df.columns = [
                    "Ticker", "Shares to Buy", "Price $", "Total Cost $",
                    "Shares Before", "Shares After",
                    "Weight Before", "Weight After", "Weight Δ", "Target Weight"
                ]

                def clr_delta(v):
                    if isinstance(v, float):
                        return f"color: {'#34d399' if v >= 0 else '#f87171'}"
                    return ""

                styled_ord = order_df.style.format({
                    "Price $":       "${:,.2f}",
                    "Total Cost $":  "${:,.2f}",
                    "Weight Before": "{:.2f}%",
                    "Weight After":  "{:.2f}%",
                    "Weight Δ":      "{:+.2f}%",
                    "Target Weight": "{:.2f}%",
                }).applymap(clr_delta, subset=["Weight Δ"])

                st.dataframe(styled_ord, use_container_width=True, hide_index=True)

                # ── Before vs after allocation chart ─────────────────────
                st.divider()
                st.markdown("#### Portfolio allocation — before vs after")

                all_tickers_chart = list(tickers)
                before_w = list(weights)

                # Recalculate after weights for all positions
                new_vals = {}
                for o in orders:
                    new_vals[o["ticker"]] = o["cost"]

                after_w = []
                for t, cur_v in zip(tkrs_opt, cur_vals):
                    added    = new_vals.get(t, 0)
                    after_w.append(round(((cur_v + added) / new_total) * 100, 2))

                fig_ba = go.Figure()
                fig_ba.add_trace(go.Bar(
                    name="Before", x=tkrs_opt, y=[round(cv/total_cur*100,2) for cv in cur_vals],
                    marker_color="#94a3b8",
                ))
                fig_ba.add_trace(go.Bar(
                    name="After", x=tkrs_opt, y=after_w,
                    marker_color="#6366f1",
                ))
                fig_ba.update_layout(
                    barmode="group", yaxis_title="Weight %",
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e2e8f0"), margin=dict(t=20, b=20),
                    yaxis=dict(gridcolor="#2a2d3e"),
                    legend=dict(orientation="h", y=1.1),
                )
                st.plotly_chart(fig_ba, use_container_width=True)

                # ── Plain-English summary ─────────────────────────────────
                st.divider()
                st.markdown("#### Summary")
                top3 = ", ".join(
                    f"{o['shares_to_buy']} shares of {o['ticker']} (${o['cost']:,.0f})"
                    for o in orders[:3]
                )
                st.info(
                    f"**{optimize_for} strategy** recommends deploying **${deployed:,.2f}** "
                    f"of your **${new_capital:,.0f}** across {len(orders)} positions. "
                    f"Priority buys: {top3}. "
                    f"{'Remaining $'+str(leftover)+' stays as cash.' if leftover > 0 else 'Full capital deployed.'}"
                )
