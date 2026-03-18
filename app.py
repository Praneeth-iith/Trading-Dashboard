import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="OVERFITTERS | Quant-Suite", layout="wide")
st.title(" OVERFITTERS | Market Microstructure Dashboard")

@st.cache_data
def process_data(df):
    df['mid_price'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    df['spread'] = df['ask_price_1'] - df['bid_price_1']
    df['OBi'] = (df['bid_volume_1'] - df['ask_volume_1']) / (df['bid_volume_1'] + df['ask_volume_1'])
    
    rolling_mean = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).mean())
    rolling_std = df.groupby('product')['mid_price'].transform(lambda x: x.rolling(30).std())
    
    df['z_score'] = ((df['mid_price'] - rolling_mean) / rolling_std).clip(-2, 2)
    df['wallmid'] = df['mid_price'] + (df['OBi'] * df['spread'])
    df['wallmid_norm'] = ((df['wallmid'] - rolling_mean) / rolling_std).clip(-2, 2)
    
    return df.fillna(0)

uploaded_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")

if uploaded_file:
    df = process_data(pd.read_csv(uploaded_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", df['product'].unique())
    p_df = df[df['product'] == product].sort_values('timestamp')

    # Custom Chart for Mid Price + Best Bid/Ask
    def create_price_chart():
        fig = go.Figure()
        # Add Best Ask
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['ask_price_1'], name="Best Ask", 
                                 line=dict(color='red', width=1, dash='dot')))
        # Add Mid Price
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['mid_price'], name="Mid Price", 
                                 line=dict(color='#00CC96', width=2)))
        # Add Best Bid
        fig.add_trace(go.Scatter(x=p_df['timestamp'], y=p_df['bid_price_1'], name="Best Bid", 
                                 line=dict(color='blue', width=1, dash='dot')))
        
        fig.update_layout(title="Mid Price, Best Bid & Best Ask", template="plotly_dark", 
                          height=350, hovermode="x unified")
        return fig

    # Standard chart for others
    def create_chart(col_name, title, color):
        c_data = p_df[['mid_price', 'spread', 'OBi', 'wallmid_norm', 'z_score']].values
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=p_df['timestamp'], y=p_df[col_name], name=title, line=dict(color=color),
            customdata=c_data,
            hovertemplate=f"<b>{title}: %{{y:.2f}}</b><br>Mid: %{{customdata[0]:.2f}}<br>Spr: %{{customdata[1]:.2f}}<br>OBi: %{{customdata[2]:.3f}}<extra></extra>"
        ))
        fig.update_layout(title=title, template="plotly_dark", height=250, hovermode="x unified")
        return fig

    # Display
    st.plotly_chart(create_price_chart(), use_container_width=True)
    st.plotly_chart(create_chart('spread', 'Spread', '#EF553B'), use_container_width=True)
    st.plotly_chart(create_chart('OBi', 'Order Book Imbalance', '#636EFA'), use_container_width=True)
    st.plotly_chart(create_chart('wallmid_norm', 'WallMid Normalized (-2 to 2)', '#AB63FA'), use_container_width=True)

else:
    st.info("Upload your market data to begin.")
