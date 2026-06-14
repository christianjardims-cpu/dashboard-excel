import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from datetime import datetime, date
import pytz

# Configuração da página
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="collapsed")

# --- FUNÇÃO AUXILIAR DE HORAS ---
def converter_para_horas(valor):
    if not isinstance(valor, str): return 0
    match = re.search(r'(\d+)', str(valor))
    return float(match.group(1)) if match else 0

# --- Mapeamento de Cores e CSS ---
COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A", "Outros": "#8E8E93"}
HEX_BG_MAP = {"Realizada": "rgba(48, 209, 88, 0.08)", "Pendente": "rgba(255, 69, 58, 0.08)", "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)", "Outros": "rgba(142, 142, 147, 0.08)"}

st.markdown("""
<style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #1C1C1E; }
    [data-testid="stVerticalBlock"] > div > div.stContainer { background: rgba(28, 28, 30, 0.65); border-radius: 18px; padding: 24px; margin-bottom: 20px; }
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; }
    .kpi-card { background: rgba(255, 255, 255, 0.03); border-radius: 16px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.2rem; font-weight: 700; color: #0A84FF; }
    .kpi-label { font-size: 0.85rem; color: #8E8E93; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# Persistência
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    return pd.read_csv(ARQUIVO_SALVO) if os.path.exists(ARQUIVO_SALVO) else None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

def update_plotly_ios_layout(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20, l=20, r=20))
    return fig

def atualizar_historico(df):
    tz = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    taxa = (len(df_f[df_f["Status_Execucao"] == "Realizada"]) / len(df_f) * 100) if len(df_f) > 0 else 0
    novo = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = pd.concat([hist[hist["Data"] != hoje], novo])
    else: hist = novo
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

def agrupar_pequenos_rotulos(series, threshold=0.05):
    freq = series.value_counts(normalize=True)
    return series.apply(lambda x: 'Outros' if freq.get(x, 0) < threshold else x)

if "df" not in st.session_state: st.session_state.df = carregar_dados()

# --- SIDEBAR E DADOS ---
with st.sidebar:
    senha = st.text_input("Senha:", type="password")
    if senha == "Programacao@2026":
        uploaded = st.file_uploader("Upload", type=["csv", "xlsx"])
        if uploaded:
            df_temp = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            st.session_state.df = df_temp
            salvar_dados(df_temp)
            st.rerun()

df = st.session_state.df
if df is not None:
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df_foco = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)].copy()
    col_tempo = "Tempo de Execução" if "Tempo de Execução" in df.columns else "Tempo"

    aba_geral, aba_exec_ind, aba_disc = st.tabs(["📊 Geral", "🛠️ Executante", "⚙️ Disciplina"])

    with aba_exec_ind:
        executantes = ["Selecione..."] + sorted(df_foco["Executante"].dropna().unique().tolist())
        exec_sel = st.selectbox("Escolha o Executante:", executantes)
        
        if exec_sel != "Selecione...":
            df_exec = df_foco[df_foco["Executante"] == exec_sel].copy()
            
            # --- O "PLUS" DE HORAS E PIZZA ---
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Aderência de Status")
                fig_p = px.pie(df_exec["Status_Execucao"].value_counts().reset_index(), names="Status_Execucao", values="count", color="Status_Execucao", color_discrete_map=COLOR_MAP)
                st.plotly_chart(update_plotly_ios_layout(fig_p), use_container_width=True)
            with col2:
                st.markdown("#### Horas (Realizado vs Meta)")
                df_exec["Horas_Num"] = df_exec[col_tempo].apply(converter_para_horas)
                meta, real = df_exec["Horas_Num"].sum(), df_exec[df_exec["Status_Execucao"]=="Realizada"]["Horas_Num"].sum()
                fig_h = go.Figure(go.Indicator(mode="gauge+number", value=real, gauge={'axis': {'range': [0, meta if meta>0 else 1]}, 'bar': {'color': "#30D158"}}))
                st.plotly_chart(update_plotly_ios_layout(fig_h), use_container_width=True)

            # --- LISTAGEM DE CARDS (Com Rerun) ---
            for idx, row in df_exec.iterrows():
                cols = st.columns([3, 1])
                cols[0].markdown(f"**{row['Ordem']}**: {row['Descrição da Ordem']}")
                novo = cols[1].radio("Status", ["Pendente", "Realizada", "Necessita Reprogramação"], index=["Pendente", "Realizada", "Necessita Reprogramação"].index(row["Status_Execucao"]), key=f"r_{idx}", label_visibility="collapsed")
                
                if novo != row["Status_Execucao"]:
                    st.session_state.df.loc[idx, "Status_Execucao"] = novo
                    salvar_dados(st.session_state.df)
                    atualizar_historico(st.session_state.df)
                    st.rerun() # ATUALIZAÇÃO INSTANTÂNEA
else:
    st.info("Faça o upload do arquivo na barra lateral.")