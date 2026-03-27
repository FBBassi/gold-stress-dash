import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Liquidity Monitor", layout="wide")

st.title("🛡️ Gold Sovereign Stress Monitor")

# --- UI Mobile ---
col1, col2 = st.columns([1, 2])
with col1:
    tf_choice = st.radio("Timeframe:", ('1D (Alta)', '1H (Media)'))

tf_map = {'1D (Alta)': '1d', '1H (Media)': '1h'}
period_map = {'1D (Alta)': '1y', '1H (Media)': '1mo'}

@st.cache_data(ttl=600)
def get_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'USD_TRY': 'USDTRY=X', 'DXY': 'DX-Y.NYB'}
    df = yf.download(list(assets.values()), period=period, interval=tf)['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_data(tf_map[tf_choice], period_map[tf_choice])
    
    # Calcolo Logica Quant
    data['Fair_Value'] = (data['Oil'] / data['DXY']) * 100
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data = data.dropna()

    # --- Segnali Rapidi (Emoji) ---
    curr_z = data['Z_Score'].iloc[-1]
    if curr_z < -2:
        status, icon, color = "EXTREME SELLING (CB)", "🚨", "#ff4b4b"
    elif curr_z > 2:
        status, icon, color = "SPECULATIVE OVERBOUGHT", "⚠️", "#ffa500"
    else:
        status, icon, color = "NORMAL REGIME", "✅", "#00ff00"

    st.markdown(f"### Status: {icon} <span style='color:{color}'>{status}</span>", unsafe_allow_html=True)

    # --- Creazione Grafico con Bande ---
    fig = make_subplots(rows=1, cols=1)

    # Prezzo Oro
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Spot", line=dict(color='gold', width=3)))

    # Logica per colorare lo sfondo in base allo Z-Score
    for i in range(1, len(data)):
        z = data['Z_Score'].iloc[i]
        if z < -2: # Zone di vendita forzata CB
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.3, line_width=0)
        elif z > 2: # Zone di eccesso speculativo
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="orange", opacity=0.2, line_width=0)

    fig.update_layout(template="plotly_dark", height=500, title=f"Analisi di Regime (Z-Score: {curr_z:.2f})")
    st.plotly_chart(fig, use_container_width=True)

    # Tabella Dati Recenti
    st.write("Dati di Chiusura Recenti:")
    st.table(data[['Gold', 'Z_Score', 'USD_TRY']].tail(3))

except Exception as e:
    st.error(f"Errore: {e}")
