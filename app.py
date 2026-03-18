import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title(" OVERFITTERS | Order-Flow & Trade Analytics")

# --- DATA LOADERS ---
@st.cache_data
def load_market_data(file):
    df = pd.read_csv(file, sep=';')
    df['mid'] = (df['ask_price_1'] + df['bid_price_1']) / 2
    return df

@st.cache_data
def load_trade_data(file):
    return pd.read_csv(file, sep=';')

# --- SIDEBAR ---
st.sidebar.header("Data Upload")
market_file = st.sidebar.file_uploader("Upload Market CSV", type="csv")
trades_file = st.sidebar.file_uploader("Upload Trades CSV", type="csv")

if market_file and trades_file:
    df_m = load_market_data(market_file)
    df_t = load_trade_data(trades_file)
    
    product = st.sidebar.selectbox("Select Product", df_m['product'].unique())
    m_df = df_m[df_m['product'] == product].sort_values('timestamp')
    t_df = df_t[df_t['symbol'] == product].sort_values('timestamp')

    # --- ORDER FLOW LOGIC ---
    # Determine if trade was a "Buy" (above mid) or "Sell" (below mid)
    t_df = pd.merge_asof(t_df, m_df[['timestamp', 'mid']], on='timestamp', direction='nearest')
    t_df['side'] = ['Buy' if p > m else 'Sell' for p, m in zip(t_df['price'], t_df['mid'])]
    
    # --- DASHBOARD LAYOUT ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Price & Trade Execution")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=m_df['timestamp'], y=m_df['mid'], name="Mid Price", line=dict(color='gray', dash='dot')))
        fig.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['price'], mode='markers', 
                                 marker=dict(color=t_df['side'].map({'Buy':'green', 'Sell':'red'}), size=8), name="Trades"))
        fig.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("Aggressive Buy vs Sell Volume")
        vol_df = t_df.groupby('side')['quantity'].sum().reset_index()
        fig_pie = px.pie(vol_df, values='quantity', names='side', color='side', 
                         color_discrete_map={'Buy':'green', 'Sell':'red'}, template="plotly_dark")
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- VOLUME PROFILE ---
    st.subheader("Trade Heatmap (Price Levels)")
    fig_hist = px.histogram(t_df, x='price', color='side', barmode='overlay', template="plotly_dark")
    st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.info("Upload BOTH Market Data and Trades CSV to begin Order-Flow analysis.")
