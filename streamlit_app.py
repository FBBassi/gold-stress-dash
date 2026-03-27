import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configurazione Mobile-First
st.set_page_config(page_title="Gold Sovereign Monitor", layout="wide")

# --- SIDEBAR PER CONTROLLI ---
with st.sidebar:
    st.header("⚙️ Impostazioni")
    tf_choice = st.radio("Timeframe di Analisi:", ('1D (Alta)', '1H (Media)'))
    st.info("Nota: L'affidabilità dello Z-Score è massima su base Daily.")

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
    
    # Logica Quantitativa
    data['Fair_Value'] = (data['Oil'] / data['DXY']) * 100
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data['Stress_Index'] = (data['Oil'].pct_change() + data['USD_TRY'].pct_change()).rolling(10).mean()
    data = data.dropna()

    # --- HEADER STATUS ---
    curr_z = data['Z_Score'].iloc[-1]
    if curr_z < -2:
        status, icon, color = "🚨 EXTREME LIQUIDATION (CB SELLING)", "🚨", "#ff4b4b"
    elif curr_z > 2:
        status, icon, color = "⚠️ SPECULATIVE OVERBOUGHT", "⚠️", "#ffa500"
    else:
        status, icon, color = "✅ NORMAL REGIME", "✅", "#00ff00"

    st.markdown(f"<h2 style='text-align: center; color: {color};'>{icon} {status}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center;'>Z-Score Attuale: <b>{curr_z:.2f}</b></p>", unsafe_allow_html=True)

    # --- DASHBOARD MULTI-CHART ---
    # Due grafici: Uno per il contesto, uno per l'operatività (con doppia scala)
    fig = make_subplots(rows=2, cols=1, 
                        shared_xaxes=True, 
                        vertical_spacing=0.05,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        subplot_titles=("Overlay Gold vs Stress", "Z-Score Signal con Overlay Prezzo"))

    # Grafico 1: Gold & Stress (Context)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Spot", line=dict(color='gold', width=2)), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress_Index'], name="Stress Index", fill='tozeroy', line=dict(color='rgba(255,0,0,0.15)')), row=1, col=1, secondary_y=True)

    # Grafico 2: Z-Score (Signal) + Gold (Secondary Y)
    # Aggiungiamo lo Z-Score sulla Y primaria
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='cyan', width=2)), row=2, col=1, secondary_y=False)
    
    # Aggiungiamo il Prezzo sulla Y secondaria per il confronto di tempestività
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold (Ref)", line=dict(color='rgba(255,255,255,0.3)', width=1)), row=2, col=1, secondary_y=True)

    # Bande di Regime sullo Z-Score
    for i in range(1, len(data)):
        z = data['Z_Score'].iloc[i]
        if z < -2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.3, line_width=0, row=2, col=1)
        elif z > 2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="orange", opacity=0.2, line_width=0, row=2, col=1)

    # Layout finale ottimizzato per mobile
    fig.update_layout(template="plotly_dark", height=850, showlegend=False, margin=dict(l=10, r=10, t=50, b=10))
    fig.update_yaxes(title_text="Price / Z-Score", row=1, col=1)
    fig.update_yaxes(title_text="Stress", secondary_y=True, row=1, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Errore tecnico: {e}")
