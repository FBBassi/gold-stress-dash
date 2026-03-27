import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Sovereign Monitor v13", layout="wide")

# --- 1. SIDEBAR (RIPRISTINATA INTEGRALMENTE) ---
with st.sidebar:
    st.header("⚙️ Parametri Monitor")
    tf_choice = st.radio("Seleziona Timeframe:", 
                         ('15m (Scalping)', '1H (Intraday)', '1D (Macro)'), index=1)
    st.markdown("---")
    st.info("💡 **Strategia:** Se Z-Score < -2 e il prezzo assorbe i massimi, attendi il breakout confermato dai driver.")

# Mappatura corretta per Yahoo Finance
tf_map = {'15m (Scalping)': '15m', '1H (Intraday)': '1h', '1D (Macro)': '1d'}
period_map = {'15m (Scalping)': '5d', '1H (Intraday)': '1mo', '1D (Macro)': '1y'}

@st.cache_data(ttl=300)
def get_market_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'EURUSD': 'EURUSD=X', 'USDTRY': 'USDTRY=X'}
    df = yf.download(list(assets.values()), period=period, interval=tf)['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_market_data(tf_map[tf_choice], period_map[tf_choice])
    
    # --- 2. LOGICA QUANTITATIVA ---
    data['Fair_Value'] = (data['Oil'] * data['EURUSD']) * 1.5
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    # Z-Score calcolato su 20 periodi
    raw_z = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    # Smoothing per pulizia segnale
    data['Z_Score'] = raw_z.rolling(window=3).mean()
    data['Z_Slope'] = data['Z_Score'].diff()
    
    # Stress Index
    oil_rets = np.log(data['Oil']/data['Oil'].shift(1))
    try_rets = np.log(data['USDTRY']/data['USDTRY'].shift(1))
    data['Stress'] = (oil_rets + try_rets).rolling(10).mean()
    
    data = data.dropna()

    # --- 3. SEMAFORO OPERATIVO ---
    curr_z = data['Z_Score'].iloc[-1]
    if curr_z < -2.0:
        b_msg, b_col = "🔥 EXTREME BUY BIAS (Sconto)", "#27AE60"
    elif curr_z > 2.0:
        b_msg, b_col = "❄️ EXTREME SELL BIAS (Premio)", "#C0392B"
    else:
        b_msg, b_col = "⚖️ REGIME NEUTRO", "#F1C40F"

    st.markdown(f"<div style='background-color:{b_col}; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;'><h1 style='color:white; margin:0;'>{b_msg}</h1><h2 style='color:white;'>Z-Score: {curr_z:.2f}</h2></div>", unsafe_allow_html=True)

    # --- 4. DASHBOARD GRAFICA (DUE SUBPLOTS) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.35, 0.65],
                        subplot_titles=("CONTESTO: Gold vs Stress", "OPERATIVO: Z-Score vs Gold Price"))

    # Grafico 1: Context
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress'], name="Stress", fill='tozeroy', line=dict(color='rgba(231,76,60,0.2)')), row=1, col=1, secondary_y=True)

    # Grafico 2: Z-Score & Price Ref (Continua)
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Price Ref", line=dict(color='#FFD700', width=3, dash='solid')), row=2, col=1, secondary_y=True)

    # Separatori e Background
    seps = data.index[data.index.hour == 0] if tf_choice != '1D (Macro)' else data.index[data.index.dayofweek == 0]
    for s in seps:
        fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.3)
    
    # Zone di Sfondo
    for i in range(1, len(data)):
        if data['Z_Score'].iloc[i] < -2.0:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.15, line_width=0, row=2, col=1)

    fig.update_layout(height=850, template="plotly_white", showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 5. SCALPING MATRIX ---
    st.markdown("---")
    st.subheader("🎯 Scalping Execution Matrix")
    c1, c2, c3 = st.columns(3)
    c1.metric("Bias Attuale", "LONG" if curr_z < 0 else "SHORT")
    c2.metric("Pressione Driver", "ALTA (Sconto)" if curr_z < -1.5 else "NORMALE")
    c3.metric("Filtro EMA 7-21", "Cerca solo LONG" if curr_z < -1 else "Cerca solo SHORT")

except Exception as e:
    st.error(f"Errore tecnico: {e}")
