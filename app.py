"""
app.py — Full Phase 1 Portfolio Dashboard
==========================================
Features:
  - Portfolio holdings from Excel
  - Live prices from Yahoo Finance
  - Allocation and position weights
  - Performance vs SPY benchmark
  - Risk metrics (volatility, Sharpe, drawdown, beta)
  - Sector exposure
  - Correlation matrix

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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  Holdings",
    "📈  Performance",
    "⚠️  Risk",
    "🏭  Sectors",
    "🔗  Correlation",
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
        fig5.update_layout(**CHART_LAYOUT, xaxis_title="Weight %",
                           margin=dict(t=10, b=20, l=10, r=60),
                           xaxis=dict(gridcolor="#2a2d3e"), yaxis=dict(gridcolor="rgba(0,0,0,0)"))
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
