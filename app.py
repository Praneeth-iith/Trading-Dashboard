import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide")
st.title("Quant Analyzer (Pure Research Mode)")


# =========================
# LOAD MULTI FILES
# =========================
def load_multiple(files, is_trade=False):

    dfs = []

    for f in files:
        df = pd.read_csv(f, sep=';')

        day_match = re.search(r'day_(-?\d+)', f.name)
        df['day'] = int(day_match.group(1)) if day_match else 0

        if is_trade:
            if 'symbol' not in df.columns and 'product' in df.columns:
                df = df.rename(columns={'product': 'symbol'})

        dfs.append(df)

    return pd.concat(dfs)


# =========================
# UPLOAD
# =========================
st.sidebar.header("Upload Data")

price_files = st.sidebar.file_uploader(
    "Upload PRICE files (multiple days)",
    accept_multiple_files=True
)

trade_files = st.sidebar.file_uploader(
    "Upload TRADE files (multiple days)",
    accept_multiple_files=True
)


if price_files:

    df_prices = load_multiple(price_files)

    df_prices = df_prices.sort_values(['product', 'day', 'timestamp'])

    # features
    df_prices['mid'] = (df_prices['bid_price_1'] + df_prices['ask_price_1']) / 2
    df_prices['spread'] = df_prices['ask_price_1'] - df_prices['bid_price_1']
    df_prices['imbalance'] = (
        (df_prices['bid_volume_1'] - df_prices['ask_volume_1']) /
        (df_prices['bid_volume_1'] + df_prices['ask_volume_1'] + 1e-9)
    )

    df_trades = pd.DataFrame()

    if trade_files:
        df_trades = load_multiple(trade_files, is_trade=True)
        df_trades = df_trades.sort_values(['symbol', 'day', 'timestamp'])

    # =========================
    # SELECT PRODUCT
    # =========================
    product = st.sidebar.selectbox(
        "Select Product",
        df_prices['product'].unique()
    )

    p_df = df_prices[df_prices['product'] == product]
    t_df = df_trades[df_trades['symbol'] == product] if not df_trades.empty else pd.DataFrame()

    # =========================
    # PLOTS
    # =========================
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Price + Trades",
            "Spread",
            "Imbalance",
            "Trade Size Distribution"
        ],
        row_heights=[0.5, 0.15, 0.15, 0.2]
    )

    # PRICE
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['ask_price_1'],
        name='Ask'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['bid_price_1'],
        name='Bid'
    ), row=1, col=1)

    if not t_df.empty:
        fig.add_trace(go.Scatter(
            x=t_df['timestamp'],
            y=t_df['price'],
            mode='markers',
            name='Trades'
        ), row=1, col=1)

    # SPREAD
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['spread'],
        fill='tozeroy'
    ), row=2, col=1)

    # IMBALANCE
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['imbalance']
    ), row=3, col=1)

    # TRADE SIZE
    if not t_df.empty:
        fig.add_trace(go.Histogram(
            x=t_df['quantity']
        ), row=4, col=1)

    fig.update_layout(
        height=900,
        template='plotly_dark',
        title=f"{product} | Multi-Day Analysis"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Upload price files to begin")
