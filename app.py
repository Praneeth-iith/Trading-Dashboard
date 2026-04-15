import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide", page_title="Quant Pattern Research")

st.title("🔬 Quant Research Mode")

# 1. HELPER: LOAD RAW DATA
def load_raw(files):
    dfs = []
    for f in files:
        try:
            # Flexible separator detection
            df = pd.read_csv(f, sep=None, engine='python')
            df.columns = [str(c).strip() for c in df.columns] # Clean column names
            # Day extraction
            day_match = re.search(r'day_(-?\d+)', f.name)
            df['day_label'] = int(day_match.group(1)) if day_match else 0
            dfs.append(df)
        except Exception as e:
            st.error(f"Error loading {f.name}: {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

# 2. SIDEBAR: UPLOAD
st.sidebar.header("Step 1: Data Source")
p_files = st.sidebar.file_uploader("Upload PRICE files", accept_multiple_files=True)
t_files = st.sidebar.file_uploader("Upload TRADE files (Optional)", accept_multiple_files=True)

if p_files:
    raw_df = load_raw(p_files)
    
    if not raw_df.empty:
        # Step 2: MAPPING (The Fix)
        st.sidebar.header("Step 2: Column Mapping")
        all_cols = list(raw_df.columns)
        
        # Smart detection of columns
        def find_col(keys, default):
            for k in keys:
                for c in all_cols:
                    if k.lower() in c.lower(): return c
            return default

        sel_prod = st.sidebar.selectbox("Product/Symbol Column", all_cols, index=all_cols.index(find_col(['product', 'symbol', 'ticker'], all_cols[0])))
        sel_time = st.sidebar.selectbox("Timestamp Column", all_cols, index=all_cols.index(find_col(['timestamp', 'time'], all_cols[0])))
        sel_bid = st.sidebar.selectbox("Bid Price 1 Column", all_cols, index=all_cols.index(find_col(['bid_price_1', 'bid'], all_cols[0])))
        sel_ask = st.sidebar.selectbox("Ask Price 1 Column", all_cols, index=all_cols.index(find_col(['ask_price_1', 'ask'], all_cols[0])))
        sel_bv = st.sidebar.selectbox("Bid Volume 1 Column", all_cols, index=all_cols.index(find_col(['bid_volume_1', 'bid_vol'], all_cols[0])))
        sel_av = st.sidebar.selectbox("Ask Volume 1 Column", all_cols, index=all_cols.index(find_col(['ask_volume_1', 'ask_vol'], all_cols[0])))

        # CREATE THE ANALYSIS DATAFRAME EXPLICITLY
        # This prevents the 'target_id' KeyError
        df = pd.DataFrame()
        df['target_id'] = raw_df[sel_prod]
        df['timestamp'] = raw_df[sel_time]
        df['day'] = raw_df['day_label']
        df['bid'] = pd.to_numeric(raw_df[sel_bid], errors='coerce')
        df['ask'] = pd.to_numeric(raw_df[sel_ask], errors='coerce')
        df['bid_v'] = pd.to_numeric(raw_df[sel_bv], errors='coerce')
        df['ask_v'] = pd.to_numeric(raw_df[sel_av], errors='coerce')
        df['mid'] = (df['bid'] + df['ask']) / 2

        # =========================
        # NEW QUANT METRICS
        # =========================
        def apply_stats(g):
            g = g.sort_values('timestamp')
            # 1. WAP (Weighted Average Price) - Leading indicator
            g['wap'] = (g['bid'] * g['ask_v'] + g['ask'] * g['bid_v']) / (g['bid_v'] + g['ask_v'] + 1e-9)
            
            # 2. Normalized Price (Log Returns)
            g['log_ret'] = np.log(g['mid'] / g['mid'].shift(1))
            g['cum_ret'] = g['log_ret'].fillna(0).cumsum()
            
            # 3. Microstructure Imbalance (Normalized -1 to 1)
            g['imbalance'] = (g['bid_v'] - g['ask_v']) / (g['bid_v'] + g['ask_v'] + 1e-9)
            
            # 4. Price Z-Score (To find mean reversion patterns)
            window = 50
            rolling_m = g['mid'].rolling(window).mean()
            rolling_s = g['mid'].rolling(window).std()
            g['zscore'] = (g['mid'] - rolling_m) / (rolling_s + 1e-9)
            
            # 5. Volatility (20-period rolling)
            g['vol'] = g['log_ret'].rolling(20).std()
            return g

        with st.spinner("Crunching Quant Metrics..."):
            df = df.groupby(['target_id', 'day'], group_keys=False).apply(apply_stats)

        # UI: FILTERING
        st.sidebar.header("Step 3: Analyze")
        active_prod = st.sidebar.selectbox("Focus Product", df['target_id'].unique())
        active_days = st.sidebar.multiselect("Days to Overlay", sorted(df['day'].unique()), default=sorted(df['day'].unique())[:1])
        
        plot_type = st.sidebar.radio("Main Metric", ["Cumulative Returns", "Raw WAP vs Mid", "Z-Score Pattern"])

        # Final Filtered DF
        fdf = df[(df['target_id'] == active_prod) & (df['day'].isin(active_days))]

        # =========================
        # RESEARCH PLOTS
        # =========================
        fig = make_subplots(
            rows=4, cols=1, shared_xaxes=True,
            subplot_titles=["Price Activity", "Imbalance (Microstructure)", "Rolling Volatility", "Return Distribution"],
            vertical_spacing=0.04,
            row_heights=[0.4, 0.2, 0.2, 0.2]
        )

        for d in active_days:
            day_data = fdf[fdf['day'] == d]
            
            # Row 1: Primary Price Metric
            if plot_type == "Cumulative Returns":
                fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['cum_ret'], name=f"Day {d} Ret"), row=1, col=1)
            elif plot_type == "Z-Score Pattern":
                fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['zscore'], name=f"Day {d} Z"), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['wap'], name=f"Day {d} WAP"), row=1, col=1)
                fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['mid'], name=f"Day {d} Mid", opacity=0.3), row=1, col=1)

            # Row 2: Imbalance
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['imbalance'], name=f"Day {d} Imb", opacity=0.4, line=dict(width=1)), row=2, col=1)
            
            # Row 3: Volatility
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['vol'], name=f"Day {d} Vol", fill='tozeroy'), row=3, col=1)
            
            # Row 4: Dist
            fig.add_trace(go.Histogram(x=day_data['log_ret'], name=f"Day {d} Dist", opacity=0.6), row=4, col=1)

        # Style updates
        fig.update_layout(height=1000, template="plotly_dark", hovermode="x unified", showlegend=True)
        if plot_type == "Z-Score Pattern":
            fig.add_hline(y=2, line_dash="dash", line_color="red", row=1, col=1)
            fig.add_hline(y=-2, line_dash="dash", line_color="green", row=1, col=1)

        st.plotly_chart(fig, use_container_width=True)

        # Statistics Table
        with st.expander("Show Detailed Metrics Table"):
            summary = fdf.groupby('day').agg({
                'mid': ['mean', 'std'],
                'imbalance': 'mean',
                'vol': 'mean'
            })
            st.dataframe(summary, use_container_width=True)

else:
    st.info("Upload Price CSV files to get started. Tip: Ensure files have 'day_X' in the filename.")
