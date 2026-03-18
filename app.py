import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Setup Page
st.set_page_config(page_title="OVERFITTERS | Quant-Suite", layout="wide")
st.title(" OVERFITTERS | Market Microstructure Dashboard")

@st.cache_data
def process_data(df):
    # Base Calculations
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    # Rolling Statistics
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).std())
    
    # WallMid Normalization (-2 to 2)
    df['wallmid_norm'] = (df['mid_price'] - rolling_mean) / rolling_std
    df['wallmid_norm'] = df['wallmid_norm'].clip(-2, 2)
    
    # Z-Score (Mean Reversion)
    df['z_score'] = (df['mid_price'] - rolling_mean) / rolling_std
    
    return df

# UI Input
uploaded_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Create 4-row subplot layout with Synchronized X-Axis
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        subplot_titles=("Normalized Mid-Price (-2 to 2)", "Spread", "Order Book Imbalance (OBi)", "Z-Score (Mean Reversion)")
    )

    # Adding Traces
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['wallmid_norm'], name="WallMid Norm"), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['spread'], name="Spread", fill='tozeroy'), row=2, col=1)
    fig.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['OBi'], name="OBi"), row=3, col=1)
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['z_score'], name="Z-Score"), row=4, col=1)

    # Add reference lines
    for r in [1, 4]:
        fig.add_hline(y=2, line_dash="dash", line_color="red", row=r, col=1)
        fig.add_hline(y=-2, line_dash="dash", line_color="green", row=r, col=1)

    # Unified Hover and Layout
    fig.update_layout(
        height=1000, 
        template="plotly_dark",
        hovermode="x unified", # THIS IS THE KEY: Shows all variables on hover
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Detailed Stats View
    st.subheader("Data Snapshot at Hover Time")
    st.write("Use the hover tool in the graph above to inspect exact values for Spread, MidPrice, WallMid, and OBi.")
    st.dataframe(p_df[['timestamp', 'mid_price', 'spread', 'wallmid_norm', 'OBi', 'z_score']].tail(5))

else:
    st.info("Please upload your Prosperity competition CSV file in the sidebar to start analysis.")
