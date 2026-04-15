import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

st.set_page_config(layout="wide", page_title="Orderbook Viewer")

st.title("📊 Orderbook Visualization")

# ==========================================
# LOAD FILES
# ==========================================
def load_files(files):
    dfs = []
    for f in files:
        df = pd.read_csv(f, sep=';')
        df.columns = [c.strip() for c in df.columns]

        # extract day from filename if present
        match = re.search(r'day_(-?\d+)', f.name)
        df['day_label'] = int(match.group(1)) if match else 0

        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


# ==========================================
# FILE UPLOAD
# ==========================================
files = st.sidebar.file_uploader("Upload CSVs", accept_multiple_files=True)

if not files:
    st.stop()

raw = load_files(files)

# ==========================================
# CLEAN DATA
# ==========================================
df = pd.DataFrame({
    "product": raw["product"],
    "timestamp": raw["timestamp"],
    "day": raw["day_label"],
    "bid": pd.to_numeric(raw["bid_price_1"], errors='coerce'),
    "ask": pd.to_numeric(raw["ask_price_1"], errors='coerce'),
    "bid_v": pd.to_numeric(raw["bid_volume_1"], errors='coerce'),
    "ask_v": pd.to_numeric(raw["ask_volume_1"], errors='coerce'),
})

df = df.dropna(subset=["bid", "ask"])
df = df.sort_values(["product", "day", "timestamp"])

# ==========================================
# FEATURES (ONLY ORDERBOOK RELATED)
# ==========================================

# mid price
df["mid"] = (df["bid"] + df["ask"]) / 2

# microprice (wall-mid)
df["microprice"] = (
    df["ask"] * df["bid_v"] + df["bid"] * df["ask_v"]
) / (df["bid_v"] + df["ask_v"] + 1e-9)

# spread
df["spread"] = df["ask"] - df["bid"]

# imbalance
df["imbalance"] = (
    (df["bid_v"] - df["ask_v"]) /
    (df["bid_v"] + df["ask_v"] + 1e-9)
)

# ==========================================
# SIDEBAR FILTERS
# ==========================================
products = df["product"].unique()
selected_product = st.sidebar.selectbox("Product", products)

days = sorted(df["day"].unique())
selected_days = st.sidebar.multiselect("Days", days, default=days)

plot_df = df[
    (df["product"] == selected_product) &
    (df["day"].isin(selected_days))
]

# ==========================================
# PLOTTING
# ==========================================
fig = make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    subplot_titles=[
        "Price (Mid / Bid1 / Ask1 / Microprice)",
        "Spread",
        "Imbalance"
    ]
)

for d in selected_days:
    ddf = plot_df[plot_df["day"] == d]

    # PRICE PANEL
    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["mid"],
        name=f"Day {d} Mid"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["bid"],
        name=f"Day {d} Bid1",
        opacity=0.5
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["ask"],
        name=f"Day {d} Ask1",
        opacity=0.5
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["microprice"],
        name=f"Day {d} MicroPrice",
        line=dict(dash="dot")
    ), row=1, col=1)

    # SPREAD PANEL
    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["spread"],
        name=f"Day {d} Spread"
    ), row=2, col=1)

    # IMBALANCE PANEL
    fig.add_trace(go.Scatter(
        x=ddf["timestamp"], y=ddf["imbalance"],
        name=f"Day {d} Imbalance",
        opacity=0.7
    ), row=3, col=1)


fig.update_layout(
    height=900,
    template="plotly_dark",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)
