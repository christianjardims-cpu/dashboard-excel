import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date
import pytz

# Configuração da página - Layout Wide e Tema Dark Nativo
st.set_page_config(page_title="Gestão de Manutenção Pro", layout="wide", initial_sidebar_state="expanded")

# Mapeamento de Cores Pro
COLOR_MAP = {
    "Realizada": "#30D158",                # Verde
    "Pendente": "#FF453A",                 # Vermelho
    "Necessita Reprogramação": "#FF9F0A"   # Amarelo/Laranja
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.12)",
    "Pendente": "rgba(255, 69, 58, 0.12)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.12)"
}

# Injeção de CSS - Design System Apple Dark Mode
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0F0F11; color: #FFFFFF; }
    
    /* Sidebar Estilizada */
    [data-testid="stSidebar"] {
        background-color: #161618;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1.5rem 1rem;
    }
    
    /* KPI Cards no Topo */
    .kpi-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        flex: 1;
        text-align: center;
        transition: transform 0.2s;
    }
    .kpi-card:hover { transform: translateY(-3px); background: rgba(255, 255, 255, 0.05); }
    .kpi-value { font-size: 2.2rem; font-weight: 700; color: #0A84FF; margin-bottom: 0.2rem; }
    .kpi-label { font-size: 0.9rem; color: #8E8E93; text-transform: uppercase; letter-spacing: 1px; }

    /* Estilo dos Cards de Ordem */
    .stContainer {
        background: rgba(255, 255, 255, 0.02) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        margin-bottom: 1rem;
    }

    /* Inputs e Selectbox */
    div[data-testid="stselectbox"] > div > div {
        background-color: #2C2C2E !important;
        border-radius: 10px !important;
    }

    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #0A84FF, #5E5CE6) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100%;
        transition: all 0.3s;
    }
</style>
""", unsafe_allow_html=True)

# --- PERSISTÊNCIA E LÓGICA ---
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        return pd.read_csv(ARQUIVO_SALVO)
    return None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

def atualizar_historico(df):
    tz = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz).strftime('%Y-%m-%d')
    df_f = df[df["Área"].str.strip().isin(AREAS_FOCO)]
    total = len(df_f)
    taxa = (len(df_f[df_f["Status_Execucao"] == "Realizada"]) / total * 100) if total > 0 else 0
    novo = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = pd.concat([hist[hist["Data"] != hoje], novo], ignore_index=True)
    else: hist = novo
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados()

# --- SIDEBAR ADMINISTRATIVA ---
with st.sidebar:
    st.markdown("### 🖥️ ADMINISTRAÇÃO")
    senha = st.text_input("Senha Master", type="password")
    
    if senha == "Programacao@2026":
        file = st.file_uploader("Atualizar Programação", type=["csv", "xlsx"])
        if file:
            with st.spinner("Sincronizando base..."):
                if file.name.endswith(".csv"): df_t = pd.read_csv(file, skiprows=1)
                else: df_t = pd.read_excel(file, skiprows=1)
                df_t.columns = df_t.columns.str.strip()
                df_t["Status_Execucao"] = "Pendente"
                df_t["Comentario"] = ""
                st.session_state.df = df_t
                salvar_dados(df_t)
                atualizar_historico(df_t)
                st.toast("Base atualizada com sucesso!", icon="✅")
    
    st.divider()
    st.markdown("### 🔍 FILTROS GLOBAIS")
    if st.session_state.df is not None:
        # Filtro de Área
        area_global = st.selectbox("Área de Atuação", ["Todas"] + AREAS_FOCO)
        
        # Filtro de Disciplina
        df_temp = st.session_state.df.copy()
        if "Centro de Trabalho Op." in df_temp.columns:
            df_temp["Disciplina"] = df_temp["Centro de Trabalho Op."].astype(str).apply(
                lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
            )
        disciplinas_disp = ["Todas"] + sorted(list(df_temp["Disciplina"].unique()))
        disc_global = st.selectbox("Disciplina", disciplinas_disp)
    
    st.markdown("<br><br><br><p style='color:#444; font-size:0.7rem;'>v2.4.0 High-Performance</p>", unsafe_allow_html=True)

# --- CABEÇALHO ---
tz = pytz.timezone("America/Sao_Paulo")
now = datetime.now(tz)
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown(f"<h1 style='margin-bottom:0;'>⚙️ Painel de Manutenção</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8E8E93;'>Filtro Ativo: <span style='color:#0A84FF;'>{area_global} | {disc_global}</span></p>", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div style='text-align:right; padding:10px; border-radius:12px; border:1px solid rgba(255,255,255,0.1); background:rgba(255,255,255,0.02);'>
            <small style='color:#8E8E93;'>BRASÍLIA, BRASIL</small><br>
            <strong style='font-size:1.1rem;'>{now.strftime('%d/%m/%Y')}</strong><br>
            <span style='color:#0A84FF; font-weight:700;'>{now.strftime('%H:%M:%S')}</span>
        </div>
    """, unsafe_allow_html=True)

# --- PROCESSAMENTO ---
df = st.session_state.df
if df is not None:
    # Preparação de colunas e filtros
    if "Disciplina" not in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica"))
    
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Área"] = df["Área"].astype(str).str.strip()
    
    # Aplicar Filtros Globais
    df_filtrado = df[df["Área"].isin(AREAS_FOCO)]
    if area_global != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Área"] == area_global]
    if disc_global != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_global]

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Geral", "🛠️ Apontamento Diário", "💬 Impedimentos"])

    with tab1:
        # --- KPI SECTION ---
        total_o = len(df_filtrado)
        realizadas_o = len(df_filtrado[df_filtrado["Status_Execucao"] == "Realizada"])
        aderencia = (realizadas_o / total_o * 100) if total_o > 0 else 0
        atrasadas = len(df_filtrado[(df_filtrado["Status_Execucao"] == "Pendente") & (df_filtrado["Data_Inicio_Parsed"] < pd.to_datetime(date.today()))])
        
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-card"><div class="kpi-value">{total_o}</div><div class="kpi-label">Ordens Totais</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:#30D158">{aderencia:.1f}%</div><div class="kpi-label">Aderência</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:#FF453A">{atrasadas}</div><div class="kpi-label">Atrasos Críticos</div></div>
            </div>
        """, unsafe_allow_html=True)

        c_g1, c_g2 = st.columns(2)
        with c_g1:
            st.markdown("#### Distribuição de Status")
            fig = px.pie(df_filtrado, names="Status_Execucao", hole=0.6, color="Status_Execucao", color_discrete_map=COLOR_MAP)
            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        
        with c_g2:
            st.markdown("#### Evolução Semanal vs Meta")
            if os.path.exists(ARQUIVO_HISTORICO):
                h = pd.read_csv(ARQUIVO_HISTORICO)
                fig_h = go.Figure()
                fig_h.add_trace(go.Scatter(x=h["Data"], y=h["Taxa"], mode='lines+markers+text', name="Realizado", fill='tozeroy', line=dict(color='#0A84FF', width=4)))
                fig_h.add_shape(type="line", x0=h["Data"].iloc[0], y0=85, x1=h["Data"].iloc[-1], y1=85, line=dict(color="#FF453A", width=2, dash="dash"))
                fig_h.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=300)
                st.plotly_chart(fig_h, use_container_width=True)

    with tab2:
        st.markdown("#### Fila de Execução Semanal")
        busca = st.text_input("🔍 Busca rápida (Ordem ou Descrição)", placeholder="Ex: 4005621...")
        
        df_view = df_filtrado.copy()
        if busca:
            df_view = df_view[df_view["Ordem"].astype(str).str.contains(busca) | df_view["Descrição da Ordem"].str.contains(busca, case=False)]
        
        dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dias_pt = {"Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta", "Thursday": "Quinta", "Friday": "Sexta", "Saturday": "Sábado", "Sunday": "Domingo"}
        
        for dia in dias:
            df_dia = df_view[df_view["Data_Inicio_Parsed"].dt.day_name() == dia]
            if not df_dia.empty:
                with st.expander(f"📅 {dias_pt[dia]} ({len(df_dia)} ordens)"):
                    for idx, row in df_dia.iterrows():
                        # Sincronia absoluta: puxar direto do DF da sessão
                        row_curr = st.session_state.df.loc[idx]
                        status = row_curr["Status_Execucao"]
                        
                        # Semaforização de atraso
                        border = COLOR_MAP[status]
                        atraso_tag = ""
                        if row_curr["Data_Inicio_Parsed"] < pd.to_datetime(date.today()) and status == "Pendente":
                            border = "#FF453A"
                            atraso_tag = " <span style='color:#FF453A;'>🚨 EM ATRASO</span>"
                        
                        st.markdown(f"""
                            <div style="background:{HEX_BG_MAP[status]}; border-left:6px solid {border}; padding:15px; border-radius:12px; margin-bottom:10px;">
                                <small style='color:#8E8E93;'>{row_curr['Ordem']} | {row_curr['Executante']}</small>{atraso_tag}<br>
                                <strong>{row_curr['Descrição da Ordem']}</strong><br>
                                <small>Operação: {row_curr['Texto Breve da Operação']}</small>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        opts = ["Pendente", "Realizada", "Necessita Reprogramação"]
                        sel = st.radio(f"Status {idx}", opts, index=opts.index(status), horizontal=True, key=f"r_{idx}", label_visibility="collapsed")
                        
                        if sel != status:
                            st.session_state.df.loc[idx, "Status_Execucao"] = sel
                            salvar_dados(st.session_state.df)
                            atualizar_historico(st.session_state.df)
                            st.rerun()

    with tab3:
        st.markdown("#### Registro de Impedimentos e Notas")
        df_imp = df_filtrado[df_filtrado["Status_Execucao"] != "Realizada"]
        if not df_imp.empty:
            for idx, row in df_imp.iterrows():
                row_curr = st.session_state.df.loc[idx]
                with st.container():
                    c_i1, c_i2 = st.columns([1, 2])
                    c_i1.markdown(f"**Ordem {row_curr['Ordem']}**<br><small>{row_curr['Status_Execucao']}</small>", unsafe_allow_html=True)
                    obs = c_i2.text_input("Observação / Justificativa", value=row_curr["Comentario"], key=f"obs_{idx}")
                    if obs != row_curr["Comentario"]:
                        st.session_state.df.loc[idx, "Comentario"] = obs
                        salvar_dados(st.session_state.df)
        else:
            st.success("Nenhuma pendência ou reprogramação registrada!")

else:
    st.info("Painel aguardando carga de dados. Utilize a barra lateral para fazer o upload da programação.")