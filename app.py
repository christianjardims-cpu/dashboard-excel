import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import pytz
import sqlite3
import requests
import re
import time
from datetime import datetime, date, timedelta

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÕES INICIAIS E ARQUITETURA VISUAL SUPREMA (ESTILO GEMINI)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Força o reset completo de qualquer estado anterior mudando a assinatura da versão (v13)
if "versao_layout" not in st.session_state or st.session_state.versao_layout != "13.0_realtime_clock_fragment":
    st.session_state.clear()  
    st.session_state.versao_layout = "13.0_realtime_clock_fragment"

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

# CSS Framework customizado
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght=400;500;600;700&family=Inter:wght=300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #0A0A0C 0%, #111217 100%) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.03) !important; 
        padding: 24px 16px !important; 
    }
    
    /* CORREÇÃO DEFINITIVA PARA BARRAS RECOLHÍVEIS (ST.EXPANDER) */
    [data-testid="stExpander"] details summary {
        padding-right: 45px !important;
        display: flex !important;
        align-items: center !important;
    }
    [data-testid="stExpander"] details summary p {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.4 !important;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    /* CARD DE CLIMA ESTILO GEMINI */
    .gemini-weather-container {
        background: rgba(22, 23, 29, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 16px;
        backdrop-filter: blur(12px);
    }
    .gemini-weather-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 6px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .gemini-weather-row:last-child { border-bottom: none; }
    .gemini-day-text { color: #AAAEB6; font-size: 0.88rem; font-weight: 400; }
    .gemini-day-active { color: #1A73E8; font-weight: 600; font-size: 0.88rem; }
    .gemini-badge-today { font-size: 0.65rem; background: rgba(26, 115, 232, 0.15); color: #1A73E8; padding: 2px 8px; border-radius: 12px; font-weight: 600; margin-left: 6px; text-transform: uppercase; letter-spacing: 0.3px; }
    .gemini-temp-text { font-weight: 600; color: #FFFFFF; font-size: 0.9rem; font-variant-numeric: tabular-nums; }
    
    /* Widget de Horário Principal */
    .ios-clock-widget { background: linear-gradient(145deg, #18191E, #0F1013); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 18px; padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .ios-clock-top { display: flex; justify-content: space-between; align-items: center; }
    .ios-time { font-size: 1.8rem; font-weight: 700; color: #1A73E8; font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
    .ios-date-badge { background: rgba(26, 115, 232, 0.1); color: #1A73E8; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    
    .ios-progress-label { font-size: 0.68rem; color: #9AA0A6; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-top: 2px; }
    .ios-progress-container { background: rgba(255, 255, 255, 0.04); border-radius: 4px; height: 6px; width: 100%; overflow: hidden; margin-bottom: 2px; }
    .ios-progress-bar { background: linear-gradient(90deg, #1A73E8, #30D158); height: 100%; }
    .ios-weather-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.04); padding-top: 6px; margin-top: 4px; }
    
    .os-card { border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); transition: transform 0.2s ease; position: relative; }
    .badge-disciplina { font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 8px; text-transform: uppercase; margin-left: 8px; color: #FFF; }
    
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(22, 23, 29, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; font-weight: 500; }
    
    .corporate-signature { text-align: right; font-family: 'Google Sans', sans-serif; }
    .corp-title { font-size: 0.95rem; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; margin: 0; }
    .corp-author { font-size: 0.72rem; color: #9AA0A6; margin: 2px 0 0 0; font-weight: 400; }
</style>""", unsafe_allow_html=True)

DB_NOME = "data_cmpc.db"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

# -----------------------------------------------------------------------------
# 2. SISTEMA DE BANCO DE DADOS (SQLITE)
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

def salvar_ou_atualizar_registro_db(id_registro, novo_status, novo_comentario, ordem_nome=""):
    with sqlite3.connect(DB_NOME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE programacao SET status_execucao = ?, comentario = ? WHERE id = ?",
            (novo_status, str(novo_comentario), id_registro)
        )
        conn.commit()
    st.session_state.recriar_cache = True
    st.toast(f"OMS {ordem_nome} atualizada com sucesso!", icon="💾")

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
# 3. TELEMETRIA METEOROLÓGICA REAL-TIME (OPEN-METEO EM GUAÍBA)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def obter_dados_meteorologicos_puros_v13():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-30.1139&longitude=-51.3250&daily=weathercode,temperature_2m_max,temperature_2m_min&current_weather=true&timezone=America/Sao_Paulo"
        res = requests.get(url, timeout=5).json()
        wmo_codes = {0: "☀️ Limpo", 1: "⛅ Parcial", 2: "⛅ Parcial", 3: "☁️ Encoberto", 61: "🌧️ Chuva", 63: "🌧️ Chuva", 71: "❄️ Neve", 95: "⚡ Tempestade"}
        current = res.get("current_weather", {})
        daily = res.get("daily", {})
        temp_atual = f"{int(current.get('temperature', 14))}°C"
        status_atual = wmo_codes.get(current.get("weathercode"), "☁️ Encoberto")
        
        cronograma = []
        dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        for i in range(min(5, len(daily.get("time", [])))):
            data_dt = datetime.strptime(daily["time"][i], "%Y-%m-%d")
            cronograma.append({
                "nome": dias_semana[data_dt.weekday()],
                "status": wmo_codes.get(daily["weathercode"][i], "☁️ Encoberto"),
                "temp": f"{int(daily['temperature_2m_max'][i])}°C"
            })
        return temp_atual, status_atual, cronograma
    except Exception:
        cronograma_fallback = [
            {"nome": "Segunda", "status": "☁️ Encoberto", "temp": "14°C"},
            {"nome": "Terça", "status": "⛅ Parcial", "temp": "15°C"},
            {"nome": "Quarta", "status": "☁️ Encoberto", "temp": "16°C"},
            {"nome": "Quinta", "status": "☁️ Encoberto", "temp": "18°C"},
            {"nome": "Sexta", "status": "⛅ Parcial", "temp": "14°C"}
        ]
        return "14°C", "☁️ Encoberto", cronograma_fallback

temp_real, status_real, dados_clima = obter_dados_meteorologicos_puros_v13()

# -----------------------------------------------------------------------------
# 4. CONFIGURAÇÕES INTERNAS DE DATA E JORNADA
# -----------------------------------------------------------------------------
if "db_data" not in st.session_state or st.session_state.get("recriar_cache", False):
    st.session_state.db_data = carregar_dados_db()
    st.session_state.recriar_cache = False

tz_br = pytz.timezone("America/Sao_Paulo")
now_br_inicial = datetime.now(tz_br)
hoje_nome_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now_br_inicial.weekday()]

dias_mapeamento = {
    "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
}

def extrair_horas(string_tempo):
    try:
        match = re.search(r"[-+]?\d*\.\d+|\d+", str(string_tempo))
        return float(match.group()) if match else 4.0
    except Exception:
        return 4.0

# -----------------------------------------------------------------------------
# 5. SIDEBAR: MONITORAMENTO DE CLIMA
# -----------------------------------------------------------------------------
with st.sidebar:
    opcoes_extensao = ["logo_cmpc.png", "logo_cmpc.jpeg", "logo_cmpc.jpg", "logo_cmpc.svg.png", "Logo-cmpc.svg.png"]
    imagem_encontrada = None
    for opt in opcoes_extensao:
        caminho_teste = os.path.join(os.path.dirname(__file__), opt) if "__file__" in locals() else opt
        if os.path.exists(caminho_teste):
            imagem_encontrada = caminho_teste
            break

    if imagem_encontrada:
        st.image(imagem_encontrada, use_container_width=True)
    else:
        st.subheader("🏭 CMPC Guaíba")
        
    st.write("---")
    st.markdown("<p style='font-size:0.7rem; color:#8E8E93; font-weight:600; letter-spacing:0.8px; text-transform:uppercase; margin-bottom:12px;'>Clima em tempo real • Guaíba</p>", unsafe_allow_html=True)
    
    st.markdown("<div class='gemini-weather-container'>", unsafe_allow_html=True)
    for info in dados_clima:
        is_hoje = info["nome"] == hoje_nome_pt
        label_dia = f"<span class='gemini-day-active'>{info['nome']}</span><span class='gemini-badge-today'>Hoje</span>" if is_hoje else f"<span class='gemini-day-text'>{info['nome']}</span>"
        icon = info["status"].split(" ")[0]
        
        st.markdown(f"""
            <div class='gemini-weather-row'>
                <div style='display:flex; align-items:center;'>{label_dia}</div>
                <div style='display:flex; align-items:center; gap:12px;'>
                    <span style='font-size:1.05rem;'>{icon}</span>
                    <span class='gemini-temp-text'>{info['temp']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
                
    st.write("")

    st.caption("🔒 CONFIGURAÇÃO INTERNA")
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed", key="v13_stable_pass_key")
    
    if senha_inserida == "Programacao@2026":
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 11000
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"], key=f"uploader_v13_{st.session_state.uploader_key}")
        
        if uploaded_file is not None:
            nome_arq = uploaded_file.name.lower()
            try:
                with st.spinner("Processando..."):
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
                st.success("Banco Atualizado!")
                st.session_state.uploader_key += 1
                st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
                
    st.write("---")
    st.caption("📊 Unidade Guaíba • Monitoramento Ativo de Caldeira e Utilidades.")

# -----------------------------------------------------------------------------
# 6. HEADER: CARD DE HORÁRIO COM REFRESH EM TEMPO REAL VIA FRAGMENT
# -----------------------------------------------------------------------------
col_tit1, col_tit2, col_signature = st.columns([2.3, 1.1, 0.6])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)

# Bloco dinâmico isolado para atualização em tempo real
@st.fragment(run_every=10)
def renderizar_relogio_realtime():
    now_br = datetime.now(pytz.timezone("America/Sao_Paulo"))
    
    hora_inicio_trabalho = 8
    hora_fim_trabalho = 17
    minutos_totais_trabalho = (hora_fim_trabalho - hora_inicio_trabalho) * 60
    minutos_atuais_jornada = (now_br.hour * 60 + now_br.minute) - (hora_inicio_trabalho * 60)
    pct_jornada = min(100.0, max(0.0, (minutos_atuais_jornada / minutos_totais_trabalho) * 100))
    
    st.markdown(f"""
        <div class='ios-clock-widget'>
            <div class='ios-clock-top'>
                <span class='ios-time'>{now_br.strftime('%H:%M:%S')}</span>
                <span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span>
            </div>
            <div class='ios-progress-label'>⏱️ Progresso da Jornada Operacional</div>
            <div class='ios-progress-container'>
                <div class='ios-progress-bar' style='width: {pct_jornada}%;'></div>
            </div>
            <div class='ios-weather-row'>
                <span style='color:#FFF; font-weight:500;'>📍 Guaíba - RS</span>
                <span style='color:#1A73E8; font-weight:600;'>{status_real.split(' ')[0]} {temp_real}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_tit2:
    renderizar_relogio_realtime()

with col_signature:
    st.markdown("""
        <div class='corporate-signature'>
            <p class='corp-title'>CMPC</p>
            <p class='corp-author'>Created by<br>Christian Jardim</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. PROCESSO DE RENDERIZAÇÃO DOS CARDS OPERACIONAIS
# -----------------------------------------------------------------------------
def tratar_mudanca_status(id_reg, prefixo, ordem_nome):
    status_escolhido = st.session_state.get(f"st_{prefixo}_{id_reg}")
    if status_escolhido in ["Pendente", "Necessita Reprogramação"]:
        motivo = st.session_state.get(f"mot_{prefixo}_{id_reg}", "Selecione motivo...")
        detalhe = st.session_state.get(f"det_{prefixo}_{id_reg}", "")
        comentario_final = f"{motivo}: {detalhe}" if motivo != "Selecione motivo..." else ""
    else:
        comentario_final = ""
    salvar_ou_atualizar_registro_db(id_reg, status_escolhido, comentario_final, ordem_nome)

def render_cards_operacionais(sub_df, unique_prefix):
    sub_df = sub_df.drop_duplicates(subset=["ordem"], keep="first")

    busca = st.text_input("🔍 Filtrar Ordens", "", placeholder="Filtrar...", key=f"src_v13_{unique_prefix}")
    if busca:
        sub_df = sub_df[sub_df["ordem"].astype(str).str.contains(busca, case=False) | sub_df["descricao"].astype(str).str.contains(busca, case=False)]
    if sub_df.empty:
        st.info("Nenhuma ordem identificada para os critérios atuais.")
        return

    modo_exibicao = st.segmented_control("Formato:", options=["Cards Detalhes", "Lista Compacta"], default="Cards Detalhes", key=f"v_v13_{unique_prefix}")
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
                    <small style='color:#8E8E93;'>🛠️ Operação Coordenada | 👤 Executante: {row['executante']}</small>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"📌 <b>OMS {ordem}</b> - <span style='color:{cor_disc}; font-weight:600;'>{row['disciplina']}</span> | {desc[:80]}...", unsafe_allow_html=True)

        col_rad, col_input = st.columns([1.6, 2.4])
        with col_rad:
            st.segmented_control(
                "Status", options=["Pendente", "Realizada", "Necessita Reprogramação"], default=status_atual, 
                key=f"st_{unique_prefix}_{id_reg}", label_visibility="collapsed",
                on_change=tratar_mudanca_status, args=(id_reg, unique_prefix, ordem)
            )
        with col_input:
            status_em_tempo_real = st.session_state.get(f"st_{unique_prefix}_{id_reg}", status_atual)
            if status_em_tempo_real in ["Pendente", "Necessita Reprogramação"]:
                motivos = ["Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Condição climática não favorável", "Outros"]
                col_sel, col_det = st.columns([1.5, 2.5])
                motivo_inicial, detalhe_inicial = "Selecione motivo...", ""
                
                if ":" in comentario_atual:
                    partes = comentario_atual.split(":", 1)
                    if partes[0] in motivos: 
                        motivo_inicial, detalhe_inicial = partes[0], partes[1].strip()
                elif comentario_atual in motivos: 
                    motivo_inicial = comentario_atual

                with col_sel:
                    st.selectbox(
                        "Justificativa", ["Selecione motivo..."] + motivos, index=(["Selecione motivo..."] + motivos).index(motivo_inicial),
                        key=f"mot_{unique_prefix}_{id_reg}", label_visibility="collapsed", on_change=tratar_mudanca_status, args=(id_reg, unique_prefix, ordem)
                    )
                with col_det:
                    st.text_input(
                        "Detalhes", value=detalhe_inicial, placeholder="Observações...", 
                        key=f"det_{unique_prefix}_{id_reg}", label_visibility="collapsed", on_change=tratar_mudanca_status, args=(id_reg, unique_prefix, ordem)
                    )

# -----------------------------------------------------------------------------
# 8. SISTEMA DE ABAS (VISUALIZAÇÃO COMPLETA)
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None:
    df_geral = st.session_state.db_data
    df_foco = df_geral[df_geral["area"].str.strip().isin(AREAS_FOCO)].copy()
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    # --- ABA 1 ---
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        df_foco_unicas = df_foco.drop_duplicates(subset=["ordem"])
        total_os = len(df_foco_unicas)
        realizadas = len(df_foco_unicas[df_foco_unicas["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Únicas (Foco)</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência de Execução Global</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#FF9F0A'>{total_os - realizadas}</div><div class='kpi-label'>Pendentes / Abertas</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Distribuição de Status</h4>", unsafe_allow_html=True)
            if not df_foco_unicas.empty:
                st_counts = df_foco_unicas["status_execucao"].value_counts().reset_index()
                fig1 = px.pie(st_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig1, use_container_width=True)
        with col_g2:
            st.markdown("<h4>Distribuição por Disciplina</h4>", unsafe_allow_html=True)
            if not df_foco_unicas.empty:
                disc_counts = df_foco_unicas["disciplina"].value_counts().reset_index()
                fig2 = px.pie(disc_counts, values="count", names="disciplina", hole=0.55, color="disciplina", color_discrete_map=DISCIPLINA_CORES)
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        
        st.markdown("<h4>Taxa de Execução Concluída (%) por Disciplina</h4>", unsafe_allow_html=True)
        if not df_foco_unicas.empty:
            lista_discs_existentes = sorted(list(df_foco_unicas["disciplina"].dropna().unique()))
            disc_alvo = st.selectbox("Escolha a disciplina que deseja acompanhar no gráfico:", lista_discs_existentes, key="seletor_reativo_final_v13")
            
            df_selecionada = df_foco_unicas[df_foco_unicas["disciplina"] == disc_alvo]
            total_atividades = len(df_selecionada)
            concluidas_atividades = len(df_selecionada[df_selecionada["status_execucao"] == "Realizada"])
            
            pct_concluida = (concluidas_atividades / total_atividades * 100) if total_atividades > 0 else 0.0
            pct_restante = 100.0 - pct_concluida
            
            fig_barras_horizontal = go.Figure()
            fig_barras_horizontal.add_trace(go.Bar(
                y=[disc_alvo], x=[pct_concluida], name="Concluído (%)", orientation='h',
                marker=dict(color=DISCIPLINA_CORES.get(disc_alvo, "#30D158")),
                text=[f"Concluído: {pct_concluida:.1f}% ({concluidas_atividades} OS)"], textposition='inside'
            ))
            fig_barras_horizontal.add_trace(go.Bar(
                y=[disc_alvo], x=[pct_restante], name="Pendente (%)", orientation='h',
                marker=dict(color="rgba(255,255,255,0.08)"),
                text=[f"Pendente: {pct_restante:.1f}%"], textposition='inside'
            ))
            
            fig_barras_horizontal.update_layout(
                barmode='stack', template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(range=[0, 100], gridcolor='rgba(255,255,255,0.05)', title="Porcentagem Base"),
                margin=dict(t=10, b=10, l=10, r=10), height=140, showlegend=False
            )
            st.plotly_chart(fig_barras_horizontal, use_container_width=True, key="graph_v13_core_engine")

    # --- ABA 2 ---
    with aba_exec:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        lista_executantes = ["Selecione executante..."] + sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Escolha o Executante da Área:", lista_executantes, key="c_exec_v13")
        
        if exec_sel != "Selecione executante...":
            df_exec = df_foco[df_foco["executante"] == exec_sel].copy()
            st.divider()
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                st.markdown(f"##### Aderência Geral de {exec_sel} (%)")
                st_exec_counts = df_exec.drop_duplicates(subset=["ordem"])["status_execucao"].value_counts().reset_index()
                f_pie_exec = px.pie(st_exec_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                f_pie_exec.update_layout(template="plotly_dark", height=230, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(f_pie_exec, use_container_width=True)
            with col_pie2:
                st.markdown("##### Carga Horária Programada vs. Horas Utilizadas")
                df_exec_unique = df_exec.drop_duplicates(subset=["ordem"]).copy()
                df_exec_unique["horas_num"] = df_exec_unique["tempo_execucao"].apply(extrair_horas)
                total_horas_alocadas = df_exec_unique["horas_num"].sum()
                horas_utilizadas = df_exec_unique[df_exec_unique["status_execucao"] == "Realizada"]["horas_num"].sum()
                horas_restantes = max(0.0, total_horas_alocadas - horas_utilizadas)
                
                df_horas_chart = pd.DataFrame([{"Métrica": "Horas Executadas", "Valor": horas_utilizadas}, {"Métrica": "Horas Pendentes", "Valor": horas_restantes}])
                f_pie_horas = px.pie(df_horas_chart, values="Valor", names="Métrica", hole=0.55, color="Métrica", color_discrete_map={"Horas Executadas": "#30D158", "Horas Pendentes": "rgba(255,255,255,0.1)"})
                f_pie_horas.update_layout(template="plotly_dark", height=230, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(f_pie_horas, use_container_width=True)
            
            st.divider()
            df_exec["data_parsed"] = pd.to_datetime(df_exec["data_inicio"], errors="coerce")
            df_exec["dia_nome"] = df_exec["data_parsed"].dt.day_name()
            
            if df_exec["data_parsed"].isna().all():
                render_cards_operacionais(df_exec, f"ex_lst_{exec_sel}")
            else:
                for eng_day, pt_day in dias_mapeamento.items():
                    df_dia_especifico = df_exec[df_exec["dia_nome"] == eng_day].copy()
                    if not df_dia_especifico.empty:
                        qtd_unicas = df_dia_especifico["ordem"].nunique()
                        with st.expander(f"➔ {pt_day} ({qtd_unicas} Ordens Únicas)", expanded=True):
                            render_cards_operacionais(df_dia_especifico, f"ex_crd_{exec_sel}_{eng_day}")

    # --- ABA 3 ---
    with aba_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina com Divisão Semanal</h2>", unsafe_allow_html=True)
        disc_sel = st.selectbox("Selecione a Disciplina para Filtragem Semanal:", sorted(list(df_foco["disciplina"].dropna().unique())), key="c_disc_page_v13_def")
        
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            df_disc["data_parsed"] = pd.to_datetime(df_disc["data_inicio"], errors="coerce")
            df_disc["dia_nome"] = df_disc["data_parsed"].dt.day_name()
            st.divider()
            
            if df_disc["data_parsed"].isna().all():
                st.warning("As atividades desta disciplina não contêm datas válidas.")
                render_cards_operacionais(df_disc, f"disc_full_list_{disc_sel}")
            else:
                for eng_day, pt_day in dias_mapeamento.items():
                    df_dia_disc = df_disc[df_disc["dia_nome"] == eng_day].copy()
                    if not df_dia_disc.empty:
                        qtd_unicas_disc = df_dia_disc["ordem"].nunique()
                        with st.expander(f"📅 {pt_day} — {disc_sel} ({qtd_unicas_disc} Ordens)", expanded=(pt_day.split("-")[0] == hoje_nome_pt)):
                            render_cards_operacionais(df_dia_disc, f"disc_crd_v13_{disc_sel}_{eng_day}")
else:
    st.warning("⬅️ Utilize o painel lateral para carregar sua planilha de programação original.")