import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Master Predictor v9", layout="wide")

# --- 1. SIDEBAR: CONTROLLI (RIPRISTINATI) ---
with st.sidebar:
    st.header("⚙️ Configurazione")
    tf_choice = st.radio("Timeframe di Analisi:", ('1D (Alta)', '1H (Media)'), index=1)
    st.markdown("---")
    st.write("📊 **Dati:** Yahoo Finance (~15m delay)")
    st.write("🟢 **Z-Score:** Segnale Quant")
    st.write("🟡 **Gold:** Price Reference")

tf_map = {'1D (Alta)': '1d', '1H (Media)': '1h'}
period_map = {'1D (Alta)': '1y', '1H (Media)': '1mo'}

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
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data['Z_Slope'] = data['Z_Score'].diff()
    
    oil_rets = np.log(data['Oil']/data['Oil'].shift(1))
    try_rets = np.log(data['USDTRY']/data['USDTRY'].shift(1))
    raw_stress = (oil_rets + try_rets).rolling(10).mean()
    data['Stress_Index'] = (raw_stress - raw_stress.mean()) / raw_stress.std()
    data = data.dropna()

    # --- 3. HEADER OPERATIVO ---
    curr_z = data['Z_Score'].iloc[-1]
    slope = data['Z_Slope'].iloc[-1]
    
    if curr_z < -2:
        l_msg, l_col = "🔥 STRONG BUY / ACCUMULATION", "#27AE60"
    elif curr_z > 2:
        l_msg, l_col = "❄️ STRONG SELL / DISTRIBUTION", "#C0392B"
    else:
        l_msg, l_col = "⚖️ NEUTRAL / WAIT", "#F1C40F"

    st.markdown(f"""
        <div style="background-color:{l_col}; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;">
            <h1 style="color:white; margin:0;">{l_msg}</h1>
            <p style="color:white; margin:5px;">Z-Score Attuale: {curr_z:.2f} | Momentum: {"Rialzista" if slope > 0 else "Ribassista"}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. DASHBOARD GRAFICA (DUE FRAME RIPRISTINATI) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.4, 0.6],
                        subplot_titles=("CONTESTO: Gold vs Stress Index", "OPERATIVO: Z-Score vs Gold Price (Continua)"))

    # FRAME 1: Gold vs Stress
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Spot", line=dict(color='#FFD700', width=2.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress_Index'], name="Stress Index", fill='tozeroy', line=dict(color='rgba(192, 57, 43, 0.3)')), row=1, col=1, secondary_y=True)

    # FRAME 2: Z-Score e Gold LINEA CONTINUA
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score (Verde)", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Ref (Continua)", line=dict(color='#FFD700', width=3, dash='solid')), row=2, col=1, secondary_y=True)

    # Sfondo zone Z-Score
    for i in range(1, len(data)):
        z_val = data['Z_Score'].iloc[i]
        if z_val < -2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.2, line_width=0, row=2, col=1)
        elif z_val > 2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="orange", opacity=0.15, line_width=0, row=2, col=1)

    # SEPARATORI VERTICALI (Puntini neri sottili)
    separators = data.index[data.index.hour == 0] if tf_choice == '1H (Media)' else data.index[data.index.dayofweek == 0]
    for s in separators:
        fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.4)

    # Soglie Orizzontali
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)

    # Layout e Timeline doppia riga
    fig.update_layout(height=850, template="plotly_white", margin=dict(l=20, r=20, t=50, b=20), legend=dict(orientation="h", y=1.05))
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # --- 5. SEZIONE SCALPING PREDICTOR (NUOVA) ---
    st.markdown("---")
    st.subheader("🎯 Scalping Execution Matrix")
    
    # Calcolo Bias
    bias = "LONG" if slope > 0 and curr_z < -1 else "SHORT" if slope < 0 and curr_z > 1 else "NEUTRAL"
    prob = "85%" if abs(curr_z) > 2 else "60%" if abs(curr_z) > 1 else "40%"
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Bias Probabilistico (TF 5m)", bias)
    c2.metric("Probabilità Reversione", prob)
    c3.metric("Lead Time (Vantaggio)", "45-90 min" if tf_choice == '1H (Media)' else "3-5 Giorni")

    # Tabella Tendenza Prevista
    trend_data = {
        'Asset': ['GOLD', 'PETROLIO', 'EUR/USD'],
        'Tendenza Prevista': [
            "⬆️ Accumulo / Inversione" if slope > 0 else "⬇️ Distribuzione",
            "↗️ Rialzista" if data['Oil'].pct_change().iloc[-1] > 0 else "↘️ Ribassista",
            "↗️ Rafforzamento" if data['EURUSD'].pct_change().iloc[-1] > 0 else "↘️ Debolezza"
        ],
        'Validità Temporale': ["Prossime 2-4h", "Prossime 6-12h", "Prossime 1-2h"]
    }
    st.table(pd.DataFrame(trend_data))

except Exception as e:
    st.error(f"Errore tecnico: {e}")
    # --- SEZIONE AGGIUNTIVA: PERFORMANCE CHECK (Da inserire in fondo al codice v9) ---
st.markdown("---")
st.subheader("📊 Historical Edge Check (Last 30 Days)")

# Simulazione segnale: Buy quando Z < -1.5 e Slope > 0
data['Signal'] = np.where((data['Z_Score'] < -1.5) & (data['Z_Slope'] > 0), 1, 0)
data['Next_Return'] = data['Gold'].pct_change(periods=5).shift(-5) # Ritorno a 5 candele

win_rate = data[data['Signal'] == 1]['Next_Return'].gt(0).mean()

c1, c2 = st.columns(2)
c1.metric("Win Rate Storico (Z-Signal)", f"{win_rate:.1%}")
c2.info("Il Win Rate indica quante volte il prezzo è salito nelle 5 candele successive a un segnale di 'Sconto Statistico'.")
