import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set wide layout for maximum screen real estate
st.set_page_config(page_title="OVERFITTERS | Unified Analytics", layout="wide")
st.title(" OVERFITTERS | Integrated Market Analysis")

@st.cache_data
def process_data(df):
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
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

    # Create a 3-row layout with SHARED X-AXES
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.5, 0.25, 0.25],
        subplot_titles=("Price Action & Mean", "Order Book Imbalance (OBi)", "Mean Reversion (Z-Score)")
    )

    # 1. Price Chart
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid_price'], name="Mid Price"), row=1, col=1)
    
    # 2. Imbalance Chart
    fig.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['OBi'], name="OBi"), row=2, col=1)
    
    # 3. Z-Score Chart
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['z_score'], name="Z-Score"), row=3, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=3, col=1)

    # Layout styling: Synchronized zooming
    fig.update_layout(
        height=900, 
        template="plotly_dark",
        hovermode="x unified", # Shows all data for one timestamp at once
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Quick Metrics Panel below the graph
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg OBi", f"{p_df['OBi'].mean():.3f}")
    c2.metric("Current Z-Score", f"{p_df['z_score'].iloc[-1]:.2f}")
    c3.metric("Total Data Points", len(p_df))

else:
    st.info("Upload data to see the synchronized dashboard.")
