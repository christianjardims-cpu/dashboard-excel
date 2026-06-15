import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date, timedelta
import pytz

# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM (GEMINI / IOS)
st.set_page_config(page_title="Gestão de Manutenção | CMPC", layout="wide", initial_sidebar_state="expanded")

COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A", "Outros": "#8E8E93"}
HEX_BG_MAP = {"Realizada": "rgba(48, 209, 88, 0.08)", "Pendente": "rgba(255, 69, 58, 0.08)", "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)", "Outros": "rgba(142, 142, 147, 0.08)"}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    [data-testid="stSidebar"] { background-color: #1E1E24 !important; border-right: 1px solid rgba(255, 255, 255, 0.04) !important; padding: 24px 14px; }
    
    /* CORREÇÃO DE ÍCONES DO STREAMLIT */
    [data-testid="stSidebarCollapseButton"] button { font-size: 0px !important; color: transparent !important; }
    .stFileUploader button span, .stDetails summary span { font-size: 0px !important; color: transparent !important; display: none !important; }
    [data-testid="stSidebarCollapseButton"] { background-color: transparent !important; }
    [data-testid="stSidebarCollapseButton"] button { background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 50% !important; color: #FFFFFF !important; width: 32px; height: 32px; }
    
    /* WIDGET RELÓGIO ESTILO IOS */
    .ios-clock-widget { background: linear-gradient(145deg, #1E1E24, #141419); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 14px 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); display: flex; flex-direction: column; gap: 8px; }
    .ios-clock-top { display: flex; justify-content: space-between; align-items: center; }
    .ios-time { font-size: 1.6rem; font-weight: 700; color: #0A84FF; font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; }
    .ios-clock-bottom { display: flex; justify-content: space-between; font-size: 0.8rem; color: #9AA0A6; }
    .ios-progress-container { background: rgba(255, 255, 255, 0.05); border-radius: 4px; height: 5px; width: 100%; overflow: hidden; }
    .ios-progress-bar { background: linear-gradient(90deg, #0A84FF, #30D158); height: 100%; }

    /* CARDS DE CARDÁPIO/ORDENS */
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; }
    .kpi-card { background: rgba(30, 30, 36, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; }
    .stButton > button { background: linear-gradient(135deg, #1A73E8, #4285F4) !important; color: white !important; border-radius: 14px !important; width: 100% !important; border: none !important; }
</style>
""", unsafe_allow_html=True)

# 2. VARIÁVEIS DE CONTROLE E FUNÇÕES BASE
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try:
            df_loaded = pd.read_csv(ARQUIVO_SALVO)
            df_loaded["Comentario"] = df_loaded["Comentario"].fillna("").astype(str)
            return df_loaded
        except: return None
    return None

def salvar_dados(df):
    df["Comentario"] = df["Comentario"].fillna("").astype(str)
    df.to_csv(ARQUIVO_SALVO, index=False)

def update_plotly_ios_layout(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20, l=20, r=20))
    fig.update_xaxes(showgrid=False, zeroline=False).update_yaxes(showgrid=False, zeroline=False)
    return fig

def atualizar_historico(df):
    tz = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    taxa = (len(df_f[df_f["Status_Execucao"] == "Realizada"]) / len(df_f) * 100) if len(df_f) > 0 else 0
    novo = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.concat([pd.read_csv(ARQUIVO_HISTORICO), novo], ignore_index=True).drop_duplicates(subset=['Data'], keep='last')
    else: hist = novo
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

# 3. CONTROLE DE TEMPO DINÂMICO
tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)
numero_semana = now_br.isocalendar()[1]
pct_dia = min(100.0, max(0.0, ((now_br.hour * 60 + now_br.minute) / 1440.0) * 100))

if "df" not in st.session_state: st.session_state.df = carregar_dados()
if "necessita_salvar" not in st.session_state: st.session_state.necessita_salvar = False

# 4. SIDEBAR OPERACIONAL CMPC
with st.sidebar:
    st.markdown("<h2 style='color:white; font-family:\"Google Sans\"; margin-bottom:20px;'>CMPC</h2>", unsafe_allow_html=True)
    senha = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed")
    
    if senha == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            try:
                df_temp = pd.read_csv(uploaded_file, skiprows=1) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
                df_temp.columns = df_temp.columns.str.strip()
                df_temp["Status_Execucao"] = "Pendente"
                df_temp["Comentario"] = ""
                st.session_state.df = df_temp
                salvar_dados(df_temp)
                st.success("Base atualizada!")
            except Exception as e: st.error(f"Erro: {e}")

# 5. CABEÇALHO COM O NOVO RELÓGIO SMART WIDGET iOS
col_t1, col_t2 = st.columns([2.8, 1.2])
with col_t1:
    st.markdown("<h1 style='margin-bottom:0;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9AA0A6;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_t2:
    st.markdown(f"""
        <div class="ios-clock-widget">
            <div class="ios-clock-top">
                <span class="ios-time">{now_br.strftime('%H:%M:%S')}</span>
                <span class="ios-date-badge">{now_br.strftime('%d %b %y')}</span>
            </div>
            <div class="ios-progress-container"><div class="ios-progress-bar" style="width: {pct_dia}%;"></div></div>
            <div class="ios-clock-bottom"><span>🗓️ Semana {numero_semana}</span><span>🕒 Horário Brasília</span></div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# 6. RENDERIZADOR DE ORDENS CORRIGIDO
def render_cards_com_busca(sub_df, prefix_key, local_col_tempo):
    busca = st.text_input(f"🔍 Filtrar Ordens ({prefix_key})", "", key=f"sb_{prefix_key}")
    df_f = sub_df.copy()
    if busca:
        df_f = df_f[df_f["Ordem"].astype(str).str.contains(busca, case=False) | df_f["Descrição da Ordem"].astype(str).str.contains(busca, case=False)]
    
    if df_f.empty:
        st.info("Nenhuma ordem encontrada.")
        return

    for idx, row in df_f.iterrows():
        r_act = st.session_state.df.loc[idx]
        status_atual = r_act["Status_Execucao"]
        coment_atual = "" if str(r_act.get("Comentario", "")) in ["nan", "None"] else str(r_act.get("Comentario", ""))
        
        st.markdown(f"""
        <div style="background: {HEX_BG_MAP.get(status_atual, '#1C1C1E')}; border-left: 6px solid {COLOR_MAP.get(status_atual, '#0A84FF')}; padding: 16px; border-radius: 12px; margin-bottom: 10px;">
            <strong>Ordem:</strong> <code>{r_act['Ordem']}</code> | <strong>Área:</strong> {r_act['Área']} | <strong>Tempo:</strong> {r_act.get(local_col_tempo, 'N/D')}<br>
            <em>{r_act['Descrição da Ordem']}</em> - {r_act['Texto Breve da Operação']}
        </div>
        """, unsafe_allow_html=True)
        
        opcoes = ["Pendente", "Realizada", "Necessita Reprogramação"]
        novo_status = st.radio(f"St_{prefix_key}_{idx}", opcoes, index=opcoes.index(status_atual) if status_atual in opcoes else 0, horizontal=True, key=f"rd_{prefix_key}_{idx}", label_visibility="collapsed")
        
        novo_coment = coment_atual
        if novo_status in ["Pendente", "Necessita Reprogramação"]:
            motivos = ["Selecione motivo...", "Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Outros"]
            m_sel = st.selectbox(f"Mot_{prefix_key}_{idx}", motivos, key=f"sel_{prefix_key}_{idx}", label_visibility="collapsed")
            if m_sel != "Selecione motivo...":
                detalhe = st.text_input(f"Det_{prefix_key}_{idx}", value=coment_atual.replace(f"{m_sel}: ", ""), key=f"tx_{prefix_key}_{idx}", placeholder="Detalhes...")
                novo_coment = f"{m_sel}: {detalhe}"
        elif novo_status == "Realizada": novo_coment = ""

        if novo_status != status_atual or novo_coment != coment_atual:
            st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
            st.session_state.df.loc[idx, "Comentario"] = str(novo_coment)
            st.session_state.necessita_salvar = True

# 7. EXECUÇÃO DA INTERFACE PRINCIPAL
if st.session_state.df is not None:
    df = st.session_state.df
    df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")) if "Centro de Trabalho Op." in df.columns else "Mecânica"
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Área"] = df["Área"].astype(str).str.strip()
    df_foco = df[df["Área"].isin(AREAS_FOCO)].copy()
    col_t = "Tempo de Execução" if "Tempo de Execução" in df.columns else ("Tempo" if "Tempo" in df.columns else None)
    if not col_t:
        df["T_Ficticio"] = "4h"
        col_t = "T_Ficticio"

    if st.session_state.necessita_salvar:
        if st.button("💾 SALVAR ALTERAÇÕES EM DISCO"):
            salvar_dados(st.session_state.df)
            atualizar_historico(st.session_state.df)
            st.session_state.necessita_salvar = False
            st.rerun()

    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "🛠️ Por Executante", "⚙️ Por Disciplina"])
    
    with aba1:
        tot, real = len(df_foco), len(df_foco[df_foco["Status_Execucao"] == "Realizada"])
        pct = (real / tot * 100) if tot > 0 else 0.0
        st.markdown(f'<div class="kpi-container"><div class="kpi-card"><div class="kpi-value">{tot}</div><div class="kpi-label">Ordens Foco</div></div><div class="kpi-card"><div class="kpi-value" style="color:#30D158">{pct:.1f}%</div><div class="kpi-label">Aderência</div></div></div>', unsafe_allow_html=True)
        
        if not df_foco.empty:
            g_df = df_foco["Status_Execucao"].value_counts().reset_index()
            g_df.columns = ["Status", "Qtd"]
            st.plotly_chart(update_plotly_ios_layout(px.pie(g_df, values="Qtd", names="Status", hole=0.55, color="Status", color_discrete_map=COLOR_MAP)), use_container_width=True)

    with aba2:
        execs = ["Selecione..."] + sorted([str(e) for e in df_foco["Executante"].dropna().unique()])
        e_sel = st.selectbox("Escolha o Executante:", execs)
        if e_sel != "Selecione...":
            render_cards_com_busca(df_foco[df_foco["Executante"] == e_sel], "exec", col_t)

    with aba3:
        d_sel = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["Disciplina"].unique())))
        if d_sel:
            render_cards_com_busca(df_foco[df_foco["Disciplina"] == d_sel], "disc", col_t)
else:
    st.warning("⬅️ Insira a credencial na aba lateral e faça o upload da planilha de programação.")