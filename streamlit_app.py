import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Quant Master v11", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Dashboard Controls")
    tf_choice = st.radio("Timeframe:", ('1D (Alta)', '1H (Media)'), index=1)
    st.markdown("---")
    st.warning("⚠️ **Alert Volatilità:** Se attiva, i driver stanno guidando il mercato. Segui il trend.")

@st.cache_data(ttl=300)
def get_market_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'EURUSD': 'EURUSD=X', 'USDTRY': 'USDTRY=X'}
    df = yf.download(list(assets.values()), period=period, interval=tf)['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_market_data('1h' if tf_choice == '1H (Media)' else '1d', '1mo')
    
    # --- LOGICA QUANT ---
    data['Fair_Value'] = (data['Oil'] * data['EURUSD']) * 1.5
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data['Z_Slope'] = data['Z_Score'].diff()
    
    # Calcolo Volatilità Driver (Alert)
    driver_vol = data['Fair_Value'].pct_change().std() * 100
    current_vol = abs(data['Fair_Value'].pct_change().iloc[-1] * 100)
    vol_alert = current_vol > (driver_vol * 2)

    data = data.dropna()

    # --- 1. HEADER DINAMICO ---
    curr_z = data['Z_Score'].iloc[-1]
    l_msg, l_col = ("🔥 BUY ZONE", "#27AE60") if curr_z < -1.5 else ("❄️ SELL ZONE", "#C0392B") if curr_z > 1.5 else ("⚖️ NEUTRAL", "#F1C40F")

    st.markdown(f"<div style='background-color:{l_col}; padding:15px; border-radius:10px; text-align:center;'><h1 style='color:white; margin:0;'>{l_msg} | Z-Score: {curr_z:.2f}</h1></div>", unsafe_allow_html=True)

    if vol_alert:
        st.error(f"🚨 VOLATILITY ALERT: I driver si muovono velocemente ({current_vol:.2f}%). Il breakout è reale!")

    # --- 2. GRAFICI ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.35, 0.65])

    # Plot 1: Contesto
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Fair_Value'], name="Fair Value", line=dict(color='#3498DB', width=1, dash='dot')), row=1, col=1)

    # Plot 2: Z-Score e Gold
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Price", line=dict(color='#FFD700', width=3)), row=2, col=1, secondary_y=True)

    # Separatori e Background
    seps = data.index[data.index.hour == 0] if '1h' in locals() else data.index
    for s in seps: fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.3)
    
    for i in range(1, len(data)):
        if data['Z_Score'].iloc[i] < -1.5:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.15, line_width=0, row=2, col=1)

    fig.update_layout(height=850, template="plotly_white", margin=dict(l=20, r=20, t=50, b=20), showlegend=False)
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # --- 3. SCALPING MATRIX ---
    st.subheader("🎯 Scalping Execution Matrix")
    c1, c2, c3 = st.columns(3)
    c1.metric("Bias", "LONG (Follow Breakout)" if curr_z < 0 else "SHORT (Fading)")
    c2.metric("Forza Driver", "ALTA" if vol_alert else "NORMALE")
    c3.metric("Probabilità Inversione", "BASSA (Trend Sano)" if curr_z < 1.5 else "ALTA")

except Exception as e:
    st.error(f"Errore: {e}")
