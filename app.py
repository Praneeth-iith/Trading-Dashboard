import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide")
st.title("🔬 Quant Research Mode: Pattern Discovery")

# =========================
# HELPER: ROBUST LOADING
# =========================
def load_multiple(files):
    dfs = []
    for f in files:
        # Some files use ',' others use ';' - we try to handle both
        try:
            df = pd.read_csv(f, sep=';')
            if len(df.columns) <= 1: # If semicolon failed to split
                f.seek(0)
                df = pd.read_csv(f, sep=',')
        except Exception as e:
            st.error(f"Error reading {f.name}: {e}")
            continue

        # 1. Clean column names (remove spaces/quotes)
        df.columns = [str(c).strip().replace('"', '').replace("'", "") for c in df.columns]
        
        # 2. Extract day from filename
        day_match = re.search(r'day_(-?\d+)', f.name)
        df['day'] = int(day_match.group(1)) if day_match else 0
        
        # 3. Standardize Product/Symbol column
        if 'product' in df.columns:
            df = df.rename(columns={'product': 'target_id'})
        elif 'symbol' in df.columns:
            df = df.rename(columns={'symbol': 'target_id'})
            
        dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

# =========================
# UPLOAD
# =========================
st.sidebar.header("Data Selection")
price_files = st.sidebar.file_uploader("Upload Price files", accept_multiple_files=True)
trade_files = st.sidebar.file_uploader("Upload Trade files", accept_multiple_files=True)

if price_files:
    df_prices = load_multiple(price_files)
    
    # Check if we successfully found a product column
    if 'target_id' not in df_prices.columns:
        st.error(f"Could not find 'product' or 'symbol' column. Found: {list(df_prices.columns)}")
        st.stop()

    df_prices = df_prices.sort_values(['target_id', 'day', 'timestamp'])

    # --- FEATURE ENGINEERING ---
    # Use .get() to avoid KeyErrors if some columns are missing
    b1 = df_prices.get('bid_price_1', 0)
    a1 = df_prices.get('ask_price_1', 0)
    bv1 = df_prices.get('bid_volume_1', 0)
    av1 = df_prices.get('ask_volume_1', 0)

    df_prices['mid'] = (b1 + a1) / 2
    df_prices['wap'] = (b1 * av1 + a1 * bv1) / (bv1 + av1 + 1e-9)
    df_prices['spread'] = a1 - b1
    df_prices['imbalance'] = (bv1 - av1) / (bv1 + av1 + 1e-9)

    # Normalization Grouped logic
    def normalize_group(group):
        group['log_ret'] = np.log(group['mid'] / group['mid'].shift(1))
        group['cum_ret'] = group['log_ret'].fillna(0).cumsum()
        group['volatility'] = group['log_ret'].rolling(window=20).std()
        
        window = 100
        rmean = group['mid'].rolling(window=window).mean()
        rstd = group['mid'].rolling(window=window).std()
        group['price_zscore'] = (group['mid'] - rmean) / (rstd + 1e-9)
        return group

    df_prices = df_prices.groupby(['target_id', 'day'], group_keys=False).apply(normalize_group)

    # Load Trades
    df_trades = pd.DataFrame()
    if trade_files:
        df_trades = load_multiple(trade_files)
        if 'target_id' in df_trades.columns:
            df_trades = df_trades.sort_values(['target_id', 'day', 'timestamp'])

    # =========================
    # RESEARCH FILTERS
    # =========================
    unique_products = df_prices['target_id'].unique()
    product = st.sidebar.selectbox("Select Product", unique_products)
    
    unique_days = sorted(df_prices['day'].unique())
    selected_days = st.sidebar.multiselect("Select Days", unique_days, default=[unique_days[0]])
    
    view_mode = st.sidebar.radio("View Mode", ["Raw Price", "Normalized (Returns)", "Z-Score Analysis"])

    # Filter data
    p_df = df_prices[(df_prices['target_id'] == product) & (df_prices['day'].isin(selected_days))]
    t_df = pd.DataFrame()
    if not df_trades.empty and 'target_id' in df_trades.columns:
        t_df = df_trades[(df_trades['target_id'] == product) & (df_trades['day'].isin(selected_days))]

    # =========================
    # PLOTS
    # =========================
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=["Primary Metric", "Imbalance", "Volatility", "Signals"],
        row_heights=[0.4, 0.2, 0.2, 0.2]
    )

    if view_mode == "Raw Price":
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid'], name='Mid'), row=1, col=1)
    elif view_mode == "Normalized (Returns)":
        for d in selected_days:
            d_slice = p_df[p_df['day'] == d]
            fig.add_trace(go.Scatter(x=d_slice['timestamp'], y=d_slice['cum_ret'], name=f'Day {d} CumRet'), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['price_zscore'], name='Z-Score'), row=1, col=1)
        fig.add_hline(y=2, line_dash="dash", line_color="red", row=1, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", row=1, col=1)

    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['imbalance'], name='Imbalance', opacity=0.6), row=2, col=1)
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['volatility'], name='Volatility', fill='tozeroy'), row=3, col=1)

    if not t_df.empty and 'quantity' in t_df.columns:
        fig.add_trace(go.Histogram(x=t_df['timestamp'], y=t_df['quantity'], name='Trade Vol', histfunc='sum'), row=4, col=1)
    else:
        fig.add_trace(go.Histogram(x=p_df['log_ret'], name='Returns Dist'), row=4, col=1)

    fig.update_layout(height=900, template='plotly_dark', title=f"Research: {product}")
    st.plotly_chart(fig, use_container_width=True)

    # Stats Summary
    with st.expander("View Daily Stats"):
        st.dataframe(p_df.groupby('day').agg({'spread': 'mean', 'volatility': 'mean', 'mid': 'std'}))

else:
    st.info("Please upload price files (CSV) to begin.")
