import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Sovereign v13.2", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Parametri Monitor")
    tf_choice = st.radio("Timeframe Analisi:", 
                         ('15m (Scalping)', '1H (Intraday)', '1D (Macro)'), index=1)
    st.markdown("---")
    st.info("💡 **Focus:** Se la Distanza al Target è positiva, l'Oro è 'a sconto' rispetto ai fondamentali.")

# Mappatura Ticker
tickers = {
    'GC=F': 'Gold',
    'BZ=F': 'Oil',
    'EURUSD=X': 'EURUSD',
    'USDTRY=X': 'USDTRY'
}

tf_map = {'15m (Scalping)': '15m', '1H (Intraday)': '1h', '1D (Macro)': '1d'}
period_map = {'15m (Scalping)': '5d', '1H (Intraday)': '1mo', '1D (Macro)': '1y'}

@st.cache_data(ttl=120)
def get_clean_data(tf, period):
    # Download esplicito per evitare errori di allineamento colonne
    raw_data = yf.download(list(tickers.keys()), period=period, interval=tf, progress=False)['Close']
    # Rinomino le colonne usando il ticker originale per sicurezza
    df = raw_data.rename(columns=tickers)
    return df.dropna()

try:
    data = get_clean_data(tf_map[tf_choice], period_map[tf_choice])
    
    # --- LOGICA QUANTITATIVA CORRETTA ---
    # Calcolo Fair Value basato sulla correlazione intermarket attuale
    # Usiamo un moltiplicatore dinamico basato sulla media degli ultimi 20 periodi per allineare le scale
    raw_fv = (data['Oil'] * data['EURUSD'])
    multiplier = (data['Gold'] / raw_fv).rolling(20).mean()
    data['Fair_Value'] = raw_fv * multiplier
    
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    
    # Z-Score (Normalizzazione della divergenza)
    std_div = data['Divergence'].rolling(20).std()
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / std_div
    data['Z_Score_Smooth'] = data['Z_Score'].rolling(3).mean()
    
    data = data.dropna()

    # --- DATI REAL-TIME ---
    curr_gold = data['Gold'].iloc[-1]
    curr_fv = data['Fair_Value'].iloc[-1]
    dist_fv = curr_fv - curr_gold
    curr_z = data['Z_Score_Smooth'].iloc[-1]

    # --- HEADER STATUS ---
    if curr_z < -1.8:
        status, color = "🚨 SCONTO ISTITUZIONALE (BUY BIAS)", "#27AE60"
    elif curr_z > 1.8:
        status, color = "⚠️ PREMIO SPECULATIVO (SELL BIAS)", "#C0392B"
    else:
        status, color = "⚖️ REGIME NEUTRO", "#F1C40F"

    st.markdown(f"<div style='background-color:{color}; padding:15px; border-radius:10px; text-align:center;'><h1 style='color:white; margin:0;'>{status}</h1></div>", unsafe_allow_html=True)

    # Widget di Controllo Prezzi
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo GOLD (GC=F)", f"{curr_gold:.2f} $")
    c2.metric("Fair Value Teorico", f"{curr_fv:.2f} $")
    c3.metric("Distanza al Target", f"{dist_fv:.2f} $", delta=f"{dist_fv:.2f}", delta_color="normal")

    # --- GRAFICI (RIPRISTINATI) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.4, 0.6],
                        subplot_titles=("Analisi di Contesto: Gold vs Fair Value", "Operativo: Z-Score con Overlay Prezzo"))

    # Subplot 1: Gold vs Fair Value (Dovrebbero correre vicini ora)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Fair_Value'], name="Fair Value", line=dict(color='#3498DB', width=1.5, dash='dot')), row=1, col=1)

    # Subplot 2: Z-Score e Prezzo
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score_Smooth'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Price Ref", line=dict(color='#FFD700', width=2, opacity=0.6)), row=2, col=1, secondary_y=True)

    # Bande di Alert
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)
    
    # Separatori Giornalieri
    if tf_choice != '1D (Macro)':
        seps = data.index[data.index.hour == 0]
        for s in seps: fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.2)

    fig.update_layout(height=850, template="plotly_white", showlegend=False, margin=dict(l=20, r=20, t=50, b=20))
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # Tabella di Verifica
    st.markdown("### Monitor Flussi Recenti")
    st.dataframe(data[['Gold', 'Fair_Value', 'Z_Score_Smooth']].tail(5).sort_index(ascending=False), use_container_width=True)

except Exception as e:
    st.error(f"Errore tecnico durante l'allineamento dati: {e}")
    st.info("Suggerimento: Prova a ricaricare la pagina tra 10 secondi per resettare la connessione API.")
