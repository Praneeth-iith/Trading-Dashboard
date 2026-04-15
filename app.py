import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide", page_title="Quant Pattern Research")

st.title("🔬 Quant Research Mode")

# ==========================================
# 1. ROBUST DATA LOADING
# ==========================================
def load_raw_files(files):
    all_data = []
    for f in files:
        try:
            # Detect separator automatically
            df = pd.read_csv(f, sep=None, engine='python')
            # Clean column names (strip spaces)
            df.columns = [str(c).strip() for c in df.columns]
            # Day extraction from filename
            day_match = re.search(r'day_(-?\d+)', f.name)
            df['day_label'] = int(day_match.group(1)) if day_match else 0
            all_data.append(df)
        except Exception as e:
            st.error(f"Error reading {f.name}: {e}")
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# ==========================================
# 2. SIDEBAR - FILE UPLOAD
# ==========================================
st.sidebar.header("Step 1: Data Source")
price_files = st.sidebar.file_uploader("Upload Price CSVs", accept_multiple_files=True)

if price_files:
    raw_df = load_raw_files(price_files)
    
    if not raw_df.empty:
        # Step 2: COLUMN MAPPING
        st.sidebar.header("Step 2: Column Mapping")
        cols = list(raw_df.columns)
        
        # Helper to find column names
        def find_c(keys):
            for k in keys:
                for c in cols:
                    if k.lower() in c.lower(): return c
            return cols[0]

        map_prod = st.sidebar.selectbox("Product ID", cols, index=cols.index(find_c(['product', 'symbol', 'ticker'])))
        map_time = st.sidebar.selectbox("Timestamp", cols, index=cols.index(find_c(['timestamp', 'time'])))
        map_bid  = st.sidebar.selectbox("Bid Price", cols, index=cols.index(find_c(['bid_price_1', 'bid_p'])))
        map_ask  = st.sidebar.selectbox("Ask Price", cols, index=cols.index(find_c(['ask_price_1', 'ask_p'])))
        map_bidv = st.sidebar.selectbox("Bid Volume", cols, index=cols.index(find_c(['bid_volume_1', 'bid_v'])))
        map_askv = st.sidebar.selectbox("Ask Volume", cols, index=cols.index(find_c(['ask_volume_1', 'ask_v'])))

        # ==========================================
        # 3. FEATURE ENGINEERING (SAFE TRANSFORM)
        # ==========================================
        # Create a clean working copy with standardized names
        df = pd.DataFrame({
            'target_id': raw_df[map_prod],
            'timestamp': raw_df[map_time],
            'day': raw_df['day_label'],
            'bid': pd.to_numeric(raw_df[map_bid], errors='coerce'),
            'ask': pd.to_numeric(raw_df[map_ask], errors='coerce'),
            'bid_v': pd.to_numeric(raw_df[map_bidv], errors='coerce'),
            'ask_v': pd.to_numeric(raw_df[map_askv], errors='coerce')
        }).sort_values(['target_id', 'day', 'timestamp'])

        # Drop rows with NaN in critical columns
        df = df.dropna(subset=['bid', 'ask'])

        # Calculate Stationarity & Microstructure Metrics
        df['mid'] = (df['bid'] + df['ask']) / 2
        
        # WAP - Leading Price Indicator
        df['wap'] = (df['bid'] * df['ask_v'] + df['ask'] * df['bid_v']) / (df['bid_v'] + df['ask_v'] + 1e-9)
        
        # Log Returns (Stationary metric)
        df['log_ret'] = df.groupby(['target_id', 'day'])['mid'].transform(lambda x: np.log(x / x.shift(1)))
        
        # Cumulative Returns (Normalized for overlay)
        df['cum_ret'] = df.groupby(['target_id', 'day'])['log_ret'].transform(lambda x: x.fillna(0).cumsum())
        
        # Z-Score (Mean Reversion Pattern)
        def calc_zscore(x):
            m = x.rolling(100).mean()
            s = x.rolling(100).std()
            return (x - m) / (s + 1e-9)
        df['zscore'] = df.groupby(['target_id', 'day'])['mid'].transform(calc_zscore)
        
        # Imbalance
        df['imbalance'] = (df['bid_v'] - df['ask_v']) / (df['bid_v'] + df['ask_v'] + 1e-9)

        # ==========================================
        # 4. FINAL VALIDATION & DISPLAY
        # ==========================================
        if 'target_id' not in df.columns:
            st.error("Column mapping failed to create 'target_id'. Check your column selections.")
        else:
            st.sidebar.header("Step 3: Analysis Filter")
            unique_prods = df['target_id'].unique()
            selected_prod = st.sidebar.selectbox("Focus Product", unique_prods)
            
            unique_days = sorted(df['day'].unique())
            selected_days = st.sidebar.multiselect("Overlay Days", unique_days, default=[unique_days[0]])

            view_mode = st.sidebar.radio("View Mode", ["Market Patterns", "Statistical Z-Score", "Raw Microstructure"])

            # Filter data for plotting
            plot_df = df[(df['target_id'] == selected_prod) & (df['day'].isin(selected_days))]

            # PLOTS
            fig = make_subplots(
                rows=3, cols=1, shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=["Price Action (Normalized)", "Orderbook Imbalance", "Volatility/Returns Distribution"],
                row_heights=[0.5, 0.25, 0.25]
            )

            for d in selected_days:
                d_data = plot_df[plot_df['day'] == d]
                
                # ROW 1: PRICE
                if view_mode == "Market Patterns":
                    fig.add_trace(go.Scatter(x=d_data['timestamp'], y=d_data['cum_ret'], name=f"Day {d} CumRet"), row=1, col=1)
                elif view_mode == "Statistical Z-Score":
                    fig.add_trace(go.Scatter(x=d_data['timestamp'], y=d_data['zscore'], name=f"Day {d} Z-Score"), row=1, col=1)
                else:
                    fig.add_trace(go.Scatter(x=d_data['timestamp'], y=d_data['mid'], name=f"Day {d} Mid"), row=1, col=1)

                # ROW 2: IMBALANCE
                fig.add_trace(go.Scatter(x=d_data['timestamp'], y=d_data['imbalance'], name=f"Day {d} Imb", opacity=0.4), row=2, col=1)
                
                # ROW 3: VOL/DIST
                fig.add_trace(go.Histogram(x=d_data['log_ret'], name=f"Day {d} Returns", opacity=0.5), row=3, col=1)

            fig.update_layout(height=900, template="plotly_dark", hovermode="x unified")
            if view_mode == "Statistical Z-Score":
                fig.add_hline(y=2, line_dash="dash", line_color="red", row=1, col=1)
                fig.add_hline(y=-2, line_dash="dash", line_color="green", row=1, col=1)

            st.plotly_chart(fig, use_container_width=True)

            # STATISTICS EXPANDER
            with st.expander("Summary Statistics"):
                stats = plot_df.groupby('day').agg({
                    'mid': ['min', 'max', 'std'],
                    'imbalance': 'mean',
                    'log_ret': 'std'
                }).rename(columns={'std': 'volatility'})
                st.dataframe(stats, use_container_width=True)

else:
    st.info("Upload CSV files to begin. Make sure filenames contain 'day_N' to identify different days.")
