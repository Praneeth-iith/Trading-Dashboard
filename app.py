import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Set page to wide
st.set_page_config(page_title="OVERFITTERS | Quant-Suite", layout="wide")
st.title(" OVERFITTERS | Market Microstructure Dashboard")

@st.cache_data
def process_data(df):
    # 1. Base Metrics
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    # 2. WallMid (Weighted by Order Book Imbalance)
    df['wallmid'] = df['mid_price'] + (df['OBi'] * df['spread'])
    
    # 3. Z-Score (Statistical Mean Reversion)
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).std())
    df['z_score'] = ((df['mid_price'] - rolling_mean) / rolling_std).clip(-2, 2)
    
    # 4. WallMid Normalized (-2 to 2)
    wm_mean = df.groupby('product')['wallmid'].transform(lambda x: x.rolling(30).mean())
    wm_std = df.groupby('product')['wallmid'].transform(lambda x: x.rolling(30).std())
    df['wallmid_norm'] = ((df['wallmid'] - wm_mean) / wm_std).clip(-2, 2)
    
    return df

# Sidebar
uploaded_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Function to create standardized charts
    def create_chart(col_name, title, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=p_df['timestamp'], y=p_df[col_name], 
            name=col_name, line=dict(color=color),
            customdata=p_df[['mid_price', 'spread', 'OBi', 'wallmid_norm', 'z_score']],
            hovertemplate=(
                f"<b>{title}: %{{y:.2f}}</b><br>"
                "MidPrice: %{{customdata[0]:.2f}}<br>"
                "Spread: %{{customdata[1]:.2f}}<br>"
                "OBi: %{{customdata[2]:.3f}}<br>"
                "WallMid Norm: %{{customdata[3]:.2f}}<br>"
                "Z-Score: %{{customdata[4]:.2f}}<extra></extra>"
            )
        ))
        fig.update_layout(
            title=title, template="plotly_dark", height=250, 
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified"
        )
        return fig

    # Display Charts
    st.plotly_chart(create_chart('mid_price', 'Mid Price', '#00CC96'), use_container_width=True)
    st.plotly_chart(create_chart('spread', 'Spread', '#EF553B'), use_container_width=True)
    st.plotly_chart(create_chart('OBi', 'Order Book Imbalance', '#636EFA'), use_container_width=True)
    st.plotly_chart(create_chart('wallmid_norm', 'WallMid Normalized (-2 to 2)', '#AB63FA'), use_container_width=True)

else:
    st.info("Upload your market data to begin.")
