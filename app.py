import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Page Setup
st.set_page_config(page_title="OVERFITTERS | Ultimate Quant View", layout="wide")
st.title(" OVERFITTERS | Integrated Market Analysis")

@st.cache_data
def process_data(df):
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).std())
    
    # Normalized WallMid (-2 to 2)
    df['wallmid_norm'] = ((df['mid_price'] - rolling_mean) / rolling_std).clip(-2, 2)
    # Z-Score
    df['z_score'] = ((df['mid_price'] - rolling_mean) / rolling_std).clip(-2, 2)
    
    return df

uploaded_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Create subplots
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03,
        subplot_titles=("Mid Price & WallMid Norm", "Spread", "Order Book Imbalance (OBi)", "Z-Score")
    )

    # 1. Mid Price (Primary) + WallMid Norm (Secondary Axis)
    # We add them to the same row so they correlate visually
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid_price'], name="Mid Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['wallmid_norm'], name="WallMid Norm", yaxis="y5"), row=1, col=1)

    # 2. Spread
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['spread'], name="Spread"), row=2, col=1)
    
    # 3. OBi
    fig.add_trace(go.Bar(x=p_df['timestamp'], y=p_df['OBi'], name="OBi"), row=3, col=1)
    
    # 4. Z-Score
    fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['z_score'], name="Z-Score"), row=4, col=1)

    # Layout: Unified Hover is the secret to seeing all variables at once
    fig.update_layout(
        height=1000, 
        template="plotly_dark",
        hovermode="x unified",  # <--- THIS LISTS ALL VARIABLES ON HOVER
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Upload your market data to begin.")
