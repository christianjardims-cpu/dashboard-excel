import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import pytz
import sqlite3
import requests
import re
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
    
    /* Sidebar e Correção de Elementos */
    [data-testid="stSidebar"] { background-color: #1E1E24 !important; border-right: 1px solid rgba(255, 255, 255, 0.04) !important; padding: 15px 14px; }
    [data-testid="stSidebarCollapseButton"] button { background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 50% !important; color: #FFFFFF !important; display: flex !important; align-items: center; justify-content: center; width: 32px; height: 32px; }
    [data-testid="stSidebarCollapseButton"] svg { width: 18px !important; height: 18px !important; fill: #FFFFFF !important; color: #FFFFFF !important; display: block !important; }
    
    /* Customização de Elementos Interativos */
    .stFileUploader button span, .stDetails summary span { font-size: 0px !important; color: transparent !important; display: none !important; }
    div[data-testid="stselectbox"] > div > div { background-color: #1E1E24; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: white; }
    
    /* Widget Unificado iOS Horário + Clima (Lateral) */
    .ios-clock-widget { background: linear-gradient(145deg, #25252E, #141419); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); margin-bottom: 20px; }
    .ios-clock-top { display: flex; justify-content: space-between; align-items: center; }
    .ios-time { font-size: 1.8rem; font-weight: 700; color: #0A84FF; font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    .ios-weather-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; margin-top: 4px; }
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
    
    /* Assinatura Corporativa no Cabeçalho */
    .corporate-signature { text-align: right; font-family: 'Google Sans', sans-serif; }
    .corp-title { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; margin: 0; }
    .corp-author { font-size: 0.75rem; color: #9AA0A6; margin: 2px 0 0 0; font-weight: 400; line-height: 1.2; }
</style>""", unsafe_allow_html=True)

DB_NOME = "data_cmpc.db"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

# -----------------------------------------------------------------------------
# 2. CAMADA DE BANCO DE DADOS (SQLITE)
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
        conn.commit()

inicializar_banco()

def carregar_dados_db():
    with sqlite3.connect(DB_NOME) as conn:
        return pd.read_sql_query("SELECT * FROM programacao", conn)

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
        cursor.execute("DELETE FROM programacao")
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
@st.cache_data(ttl=1800)
def obter_previsao_real_guaiba():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-30.1139&longitude=-51.3250&daily=weathercode,temperature_2m_max,temperature_2m_min&current_weather=true&timezone=America/Sao_Paulo"
        res = requests.get(url, timeout=5).json()
        wmo_codes = {0: "☀️ Limpo", 1: "⛅ Parcial", 2: "⛅ Parcial", 3: "☁️ Encoberto", 61: "🌧️ Chuva", 63: "🌧️ Chuva", 71: "❄️ Neve", 95: "⚡ Tempestade"}
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
        return "22°C", "⛅ Parcial", [{"nome": "Segunda", "data_str": "15/06", "status": "☀️ Ensolarado", "temp": "24°C / 14°C", "hoje": True}]

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

# Auxiliar para extrair horas numéricas de strings (Ex: "4h" -> 4.0, "4" -> 4.0)
def extrair_horas(string_tempo):
    try:
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(string_tempo))
        return float(match.group()) if match else 4.0
    except Exception:
        return 4.0

# -----------------------------------------------------------------------------
# 5. SIDEBAR DESIGN (LOGO + CLIMA INTEGRADO + CARGA)
# -----------------------------------------------------------------------------
with st.sidebar:
    # Mapeamento robusto para encontrar a imagem carregada
    opcoes_extensao = ["logo_cmpc.png", "logo_cmpc.jpeg", "logo_cmpc.jpg", "logo_cmpc.svg.png", "Logo-cmpc.svg.png"]
    imagem_encontrada = None
    
    for opt in opcoes_extensao:
        caminho_teste = os.path.join(os.path.dirname(__file__), opt) if "__file__" in locals() else opt
        if os.path.exists(caminho_teste):
            imagem_encontrada = caminho_teste
            break
        elif os.path.exists(opt):
            imagem_encontrada = opt
            break

    if imagem_encontrada:
        st.image(imagem_encontrada, use_container_width=True)
    else:
        st.markdown("<div style='padding: 20px; background: linear-gradient(135deg, #30D158, #1A73E8); border-radius: 12px; text-align: center; font-weight: 700; font-size: 1.8rem; color: white; letter-spacing: -1px; margin-bottom: 10px;'>CMPC</div>", unsafe_allow_html=True)
        
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    # REQUISITO: Sistema de Clima + Horário fixado na Barra Lateral como antes
    st.markdown(f"""
        <div class='ios-clock-widget'>
            <div class='ios-clock-top'>
                <span class='ios-time'>{now_br.strftime('%H:%M')}</span>
                <span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span>
            </div>
            <div class='ios-progress-container'><div class='ios-progress-bar' style='width: {pct_dia}%;'></div></div>
            <div class='ios-weather-row'>
                <span style='color:#FFF; font-weight:500;'>📍 Guaíba - RS</span>
                <span style='color:#0A84FF; font-weight:600;'>{status_real.split(' ')[0]} {temp_real}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:6px;'>ADMINISTRAÇÃO BASE</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed")
    
    if senha_inserida == "Programacao@2026":
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"], key=f"uploader_{st.session_state.uploader_key}")
        
        if uploaded_file is not None:
            nome_arq = uploaded_file.name.lower()
            try:
                with st.spinner("Otimizando base no SQLite..."):
                    df_temp = pd.read_csv(uploaded_file, skiprows=1) if nome_arq.endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Centro de Trabalho Op." in df_temp.columns:
                        df_temp["Disciplina"] = df_temp["Centro de Trabalho Op."].astype(str).apply(
                            lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
                        )
                    else: df_temp["Disciplina"] = "Mecânica"
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    atualizar_banco_completo(df_temp)
                    st.session_state.db_data = carregar_dados_db()
                    st.session_state.recriar_cache = False
                st.success("Banco de Dados Atualizado!")
                st.session_state.uploader_key += 1
                st.rerun()
            except Exception as e: st.error(f"Erro no processamento: {e}")
                
    st.markdown("<hr style='margin: 18px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:8px;'>PROGRAMAÇÃO DO TURNO</p>", unsafe_allow_html=True)
    st.markdown(f"<small style='color:#9AA0A6;'>Unidade Guaíba • Monitoramento Ativo de Caldeira e Utilidades.</small>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. HEADER COM INFOS DA EMPRESA E CRÉDITOS NO CANTO DIREITO
# -----------------------------------------------------------------------------
col_tit1, col_signature = st.columns([3.4, 0.6])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_signature:
    st.markdown("""
        <div class='corporate-signature'>
            <p class='corp-title'>CMPC</p>
            <p class='corp-author'>Created by<br>Christian Jardim</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. FUNÇÃO DE RENDERIZAÇÃO INTELIGENTE DE CARDS (OMS + AUTO-SAVE)
# -----------------------------------------------------------------------------
def render_cards_operacionais(sub_df, unique_prefix):
    busca = st.text_input("🔍 Filtrar Ordens Ativas", "", placeholder="Digite número da ordem, tag ou escopo...", key=f"src_{unique_prefix}")
    if busca:
        sub_df = sub_df[sub_df["ordem"].astype(str).str.contains(busca, case=False) | sub_df["descricao"].astype(str).str.contains(busca, case=False)]
        
    if sub_df.empty:
        st.info("Nenhuma ordem identificada para os critérios atuais.")
        return

    modo_exibicao = st.segmented_control("Formato:", options=["Cards Detalhes", "Lista Compacta"], default="Cards Detalhes", key=f"view_{unique_prefix}")
    st.markdown("<br>", unsafe_allow_html=True)

    for _, row in sub_df.iterrows():
        id_reg, ordem, desc, operacao, status_atual, cor_disc = row["id"], row["ordem"], row["descricao"], row["operacao"], row["status_execucao"], DISCIPLINA_CORES.get(row["disciplina"], "#8E8E93")
        comentario_atual = "" if str(row["comentario"]) in ["nan", "None", ""] else str(row["comentario"])
        bg_card = HEX_BG_MAP.get(status_atual, "rgba(255,255,255,0.02)")
        border_left_color = COLOR_MAP.get(status_atual, "#8E8E93")
        
        if modo_exibicao == "Cards Detalhes":
            st.markdown(f"""
                <div class='os-card' style='background: {bg_card}; border-left: 5px solid {border_left_color};'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span><strong>OMS:</strong> <code>{ordem}</code> <span class='badge-disciplina' style='background:{cor_disc};'>{row['disciplina']}</span></span>
                        <span style='font-size:0.85rem; color:#9AA0A6;'>⏱️ Carga: {row['tempo_execucao']}</span>
                    </div>
                    <p style='margin:8px 0 4px 0; font-size:0.95rem; font-weight:500;'>{desc}</p>
                    <small style='color:#8E8E93;'>🛠️ Operação: {operacao} | 👤 Executante: {row['executante']}</small>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"📌 <b>OMS {ordem}</b> - <span style='color:{cor_disc}; font-weight:600;'>{row['disciplina']}</span> | {desc[:80]}...", unsafe_allow_html=True)

        opcoes = ["Pendente", "Realizada", "Necessita Reprogramação"]
        col_rad, col_input = st.columns([1.6, 2.4])
        with col_rad:
            novo_status = st.segmented_control("Status", options=opcoes, default=status_atual, key=f"st_{unique_prefix}_{id_reg}", label_visibility="collapsed")
            if not novo_status: novo_status = status_atual
            
        with col_input:
            novo_comentario = comentario_atual
            if novo_status in ["Pendente", "Necessita Reprogramação"]:
                motivos = ["Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Condição climática não favorável", "Outros"]
                col_sel, col_det = st.columns([1.5, 2.5])
                with col_sel:
                    motivo_sel = st.selectbox("Justificativa", ["Selecione motivo..."] + motivos, index=0, key=f"mot_{unique_prefix}_{id_reg}", label_visibility="collapsed")
                with col_det:
                    detalhe = st.text_input("Detalhes", placeholder="Adicione observações...", key=f"det_{unique_prefix}_{id_reg}", label_visibility="collapsed")
                    if motivo_sel != "Selecione motivo...": novo_comentario = f"{motivo_sel}: {detalhe}" if detalhe else motivo_sel
            else:
                if comentario_atual: st.markdown(f"<p style='margin-top:5px; font-size:0.8rem; color:#30D158;'>✓ Histórico de comentários concluído.</p>", unsafe_allow_html=True)
                novo_comentario = ""

        if novo_status != status_atual or novo_comentario != comentario_atual:
            salvar_ou_atualizar_registro_db(id_reg, novo_status, novo_comentario)
            st.toast(f"OMS {ordem} atualizada com sucesso!", icon="💾")
            st.session_state.recriar_cache = True

# -----------------------------------------------------------------------------
# 8. ABAS DE VISUALIZAÇÃO E ANÁLISE DE DADOS
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None:
    df_geral = st.session_state.db_data
    df_foco = df_geral[df_geral["area"].str.strip().isin(AREAS_FOCO)].copy()
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    # --- ABA 1: VISÃO MACRO ---
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        # Parse prévio das horas numéricas para os indicadores principais
        df_foco["horas_num"] = df_foco["tempo_execucao"].apply(extrair_horas)
        total_horas_foco = df_foco["horas_num"].sum()
        horas_realizadas_foco = df_foco[df_foco["status_execucao"] == "Realizada"]["horas_num"].sum()
        
        total_os = len(df_foco)
        realizadas = len(df_foco[df_foco["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Totais</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência de Atividades Concluídas</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#0A84FF'>{total_horas_foco:.1f}h</div><div class='kpi-label'>Volume Total Programado</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{horas_realizadas_foco:.1f}h</div><div class='kpi-label'>Volume Executado (Baixas)</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # REQUISITO: Escolher a disciplina que quero acompanhar e ver o progresso conforme as baixas
            st.markdown("<h4>Progresso Dinâmico por Disciplina</h4>", unsafe_allow_html=True)
            disciplinas_disponiveis = sorted(list(df_foco["disciplina"].dropna().unique()))
            disciplina_grafico = st.selectbox("Selecione a disciplina para monitorar o avanço:", disciplinas_disponiveis, key="sb_grafico_macro")
            
            df_filtrado_grafico = df_foco[df_foco["disciplina"] == disciplina_grafico]
            
            if not df_filtrado_grafico.empty:
                st_counts = df_filtrado_grafico["status_execucao"].value_counts().reset_index()
                fig1 = px.pie(st_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Sem dados para a disciplina selecionada.")
                
        with col_g2:
            # REQUISITO: Gráfico de carga horária em HORAS (Programadas vs Usadas atualmente conforme retorno)
            st.markdown("<h4>Balanço de Carga Horária Global (Horas)</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                horas_pendentes_foco = max(0.0, total_horas_foco - horas_realizadas_foco)
                
                df_balanco_horas = pd.DataFrame([
                    {"Métrica": "Horas Usadas (Concluídas)", "Horas": horas_realizadas_foco},
                    {"Métrica": "Horas Pendentes", "Horas": horas_pendentes_foco}
                ])
                
                fig2 = px.pie(
                    df_balanco_horas, 
                    values="Horas", 
                    names="Métrica", 
                    hole=0.55, 
                    color="Métrica", 
                    color_discrete_map={"Horas Usadas (Concluídas)": "#30D158", "Horas Pendentes": "rgba(255,255,255,0.15)"}
                )
                fig2.update_traces(texttemplate='%{value:.1f}h<br>(%{percent})', textinfo='value+percent')
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        st.markdown("<h4>Aderência à Programação (%) por Divisão de Disciplina</h4>", unsafe_allow_html=True)
        if not df_foco.empty:
            disc_performance = []
            for disc, d_sub in df_foco.groupby("disciplina"):
                total_d = len(d_sub)
                realizadas_d = len(d_sub[d_sub["status_execucao"] == "Realizada"])
                taxa_d = (realizadas_d / total_d * 100) if total_d > 0 else 0
                disc_performance.append({"Disciplina": disc, "Taxa Conclusão (%)": taxa_d})
            df_perf = pd.DataFrame(disc_performance)
            
            fig3 = px.bar(df_perf, x="Disciplina", y="Taxa Conclusão (%)", color="Disciplina", color_discrete_map=DISCIPLINA_CORES, text_auto='.1f%')
            fig3.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis_range=[0,100])
            st.plotly_chart(fig3, use_container_width=True)

    # --- ABA 2: APONTAMENTO POR EXECUTANTE ---
    with aba_exec:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        lista_executantes = ["Selecione executante..."] + sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Escolha o Executante da Área:", lista_executantes, key="combo_exec")
        
        if exec_sel != "Selecione executante...":
            df_exec = df_foco[df_foco["executante"] == exec_sel].copy()
            st.divider()
            
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                st.markdown(f"##### Aderência de Escopo: {exec_sel}")
                st_exec_counts = df_exec["status_execucao"].value_counts().reset_index()
                f_pie_exec = px.pie(st_exec_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                f_pie_exec.update_layout(template="plotly_dark", height=230, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(f_pie_exec, use_container_width=True)
                
            with col_pie2:
                st.markdown("##### Carga Horária de Trabalho (Horas)")
                df_exec["horas_num"] = df_exec["tempo_execucao"].apply(extrair_horas)
                total_horas_alocadas = df_exec["horas_num"].sum()
                horas_utilizadas = df_exec[df_exec["status_execucao"] == "Realizada"]["horas_num"].sum()
                horas_restantes = max(0.0, total_horas_alocadas - horas_utilizadas)
                
                df_horas_chart = pd.DataFrame([
                    {"Métrica": "Horas Usadas", "Horas": horas_utilizadas},
                    {"Métrica": "Horas Pendentes", "Horas": horas_restantes}
                ])
                f_pie_horas = px.pie(df_horas_chart, values="Horas", names="Métrica", hole=0.55, color="Métrica", color_discrete_map={"Horas Usadas": "#30D158", "Horas Pendentes": "rgba(255,255,255,0.1)"})
                f_pie_horas.update_traces(texttemplate='%{value:.1f}h', textinfo='value')
                f_pie_horas.update_layout(template="plotly_dark", height=230, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(f_pie_horas, use_container_width=True)
            
            st.divider()
            st.markdown(f"### 📅 Cronograma Semanal de Atividades")
            
            df_exec["data_parsed"] = pd.to_datetime(df_exec["data_inicio"], errors="coerce")
            df_exec["dia_nome"] = df_exec["data_parsed"].dt.day_name()
            
            dias_mapeamento = {
                "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
                "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
            }
            
            if df_exec["data_parsed"].isna().all():
                st.markdown("#### Lista de Atividades Atribuídas (Sem data estruturada)")
                render_cards_operacionais(df_exec, f"exec_list_{exec_sel}")
            else:
                for eng_day, pt_day in dias_mapeamento.items():
                    df_dia_especifico = df_exec[df_exec["dia_nome"] == eng_day].copy()
                    if not df_dia_especifico.empty:
                        with st.expander(f"➔ {pt_day} ({len(df_dia_especifico)} Atividades)", expanded=True):
                            render_cards_operacionais(df_dia_especifico, f"exec_card_{exec_sel}_{eng_day}")

    # --- ABA 3: APONTAMENTO POR DISCIPLINA ---
    with aba_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina (Caldeira e Energia)</h2>", unsafe_allow_html=True)
        disc_sel = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["disciplina"].dropna().unique())), key="combo_disc")
        
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            st.divider()
            render_cards_operacionais(df_disc, f"disc_{disc_sel}")
else:
    st.warning("⬅ extinction Por favor, utilize o painel lateral para carregar sua planilha de programação original.")