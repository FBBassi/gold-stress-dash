import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Gold Sovereign Monitor v6", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configurazione")
    tf_choice = st.radio("Timeframe:", ('1D (Alta)', '1H (Media)'), index=0)
    st.markdown("---")
    st.write("📈 **Dati:** Ritardo ~15min (Yahoo Finance)")
    st.write("📅 **Separatori:** Giornalieri (1H) / Mensili (1D)")

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
    
    # Calcoli Quant
    data['Fair_Value'] = (data['Oil'] / data['DXY']) * 100
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(20).mean()) / data['Divergence'].rolling(20).std()
    
    oil_rets = np.log(data['Oil']/data['Oil'].shift(1))
    try_rets = np.log(data['USD_TRY']/data['USD_TRY'].shift(1))
    raw_stress = (oil_rets + try_rets).rolling(10).mean()
    data['Stress_Index'] = (raw_stress - raw_stress.mean()) / raw_stress.std()
    data = data.dropna()

    # Header Status
    curr_z = data['Z_Score'].iloc[-1]
    status_msg = "🚨 EXTREME LIQUIDATION" if curr_z < -2 else "⚠️ OVERBOUGHT" if curr_z > 2 else "✅ REGIME NORMALE"
    st.info(f"{status_msg} | Z-Score: {curr_z:.2f}")

    # Dashboard
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        specs=[[{"secondary_y": True}], [{"secondary_y": True}]],
                        row_heights=[0.4, 0.6],
                        subplot_titles=("CONTESTO: Gold vs Stress", "OPERATIVO: Z-Score (Verde) vs Gold Price (Oro)"))

    # Grafico 1
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='#FFD700', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress_Index'], name="Stress", fill='tozeroy', line=dict(color='rgba(231, 76, 60, 0.3)')), row=1, col=1, secondary_y=True)

    # Grafico 2: Z-Score e Gold LINEA CONTINUA
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='#2ECC71', width=2.5)), row=2, col=1)
    # LINEA CONTINUA ORO (Price Ref)
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Price Ref", line=dict(color='#FFD700', width=3, dash='solid')), row=2, col=1, secondary_y=True)

    # Background Colors
    for i in range(1, len(data)):
        z = data['Z_Score'].iloc[i]
        if z < -2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="red", opacity=0.2, line_width=0, row=2, col=1)
        elif z > 2:
            fig.add_vrect(x0=data.index[i-1], x1=data.index[i], fillcolor="orange", opacity=0.15, line_width=0, row=2, col=1)

    # SEPARATORI VERTICALI DI PERIODO (Puntini neri sottili)
    # Su 1H mettiamo una linea ogni giorno alle 00:00
    if tf_choice == '1H (Media)':
        separators = data.index[data.index.hour == 0]
    else: # Su 1D mettiamo una linea ogni lunedì (inizio settimana)
        separators = data.index[data.index.dayofweek == 0]
    
    for x_val in separators:
        fig.add_vline(x=x_val, line_width=1, line_dash="dot", line_color="black", opacity=0.5)

    # SOGLIE ORIZZONTALI
    fig.add_hline(y=-2, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", row=2, col=1)

    # LAYOUT E FORMATO ORA SU DUE RIGHE
    fig.update_layout(height=850, template="plotly_white", margin=dict(l=20, r=20, t=50, b=20), showlegend=False)
    
    # Formato asse X: Giorno su riga 1, Ora su riga 2
    x_format = "%d %b<br>%H:%M" if tf_choice == '1H (Media)' else "%d %b"
    fig.update_xaxes(tickformat=x_format, row=2, col=1)

    st.plotly_chart(fig, use_container_width=True)

    # Tabella Dati Recenti
    st.markdown("### Dati Recenti")
    st.table(data[['Gold', 'Z_Score', 'USD_TRY']].tail(5).sort_index(ascending=False))

except Exception as e:
    st.error(f"Errore tecnico: {e}")
