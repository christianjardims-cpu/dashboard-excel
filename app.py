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
# 1. CONFIGURAÇÕES INICIAIS E ARQUITETURA VISUAL (GEMINI SPACE + iOS)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Forçar destruição de caches antigos do Streamlit injetando novos estados
if "versao_layout" not in st.session_state:
    st.session_state.clear()  # Limpa o estado residual antigo travado
    st.session_state.versao_layout = "3.0_gemini_stable"

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

# CSS de Alta Performance para sobrepor qualquer layout anterior
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    /* MODIFICAÇÃO RADICAL DA BARRA LATERAL (ESTILO GEMINI SPACE + BORDAS GRADIENTES) */
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #101114 0%, #15161C 100%) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important; 
        padding: 24px 16px !important; 
    }
    [data-testid="stSidebarCollapseButton"] button { 
        background-color: rgba(255, 255, 255, 0.04) !important; 
        border: 1px solid rgba(255, 255, 255, 0.08) !important; 
        border-radius: 50% !important; color: #FFFFFF !important; 
    }
    
    /* Inputs Globais Customizados */
    div[data-testid="stselectbox"] > div > div { background-color: #1A1B22; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; color: white; }
    
    /* Widget Principal de Horário Estilo iOS (CONSERVADO) */
    .ios-clock-widget { background: linear-gradient(145deg, #1E1E24, #141419); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .ios-clock-top { display: flex; justify-content: space-between; align-items: center; }
    .ios-time { font-size: 1.8rem; font-weight: 700; color: #0A84FF; font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    .ios-weather-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 6px; margin-top: 4px; }
    .ios-progress-container { background: rgba(255, 255, 255, 0.05); border-radius: 4px; height: 5px; width: 100%; overflow: hidden; }
    .ios-progress-bar { background: linear-gradient(90deg, #0A84FF, #30D158); height: 100%; }
    
    /* Painel de Clima de Segunda a Sexta Estilo Gemini Glass Translúcido */
    .gemini-sidebar-weather { 
        background: rgba(30, 31, 38, 0.45) !important; 
        border: 1px solid rgba(138, 180, 248, 0.18) !important; 
        border-radius: 20px !important; padding: 16px !important; 
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45) !important; 
        backdrop-filter: blur(20px); position: relative; overflow: hidden; margin-bottom: 24px; 
    }
    .gemini-sidebar-weather::before { 
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; 
        background: linear-gradient(90deg, #4285F4, #9B72CB, #D96570); 
    }
    .gemini-sidebar-header { font-family: 'Google Sans', sans-serif; font-size: 0.85rem; font-weight: 600; color: #8AB4F8; letter-spacing: 0.5px; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
    .gemini-sidebar-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); font-size: 0.85rem; border-radius: 8px; }
    .gemini-sidebar-row.active-day { background: rgba(66, 133, 244, 0.12); border-left: 3px solid #4285F4; padding-left: 10px; }
    .gemini-sidebar-row:last-child { border-bottom: none; }
    .gemini-sidebar-dayname { font-weight: 500; color: #E3E3E3; }
    .gemini-sidebar-icon { font-size: 1.1rem; }
    .gemini-sidebar-temp { font-variant-numeric: tabular-nums; font-weight: 600; color: #C58AF9; }
    
    /* Layout dos Cards Operacionais */
    .os-card { border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); transition: transform 0.2s ease; position: relative; }
    .os-card:hover { transform: translateY(-2px); }
    .badge-disciplina { font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 8px; text-transform: uppercase; margin-left: 8px; color: #FFF; }
    
    /* Painéis de KPI */
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(30, 30, 36, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; font-weight: 500; }
    
    /* Rodapé Corporativo */
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
# 3. TELEMETRIA METEOROLÓGICA REAL DE GUAÍBA - RS (OPEN-METEO)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=900)  # Reduzido tempo de cache para forçar atualização
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
        for i in range(min(7, len(daily.get("time", [])))):
            data_dt = datetime.strptime(daily["time"][i], "%Y-%m-%d")
            cronograma.append({
                "nome": dias_semana[data_dt.weekday()],
                "data_str": data_dt.strftime("%d/%m"),
                "status": wmo_codes.get(daily["weathercode"][i], "⛅ Oscilando"),
                "temp": f"{int(daily['temperature_2m_max'][i])}°C",
                "hoje": (i == 0)
            })
        return temp_atual, status_atual, cronograma
    except Exception:
        fallback = []
        dias_mock = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        for i, d in enumerate(dias_mock):
            fallback.append({"nome": d, "data_str": f"{15+i}/06", "status": "☀️ Limpo", "temp": "23°C", "hoje": (i==0)})
        return "22°C", "⛅ Parcial", fallback

temp_real, status_real, dados_clima = obter_previsao_real_guaiba()

# -----------------------------------------------------------------------------
# 4. CONFIGURAÇÕES INTERNAS DE DATA
# -----------------------------------------------------------------------------
if "db_data" not in st.session_state or st.session_state.get("recriar_cache", False):
    st.session_state.db_data = carregar_dados_db()
    st.session_state.recriar_cache = False

tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)
hoje_nome_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now_br.weekday()]
pct_dia = min(100.0, max(0.0, ((now_br.hour * 60 + now_br.minute) / 1440.0) * 100))

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
# 5. SIDEBAR: LAYOUT GEMINI DEFINITIVO COM WIDGET DE PREVISÃO DO TEMPO
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
        st.markdown("<div style='padding: 20px; background: linear-gradient(135deg, #30D158, #1A73E8); border-radius: 12px; text-align: center; font-weight: 700; font-size: 1.8rem; color: white; letter-spacing: -1px; margin-bottom: 10px;'>cmpc</div>", unsafe_allow_html=True)
        
    st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
    
    # WIDGET DE CLIMA PREMIUM DE SEGUNDA A SEXTA (ESTILO GOOGLE GEMINI)
    html_gemini_weather = """
    <div class='gemini-sidebar-weather'>
        <div class='gemini-sidebar-header'>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L14.8 9.2L22 12L14.8 14.8L12 22L9.2 14.8L2 12L9.2 9.2L12 2Z" fill="#8AB4F8"/>
            </svg>
            Previsão do Tempo (Guaíba)
        </div>
    """
    filtro_dias_uteis = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    for info in dados_clima:
        if info["nome"] in filtro_dias_uteis:
            classe_ativa = "active-day" if info["nome"] == hoje_nome_pt else ""
            tag_hoje = " <small style='color:#4285F4;font-weight:700;'>• Hoje</small>" if info["nome"] == hoje_nome_pt else ""
            
            html_gemini_weather += f"""
            <div class='gemini-sidebar-row {classe_ativa}'>
                <span class='gemini-sidebar-dayname'>{info['nome']}{tag_hoje}</span>
                <span class='gemini-sidebar-icon'>{info['status'].split(' ')[0]}</span>
                <span class='gemini-sidebar-temp'>{info['temp']}</span>
            </div>
            """
    html_gemini_weather += "</div>"
    st.markdown(html_gemini_weather, unsafe_allow_html=True)
    
    # Formulário de Autenticação
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:6px;'>ADMINISTRAÇÃO BASE</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed", key="v3_stable_pass_key")
    
    if senha_inserida == "Programacao@2026":
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 1000
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"], key=f"uploader_v3_{st.session_state.uploader_key}")
        
        if uploaded_file is not None:
            nome_arq = uploaded_file.name.lower()
            try:
                with st.spinner("Processando dados corporativos..."):
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
            except Exception as e: st.error(f"Erro: {e}")
                
    st.markdown("<hr style='margin: 18px 0; border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:8px;'>PROGRAMAÇÃO DO TURNO</p>", unsafe_allow_html=True)
    st.markdown(f"<small style='color:#9AA0A6;'>Unidade Guaíba • Monitoramento Ativo de Caldeira e Utilidades.</small>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. HEADER: MANUTENÇÃO INTEGRA DO CARD DE HORÁRIO EXISTENTE
# -----------------------------------------------------------------------------
col_tit1, col_tit2, col_signature = st.columns([2.3, 1.1, 0.6])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_tit2:
    st.markdown(f"""
        <div class='ios-clock-widget'>
            <div class='ios-clock-top'>
                <span class='ios-time'>{now_br.strftime('%H:%M')}</span>
                <span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span>
            </div>
            <div class='ios-progress-container'><div class='ios-progress-bar' style='width: {pct_dia}%;'></div></div>
            <div class='ios-weather-row'>
                <span style='color:#FFF; font-weight:500;'>📍 Principal - RS</span>
                <span style='color:#0A84FF; font-weight:600;'>{status_real.split(' ')[0]} {temp_real}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
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
    busca = st.text_input("🔍 Filtrar Ordens", "", placeholder="Filtrar...", key=f"src_v3_{unique_prefix}")
    if busca:
        sub_df = sub_df[sub_df["ordem"].astype(str).str.contains(busca, case=False) | sub_df["descricao"].astype(str).str.contains(busca, case=False)]
    if sub_df.empty:
        st.info("Nenhuma ordem identificada para os critérios atuais.")
        return

    modo_exibicao = st.segmented_control("Formato:", options=["Cards Detalhes", "Lista Compacta"], default="Cards Detalhes", key=f"v_v3_{unique_prefix}")
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
                    if partes[0] in motifs:
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
# 8. SISTEMA DE ABAS ATUALIZADO (SELETOR DE GRÁFICO E DIVISÃO DE DIAS)
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None:
    df_geral = st.session_state.db_data
    df_foco = df_geral[df_geral["area"].str.strip().isin(AREAS_FOCO)].copy()
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    # --- ABA 1: VISÃO MACRO COM SELETOR DE GRÁFICO ---
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        total_os = len(df_foco)
        realizadas = len(df_foco[df_foco["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Totais (Foco)</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência de Execução Global</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#FF9F0A'>{total_os - realizadas}</div><div class='kpi-label'>Pendentes / Abertas</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Distribuição de Status (Áreas de Foco)</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                st_counts = df_foco["status_execucao"].value_counts().reset_index()
                fig1 = px.pie(st_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig1, use_container_width=True)
        with col_g2:
            st.markdown("<h4>Distribuição por Disciplina de Trabalho</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                disc_counts = df_foco["disciplina"].value_counts().reset_index()
                fig2 = px.pie(disc_counts, values="count", names="disciplina", hole=0.55, color="disciplina", color_discrete_map=DISCIPLINA_CORES)
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig2, use_container_width=True)

        st.divider()
        
        # 📊 SOLUÇÃO DO GRÁFICO COM SELETOR REATIVO SOLICITADO
        st.markdown("<h4>Taxa de Execução Concluída (%) por Disciplina</h4>", unsafe_allow_html=True)
        if not df_foco.empty:
            lista_discs_existentes = sorted(list(df_foco["disciplina"].dropna().unique()))
            # Seletor dinâmico exigido
            disc_alvo = st.selectbox("Escolha a disciplina que deseja acompanhar no gráfico:", lista_discs_existentes, key="seletor_reativo_final_v3")
            
            df_selecionada = df_foco[df_foco["disciplina"] == disc_alvo]
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
                xaxis=dict(range=[0, 100], gridcolor='rgba(255,255,255,0.05)', title="Porcentagem Base do Escopo Total"),
                margin=dict(t=10, b=10, l=10, r=10), height=140, showlegend=False
            )
            st.plotly_chart(fig_barras_horizontal, use_container_width=True, key="graph_v3_core_engine")

    # --- ABA 2: APONTAMENTO POR EXECUTANTE ---
    with aba_exec:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        lista_executantes = ["Selecione executante..."] + sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Escolha o Executante da Área:", lista_executantes, key="c_exec_v3")
        
        if exec_sel != "Selecione executante...":
            df_exec = df_foco[df_foco["executante"] == exec_sel].copy()
            st.divider()
            col_pie1, col_pie2 = st.columns(2)
            with col_pie1:
                st.markdown(f"##### Aderência Geral de {exec_sel} (%)")
                st_exec_counts = df_exec["status_execucao"].value_counts().reset_index()
                f_pie_exec = px.pie(st_exec_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                f_pie_exec.update_layout(template="plotly_dark", height=230, paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(f_pie_exec, use_container_width=True)
            with col_pie2:
                st.markdown("##### Carga Horária Programada vs. Horas Utilizadas")
                df_exec["horas_num"] = df_exec["tempo_execucao"].apply(extrair_horas)
                total_horas_alocadas = df_exec["horas_num"].sum()
                horas_utilizadas = df_exec[df_exec["status_execucao"] == "Realizada"]["horas_num"].sum()
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
                        with st.expander(f"➔ {pt_day} ({len(df_dia_especifico)} Atividades)", expanded=True):
                            render_cards_operacionais(df_dia_especifico, f"ex_crd_{exec_sel}_{eng_day}")

    # --- ABA 3: APONTAMENTO POR DISCIPLINA (ATIVIDADES SEPARADAS POR DIA DA SEMANA) ---
    with aba_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina com Divisão Semanal</h2>", unsafe_allow_html=True)
        disc_sel = st.selectbox("Selecione a Disciplina para Filtragem Semanal:", sorted(list(df_foco["disciplina"].dropna().unique())), key="c_disc_page_v3_def")
        
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            df_disc["data_parsed"] = pd.to_datetime(df_disc["data_inicio"], errors="coerce")
            df_disc["dia_nome"] = df_disc["data_parsed"].dt.day_name()
            st.divider()
            
            if df_disc["data_parsed"].isna().all():
                st.warning("As atividades desta disciplina não contêm datas válidas configuradas no arquivo.")
                render_cards_operacionais(df_disc, f"disc_full_list_{disc_sel}")
            else:
                # Modificação aplicada: Separação obrigatória por dias úteis da semana
                for eng_day, pt_day in dias_mapeamento.items():
                    df_dia_disc = df_disc[df_disc["dia_nome"] == eng_day].copy()
                    if not df_dia_disc.empty:
                        with st.expander(f"📅 {pt_day} — {disc_sel} ({len(df_dia_disc)} Ordens)", expanded=(pt_day.split("-")[0] == hoje_nome_pt)):
                            render_cards_operacionais(df_dia_disc, f"disc_crd_v3_{disc_sel}_{eng_day}")
else:
    st.warning("⬅️ Utilize o painel lateral para carregar sua planilha de programação original.")