import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide")
st.title("🔬 Quant Research Mode: Pattern Discovery")

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
st.sidebar.header("Data Selection")
price_files = st.sidebar.file_uploader("Price files", accept_multiple_files=True)
trade_files = st.sidebar.file_uploader("Trade files", accept_multiple_files=True)

if price_files:
    df_prices = load_multiple(price_files)
    df_prices = df_prices.sort_values(['product', 'day', 'timestamp'])

    # --- FEATURE ENGINEERING ---
    # 1. Microstructure Mid/WAP
    df_prices['mid'] = (df_prices['bid_price_1'] + df_prices['ask_price_1']) / 2
    # Weighted Average Price (WAP) takes volume into account
    df_prices['wap'] = (df_prices['bid_price_1'] * df_prices['ask_volume_1'] + 
                        df_prices['ask_price_1'] * df_prices['bid_volume_1']) / \
                       (df_prices['bid_volume_1'] + df_prices['ask_volume_1'])
    
    # 2. Spread & Imbalance
    df_prices['spread'] = df_prices['ask_price_1'] - df_prices['bid_price_1']
    df_prices['imbalance'] = (df_prices['bid_volume_1'] - df_prices['ask_volume_1']) / \
                             (df_prices['bid_volume_1'] + df_prices['ask_volume_1'] + 1e-9)

    # 3. Normalization (By Day & Product)
    # This allows comparing "Day -1" and "Day 1" on the same scale
    def normalize_group(group):
        # Log Returns
        group['log_ret'] = np.log(group['mid'] / group['mid'].shift(1))
        # Cumulative Returns (Start at 0)
        group['cum_ret'] = group['log_ret'].fillna(0).cumsum()
        # Rolling Volatility (20 period)
        group['volatility'] = group['log_ret'].rolling(window=20).std()
        # Price Z-Score (Mean Reversion Indicator)
        window = 100
        rolling_mean = group['mid'].rolling(window=window).mean()
        rolling_std = group['mid'].rolling(window=window).std()
        group['price_zscore'] = (group['mid'] - rolling_mean) / (rolling_std + 1e-9)
        return group

    df_prices = df_prices.groupby(['product', 'day'], group_keys=False).apply(normalize_group)

    # Load Trades
    df_trades = pd.DataFrame()
    if trade_files:
        df_trades = load_multiple(trade_files, is_trade=True)
        df_trades = df_trades.sort_values(['symbol', 'day', 'timestamp'])

    # =========================
    # RESEARCH FILTERS
    # =========================
    product = st.sidebar.selectbox("Select Product", df_prices['product'].unique())
    selected_day = st.sidebar.multiselect("Select Days", df_prices['day'].unique(), default=df_prices['day'].unique()[0])
    
    view_mode = st.sidebar.radio("View Mode", ["Raw Price", "Normalized (Returns)", "Z-Score Analysis"])

    p_df = df_prices[(df_prices['product'] == product) & (df_prices['day'].isin(selected_day))]
    t_df = df_trades[(df_trades['symbol'] == product) & (df_trades['day'].isin(selected_day))] if not df_trades.empty else pd.DataFrame()

    # =========================
    # PLOTS
    # =========================
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[
            "Primary Metric", 
            "Imbalance / Pressure", 
            "Volatility / Spread", 
            "Signal Distribution"
        ],
        row_heights=[0.4, 0.2, 0.2, 0.2]
    )

    # --- ROW 1: PRIMARY METRIC ---
    if view_mode == "Raw Price":
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid'], name='Mid Price'), row=1, col=1)
        if not t_df.empty:
            fig.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['price'], mode='markers', name='Trades', marker=dict(size=4, color='white', opacity=0.5)), row=1, col=1)
    
    elif view_mode == "Normalized (Returns)":
        # Plotting Cumulative returns for each day overlapping
        for day in selected_day:
            day_data = p_df[p_df['day'] == day]
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['cum_ret'], name=f'Day {day} CumRet'), row=1, col=1)
            
    elif view_mode == "Z-Score Analysis":
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['price_zscore'], name='Price Z-Score'), row=1, col=1)
        fig.add_hline(y=2, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", row=1, col=1)

    # --- ROW 2: IMBALANCE ---
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['imbalance'], name='Imbalance', line=dict(color='rgba(0, 255, 255, 0.5)')), row=2, col=1)
    
    # --- ROW 3: VOLATILITY / SPREAD ---
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['volatility'], name='Volatility', fill='tozeroy'), row=3, col=1)

    # --- ROW 4: CUSTOM HISTOGRAM OR TRADES ---
    if not t_df.empty:
        # Show trade intensity (volume clusters)
        fig.add_trace(go.Histogram(x=t_df['timestamp'], y=t_df['quantity'], name='Trade Intensity', histfunc='sum', nbinsx=100), row=4, col=1)
    else:
        # Show distribution of log returns
        fig.add_trace(go.Histogram(x=p_df['log_ret'], name='Log Ret Dist'), row=4, col=1)

    fig.update_layout(height=1000, template='plotly_dark', title=f"Analysis: {product} (Mode: {view_mode})", showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # STATS TABLE
    # =========================
    st.subheader("Statistical Summary")
    stats = p_df.groupby('day').agg({
        'spread': 'mean',
        'imbalance': 'std',
        'volatility': 'mean',
        'mid': ['min', 'max']
    }).reset_index()
    st.dataframe(stats, use_container_width=True)

else:
    st.info("Upload price files to begin research session.")
