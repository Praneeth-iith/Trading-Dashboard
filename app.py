import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

st.set_page_config(layout="wide", page_title="OVERFITTERS Terminal")
st.title("📈 OVERFITTERS | Professional Quant Terminal")

# --- DATA PROCESSING ---
@st.cache_data
def process_data(m_df, t_df):
    m_df = m_df.sort_values('timestamp')
    t_df = t_df.sort_values('timestamp')
    m_df['mid'] = (m_df['ask_price_1'] + m_df['bid_price_1']) / 2
    # Determine Aggression (Buy/Sell)
    t_df = pd.merge_asof(t_df, m_df[['timestamp', 'mid']], on='timestamp', direction='nearest')
    t_df['side'] = ['Buy' if p > m else 'Sell' for p, m in zip(t_df['price'], t_df['mid'])]
    return m_df, t_df

# --- UPLOADERS ---
col_u1, col_u2 = st.columns(2)
market_file = col_u1.file_uploader("Upload Market Data (CSV)", type="csv")
trades_file = col_u2.file_uploader("Upload Trades Data (CSV)", type="csv")

if market_file and trades_file:
    m_df, t_df = process_data(pd.read_csv(market_file, sep=';'), pd.read_csv(trades_file, sep=';'))
    product = st.sidebar.selectbox("Select Product", m_df['product'].unique())
    m_df = m_df[m_df['product'] == product]
    t_df = t_df[t_df['symbol'] == product]

    # --- DASHBOARD LAYOUT ---
    # ROW 1: Price Corridor + Trades
    st.subheader("Market Context & Trade Flow")
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=m_df['timestamp'], y=m_df['ask_price_1'], line=dict(color='red', width=1, dash='dot'), name="Best Ask"))
    fig1.add_trace(go.Scatter(x=m_df['timestamp'], y=m_df['mid'], line=dict(color='green', width=2), name="Mid Price"))
    fig1.add_trace(go.Scatter(x=m_df['timestamp'], y=m_df['bid_price_1'], line=dict(color='blue', width=1, dash='dot'), name="Best Bid"))
    fig1.add_trace(go.Scatter(x=t_df['timestamp'], y=t_df['price'], mode='markers', marker=dict(color=t_df['side'].map({'Buy':'#00FF00', 'Sell':'#FF0000'}), size=8), name="Executions"))
    fig1.update_layout(template="plotly_dark", height=400, hovermode="x unified")
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("ℹ️ **Price Corridor & Trades:** Shows the 'spread' where bots are quoting vs where trades are actually happening. Look for trades outside the dotted lines—those are 'Aggressive Sweeps'.")

    # ROW 2: Microstructure (Spread/OBi/WallMid)
    st.subheader("Microstructure Indicators")
    cols = st.columns(3)
    
    # 1. Spread
    fig2 = px.line(m_df, x='timestamp', y=m_df['ask_price_1']-m_df['bid_price_1'], template="plotly_dark")
    cols[0].plotly_chart(fig2, use_container_width=True)
    cols[0].caption("ℹ️ **Spread:** Measures market liquidity. Spikes = Low Liquidity/Risk.")

    # 2. Imbalance
    ibi = (m_df['bid_volume_1'] - m_df['ask_volume_1']) / (m_df['bid_volume_1'] + m_df['ask_volume_1'])
    fig3 = px.bar(x=m_df['timestamp'], y=ibi, template="plotly_dark")
    cols[1].plotly_chart(fig3, use_container_width=True)
    cols[1].caption("ℹ️ **Imbalance (OBi):** Positive = Buying pressure. Negative = Selling pressure.")

    # 3. WallMid Norm
    rolling_mean = m_df['mid'].rolling(30).mean()
    rolling_std = m_df['mid'].rolling(30).std()
    norm = ((m_df['mid'] - rolling_mean) / rolling_std).clip(-2, 2)
    fig4 = px.line(x=m_df['timestamp'], y=norm, template="plotly_dark")
    cols[2].plotly_chart(fig4, use_container_width=True)
    cols[2].caption("ℹ️ **WallMid Norm:** Indicates how 'stretched' the price is relative to its average. |N| > 1.5 is an extreme.")

    # ROW 3: Volume Profile (Read Points)
    st.subheader("Volume Heatmap (Read Points)")
    fig5 = px.histogram(t_df, x='price', y='quantity', color='side', barmode='group', template="plotly_dark")
    st.plotly_chart(fig5, use_container_width=True)
    st.caption("ℹ️ **Volume Profile (Read Points):** These are price levels with high trade volume. This is where market participants define 'Fair Value'. If a price level has a massive spike here, it is a high-probability 'Support' or 'Resistance' zone for your algorithm.")

else:
    st.info("Upload CSV files to populate the Terminal.")
