import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
import pytz
import sqlite3
import requests
import re
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CONFIGURAÇÕES VISUAIS DA INTERFACE (ESTILO GEMINI / CLEAN DARK)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Alerta visual temporário para você ter 100% de certeza que o appv17.py foi carregado
st.success("⚡ ARQUIVO 'appv17.py' IDENTIFICADO E RECARREGADO COM SUCESSO ⚡")

# Limpeza rígida de memória local
for key in list(st.session_state.keys()):
    if key != "db_data":
        del st.session_state[key]

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

# CSS Framework Limpo - Mantém as setas (arrows) originais dos expanders intocadas
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght=400;500;600;700&family=Inter:wght=300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #0A0A0C 0%, #111217 100%) !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.03) !important; 
    }
    
    .gemini-weather-container {
        background: rgba(22, 23, 29, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 16px;
    }
    .gemini-weather-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 6px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    }
    .gemini-weather-row:last-child { border-bottom: none; }
    
    .ios-clock-widget { background: linear-gradient(145deg, #18191E, #0F1013); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 18px; padding: 16px 20px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
    .ios-time { font-size: 1.8rem; font-weight: 700; color: #1A73E8; font-variant-numeric: tabular-nums; }
    .ios-date-badge { background: rgba(26, 115, 232, 0.1); color: #1A73E8; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    
    .os-card { border-radius: 14px; padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
    .badge-disciplina { font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 8px; text-transform: uppercase; margin-left: 8px; color: #FFF; }
    
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(22, 23, 29, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; }
    
    div.stButton > button:first-child {
        border-radius: 20px !important;
        font-weight: 500 !important;
    }
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
    st.toast(f"OMS {ordem_nome} atualizada!", icon="💾")

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
# 3. CONEXÃO CLIMÁTICA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def obter_dados_clima_v17():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-30.1139&longitude=-51.3250&daily=weathercode,temperature_2m_max,temperature_2m_min&current_weather=true&timezone=America/Sao_Paulo"
        res = requests.get(url, timeout=4).json()
        wmo = {0: "☀️ Limpo", 1: "⛅ Parcial", 2: "⛅ Parcial", 3: "☁️ Encoberto", 61: "🌧️ Chuva", 95: "⚡ Tempestade"}
        curr = res.get("current_weather", {})
        daily = res.get("daily", {})
        cronograma = []
        dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        for i in range(min(5, len(daily.get("time", [])))):
            dt = datetime.strptime(daily["time"][i], "%Y-%m-%d")
            cronograma.append({"nome": dias[dt.weekday()], "status": wmo.get(daily["weathercode"][i], "☁️ Encoberto"), "temp": f"{int(daily['temperature_2m_max'][i])}°C"})
        return f"{int(curr.get('temperature', 14))}°C", wmo.get(curr.get("weathercode"), "☁️ Encoberto"), cronograma
    except:
        return "14°C", "☁️ Encoberto", [{"nome": "Segunda", "status": "☁️ Encoberto", "temp": "14°C"}]

temp_real, status_real, dados_clima = obter_dados_clima_v17()

if "db_data" not in st.session_state or st.session_state.get("recriar_cache", False):
    st.session_state.db_data = carregar_dados_db()
    st.session_state.recriar_cache = False

tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)
hoje_nome_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][now_br.weekday()]
dias_mapeamento = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}

# -----------------------------------------------------------------------------
# 4. SIDEBAR OPERACIONAL
# -----------------------------------------------------------------------------
with st.sidebar:
    st.subheader("🏭 CMPC Guaíba")
    st.write("---")
    st.markdown("<div class='gemini-weather-container'>", unsafe_allow_html=True)
    for info in dados_clima:
        act = "color:#1A73E8; font-weight:600;" if info["nome"] == hoje_nome_pt else "color:#AAAEB6;"
        st.markdown(f"<div class='gemini-weather-row'><span style='{act}'>{info['nome']}</span><span>{info['status']} | <b>{info['temp']}</b></span></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    senha = st.text_input("Chave operacional:", type="password", key="v17_pass_secure")
    if senha == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload da Planilha:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            df_t = pd.read_csv(uploaded_file, skiprows=1) if uploaded_file.name.lower().endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
            df_t.columns = df_t.columns.str.strip()
            df_t["Disciplina"] = df_t["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")) if "Centro de Trabalho Op." in df_t.columns else "Mecânica"
            df_t["Status_Execucao"] = "Pendente"
            df_t["Comentario"] = ""
            atualizar_banco_completo(df_t)
            st.session_state.db_data = carregar_dados_db()
            st.rerun()

# -----------------------------------------------------------------------------
# 5. HEADER COM FIXAÇÃO DE STRING (SEM SEGUNDOS NATIVO)
# -----------------------------------------------------------------------------
col_tit1, col_tit2, col_signature = st.columns([2.3, 1.1, 0.6])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)

with col_tit2:
    # A string abaixo extrai rigorosamente apenas HH:MM do servidor Python. Os segundos foram limpos da raiz.
    string_relogio_estatica = f"{now_br.hour:02d}:{now_br.minute:02d}"
    st.markdown(f"""
        <div class='ios-clock-widget'>
            <div style='display:flex; justify-content:between; align-items:center;'>
                <span class='ios-time'>{string_relogio_estatica}</span>
                <span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span>
            </div>
            <div style='font-size:0.85rem; color:#1A73E8; margin-top:4px;'>📍 Guaíba - RS • {status_real} {temp_real}</div>
        </div>
    """, unsafe_allow_html=True)

with col_signature:
    st.markdown("<div style='text-align:right;'><p style='font-weight:700; margin:0;'>CMPC</p><p style='font-size:0.7rem; color:#9AA0A6; margin:0;'>Christian Jardim</p></div>", unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 6. ENGINE DE APONTAMENTO COM BOTÕES DIRETOS DE STATUS ATIVO (FIX CORES)
# -----------------------------------------------------------------------------
def render_cards_operacionais(sub_df, unique_prefix):
    sub_df = sub_df.drop_duplicates(subset=["ordem"], keep="first")
    
    for _, row in sub_df.iterrows():
        id_reg, ordem, desc, status_atual, cor_disc = row["id"], row["ordem"], row["descricao"], row["status_execucao"], DISCIPLINA_CORES.get(row["disciplina"], "#8E8E93")
        comentario_atual = "" if str(row["comentario"]) in ["nan", "None", ""] else str(row["comentario"])
        
        st.markdown(f"""
            <div class='os-card' style='background: {HEX_BG_MAP.get(status_atual, "rgba(255,255,255,0.02)")}; border-left: 5px solid {COLOR_MAP.get(status_atual, "#8E8E93")}; margin-bottom:15px;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span><strong>OMS:</strong> <code>{ordem}</code> <span class='badge-disciplina' style='background:{cor_disc};'>{row['disciplina']}</span></span>
                    <span style='font-size:0.85rem; color:#9AA0A6;'>⏱️ Carga: {row['tempo_execucao']}</span>
                </div>
                <p style='margin:8px 0 4px 0; font-size:0.95rem; font-weight:500;'>{desc}</p>
                <small style='color:#8E8E93;'>👤 Executante: {row['executante']}</small>
            </div>
        """, unsafe_allow_html=True)

        col_b1, col_b2, col_b3 = st.columns([1, 1, 1.2])
        status_novo = status_atual
        
        with col_b1:
            label_p = "🔴 PENDENTE (ATIVO)" if status_atual == "Pendente" else "Pendente"
            if st.button(label_p, key=f"bp_{unique_prefix}_{id_reg}", use_container_width=True, type="primary" if status_atual == "Pendente" else "secondary"):
                status_novo = "Pendente"
        with col_b2:
            label_r = "🟢 REALIZADA (ATIVO)" if status_atual == "Realizada" else "Realizada"
            if st.button(label_r, key=f"br_{unique_prefix}_{id_reg}", use_container_width=True, type="primary" if status_atual == "Realizada" else "secondary"):
                status_novo = "Realizada"
        with col_b3:
            label_o = "🟠 REPROGRAMAR (ATIVO)" if status_atual == "Necessita Reprogramação" else "Reprogramar"
            if st.button(label_o, key=f"bo_{unique_prefix}_{id_reg}", use_container_width=True, type="primary" if status_atual == "Necessita Reprogramação" else "secondary"):
                status_novo = "Necessita Reprogramação"

        # Injeta CSS direcionado para colorir as bordas dos botões conforme as cores dos balões
        st.markdown(f"""
            <style>
                button[key*="bp_{unique_prefix}_{id_reg}"] {{ border-color: #FF453A !important; color: #FF453A !important; }}
                button[key*="br_{unique_prefix}_{id_reg}"] {{ border-color: #30D158 !important; color: #30D158 !important; }}
                button[key*="bo_{unique_prefix}_{id_reg}"] {{ border-color: #FF9F0A !important; color: #FF9F0A !important; }}
            </style>
        """, unsafe_allow_html=True)

        if status_novo in ["Pendente", "Necessita Reprogramação"]:
            motivos = ["Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Condição climática não favorável", "Outros"]
            col_sel, col_det = st.columns([1.5, 2.5])
            motivo_inicial, detalhe_inicial = "Selecione motivo...", ""
            
            if ":" in comentario_atual:
                partes = comentario_atual.split(":", 1)
                if partes[0] in motives: motivo_inicial, detalhe_inicial = partes[0], partes[1].strip()
            elif comentario_atual in motives: motivo_inicial = comentario_atual

            with col_sel:
                motivo_escolhido = st.selectbox("Justificativa", ["Selecione motivo..."] + motivos, index=(["Selecione motivo..."] + motivos).index(motivo_inicial), key=f"sm_{unique_prefix}_{id_reg}", label_visibility="collapsed")
            with col_det:
                detalhe_escolhido = st.text_input("Detalhes", value=detalhe_inicial, placeholder="Observações adicionais...", key=f"dm_{unique_prefix}_{id_reg}", label_visibility="collapsed")
            
            comentario_final = f"{motivo_escolhido}: {detalhe_escolhido}" if motivo_escolhido != "Selecione motivo..." else ""
            if status_novo != status_atual or comentario_final != comentario_atual:
                salvar_ou_atualizar_registro_db(id_reg, status_novo, comentario_final, ordem)
                st.rerun()
        else:
            if status_novo != status_atual:
                salvar_ou_atualizar_registro_db(id_reg, status_novo, "", ordem)
                st.rerun()
        st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. EXIBIÇÃO DE DADOS POR ABAS (EXPANDERS 100% NATIVOS PARA PRESERVAR AS SETAS)
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None:
    df_geral = st.session_state.db_data
    df_foco = df_geral[df_geral["area"].str.strip().isin(AREAS_FOCO)].copy()
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        df_foco_unicas = df_foco.drop_duplicates(subset=["ordem"])
        total_os = len(df_foco_unicas)
        realizadas = len(df_foco_unicas[df_foco_unicas["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Únicas</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência Global</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#FF9F0A'>{total_os - realizadas}</div><div class='kpi-label'>Pendentes</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if not df_foco_unicas.empty:
                fig1 = px.pie(df_foco_unicas["status_execucao"].value_counts().reset_index(), values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP)
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig1, use_container_width=True)
        with col_g2:
            if not df_foco_unicas.empty:
                fig2 = px.pie(df_foco_unicas["disciplina"].value_counts().reset_index(), values="count", names="disciplina", hole=0.55, color="disciplina", color_discrete_map=DISCIPLINA_CORES)
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=10,b=10,l=10,r=10))
                st.plotly_chart(fig2, use_container_width=True)

    with aba_exec:
        lista_executantes = ["Selecione executante..."] + sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Escolha o Executante:", lista_executantes, key="c_exec_v17_page")
        if exec_sel != "Selecione executante...":
            df_exec = df_foco[df_foco["executante"] == exec_sel].copy()
            df_exec["data_parsed"] = pd.to_datetime(df_exec["data_inicio"], errors="coerce")
            df_exec["dia_nome"] = df_exec["data_parsed"].dt.day_name()
            
            for eng_day, pt_day in dias_mapeamento.items():
                df_dia_especifico = df_exec[df_exec["dia_nome"] == eng_day].copy()
                if not df_dia_especifico.empty:
                    with st.expander(f"{pt_day} ({df_dia_especifico['ordem'].nunique()} Ordens Únicas)", expanded=True):
                        render_cards_operacionais(df_dia_especifico, f"ex_v17_{exec_sel}_{eng_day}")

    with aba_disc:
        disc_sel = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["disciplina"].dropna().unique())), key="c_disc_v17_page")
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            df_disc["data_parsed"] = pd.to_datetime(df_disc["data_inicio"], errors="coerce")
            df_disc["dia_nome"] = df_disc["data_parsed"].dt.day_name()
            
            for eng_day, pt_day in dias_mapeamento.items():
                df_dia_disc = df_disc[df_disc["dia_nome"] == eng_day].copy()
                if not df_dia_disc.empty:
                    with st.expander(f"{pt_day} — {disc_sel} ({df_dia_disc['ordem'].nunique()} Ordens)", expanded=(pt_day.split("-")[0] == hoje_nome_pt)):
                        render_cards_operacionais(df_dia_disc, f"disc_v17_{disc_sel}_{eng_day}")
else:
    st.warning("⬅️ Faça o login operacional e envie a planilha no menu lateral para iniciar.")