import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date
import pytz
import requests

# Configuração da página
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="expanded")

# Mapeamento de Cores e Configurações
COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A", "Outros": "#8E8E93"}
HEX_BG_MAP = {"Realizada": "rgba(48, 209, 88, 0.08)", "Pendente": "rgba(255, 69, 58, 0.08)", "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)", "Outros": "rgba(142, 142, 147, 0.08)"}
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

# --- CSS MODERNO ESTILO GEMINI ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #0E0E10; border-right: 1px solid #222; padding: 20px; }
    .sidebar-header { font-size: 0.85rem; font-weight: 600; color: #888; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px; }
    .nav-item { padding: 10px; border-radius: 8px; cursor: pointer; color: #E0E0E0; transition: 0.3s; }
    .nav-item:hover { background-color: #1A1A1A; }
    [data-testid="stVerticalBlock"] > div > div.stContainer { background: rgba(20, 20, 22, 0.8); backdrop-filter: blur(10px); border-radius: 16px; border: 1px solid #333; padding: 20px; }
    .stButton > button { background: #FFFFFF; color: #000; border-radius: 8px; font-weight: 600; border: none; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    return pd.read_csv(ARQUIVO_SALVO) if os.path.exists(ARQUIVO_SALVO) else None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

def get_weather():
    try:
        # Substitua pela sua API KEY
        url = "http://api.openweathermap.org/data/2.5/forecast?q=Guaiba,BR&appid=SUA_API_KEY_AQUI&units=metric&lang=pt_br"
        data = requests.get(url, timeout=5).json()
        return [{"Data": i['dt_txt'][:10], "Temp": f"{int(i['main']['temp'])}°C", "Desc": i['weather'][0]['description']} for i in data['list'][::8]]
    except: return None

# --- ESTADO DA SESSÃO ---
if "df" not in st.session_state: st.session_state.df = carregar_dados()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚙️ Gestão Manutenção")
    st.markdown("<div class='sidebar-header'>Administração</div>", unsafe_allow_html=True)
    senha = st.text_input("Senha:", type="password")
    if senha == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload Base", type=["csv", "xlsx"])
        if uploaded_file:
            df_temp = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            st.session_state.df = df_temp
            salvar_dados(df_temp)
    
    st.markdown("<div class='sidebar-header'>Previsão em Guaíba</div>", unsafe_allow_html=True)
    clima = get_weather()
    if clima:
        for c in clima[:4]: st.write(f"📅 {c['Data']}: **{c['Temp']}** - {c['Desc']}")
    else: st.caption("Previsão indisponível")

# --- MAIN ---
if st.session_state.df is not None:
    df = st.session_state.df
    st.title("Painel de Acompanhamento")
    
    # Aba Principal
    tab1, tab2 = st.tabs(["📊 Visão Geral", "🛠️ Apontamentos"])
    
    with tab1:
        st.metric("Total de Ordens", len(df))
        st.bar_chart(df['Status_Execucao'].value_counts())
        
    with tab2:
        busca = st.text_input("🔍 Buscar Ordem")
        df_display = df[df['Ordem'].astype(str).str.contains(busca, na=False)] if busca else df
        st.dataframe(df_display, use_container_width=True)
else:
    st.info("Aguardando carregamento de dados na barra lateral.")