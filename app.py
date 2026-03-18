import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title(" OVERFITTERS | Surgical Quant View")

# Data Loader
@st.cache_data
def get_data(file):
    df = pd.read_csv(file, sep=';')
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    # Rolling stats for WallMid and Z-Score
    mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).mean())
    std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).std())
    df['wallmid_norm'] = ((df['mid_price'] - mean) / std).clip(-2, 2)
    df['z_score'] = ((df['mid_price'] - mean) / std).clip(-2, 2)
    return df

uploaded_file = st.sidebar.file_uploader("Upload CSV", type="csv")

if uploaded_file:
    df = get_data(uploaded_file)
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Create the four separate, clean graphs
    def plot_metric(df, column, title, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df[column], name=title, line=dict(color=color)))
        fig.update_layout(title=title, template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
        return fig

    # LAYOUT: Graph on left, Data Inspection on Right
    left_col, right_cimport streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Set page to wide for maximum dashboard real estate
st.set_page_config(page_title="OVERFITTERS | Quant-Suite", layout="wide")
st.title(" OVERFITTERS | Professional Quant Dashboard")

@st.cache_data
def process_data(df):
    # 1. Base Metrics
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    # 2. WallMid (Weighted by Order Book Imbalance)
    # Formula: Price + (Imbalance * Spread)
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

# Sidebar Input
uploaded_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Create 4 separate charts
    # We use 'hovermode="x unified"' to show ALL variables at the hovered timestamp
    def create_chart(col_name, title, color):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=p_df['timestamp'], y=p_df[col_name], 
            name=col_name, line=dict(color=color),
            # Add all other variables to the hover box
            customdata=p_df[['mid_price', 'spread', 'OBi', 'wallmid_norm', 'z_score']],
            hovertemplate=(
                f"{title}: %{{y:.2f}}<br>"
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
    st.info("Upload your Prosperity competition CSV file in the sidebar to start analysis.")l = st.columns([3, 1])

    with left_col:
        st.plotly_chart(plot_metric(p_df, 'mid_price', 'Mid Price', '#00CC96'), use_container_width=True)
        st.plotly_chart(plot_metric(p_df, 'spread', 'Spread', '#EF553B'), use_container_width=True)
        st.plotly_chart(plot_metric(p_df, 'OBi', 'OBi', '#636EFA'), use_container_width=True)
        st.plotly_chart(plot_metric(p_df, 'wallmid_norm', 'WallMid Norm', '#AB63FA'), use_container_width=True)

    with right_col:
        st.subheader("Data Inspector")
        # This slider acts as your 'Hover' to inspect the exact state of all variables
        idx = st.slider("Select Timestamp Index", 0, len(p_df)-1, len(p_df)-1)
        row = p_df.iloc[idx]
        
        st.metric("Timestamp", row['timestamp'])
        st.metric("Mid Price", f"{row['mid_price']:.2f}")
        st.metric("Spread", f"{row['spread']:.2f}")
        st.metric("OBi", f"{row['OBi']:.3f}")
        st.metric("WallMid Norm", f"{row['wallmid_norm']:.2f}")
        st.metric("Z-Score", f"{row['z_score']:.2f}")

else:
    st.info("Upload CSV to start analysis.")
