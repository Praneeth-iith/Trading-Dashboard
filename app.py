import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="OVERFITTERS Analytics", layout="wide")

st.title(" OVERFITTERS | Market Data Deep Dive")

# Optimized File Loader
@st.cache_data
def process_data(file):
    df = pd.read_csv(file, sep=';')
    # Pre-calculate critical metrics
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    # Rolling Metrics
    df['sma_20'] = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).mean())
    df['volatility'] = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).std())
    # Order Book Imbalance
    df['imbalance'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    return df

uploaded_file = st.sidebar.file_uploader("Upload Competition CSV", type="csv")

if uploaded_file:
    df = process_data(uploaded_file)
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product]

    # Row 1: Key Performance Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Latest Mid-Price", f"{p_df['mid_price'].iloc[-1]:.2f}")
    c2.metric("Avg Spread", f"{p_df['spread'].mean():.2f}")
    c3.metric("Volatility (20t)", f"{p_df['volatility'].iloc[-1]:.4f}")
    c4.metric("Current Imbalance", f"{p_df['imbalance'].iloc[-1]:.2f}")

    # Row 2: Charts
    # Subplots for Price vs SMA and Order Book Imbalance
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, 
                        subplot_titles=(f"Price Action: {product}", "Market Imbalance"),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid_price'], name="Mid Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['sma_20'], name="SMA 20"), row=1, col=1)
    
    fig.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['imbalance'], name="Imbalance"), row=2, col=1)

    fig.update_layout(height=700, template="plotly_dark", showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    # Row 3: Spread Analysis
    st.subheader("Spread Distribution")
    fig_spread = go.Figure(data=[go.Histogram(x=p_df['spread'])])
    fig_spread.update_layout(template="plotly_dark", title="Spread Frequency")
    st.plotly_chart(fig_spread, use_container_width=True)

else:
    st.warning("Upload your CSV to view OVERFITTERS analytics.")
