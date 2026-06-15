import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import pytz
import sqlite3
import requests
from datetime import datetime, date, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÕES INICIAIS E ESTILIZAÇÃO (UI/UX)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLOR_MAP = {
    "Realizada": "#30D158",
    "Pendente": "#FF453A",
    "Necessita Reprogramação": "#FF9F0A",
    "Outros": "#8E8E93"
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.06)",
    "Pendente": "rgba(255, 69, 58, 0.06)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.06)",
    "Outros": "rgba(142, 142, 147, 0.06)"
}

DISCIPLINA_CORES = {
    "Mecânica": "#0A84FF",
    "Elétrica": "#BF5AF2",
    "Instrumentação": "#30D158"
}

st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    /* Sidebar e Correção dos Ícones/Setas */
    [data-testid="stSidebar"] { background-color: #1E1E24 !important; border-right: 1px solid rgba(255, 255, 255, 0.04) !important; padding: 24px 14px; }
    [data-testid="stSidebarCollapseButton"] button { background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 50% !important; color: #FFFFFF !important; display: flex !important; align-items: center; justify-content: center; width: 32px; height: 32px; }
    [data-testid="stSidebarCollapseButton"] svg { width: 18px !important; height: 18px !important; fill: #FFFFFF !important; color: #FFFFFF !important; display: block !important; }
    
    /* Customização de Elementos Interativos */
    .stFileUploader button span, .stDetails summary span { font-size: 0px !important; color: transparent !important; display: none !important; }
    div[data-testid="stselectbox"] > div > div { background-color: #1E1E24; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: white; }
    
    /* Widgets e Cards Compactos */
    .weather-card-today { background: linear-gradient(135deg, rgba(34, 34, 42, 0.8), rgba(20, 20, 28, 0.95)); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3); }
    .weather-row { display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 8px 12px; margin-bottom: 6px; }
    .ios-clock-widget { background: linear-gradient(145deg, #1E1E24, #141419); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 14px 18px; display: flex; flex-direction: column; gap: 8px; }
    .ios-time { font-size: 1.6rem; font-weight: 700; color: #0A84FF; font-variant-numeric: tabular-nums; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    .ios-progress-container { background: rgba(255, 255, 255, 0.05); border-radius: 4px; height: 5px; width: 100%; overflow: hidden; }
    .ios-progress-bar { background: linear-gradient(90deg, #0A84FF, #30D158); height: 100%; }
    
    /* Estrutura de Atividades / Ordem de Serviço */
    .os-card { border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); transition: transform 0.2s ease; position: relative; }
    .os-card:hover { transform: translateY(-2px); }
    .badge-disciplina { font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 8px; text-transform: uppercase; margin-left: 8px; color: #FFF; }
    
    /* KPIs */
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(30, 30, 36, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; font-weight: 500; }
</style>""", unsafe_allow_html=True)

DB_NOME = "data_cmpc.db"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

# -----------------------------------------------------------------------------
# 2. CAMADA DE BANCO DE DADOS (SQLITE PARA CONCORRÊNCIA E PERFORMANCE)
# -----------------------------------------------------------------------------
def inicializar_banco():
    with sqlite3.connect(DB_NOME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS programacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ordem TEXT, area TEXT, descricao TEXT, operacao TEXT, 
                executante TEXT, data_inicio TEXT, tempo_execucao TEXT, 
                disciplina TEXT, status_execucao TEXT, comentario TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT UNIQUE, taxa REAL
            )
        """)
        conn.commit()

inicializar_banco()

def carregar_dados_db():
    with sqlite3.connect(DB_NOME) as conn:
        df = pd.read_sql_query("SELECT * FROM programacao", conn)
    if df.empty:
        return None
    return df

def salvar_ou_atualizar_registro_db(id_registro, novo_status, novo_comentario):
    with sqlite3.connect(DB_NOME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE programacao SET status_execucao = ?, comentario = ? WHERE id = ?",
            (novo_status, str(novo_comentario), id_registro)
        )
        conn.commit()

def atualizar_banco_completo(df_novo):
    with sqlite3.connect(DB_NOME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM programacao") # Limpa anterior para carga nova
        for _, row in df_novo.iterrows():
            cursor.execute("""
                INSERT INTO programacao (ordem, area, descricao, operacao, executante, data_inicio, tempo_execucao, disciplina, status_execucao, comentario)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get("Ordem", "")), str(row.get("Área", "")), str(row.get("Descrição da Ordem", "")),
                str(row.get("Texto Breve da Operação", "")), str(row.get("Executante", "")), str(row.get("Data de Início", "")),
                str(row.get("Tempo de Execução", "4h")), str(row.get("Disciplina", "Mecânica")),
                str(row.get("Status_Execucao", "Pendente")), str(row.get("Comentario", ""))
            ))
        conn.commit()

# -----------------------------------------------------------------------------
# 3. INTEGRAÇÃO COM API DE CLIMA REAL (OPEN-METEO)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800) # Atualiza a cada 30 minutos
def obter_previsao_real_guaiba():
    try:
        # Coordenadas aproximadas de Guaíba - RS
        url = "https://api.open-meteo.com/v1/forecast?latitude=-30.1139&longitude=-51.3250&daily=weathercode,temperature_2m_max,temperature_2m_min&current_weather=true&timezone=America/Sao_Paulo"
        res = requests.get(url, timeout=5).json()
        
        # Mapeamento básico simplificado de WeatherCode da WMO para strings/emojis
        wmo_codes = {0: "☀️ Limpo", 1: "⛅ Parcialmente Nublado", 2: "⛅ Parcialmente Nublado", 3: "☁️ Encoberto", 61: "🌧️ Chuva Leve", 63: "🌧️ Chuva", 71: "❄️ Neve", 95: "⚡ Tempestade"}
        
        current = res.get("current_weather", {})
        daily = res.get("daily", {})
        
        temp_atual = f"{int(current.get('temperature', 20))}°C"
        status_atual = wmo_codes.get(current.get("weathercode"), "⛅ Nublado")
        
        cronograma = []
        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        
        for i in range(min(5, len(daily.get("time", [])))):
            data_dt = datetime.strptime(daily["time"][i], "%Y-%m-%d")
            cronograma.append({
                "nome": dias_semana[data_dt.weekday()],
                "data_str": data_dt.strftime("%d/%m"),
                "status": wmo_codes.get(daily["weathercode"][i], "⛅ Oscilando"),
                "temp": f"{int(daily['temperature_2m_max'][i])}°C / {int(daily['temperature_2m_min'][i])}°C",
                "hoje": (i == 0)
            })
        return temp_atual, status_atual, cronograma
    except Exception:
        # Fallback caso a API falhe em campo
        return "22°C", "⛅ Parcialmente Nublado", [
            {"nome": "Segunda", "data_str": "15/06", "status": "☀️ Ensolarado", "temp": "24°C / 14°C", "hoje": True},
            {"nome": "Terça", "data_str": "16/06", "status": "⛅ Nublado", "temp": "23°C / 15°C", "hoje": False},
            {"nome": "Quarta", "data_str": "17/06", "status": "🌧️ Instável", "temp": "20°C / 13°C", "hoje": False},
            {"nome": "Quinta", "data_str": "18/06", "status": "🌧️ Chuva", "temp": "18°C / 11°C", "hoje": False},
            {"nome": "Sexta", "data_str": "19/06", "status": "☀️ Limpo", "temp": "17°C / 9°C", "hoje": False}
        ]

temp_real, status_real, dados_clima = obter_previsao_real_guaiba()

# -----------------------------------------------------------------------------
# 4. CONTROLE DE ESTADO INTERNO (SESSION STATE)
# -----------------------------------------------------------------------------
if "db_data" not in st.session_state or st.session_state.get("recriar_cache", False):
    st.session_state.db_data = carregar_dados_db()
    st.session_state.recriar_cache = False

tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)
hoje_dt = now_br.date()
numero_semana = now_br.isocalendar()[1]
pct_dia = min(100.0, max(0.0, ((now_br.hour * 60 + now_br.minute) / 1440.0) * 100))

# -----------------------------------------------------------------------------
# 5. SIDEBAR DESIGN E CARGA DE DADOS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div style='display: flex; align-items: center; gap: 12px; margin-bottom: 25px; margin-top: 5px;'><div style='background: linear-gradient(135deg, #30D158, #1A73E8); width: 14px; height: 26px; border-radius: 4px;'></div><span style='font-family: \"Google Sans\"; font-size: 1.6rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;'>CMPC</span></div>", unsafe_allow_html=True)
    
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:6px;'>ADMINISTRAÇÃO BASE</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed")
    
    if senha_inserida == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arq = uploaded_file.name.lower()
            try:
                with st.spinner("Processando e otimizando base no SQLite..."):
                    df_temp = pd.read_csv(uploaded_file, skiprows=1) if nome_arq.endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    
                    # Criação da coluna Inteligente de Disciplina por Engenharia Reversa do Centro de Trabalho
                    if "Centro de Trabalho Op." in df_temp.columns:
                        df_temp["Disciplina"] = df_temp["Centro de Trabalho Op."].astype(str).apply(
                            lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
                        )
                    else:
                        df_temp["Disciplina"] = "Mecânica"
                        
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    
                    atualizar_banco_completo(df_temp)
                    st.session_state.recriar_cache = True
                st.success("Banco de Dados Atualizado!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro no processamento: {e}")
                
    st.markdown("<hr style='margin: 18px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:8px;'>CONDIÇÃO METEOROLÓGICA REAL</p><p style='font-size:1.15rem; font-weight:500; color:#FFFFFF; margin-top:-5px; margin-bottom:12px;'>Guaíba - RS</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class='weather-card-today'>
            <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                <div>
                    <h3 style='margin:0; font-size:1.8rem; font-weight:500; color:#FFF;'>{temp_real}</h3>
                    <p style='margin:2px 0 0 0; font-size:0.85rem; color:#C4C7C5;'>{status_real}</p>
                </div>
                <span style='font-size:1.8rem;'>{status_real.split(' ')[0]}</span>
            </div>
            <div style='margin-top:14px; font-size:0.72rem; color:#FF9F0A; font-weight:500;'>
                ⚠️ Atenção a trabalhos externos na Caldeira se houver chuva.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("Previsão Semanal Expandida", expanded=False):
        for d in dados_clima:
            st.markdown(f"<div class='weather-row'><span style='font-size:0.8rem; color:#FFF;'>{d['nome']} <small style='color:#80868B;'>({d['data_str']})</small></span><span style='font-size:0.8rem; color:#9AA0A6;'>{d['temp']} {d['status'].split(' ')[0]}</span></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. HEADER E CARD DE HORÁRIO ESTILO IOS
# -----------------------------------------------------------------------------
col_tit1, col_tit2 = st.columns([2.8, 1.2])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_tit2:
    st.markdown(f"<div class='ios-clock-widget'><div class='ios-clock-top'><span class='ios-time'>{now_br.strftime('%H:%M')}</span><span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span></div><div class='ios-progress-container'><div class='ios-progress-bar' style='width: {pct_dia}%;'></div></div><div class='ios-clock-bottom' style='display:flex; justify-content:space-between; font-size:0.75rem; color:#8E8E93;'><span>🗓️ Semana {numero_semana}</span><span>🕒 Horário de Turno</span></div></div>", unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. FUNÇÃO DE RENDERIZAÇÃO INTELIGENTE DE CARDS (UI COMPACTA + AUTO-SAVE)
# -----------------------------------------------------------------------------
def render_cards_operacionais(sub_df, unique_prefix):
    # Campo de busca integrado por aba
    busca = st.text_input("🔍 Filtrar Ordens Ativas", "", placeholder="Digite número da ordem, tag ou palavras-chave...", key=f"src_{unique_prefix}")
    
    if busca:
        sub_df = sub_df[sub_df["ordem"].astype(str).str.contains(busca, case=False) | sub_df["descricao"].astype(str).str.contains(busca, case=False)]
        
    if sub_df.empty:
        st.info("Nenhuma ordem aberta identificada para a seleção atual.")
        return

    # Seletor de modo de exibição (Melhoria de Visualização Compacta)
    modo_exibicao = st.segmented_control("Visualização:", options=["Cards Detalhados", "Lista de Produção"], default="Cards Detalhados", key=f"view_{unique_prefix}")
    st.markdown("<br>", unsafe_allow_html=True)

    for _, row in sub_df.iterrows():
        id_reg, ordem, desc, operacao, status_atual, cor_disc = row["id"], row["ordem"], row["descricao"], row["operacao"], row["status_execucao"], DISCIPLINA_CORES.get(row["disciplina"], "#8E8E93")
        comentario_atual = "" if str(row["comentario"]) in ["nan", "None", ""] else str(row["comentario"])
        
        bg_card = HEX_BG_MAP.get(status_atual, "rgba(255,255,255,0.02)")
        border_left_color = COLOR_MAP.get(status_atual, "#8E8E93")
        
        if modo_exibicao == "Cards Detalhados":
            st.markdown(f"""
                <div class='os-card' style='background: {bg_card}; border-left: 5px solid {border_left_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span><strong>OS:</strong> <code>{ordem}</code> <span class='badge-disciplina' style='background:{cor_disc};'>{row['disciplina']}</span></span>
                        <span style='font-size:0.85rem; color:#9AA0A6;'>⏱️ {row['tempo_execucao']}</span>
                    </div>
                    <p style='margin:8px 0 4px 0; font-size:0.95rem;'>{desc}</p>
                    <small style='color:#8E8E93;'>🛠️ Operação: {operacao} | 👤 Executante: {row['executante']}</small>
                </div>
            """, unsafe_allow_html=True)
        else:
            # Lista de Produção (Super Compacta para desktops industriais)
            st.markdown(f"📌 <b>{ordem}</b> - <span style='color:{cor_disc}; font-weight:600;'>{row['disciplina']}</span> | {desc[:70]}...", unsafe_allow_html=True)

        # Componentes nativos de entrada
        opcoes = ["Pendente", "Realizada", "Necessita Reprogramação"]
        idx_status = opcoes.index(status_atual) if status_atual in opcoes else 0
        
        col_rad, col_input = st.columns([1.5, 2.5])
        with col_rad:
            # Segmented control nativo do streamlit substitui os botões de rádio desajeitados
            novo_status = st.segmented_control(
                "Status", options=opcoes, default=status_atual,
                key=f"st_{unique_prefix}_{id_reg}", label_visibility="collapsed"
            )
            if not novo_status: novo_status = status_atual
            
        with col_input:
            novo_comentario = comentario_atual
            if novo_status in ["Pendente", "Necessita Reprogramação"]:
                motivos = ["Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Condição climática não favorável", "Outros"]
                idx_motivo = next((m_idx for m_idx, m_val in enumerate(motivos) if comentario_atual.startswith(m_val)), None)
                
                col_sel, col_det = st.columns([1.5, 2.5])
                with col_sel:
                    motivo_sel = st.selectbox("Justificativa", ["Selecione motivo..."] + motivos, index=idx_motivo+1 if idx_motivo is not None else 0, key=f"mot_{unique_prefix}_{id_reg}", label_visibility="collapsed")
                with col_det:
                    default_det = comentario_atual.replace(f"{motivo_sel}: ", "") if idx_motivo is not None and comentario_atual.startswith(str(motivo_sel)) else comentario_atual
                    detalhe = st.text_input("Detalhes", value=default_det, placeholder="Detalhes adicionais...", key=f"det_{unique_prefix}_{id_reg}", label_visibility="collapsed")
                    if motivo_sel != "Selecione motivo...":
                        novo_comentario = f"{motivo_sel}: {detalhe}" if detalhe else motivo_sel
            else:
                if comentario_atual:
                    st.markdown(f"<p style='margin-top:5px; font-size:0.8rem; color:#30D158;'>✓ Histórico limpo para conclusão.</p>", unsafe_allow_html=True)
                novo_comentario = ""

        # SALVAMENTO AUTOMÁTICO INDIVIDUAL (Fim do botão global de salvar e fim dos resets da tela)
        if novo_status != status_atual or novo_comentario != comentario_atual:
            salvar_ou_atualizar_registro_db(id_reg, novo_status, novo_comentario)
            st.toast(f"Alteração da OS {ordem} salva automaticamente!", icon="💾")
            st.session_state.recriar_cache = True

# -----------------------------------------------------------------------------
# 8. ABAS DE VISUALIZAÇÃO E ANÁLISE DE DADOS
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None:
    df_geral = st.session_state.db_data
    df_foco = df_geral[df_geral["area"].str.strip().isin(AREAS_FOCO)].copy()
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        # Cálculos de KPIs confiáveis baseados no banco real
        total_os = len(df_foco)
        realizadas = len(df_foco[df_foco["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Totais (Foco)</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência de Execução</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#FF9F0A'>{total_os - realizadas}</div><div class='kpi-label'>Pendentes / Abertas</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Distribuição de Status (Áreas de Foco)</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                st_counts = df_foco["status_execucao"].value_counts().reset_index()
                fig1 = px.pie(st_counts, values="count", names="status_execucao", hole=0.6, color="status_execucao", color_discrete_map=COLOR_MAP)
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig1, use_container_width=True)
        with col_g2:
            st.markdown("<h4>Distribuição por Disciplina de Trabalho</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                disc_counts = df_foco["disciplina"].value_counts().reset_index()
                fig2 = px.pie(disc_counts, values="count", names="disciplina", hole=0.6, color="disciplina", color_discrete_map=DISCIPLINA_CORES)
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.markdown("<h3>📋 Download Relatório Consolidado</h3>", unsafe_allow_html=True)
        st.download_button(label="📥 Exportar Base para CSV de Auditoria", data=df_foco.to_csv(index=False), file_name="cmpc_relatorio_apontamentos.csv", mime="text/csv")
        
    with aba_exec:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        lista_executantes = ["Selecione executante..."] + sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Escolha o Executante da Área:", lista_executantes, key="combo_exec")
        
        if exec_sel != "Selecione executante...":
            df_exec = df_foco[df_foco["executante"] == exec_sel].copy()
            st.divider()
            render_cards_operacionais(df_exec, f"exec_{exec_sel}")
            
    with aba_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina (Caldeira e Energia)</h2>", unsafe_allow_html=True)
        disc_sel = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["disciplina"].dropna().unique())), key="combo_disc")
        
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            st.divider()
            render_cards_operacionais(df_disc, f"disc_{disc_sel}")
else:
    st.warning("⬅️ Utilize o painel lateral para carregar sua planilha de programação original no Banco de Dados.")