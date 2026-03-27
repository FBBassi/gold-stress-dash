import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Scalping Predictor", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚡ Scalping Config")
    tf_choice = st.radio("Timeframe Primario:", ('1D (Alta)', '1H (Media)'), index=1)
    st.markdown("---")
    st.info("Utilizza il TF 1H per anticipare i movimenti sul grafico 5m di MT4.")

@st.cache_data(ttl=300) # Aggiornamento più rapido ogni 5 min
def get_market_data(tf, period):
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'EURUSD': 'EURUSD=X', 'USDTRY': 'USDTRY=X'}
    df = yf.download(list(assets.values()), period=period, interval=tf)['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_market_data(tf_map[tf_choice] if 'tf_map' in locals() else '1h', '1mo')
    
    # --- LOGICA QUANT ---
    data['Fair_Value'] = (data['Oil'] * data['EURUSD']) * 1.5
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    # Calcolo Z-Score: $$Z = \frac{x - \mu}{\sigma}$$
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    data['Z_Slope'] = data['Z_Score'].diff() # Pendenza per prevedere la tendenza
    data['Stress'] = (np.log(data['Oil']/data['Oil'].shift(1)) + np.log(data['USDTRY']/data['USDTRY'].shift(1))).rolling(10).mean()
    data = data.dropna()

    # --- SEZIONE 3: STRATEGIC EXECUTION MATRIX (NUOVA) ---
    st.header("🎯 Scalping Strategic Matrix (Probabilistic)")
    
    curr_z = data['Z_Score'].iloc[-1]
    slope = data['Z_Slope'].iloc[-1]
    
    # Calcolo Bias e Lead Time
    def calculate_bias(z, s):
        if z < -1.5 and s > 0: return "BULLISH REVERSAL", "🟩", "Alta (Swing Low formato)"
        if z > 1.5 and s < 0: return "BEARISH REVERSAL", "🟥", "Alta (Swing High formato)"
        if s > 0: return "CONTINUATION UP", "↗️", "Media"
        if s < 0: return "CONTINUATION DOWN", "↘️", "Media"
        return "NEUTRAL", "⚪", "Bassa"

    bias, icon, prob = calculate_bias(curr_z, slope)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Bias Operativo (5m)", f"{icon} {bias}")
    with col2:
        st.metric("Probabilità Swing", prob)
    with col3:
        # Lead time stimato: ~ 2-3 candele del TF selezionato
        lead = "30-90 min" if tf_choice == '1H (Media)' else "2-5 Giorni"
        st.metric("Lead Time stimato", lead)

    # Tabella Predittiva Asset
    st.subheader("Tendenza Prevista (Prossime Ore)")
    predictive_df = pd.DataFrame({
        'Asset': ['GOLD', 'PETROLIO', 'EUR/USD'],
        'Tendenza': [
            "⬆️ Accumulo" if slope > 0 and curr_z < 0 else "⬇️ Distribuzione",
            "⬆️ Rialzista" if data['Oil'].pct_change().iloc[-1] > 0 else "⬇️ Ribassista",
            "↗️ Rafforzamento" if data['EURUSD'].pct_change().iloc[-1] > 0 else "↘️ Debolezza"
        ],
        'Validità (H)': ["2-4h", "6-8h", "1-3h"]
    })
    st.table(predictive_df)

    # --- SEZIONE GRAFICA (Ripristinata e Corretta) ---
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.3, 0.7])

    # Grafico 2 (Operativo) - Fokus sulla richiesta
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=3)), row=2, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold Price", line=dict(color='#FFD700', width=3)), row=2, col=1, secondary_y=True)

    # Separatori e Bande
    if tf_choice == '1H (Media)':
        seps = data.index[data.index.hour == 0]
        for s in seps: fig.add_vline(x=s, line_width=1, line_dash="dot", line_color="black", opacity=0.3, row=2, col=1)

    # Sfondo zone stress
    for i in range(1, len(data)):
        if data['Z_Score'].iloc[i] < -2: fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.2, row=2, col=1)

    fig.update_layout(height=800, template="plotly_white", showlegend=False)
    fig.update_xaxes(tickformat="%d %b<br>%H:%M", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
