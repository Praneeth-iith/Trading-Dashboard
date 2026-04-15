import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide", page_title="Quant Pro")

st.title("🔬 Quant Research Mode")

# =========================
# DATA LOADER
# =========================
def load_data(files):
    all_dfs = []
    for f in files:
        try:
            # Auto-detect separator
            df = pd.read_csv(f, sep=None, engine='python')
            # Clean whitespace from headers
            df.columns = [str(c).strip() for c in df.columns]
            
            # Day extraction from filename
            day_match = re.search(r'day_(-?\d+)', f.name)
            df['day_label'] = int(day_match.group(1)) if day_match else 0
            all_dfs.append(df)
        except Exception as e:
            st.error(f"Error reading {f.name}: {e}")
    
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# =========================
# SIDEBAR: UPLOAD
# =========================
st.sidebar.header("1. Upload Files")
price_files = st.sidebar.file_uploader("Price CSVs", accept_multiple_files=True)
trade_files = st.sidebar.file_uploader("Trade CSVs", accept_multiple_files=True)

if price_files:
    # Initial Load
    raw_price_df = load_data(price_files)
    
    if not raw_price_df.empty:
        st.sidebar.header("2. Map Columns")
        cols = list(raw_price_df.columns)
        
        # Help the user map the columns
        def_prod = next((c for c in cols if c.lower() in ['product', 'symbol', 'ticker']), cols[0])
        def_time = next((c for c in cols if c.lower() in ['timestamp', 'time']), cols[0])
        def_bid = next((c for c in cols if 'bid_price_1' in c.lower()), cols[0])
        def_ask = next((c for c in cols if 'ask_price_1' in c.lower()), cols[0])

        prod_col = st.sidebar.selectbox("Product/Symbol Column", cols, index=cols.index(def_prod))
        time_col = st.sidebar.selectbox("Timestamp Column", cols, index=cols.index(def_time))
        bid_col = st.sidebar.selectbox("Bid Price Column", cols, index=cols.index(def_bid))
        ask_col = st.sidebar.selectbox("Ask Price Column", cols, index=cols.index(def_ask))

        # Rename to standardized internal names
        df_prices = raw_price_df.rename(columns={
            prod_col: 'target_id',
            time_col: 'timestamp',
            bid_col: 'bid_p',
            ask_col: 'ask_p'
        })

        # =========================
        # FEATURE ENGINEERING
        # =========================
        with st.spinner("Calculating Research Metrics..."):
            df_prices['mid'] = (df_prices['bid_p'] + df_prices['ask_p']) / 2
            
            def process_group(group):
                group = group.sort_values('timestamp')
                # 1. Normalized Mid Price (Log Returns)
                group['log_ret'] = np.log(group['mid'] / group['mid'].shift(1))
                group['cum_ret'] = group['log_ret'].fillna(0).cumsum()
                
                # 2. Volatility (Stationary)
                group['vol'] = group['log_ret'].rolling(50).std()
                
                # 3. Z-Score (Pattern Recognition)
                window = 100
                rolling_m = group['mid'].rolling(window).mean()
                rolling_s = group['mid'].rolling(window).std()
                group['zscore'] = (group['mid'] - rolling_m) / (rolling_s + 1e-9)
                
                return group

            df_prices = df_prices.groupby(['target_id', 'day_label'], group_keys=False).apply(process_group)

        # =========================
        # UI FILTERS
        # =========================
        st.sidebar.header("3. Research Filters")
        products = df_prices['target_id'].unique()
        selected_prod = st.sidebar.selectbox("Focus Product", products)
        
        days = sorted(df_prices['day_label'].unique())
        selected_days = st.sidebar.multiselect("Compare Days", days, default=[days[0]])

        # Filtered DFs
        view_df = df_prices[(df_prices['target_id'] == selected_prod) & (df_prices['day_label'].isin(selected_days))]

        # =========================
        # PLOTTING
        # =========================
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=["Normalized Price (Cumulative Log Returns)", "Z-Score (Mean Reversion)", "Volatility"],
            row_heights=[0.5, 0.25, 0.25]
        )

        for d in selected_days:
            day_data = view_df[view_df['day_label'] == d]
            
            # Row 1: Cumulative Returns (allows comparing different days on same scale)
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['cum_ret'], name=f"Day {d} Ret"), row=1, col=1)
            
            # Row 2: Z-Score
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['zscore'], name=f"Day {d} Z", opacity=0.5), row=2, col=1)
            
            # Row 3: Volatility
            fig.add_trace(go.Scatter(x=day_data['timestamp'], y=day_data['vol'], name=f"Day {d} Vol"), row=3, col=1)

        fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", row=2, col=1)

        fig.update_layout(height=800, template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # Stats Table
        st.subheader("Day-over-Day Comparison")
        stats = view_df.groupby('day_label').agg({
            'mid': ['mean', 'std'],
            'vol': 'mean'
        })
        st.dataframe(stats, use_container_width=True)

else:
    st.info("Please upload your price CSV files to begin. The app will let you select columns after upload.")
