import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide", page_title="OVERFITTERS PRO")

st.title("🚀 OVERFITTERS PRO | Quant Trading Terminal")

# =========================
# DATA PROCESSING
# =========================
@st.cache_data
def process_data(m_df, t_df):
    m_df = m_df.sort_values('timestamp')
    t_df = t_df.sort_values('timestamp')

    # ✅ NO FUTURE LEAK
    df = pd.merge_asof(
        t_df,
        m_df[['timestamp', 'bid_price_1', 'ask_price_1',
              'bid_volume_1', 'ask_volume_1']],
        on='timestamp',
        direction='backward'
    )

    # Mid price
    df['mid'] = (df['bid_price_1'] + df['ask_price_1']) / 2

    # =========================
    # ROBUST TRADE CLASSIFICATION
    # =========================
    df['side'] = 'Neutral'

    df.loc[df['price'] >= df['ask_price_1'], 'side'] = 'Buy'
    df.loc[df['price'] <= df['bid_price_1'], 'side'] = 'Sell'

    # fallback (mid-based)
    df.loc[(df['side'] == 'Neutral') & (df['price'] > df['mid']), 'side'] = 'Buy'
    df.loc[(df['side'] == 'Neutral') & (df['price'] < df['mid']), 'side'] = 'Sell'

    # =========================
    # ORDER BOOK IMBALANCE
    # =========================
    df['imbalance'] = (
        (df['bid_volume_1'] - df['ask_volume_1']) /
        (df['bid_volume_1'] + df['ask_volume_1'] + 1e-9)
    )

    return m_df, df


# =========================
# SIGNAL ENGINE
# =========================
def generate_signals(df):

    signals = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]

        # =========================
        # ABSORPTION SIGNAL
        # =========================
        if row['side'] == 'Sell':
            if row['price'] >= prev['price']:  # price not falling
                signals.append("BUY_ABSORB")

        if row['side'] == 'Buy':
            if row['price'] <= prev['price']:  # price not rising
                signals.append("SELL_ABSORB")

        # =========================
        # IMBALANCE SIGNAL
        # =========================
        elif row['imbalance'] > 0.3:
            signals.append("BUY_IMB")

        elif row['imbalance'] < -0.3:
            signals.append("SELL_IMB")

        else:
            signals.append("HOLD")

    df = df.iloc[1:]
    df['signal'] = signals

    return df


# =========================
# SIMPLE PNL ENGINE
# =========================
def simulate(df):
    position = 0
    cash = 0
    max_pos = 80

    pnl = []

    for _, row in df.iterrows():

        if row['signal'] in ['BUY_ABSORB', 'BUY_IMB'] and position < max_pos:
            position += 1
            cash -= row['price']

        elif row['signal'] in ['SELL_ABSORB', 'SELL_IMB'] and position > -max_pos:
            position -= 1
            cash += row['price']

        pnl.append(cash + position * row['price'])

    df['pnl'] = pnl
    df['position'] = position

    return df


# =========================
# UI
# =========================
col1, col2 = st.columns(2)

market_file = col1.file_uploader("Upload Market CSV", type="csv")
trades_file = col2.file_uploader("Upload Trades CSV", type="csv")

if market_file and trades_file:

    m_df = pd.read_csv(market_file, sep=';')
    t_df = pd.read_csv(trades_file, sep=';')

    m_df, df = process_data(m_df, t_df)

    product = st.sidebar.selectbox("Product", m_df['product'].unique())

    m_df = m_df[m_df['product'] == product]
    df = df[df['symbol'] == product]

    df = generate_signals(df)
    df = simulate(df)

    # =========================
    # CHART 1: PRICE + TRADES
    # =========================
    st.subheader("📊 Market + Trades")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=m_df['timestamp'],
        y=m_df['ask_price_1'],
        name="Ask",
        line=dict(color='red', dash='dot')
    ))

    fig.add_trace(go.Scatter(
        x=m_df['timestamp'],
        y=m_df['bid_price_1'],
        name="Bid",
        line=dict(color='blue', dash='dot')
    ))

    buys = df[df['side'] == 'Buy']
    sells = df[df['side'] == 'Sell']

    fig.add_trace(go.Scatter(
        x=buys['timestamp'],
        y=buys['price'],
        mode='markers',
        name="Agg Buy",
        marker=dict(color='green', size=6)
    ))

    fig.add_trace(go.Scatter(
        x=sells['timestamp'],
        y=sells['price'],
        mode='markers',
        name="Agg Sell",
        marker=dict(color='red', size=6)
    ))

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # CHART 2: IMBALANCE
    # =========================
    st.subheader("⚖️ Order Book Imbalance")

    fig2 = px.line(df, x='timestamp', y='imbalance')
    st.plotly_chart(fig2, use_container_width=True)

    # =========================
    # CHART 3: VOLUME PROFILE
    # =========================
    st.subheader("🔥 Volume Profile")

    fig3 = px.histogram(
        df,
        x='price',
        y='quantity',
        color='side',
        barmode='group'
    )

    st.plotly_chart(fig3, use_container_width=True)

    # =========================
    # CHART 4: PNL
    # =========================
    st.subheader("💰 Strategy PnL")

    fig4 = px.line(df, x='timestamp', y='pnl')
    st.plotly_chart(fig4, use_container_width=True)

    # =========================
    # METRICS
    # =========================
    st.sidebar.metric("Final PnL", round(df['pnl'].iloc[-1], 2))
    st.sidebar.metric("Trades", len(df))
    st.sidebar.metric("Avg Imbalance", round(df['imbalance'].mean(), 3))

else:
    st.info("Upload both CSVs to start")
