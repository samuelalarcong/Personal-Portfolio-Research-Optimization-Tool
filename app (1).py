"""
app.py — Streamlit Portfolio Dashboard
=======================================
RUN:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data    import load_client, CLIENTS
from prices  import fetch_prices
from metrics import calculate

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📈",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — client selector + refresh
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Portfolio")
    client = st.selectbox("Select client", CLIENTS)
    refresh = st.button("🔄 Refresh prices", use_container_width=True)
    st.caption("Prices from Yahoo Finance")

# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA — cached so it doesn't re-fetch on every interaction
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Fetching live prices from Yahoo Finance...")
def get_portfolio(client_name: str) -> dict:
    df        = load_client(client_name)
    price_map = fetch_prices(df["ticker"].tolist())
    return calculate(df, price_map)


# Clear cache and reload when refresh button is clicked
if refresh:
    st.cache_data.clear()

data    = get_portfolio(client)
summary = data["summary"]
positions = pd.DataFrame(data["positions"])

# ─────────────────────────────────────────────────────────────────────────────
# METRIC CARDS — top row
# ─────────────────────────────────────────────────────────────────────────────

st.subheader(f"{client}'s Portfolio")

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Portfolio Value",
    f"${summary['total_value']:,.2f}",
)
c2.metric(
    "Total Invested",
    f"${summary['total_invested']:,.2f}",
)
c3.metric(
    "Total Gain / Loss",
    f"${summary['total_gain']:,.2f}",
    f"{summary['total_gain_pct']:+.2f}%",
    delta_color="normal",
)
c4.metric(
    "Today's P&L",
    f"${summary['total_day_pnl']:,.2f}",
    delta_color="normal",
)
c5.metric(
    "Positions",
    summary["num_positions"],
)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN CONTENT — table + donut chart
# ─────────────────────────────────────────────────────────────────────────────

left, right = st.columns([2, 1])

# ── Holdings table ────────────────────────────────────────────────────────────
with left:
    st.markdown("#### Holdings")

    display = positions[[
        "ticker", "shares", "avg_cost", "live_price",
        "current_value", "gain_loss", "gain_loss_pct",
        "day_pnl", "day_pnl_pct", "weight_pct"
    ]].copy()

    display.columns = [
        "Ticker", "Shares", "Avg Cost", "Live $",
        "Value", "Gain/Loss $", "Gain/Loss %",
        "Today $", "Today %", "Weight %"
    ]

    # Colour the gain/loss column green or red
    def color_pnl(val):
        if isinstance(val, float) or isinstance(val, int):
            color = "#34d399" if val >= 0 else "#f87171"
            return f"color: {color}"
        return ""

    styled = display.style\
        .format({
            "Avg Cost":    "${:.2f}",
            "Live $":      "${:.2f}",
            "Value":       "${:,.2f}",
            "Gain/Loss $": "${:,.2f}",
            "Gain/Loss %": "{:+.2f}%",
            "Today $":     "${:,.2f}",
            "Today %":     "{:+.2f}%",
            "Weight %":    "{:.1f}%",
        })\
        .applymap(color_pnl, subset=["Gain/Loss $", "Gain/Loss %", "Today $", "Today %"])

    st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Donut chart ───────────────────────────────────────────────────────────────
with right:
    st.markdown("#### Allocation")

    fig = px.pie(
        positions,
        names  = "ticker",
        values = "weight_pct",
        hole   = 0.6,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(
        showlegend    = True,
        margin        = dict(t=0, b=0, l=0, r=0),
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        legend        = dict(font=dict(size=11)),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# BAR CHART — gain/loss per position
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("#### Gain / Loss per position")

colors = ["#34d399" if v >= 0 else "#f87171" for v in positions["gain_loss_pct"]]

fig2 = go.Figure(go.Bar(
    x    = positions["ticker"],
    y    = positions["gain_loss_pct"],
    marker_color = colors,
    text = positions["gain_loss_pct"].apply(lambda x: f"{x:+.1f}%"),
    textposition = "outside",
))
fig2.update_layout(
    yaxis_title   = "Gain / Loss %",
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    margin        = dict(t=20, b=20),
    yaxis         = dict(gridcolor="#2a2d3e"),
    font          = dict(color="#e2e8f0"),
)
st.plotly_chart(fig2, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# BEST / WORST callouts
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
b1, b2, b3 = st.columns(3)

b1.success(f"**Best:** {summary['best_ticker']}  {summary['best_pct']:+.2f}%")
b2.error(  f"**Worst:** {summary['worst_ticker']}  {summary['worst_pct']:+.2f}%")
b3.info(   f"**Biggest position:** {summary['biggest_ticker']}  {summary['biggest_weight']:.1f}%")
