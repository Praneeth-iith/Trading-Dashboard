import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import glob
import re
import plotly.io as pio

pio.renderers.default = 'notebook_connected'


# =========================
# 1. LOAD MULTI-DAY DATA
# =========================
def load_data(folder_path):

    price_files = glob.glob(f"{folder_path}/prices_round_1_day_*.csv")
    trade_files = glob.glob(f"{folder_path}/trades_round_1_day_*.csv")

    if len(price_files) == 0:
        print("❌ No price files found")
        return None, None

    # ---- PRICES ----
    price_dfs = []
    for f in price_files:
        df = pd.read_csv(f, sep=';')

        day_match = re.search(r'day_(-?\d+)', f)
        df['day'] = int(day_match.group(1)) if day_match else 0

        price_dfs.append(df)

    df_prices = pd.concat(price_dfs).sort_values(['product', 'day', 'timestamp'])


    # ---- TRADES ----
    trade_dfs = []
    for f in trade_files:
        df = pd.read_csv(f, sep=';')

        day_match = re.search(r'day_(-?\d+)', f)
        df['day'] = int(day_match.group(1)) if day_match else 0

        if 'symbol' not in df.columns and 'product' in df.columns:
            df = df.rename(columns={'product': 'symbol'})

        trade_dfs.append(df)

    df_trades = pd.concat(trade_dfs).sort_values(['symbol', 'day', 'timestamp'])


    # ---- FEATURES ----
    df_prices['mid'] = (df_prices['bid_price_1'] + df_prices['ask_price_1']) / 2
    df_prices['spread'] = df_prices['ask_price_1'] - df_prices['bid_price_1']

    df_prices['imbalance'] = (
        (df_prices['bid_volume_1'] - df_prices['ask_volume_1']) /
        (df_prices['bid_volume_1'] + df_prices['ask_volume_1'] + 1e-9)
    )

    return df_prices, df_trades


# =========================
# 2. ANALYZER FUNCTION
# =========================
def analyze(product):

    p_df = df_prices[df_prices['product'] == product]
    t_df = df_trades[df_trades['symbol'] == product]

    if p_df.empty:
        print("No price data")
        return

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[
            "Price (Bid/Ask + Trades)",
            "Spread",
            "Order Book Imbalance",
            "Trade Volume"
        ],
        row_heights=[0.5, 0.15, 0.15, 0.2]
    )

    # =========================
    # PRICE
    # =========================
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['ask_price_1'],
        name='Ask'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['bid_price_1'],
        name='Bid'
    ), row=1, col=1)

    if not t_df.empty:
        fig.add_trace(go.Scatter(
            x=t_df['timestamp'],
            y=t_df['price'],
            mode='markers',
            name='Trades'
        ), row=1, col=1)

    # =========================
    # SPREAD
    # =========================
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['spread'],
        fill='tozeroy',
        name='Spread'
    ), row=2, col=1)

    # =========================
    # IMBALANCE
    # =========================
    fig.add_trace(go.Scatter(
        x=p_df['timestamp'],
        y=p_df['imbalance'],
        name='Imbalance'
    ), row=3, col=1)

    # =========================
    # TRADE VOLUME
    # =========================
    if not t_df.empty:
        fig.add_trace(go.Histogram(
            x=t_df['quantity'],
            name='Trade Size Dist'
        ), row=4, col=1)

    fig.update_layout(
        height=900,
        template='plotly_dark',
        title=f"Analyzer: {product} (All Days Combined)"
    )

    fig.show()


# =========================
# 3. RUN
# =========================

df_prices, df_trades = load_data("ROUND_1")

# 🔥 List products
print("Products:", df_prices['product'].unique())

# 👉 CHANGE THIS MANUALLY
analyze(product=df_prices['product'].iloc[0])
