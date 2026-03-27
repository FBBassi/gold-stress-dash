import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configurazione Browser/Mobile
st.set_page_config(page_title="Gold Sovereign v13.1", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Parametri Monitor")
    tf_choice = st.radio("Seleziona Timeframe:", 
                         ('15m (Scalping)', '1H (Intraday)', '1D (Macro)'), index=1)
    st.markdown("---")
    st.info("💡 **Target:** Cerca di chiudere i Long quando il prezzo si avvicina al Fair Value (Distanza < 2$).")

tf_map = {'15m (Scalping)': '15m', '1H (Intraday)': '1h', '1D (Macro)': '1d'}
period_map = {'15m (Scalping)': '5d', '1H (Intraday)': '1mo', '1D (Macro)': '1y'}

@st.cache_data(ttl=120) # Aggiornamento più frequente per scalping
def get_market_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'EURUSD': 'EURUSD=X', 'USDTRY': 'USDTRY=X'}
    try:
        df = yf.download(list(assets.values()), period=period, interval=tf, progress=False)['Close']
        df.columns = assets.keys()
        return df.dropna()
    except Exception:
        return pd.DataFrame()

data = get_market_data(tf_map[tf_choice], period_map[tf_choice])

if not data.empty:
    # --- LOGICA QUANT ---
    # Fair Value approssimato per visione intermarket
    data['Fair_Value'] = (data['Oil'] * data['EURUSD']) * 1.5
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    
    # Z-Score
    mean_div = data['Divergence'].rolling(20).mean()
    std_div = data['Divergence'].rolling(20).std()
    data['Z_Score'] = (data['Divergence'] - mean_div) / std_div
    data['Z_Score_Smooth'] = data['Z_Score'].rolling(3).mean()
    
    # Stress Index
    oil_rets = np.log(data['Oil']/data['Oil'].shift(1))
    try_rets = np.log(data['USDTRY']/data['USDTRY'].shift(1))
    data['Stress'] = (oil_rets + try_rets).rolling(10).mean()
    
    data = data.dropna()

    # --- INDICATORI DI TARGET (NEW) ---
    curr_gold = data['Gold'].iloc[-1]
    curr_fv = data['Fair_Value'].iloc[-1]
    dist_fv = curr_fv - curr_gold # Distanza matematica
    curr_z = data['Z_Score_Smooth'].iloc[-1]

    # --- HEADER DINAMICO ---
    b_msg, b_col = ("🔥 EXTREME LONG", "#27AE60") if curr_z < -2 else ("❄️ EXTREME SHORT", "#C0392B") if curr_z > 2 else ("⚖️ NEUTRAL", "#F1C40F")
    
    st.markdown(f"<div style='background-color:{b_col}; padding:15px; border-radius:10px; text-align:center;'><h1 style='color:white; margin:0;'>{b_msg} | Z-Score: {curr_z:.2f}</h1></div>", unsafe_allow_html=True)

    # Widget di riepilogo
    c1, c2, c3 = st.columns(3)
    c1.metric("Prezzo Attuale (Gold)", f"{curr_gold:.2f}$")
    c2.metric("Fair Value Teorico", f"{curr_fv:.2f}$")
    # Se il valore è positivo, l'oro deve salire (Sconto)
    c3.metric("Distanza al Target", f"{dist_fv:.2f}$", delta=f"{dist_fv:.2f}", delta_color="normal")

    # --- GRAFICI ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.35, 0.65])

    # Plot 1: Context
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress'], name="Stress", fill='tozeroy', line=dict(color='rgba(231,76,60,0.2)')), row=1, col=1, secondary_y=True)

    # Plot 2: Z-Score & Price Ref
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score_Smooth'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Price", line=dict(color='#FFD700', width=3)), row=2, col=1, secondary_y=True)

    # Background zones e Separatori
    seps = data.index[data.index.hour == 0] if tf_choice != '1D (Macro)' else data.index[data.index.dayofweek == 0]
    for s in seps: fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.3)
    
    fig.update_layout(height=800, template="plotly_white", showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # Matrix di Scalping
    st.table(pd.DataFrame({
        'Analisi': ['Gap di Prezzo', 'Forza Trend', 'Consiglio Scalping'],
        'Valore': [f"{dist_fv:.2f} $", "ALTA (Breakout)", "Mantenere LONG fino a FV"]
    }))

else:
    st.warning("⚠️ Caricamento dati in corso o mercato chiuso. Attendi 10 secondi...")
