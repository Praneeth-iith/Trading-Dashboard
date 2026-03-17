import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIGURATION ---
st.set_page_config(page_title="OVERFITTERS | Trading Engine", layout="wide")
st.title(" OVERFITTERS | Prosperity Quantitative Dashboard")

# --- DATA PROCESSING ---
@st.cache_data
def process_data(df):
    # Core Metrics
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    
    # 1. Microstructure: Order Book Imbalance (OBi)
    # If OBi > 0: Buying pressure, If OBi < 0: Selling pressure
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    # 2. Risk Metrics: Mean Reversion (Z-Score)
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(20).std())
    df['z_score'] = (df['mid_price'] - rolling_mean) / rolling_std
    
    # 3. Volatility
    df['volatility'] = df.groupby('product')['mid_price'].transform(lambda x: x.pct_change().rolling(20).std())
    
    return df

# --- UI LAYER ---
uploaded_file = st.sidebar.file_uploader("Upload Market Data (CSV)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    df = process_data(df)
    
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Tab System
    tab1, tab2, tab3 = st.tabs(["📊 Price & Trends", "📈 Market Microstructure", "⚠️ Risk & Z-Score"])

    with tab1:
        st.subheader("Price Action")
        fig1 = px.line(p_df, x='timestamp', y=['mid_price'], title="Mid Price Movement")
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Order Book Pressure")
        fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Spread", "Order Book Imbalance"))
        fig2.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['spread'], name="Spread"), row=1, col=1)
        fig2.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['OBi'], name="OB Imbalance"), row=2, col=1)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Mean Reversion Signals")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['z_score'], name="Z-Score"))
        fig3.add_hline(y=2, line_dash="dash", line_color="red")
        fig3.add_hline(y=-2, line_dash="dash", line_color="green")
        st.plotly_chart(fig3, use_container_width=True)
        st.write("Interpretation: Z-Score > 2 indicates **Overbought** (Short). Z-Score < -2 indicates **Oversold** (Long).")

    # Data Table
    st.subheader("Raw Analytics Data")
    st.dataframe(p_df.tail(100))

else:
    st.info("Upload your CSV in the sidebar to begin analysis.")
