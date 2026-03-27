import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configurazione Interfaccia
st.set_page_config(page_title="Gold Sovereign Monitor v5", layout="wide")

# --- SIDEBAR: CONTROLLI E LOGICA ---
with st.sidebar:
    st.header("📊 Parametri")
    tf_choice = st.radio("Timeframe:", ('1D (Alta)', '1H (Media)'), index=0)
    st.markdown("---")
    st.write("**Legenda Colori:**")
    st.markdown("🟡 **Oro:** Prezzo Gold")
    st.markdown("🟢 **Verde:** Z-Score (Segnale)")
    st.markdown("🔴 **Area Rossa:** Stress / Vendita CB")

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
    
    # --- CALCOLI QUANT ---
    data['Fair_Value'] = (data['Oil'] / data['DXY']) * 100
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    
    # Stress Index Normalizzato
    oil_rets = np.log(data['Oil']/data['Oil'].shift(1))
    try_rets = np.log(data['USD_TRY']/data['USD_TRY'].shift(1))
    raw_stress = (oil_rets + try_rets).rolling(10).mean()
    data['Stress_Index'] = (raw_stress - raw_stress.mean()) / raw_stress.std()
    data = data.dropna()

    # --- HEADER DINAMICO ---
    curr_z = data['Z_Score'].iloc[-1]
    if curr_z < -2:
        st.error(f"🚨 EXTREME LIQUIDATION | Z-Score: {curr_z:.2f}")
    elif curr_z > 2:
        st.warning(f"⚠️ SPECULATIVE OVERBOUGHT | Z-Score: {curr_z:.2f}")
    else:
        st.success(f"✅ REGIME NORMALE | Z-Score: {curr_z:.2f}")

    # --- DASHBOARD GRAFICA ---
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.07,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
        row_heights=[0.4, 0.6],
        subplot_titles=("CONTESTO: Gold vs Stress", "OPERATIVO: Z-Score (Verde) vs Gold Price (Oro)")
    )

    # Grafico 1: Gold & Stress
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2.5)), row=1, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress_Index'], name="Stress", fill='tozeroy', line=dict(color='#E74C3C', width=1)), row=1, col=1, secondary_y=True)

    # Grafico 2: Z-Score (VERDE) e Gold (ORO)
    # Z-Score sulla scala primaria (sinistra)
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=2.5)), row=2, col=1, secondary_y=False)
    # Gold sulla scala secondaria (destra)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Price Ref", line=dict(color='#FFD700', width=1.5, dash='dot')), row=2, col=1, secondary_y=True)

    # Bande di Regime (Background)
    for i in range(1, len(data)):
        z = data['Z_Score'].iloc[i]
        if z < -2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="#E74C3C", opacity=0.25, line_width=0, row=2, col=1)
        elif z > 2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="#F39C12", opacity=0.15, line_width=0, row=2, col=1)

    # Linee Orizzontali di Soglia
    fig.add_hline(y=-2, line_dash="dash", line_color="#27AE60", row=2, col=1) # Verde scuro per soglia buy
    fig.add_hline(y=2, line_dash="dash", line_color="#C0392B", row=2, col=1) # Rosso scuro per soglia sell

    # Layout Ergonomico (Compatibile Dark/Light)
    fig.update_layout(
        height=850,
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    # Formattazione Assi X (Gestione Ore)
    if tf_choice == '1H (Media)':
        fig.update_xaxes(tickformat="%d %b\n%H:%M", row=2, col=1)
    else:
        fig.update_xaxes(tickformat="%d %b", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # --- TABELLA DATI ---
    st.markdown("### Dati Recenti")
    res_df = data[['Gold', 'Z_Score', 'USD_TRY']].tail(10).sort_index(ascending=False).reset_index()
    st.dataframe(res_df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Errore tecnico: {e}")
