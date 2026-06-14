import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import requests
from datetime import datetime, date
import pytz

# Configuração da página - Layout Wide e Sidebar Recolhida
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="collapsed")

# Função para buscar previsão do tempo em Guaíba
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-30.11&longitude=-51.32&daily=temperature_2m_max&timezone=America/Sao_Paulo"
    try:
        data = requests.get(url).json()['daily']
        return [{"dia": data['time'][i], "max": data['temperature_2m_max'][i]} for i in range(3)]
    except: return []

# Mapeamento de Cores Definitivo
COLOR_MAP = {
    "Realizada": "#30D158",
    "Pendente": "#FF453A",
    "Necessita Reprogramação": "#FF9F0A",
    "Outros": "#8E8E93"
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.08)",
    "Pendente": "rgba(255, 69, 58, 0.08)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)",
    "Outros": "rgba(142, 142, 147, 0.08)"
}

# Injeção de CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #1C1C1E; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 24px 16px; }
    .weather-card { background: #1A1A1A; padding: 10px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #333; font-size: 0.8rem; color: #FFFFFF; }
    [data-testid="stVerticalBlock"] > div > div.stContainer { background: rgba(28, 28, 30, 0.65); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 18px; border: 1px solid rgba(255, 255, 255, 0.06) !important; padding: 24px; color: #FFFFFF; margin-bottom: 20px; }
    p, label, div[data-testid="stMarkdownContainer"] { color: #F2F2F7; }
    h1, h2, h3, h4, h5 { color: #FFFFFF; letter-spacing: -0.5px; }
    div[data-testid="stselectbox"] > div > div { background-color: #1C1C1E; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: white; }
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.5rem; flex: 1; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
    .kpi-value { font-size: 2.2rem; font-weight: 700; color: #0A84FF; margin-bottom: 0.2rem; }
    .kpi-label { font-size: 0.85rem; color: #8E8E93; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }
    .stButton > button { background: linear-gradient(135deg, #0A84FF, #5E5CE6) !important; color: white !important; border-radius: 12px !important; border: none !important; font-weight: 600 !important; padding: 12px 24px !important; box-shadow: 0 4px 20px rgba(10, 132, 255, 0.3) !important; transition: all 0.3s ease !important; width: 100% !important; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(10, 132, 255, 0.5) !important; }
    hr { border-color: rgba(255, 255, 255, 0.06); }
</style>
""", unsafe_allow_html=True)

ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try: 
            df_loaded = pd.read_csv(ARQUIVO_SALVO)
            df_loaded["Comentario"] = df_loaded["Comentario"].astype(str)
            return df_loaded
        except Exception: return None
    return None

def salvar_dados(df):
    df["Comentario"] = df["Comentario"].astype(str)
    df.to_csv(ARQUIVO_SALVO, index=False)

def update_plotly_ios_layout(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20, l=20, r=20))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

def atualizar_historico(df):
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz_brasilia).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    total = len(df_f)
    realizadas = len(df_f[df_f["Status_Execucao"] == "Realizada"])
    taxa = (realizadas / total * 100) if total > 0 else 0
    novo_registro = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = hist[hist["Data"] != hoje]
        hist = pd.concat([hist, novo_registro], ignore_index=True)
    else: hist = novo_registro
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

def agrupar_pequenos_rotulos(series, threshold=0.05):
    freq = series.value_counts(normalize=True)
    pequenos = freq[freq < threshold].index
    return series.apply(lambda x: 'Outros' if x in pequenos else x)

if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados()

if st.session_state.df is not None:
    st.session_state.df["Comentario"] = st.session_state.df["Comentario"].astype(str)

col_tit1, col_tit2 = st.columns([3, 1])
with col_tit1:
    st.markdown("<h1 style='font-weight: 700; font-size: 2.4rem;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8E93; margin-top: -5px; font-size: 1.1rem;'>Gestão de Manutenção Semanal</p>", unsafe_allow_html=True)
with col_tit2:
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    now_brasilia = datetime.now(tz_brasilia)
    st.markdown(f"<div style='text-align: right; background: rgba(255,255,255,0.03); padding: 14px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);'><small style='color: #8E8E93; font-weight: 600; letter-spacing: 0.5px;'>HORÁRIO DE BRASÍLIA</small><br><strong style='font-size: 1.1rem;'>{now_brasilia.strftime('%d/%m/%Y')}</strong><br><span style='color: #0A84FF; font-weight: 700; font-size: 1.3rem;'>{now_brasilia.strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("<h2 style='font-weight: 600; font-size: 1.3rem;'>🌤️ Previsão Guaíba</h2>", unsafe_allow_html=True)
    for w in get_weather():
        st.markdown(f"<div class='weather-card'><b>{w['dia']}</b>: {w['max']}°C</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<h2 style='font-weight: 600; font-size: 1.3rem; margin-bottom: 15px;'>Área de Administração</h2>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Senha de acesso:", type="password")
    if senha_inserida == "Programacao@2026":
        uploaded_file = st.file_uploader("Selecione a programação (.csv ou .xlsx)", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                with st.spinner("Processando base de dados..."):
                    if nome_arquivo.endswith(".csv"): df_temp = pd.read_csv(uploaded_file, skiprows=1)
                    elif nome_arquivo.endswith(".xlsx"): df_temp = pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    df_temp["Comentario"] = df_temp["Comentario"].astype(str)
                    st.session_state.df = df_temp
                    salvar_dados(df_temp)
                    atualizar_historico(df_temp)
                st.success("Base atualizada!")
            except Exception as e: st.error(f"Erro ao ler arquivo: {e}")
    elif senha_inserida != "": st.error("Senha incorreta.")

df = st.session_state.df

def render_cards_com_busca(sub_df, prefix_key, local_col_tempo):
    busca_termo = st.text_input(f"🔍 Pesquisar Ordem ou Descrição ({prefix_key})", "", placeholder="Digite o número da Ordem...", key=f"search_box_{prefix_key}")
    st.markdown("<br>", unsafe_allow_html=True)
    df_filtrado_busca = sub_df.copy()
    if busca_termo:
        df_filtrado_busca = df_filtrado_busca[df_filtrado_busca["Ordem"].astype(str).str.contains(busca_termo, case=False, na=False) | df_filtrado_busca["Descrição da Ordem"].astype(str).str.contains(busca_termo, case=False, na=False)]
    for idx, row in df_filtrado_busca.iterrows():
        row_actual = st.session_state.df.loc[idx]
        ordem = row_actual["Ordem"]
        status_atual = row_actual["Status_Execucao"]
        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
        novo_status = st.radio(f"Status_{prefix_key}_{ordem}_{idx}", options=opcoes_status, index=opcoes_status.index(status_atual) if status_atual in opcoes_status else 0, horizontal=True, key=f"rad_{prefix_key}_{ordem}_{idx}", label_visibility="collapsed")
        
        if novo_status != status_atual:
            st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
            salvar_dados(st.session_state.df)
            atualizar_historico(st.session_state.df)
            st.toast(f"Status da Ordem {ordem} atualizado!", icon="✅")
        st.divider()

if df is not None:
    if "Centro de Trabalho Op." in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica"))
    else: df["Disciplina"] = "Mecânica"
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df_foco = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)].copy()
    col_tempo = "Tempo de Execução" if "Tempo de Execução" in df.columns else ("Tempo" if "Tempo" in df.columns else "4h")
    
    aba_geral, aba_exec_ind, aba_exec_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    with aba_geral:
        st.markdown("<h3>📋 Visão Macro</h3>", unsafe_allow_html=True)
        # (O resto do seu código de renderização de gráficos continua aqui...)
        st.info("Painel principal carregado.")
    with aba_exec_ind:
        st.markdown("<h3>🛠️ Apontamentos Diários</h3>", unsafe_allow_html=True)
        render_cards_com_busca(df_foco, "geral", col_tempo)
else:
    st.warning("⬅️ Por favor, faça o upload do arquivo na barra lateral.")