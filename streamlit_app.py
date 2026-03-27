import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Executioner v12.1", layout="wide")

# --- SIDEBAR: FOCUS SCALPING ---
with st.sidebar:
    st.header("⚡ Scalper Dashboard")
    tf_choice = st.radio("TF Analisi:", ('1H (Bias)', '15m (Entry Bias)'), index=1)
    st.markdown("---")
    st.write("**Stato Attuale:**")
    st.info("Z-Score < -2: L'oro è 'compressa'. Cerca il rimbalzo sulle medie mobili.")

@st.cache_data(ttl=300)
def get_market_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'EURUSD': 'EURUSD=X', 'USDTRY': 'USDTRY=X'}
    df = yf.download(list(assets.values()), period=period, interval=tf)['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_market_data('15m' if tf_choice == '15m (Entry Bias)' else '1h', '5d')
    
    # Logica Quant Smoothed
    data['Fair_Value'] = (data['Oil'] * data['EURUSD']) * 1.5
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    raw_z = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data['Z_Score'] = raw_z.rolling(window=3).mean() # Smoothing ridotto per più reattività
    data = data.dropna()

    # --- BIAS VISIVO ---
    curr_z = data['Z_Score'].iloc[-1]
    
    if curr_z < -2.0:
        b_msg, b_col = "🔥 EXTREME LONG BIAS (Sconto Istituzionale)", "#27AE60"
    elif curr_z > 2.0:
        b_msg, b_col = "❄️ EXTREME SHORT BIAS (Premio Speculativo)", "#C0392B"
    else:
        b_msg, b_col = "⚖️ REGIME NEUTRO", "#F1C40F"

    st.markdown(f"<div style='background-color:{b_col}; padding:20px; border-radius:15px; text-align:center;'><h1 style='color:white; margin:0;'>{b_msg}</h1><h2 style='color:white;'>Z-Score: {curr_z:.2f}</h2></div>", unsafe_allow_html=True)

    # --- GRAFICO OPERATIVO ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.3, 0.7])

    # Plot 1: Contesto Prezzo vs Fair Value
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Fair_Value'], name="Fair Value", line=dict(color='#3498DB', width=1, dash='dot')), row=1, col=1)

    # Plot 2: Z-Score e Gold
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Ref", line=dict(color='#FFD700', width=3)), row=2, col=1, secondary_y=True)

    # Separatori Giornalieri (Puntini Neri)
    seps = data.index[data.index.hour == 0]
    for s in seps: fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.3)

    fig.update_layout(height=800, template="plotly_white", showlegend=False)
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
