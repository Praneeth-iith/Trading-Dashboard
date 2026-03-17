import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="OVERFITTERS | Quant-Suite", layout="wide")
st.title(" OVERFITTERS | Market Microstructure Dashboard")

@st.cache_data
def process_data(df):
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).std())
    df['z_score'] = (df['mid_price'] - rolling_mean) / rolling_std
    return df

uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # 4-Row layout: Price, Spread, OBi, Z-Score
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        row_heights=[0.35, 0.20, 0.20, 0.25],
        subplot_titles=("Price Action", "Spread (Cost to Trade)", "Order Book Imbalance", "Z-Score (Mean Reversion)")
    )

    # 1. Price
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid_price'], name="Mid Price"), row=1, col=1)
    # 2. Spread
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['spread'], name="Spread", fill='tozeroy'), row=2, col=1)
    # 3. OBi
    fig.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['OBi'], name="OBi"), row=3, col=1)
    # 4. Z-Score
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['z_score'], name="Z-Score"), row=4, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=4, col=1)

    fig.update_layout(
        height=1000, 
        template="plotly_dark",
        hovermode="x unified",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Key Stat Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Avg Spread", f"{p_df['spread'].mean():.2f}")
    col2.metric("Spread Volatility", f"{p_df['spread'].std():.2f}")
    col3.metric("Latest OBi", f"{p_df['OBi'].iloc[-1]:.3f}")
    col4.metric("Current Z-Score", f"{p_df['z_score'].iloc[-1]:.2f}")

else:
    st.info("Upload your market data to see the synchronized multi-factor view.")
