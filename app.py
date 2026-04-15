import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide", page_title="Quant Research Pro")
st.title("🔬 Quant Research Mode")

# =========================
# ROBUST LOADER
# =========================
def load_multiple(files):
    dfs = []
    for f in files:
        try:
            # Try semicolon first, then comma
            df = pd.read_csv(f, sep=';')
            if len(df.columns) <= 1:
                f.seek(0)
                df = pd.read_csv(f, sep=',')
            
            # 1. Clean Column Names: trim spaces and lowercase everything for matching
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # 2. Extract Day from filename
            day_match = re.search(r'day_(-?\d+)', f.name)
            df['day'] = int(day_match.group(1)) if day_match else 0
            
            # 3. Standardize 'Product' Column
            # We look for common names used in quant data
            potential_names = ['product', 'symbol', 'ticker', 'asset', 'item']
            found_col = None
            for name in potential_names:
                if name in df.columns:
                    found_col = name
                    break
            
            if found_col:
                df = df.rename(columns={found_col: 'target_id'})
            else:
                # If no match, use the first column that isn't numeric as the ID
                non_numeric = df.select_dtypes(exclude=[np.number]).columns
                if len(non_numeric) > 0:
                    df = df.rename(columns={non_numeric[0]: 'target_id'})
            
            dfs.append(df)
        except Exception as e:
            st.error(f"Error processing {f.name}: {e}")
            
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("Data Upload")
p_files = st.sidebar.file_uploader("Price Files (CSV)", accept_multiple_files=True)
t_files = st.sidebar.file_uploader("Trade Files (CSV)", accept_multiple_files=True)

if p_files:
    df_prices = load_multiple(p_files)
    
    if df_prices.empty:
        st.warning("No data loaded. Check file format.")
        st.stop()

    # DEBUG: Show columns if target_id still missing
    if 'target_id' not in df_prices.columns:
        st.error(f"Critical Error: Could not identify a 'Product' or 'Symbol' column. Available columns are: {list(df_prices.columns)}")
        st.info("Rename your product column to 'product' in your CSV and re-upload.")
        st.stop()

    # --- Calculation Engine ---
    # Use .get() with defaults to prevent crashes if columns like 'bid_price_1' are missing
    df_prices['mid'] = (df_prices.get('bid_price_1', 0) + df_prices.get('ask_price_1', 0)) / 2
    
    # Calculate additional research metrics
    def add_metrics(group):
        group = group.sort_values('timestamp')
        # Normalized Price (Stationary)
        group['returns'] = group['mid'].pct_change()
        group['cum_ret'] = (1 + group['returns']).cumprod() - 1
        # Volatility
        group['rolling_vol'] = group['returns'].rolling(30).std()
        # Z-Score
        m = group['mid'].rolling(100).mean()
        s = group['mid'].rolling(100).std()
        group['zscore'] = (group['mid'] - m) / (s + 1e-9)
        # Orderbook Pressure
        bv = group.get('bid_volume_1', 1)
        av = group.get('ask_volume_1', 1)
        group['imbalance'] = (bv - av) / (bv + av + 1e-9)
        return group

    df_prices = df_prices.groupby(['target_id', 'day'], group_keys=False).apply(add_metrics)

    # Load Trades
    df_trades = load_multiple(t_files) if t_files else pd.DataFrame()

    # --- UI Filters ---
    unique_products = df_prices['target_id'].unique()
    sel_prod = st.sidebar.selectbox("Select Product", unique_products)
    
    unique_days = sorted(df_prices['day'].unique())
    sel_days = st.sidebar.multiselect("Select Days", unique_days, default=[unique_days[0]])
    
    analysis_type = st.sidebar.segmented_control(
        "Analysis Type", 
        options=["Price Action", "Mean Reversion", "Microstructure"],
        default="Price Action"
    )

    # Filtered Data
    pdf = df_prices[(df_prices['target_id'] == sel_prod) & (df_prices['day'].isin(sel_days))]
    tdf = pd.DataFrame()
    if not df_trades.empty and 'target_id' in df_trades.columns:
        tdf = df_trades[(df_trades['target_id'] == sel_prod) & (df_trades['day'].isin(sel_days))]

    # =========================
    # VISUALIZATION
    # =========================
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=("Price", "Returns / Z-Score", "Imbalance", "Volume Distribution")
    )

    # Row 1: Price
    fig.add_trace(go.Scatter(x=pdf['timestamp'], y=pdf['mid'], name="Mid Price", line_color='#00ffcc'), row=1, col=1)
    
    # Row 2: Logic based on analysis type
    if analysis_type == "Mean Reversion":
        fig.add_trace(go.Scatter(x=pdf['timestamp'], y=pdf['zscore'], name="Z-Score", line_color='orange'), row=2, col=1)
        fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", row=2, col=1)
    else:
        fig.add_trace(go.Scatter(x=pdf['timestamp'], y=pdf['cum_ret'], name="Cum Returns", fill='tozeroy'), row=2, col=1)

    # Row 3: Imbalance
    fig.add_trace(go.Scatter(x=pdf['timestamp'], y=pdf['imbalance'], name="Imbalance", line_color='magenta', opacity=0.4), row=3, col=1)

    # Row 4: Trades or Return Dist
    if not tdf.empty:
        fig.add_trace(go.Bar(x=tdf['timestamp'], y=tdf.get('quantity', 0), name="Trade Volume"), row=4, col=1)
    else:
        fig.add_trace(go.Histogram(x=pdf['returns'], name="Returns Dist", marker_color='grey'), row=4, col=1)

    fig.update_layout(height=900, template="plotly_dark", hovermode="x unified", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Data Inspector ---
    with st.expander("Raw Data Inspector"):
        st.write("Columns found:", list(df_prices.columns))
        st.dataframe(pdf.head(50))

else:
    st.info("👋 Welcome! Please upload price CSV files in the sidebar to start the analysis.")
    st.markdown("""
    **Required CSV Columns (or similar):**
    - `product` / `symbol`
    - `timestamp`
    - `bid_price_1`, `ask_price_1`
    - `bid_volume_1`, `ask_volume_1`
    """)
