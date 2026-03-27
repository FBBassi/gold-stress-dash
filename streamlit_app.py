import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configurazione Pagina Mobile-Friendly
st.set_page_config(page_title="Gold Liquidity Stress", layout="wide")

st.title("🛡️ Gold vs Central Bank Stress")
st.write("Analisi dell'inefficienza: Oro vs Stress Energetico/Valutario")

@st.cache_data(ttl=3600)
def get_data():
    assets = {'Gold': 'GC=F', 'Oil': 'BZ=F', 'USD_TRY': 'USDTRY=X', 'DXY': 'DX-Y.NYB'}
    df = yf.download(list(assets.values()), period="1y", interval="1d")['Close']
    df.columns = assets.keys()
    return df.dropna()

try:
    data = get_data()

    # Logica Quant: Stress Index e Z-Score
    data['Stress_Index'] = (data['Oil'].pct_change() + data['USD_TRY'].pct_change()).rolling(10).mean()
    data['Fair_Value'] = (data['Oil'] / data['DXY']) * 100
    data['Divergence'] = data['Gold'] - data['Fair_Value']
    
    # Formula Z-Score: $$Z = \frac{x - \mu}{\sigma}$$
    window = 20
    data['Z_Score'] = (data['Divergence'] - data['Divergence'].rolling(window).mean()) / data['Divergence'].rolling(window).std()

    # Dashboard Dinamica
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Prezzo Oro vs Stress (CBRT)", "Z-Score: Anomalia di Prezzo"))

    # Grafico 1
    fig.add_trace(go.Scatter(x=data.index, y=data['Gold'], name="Gold", line=dict(color='gold')), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data['Stress_Index'], name="Stress", fill='tozeroy', line=dict(color='rgba(255,0,0,0.2)')), row=1, col=1)

    # Grafico 2: Segnali Operativi
    fig.add_trace(go.Scatter(x=data.index, y=data['Z_Score'], name="Z-Score", line=dict(color='cyan')), row=2, col=1)
    fig.add_hline(y=-2, line_dash="dash", line_color="green", annotation_text="Buy Zone (CB Over-selling)", row=2, col=1)
    fig.add_hline(y=2, line_dash="dash", line_color="red", annotation_text="Sell Zone", row=2, col=1)

    fig.update_layout(template="plotly_dark", height=600, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Tabella degli ultimi segnali
    st.subheader("Ultimi Dati Real-Time")
    st.dataframe(data[['Gold', 'Z_Score', 'USD_TRY']].tail(5).sort_index(ascending=False))

except Exception as e:
    st.error(f"Errore nel recupero dati: {e}")
