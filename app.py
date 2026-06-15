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
# 1. CONFIGURAÇÕES INICIAIS E QUEBRA DE CACHE SEVERA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Forçar o reset completo limpando estados antigos que travam o layout
if "chave_reset_v6" not in st.session_state:
    st.session_state.clear()  
    st.session_state.chave_reset_v6 = "v6_linha_fibras_fixo"

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

# Interface Visual Premium
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght=400;500;600;700&family=Inter:wght=300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    [data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #101114 0%, #15161C 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important; 
        padding: 24px 16px !important;
    }
    
    div[data-testid="stselectbox"] > div > div { background-color: #1A1B22 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important; border-radius: 12px !important; color: white !important;
    }
    
    .ios-clock-widget { background: linear-gradient(145deg, #1E1E24, #141419);
        border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 16px 20px; display: flex; flex-direction: column; gap: 6px; }
    .ios-time { font-size: 1.8rem; font-weight: 700; color: #0A84FF; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; }
    
    .os-card { border-radius: 14px; padding: 18px; margin-bottom: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative; }
    .badge-disciplina { font-size: 0.7rem; font-weight: 600; padding: 3px 8px; border-radius: 8px; text-transform: uppercase; margin-left: 8px; color: #FFF; }
    
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(30, 30, 36, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; font-weight: 500; }
</style>""", unsafe_allow_html=True)

DB_NOME = "data_cmpc.db"

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
# 3. VARIÁVEIS DE TEMPO E AMBIENTE
# -----------------------------------------------------------------------------
if "db_data" not in st.session_state or st.session_state.get("recriar_cache", False):
    st.session_state.db_data = carregar_dados_db()
    st.session_state.recriar_cache = False

tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)

dias_mapeamento = {
    "Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira",
    "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"
}

# -----------------------------------------------------------------------------
# 4. SIDEBAR 
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("<div style='padding: 15px; background: linear-gradient(135deg, #30D158, #1A73E8); border-radius: 12px; text-align: center; font-weight: 700; font-size: 1.5rem; color: white;'>CMPC MANUTENÇÃO</div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-top:20px;'>AUTENTICAÇÃO</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Senha...", label_visibility="collapsed")
    
    if senha_inserida == "Programacao@2026":
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 6000
        uploaded_file = st.file_uploader("Carregar nova planilha:", type=["csv", "xlsx"], key=f"upl_{st.session_state.uploader_key}")
        
        if uploaded_file is not None:
            nome_arq = uploaded_file.name.lower()
            try:
                df_temp = pd.read_csv(uploaded_file, skiprows=1) if nome_arq.endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
                df_temp.columns = df_temp.columns.str.strip()
                
                if "Centro de Trabalho Op." in df_temp.columns:
                    df_temp["Disciplina"] = df_temp["Centro de Trabalho Op."].astype(str).apply(
                        lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
                    )
                else: df_temp["Disciplina"] = "Mecânica"
                
                df_temp["Status_Execucao"] = "Pendente"
                df_temp["Comentario"] = ""
                
                atualizar_banco_completo(df_temp)
                st.session_state.db_data = carregar_dados_db()
                st.session_state.recriar_cache = True
                st.success("Planilha processada e gravada!")
                st.session_state.uploader_key += 1
                st.rerun()
            except Exception as e: st.error(f"Erro no processamento: {e}")

# -----------------------------------------------------------------------------
# 5. HEADER FIXO
# -----------------------------------------------------------------------------
col_tit1, col_tit2, col_signature = st.columns([2.3, 1.1, 0.6])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão por Áreas Estuturadas • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_tit2:
    st.markdown(f"""
        <div class='ios-clock-widget'>
            <div class='ios-clock-top' style='display:flex; justify-content:space-between; align-items:center;'>
                <span class='ios-time' style='font-size: 1.5rem; font-weight:700; color:#0A84FF;'>{now_br.strftime('%H:%M')}</span>
                <span class='ios-date-badge'>{now_br.strftime('%d %b %y')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
with col_signature:
    st.markdown("<div style='text-align:right;'><p style='font-weight:700;margin:0;'>CMPC</p><p style='font-size:0.75rem;color:#9AA0A6;margin:0;'>Christian Jardim</p></div>", unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 6. FUNÇÃO OPERACIONAL DOS CARDS
# -----------------------------------------------------------------------------
def tratar_mudanca_status(id_reg, prefixo, ordem_nome):
    status_escolhido = st.session_state.get(f"st_{prefixo}_{id_reg}")
    if status_escolhido in ["Pendente", "Necessita Reprogramação"]:
        motivo = st.session_state.get(f"mot_{prefixo}_{id_reg}", "Selecione motivo...")
        detalhe = st.session_state.get(f"det_{prefixo}_{id_reg}", "")
        comentario_final = f"{motivo}: {detalhe}" if motivo != "Selecione motivo..." else ""
    else: comentario_final = ""
    salvar_ou_atualizar_registro_db(id_reg, status_escolhido, comentario_final, ordem_nome)

def render_cards_operacionais(sub_df, unique_prefix):
    for _, row in sub_df.iterrows():
        id_reg, ordem, desc, operacao, status_atual, cor_disc = row["id"], row["ordem"], row["descricao"], row["operacao"], row["status_execucao"], DISCIPLINA_CORES.get(row["disciplina"], "#8E8E93")
        comentario_atual = "" if str(row["comentario"]) in ["nan", "None", ""] else str(row["comentario"])
        bg_card = HEX_BG_MAP.get(status_atual, "rgba(255,255,255,0.02)")
        border_left_color = COLOR_MAP.get(status_atual, "#8E8E93")
        
        st.markdown(f"""
            <div class='os-card' style='background: {bg_card}; border-left: 5px solid {border_left_color};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span><strong>OMS:</strong> <code>{ordem}</code> <span class='badge-disciplina' style='background:{cor_disc};'>{row['disciplina']}</span></span>
                    <span style='font-size:0.85rem; color:#9AA0A6;'>⏱️ Carga: {row['tempo_execucao']}</span>
                </div>
                <p style='margin:6px 0; font-size:0.95rem; font-weight:500;'>{desc}</p>
                <small style='color:#8E8E93;'>🛠️ Operação: {operacao} | 👤 Executante: {row['executante']}</small>
            </div>
        """, unsafe_allow_html=True)

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
                    if partes[0] in motifs: motivo_inicial, detalhe_inicial = partes[0], partes[1].strip()
                elif comentario_atual in motivos: motivo_inicial = comentario_atual

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
        st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. INJEÇÃO FORÇADA DE ÁREAS E EXECUTANTES (PREVINE TRAVAS DE CACHE)
# -----------------------------------------------------------------------------
if st.session_state.db_data is not None and not st.session_state.db_data.empty:
    df_geral = st.session_state.db_data
    
    # Coleta automática do banco
    areas_do_banco = [str(area).strip() for area in df_geral["area"].dropna().unique() if str(area).strip() != ""]
    
    # FORÇANDO MANUALMENTE A LISTA PARA INCLUIR A LINHA DE FIBRAS CASO O BANCO ESTEJA TRAVADO
    todas_areas_reais = sorted(list(set(areas_do_banco + ["LINHA DE FIBRAS"])))
    
    aba_geral, aba_exec, aba_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
   
    # --- ABA 1: MÉTRICAS ---
    with aba_geral:
        st.markdown("<h3 style='color:#8AB4F8;'>Selecione a Área para Análise de Métricas</h3>", unsafe_allow_html=True)
        area_macro_sel = st.selectbox("Área Operacional Alvo:", todas_areas_reais, key="sel_macro_v6")
        
        df_foco = df_geral[df_geral["area"].str.strip() == area_macro_sel].copy()
        
        total_os = len(df_foco)
        realizadas = len(df_foco[df_foco["status_execucao"] == "Realizada"])
        aderencia = (realizadas / total_os * 100) if total_os > 0 else 0.0
        
        st.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-card'><div class='kpi-value'>{total_os}</div><div class='kpi-label'>Ordens Totais ({area_macro_sel})</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia:.1f}%</div><div class='kpi-label'>Aderência da Área</div></div>
                <div class='kpi-card'><div class='kpi-value' style='color:#FF9F0A'>{total_os - realizadas}</div><div class='kpi-label'>Pendentes</div></div>
            </div>
        """, unsafe_allow_html=True)
         
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if not df_foco.empty:
                st_counts = df_foco["status_execucao"].value_counts().reset_index()
                fig1 = px.pie(st_counts, values="count", names="status_execucao", hole=0.55, color="status_execucao", color_discrete_map=COLOR_MAP, title=f"Status - {area_macro_sel}")
                fig1.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig1, use_container_width=True)
        with col_g2:
            if not df_foco.empty:
                disc_counts = df_foco["disciplina"].value_counts().reset_index()
                fig2 = px.pie(disc_counts, values="count", names="disciplina", hole=0.55, color="disciplina", color_discrete_map=DISCIPLINA_CORES, title=f"Distribuição - {area_macro_sel}")
                fig2.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig2, use_container_width=True)

    # --- ABA 2: EXECUTANTE ---
    with aba_exec:
        st.markdown("<h3 style='color:#8AB4F8;'>Filtro de Atividades por Área e Executante</h3>", unsafe_allow_html=True)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            area_exec_sel = st.selectbox("1. Escolha a Área para filtrar a equipe:", todas_areas_reais, key="sel_area_exec_v6")
            df_filtrado_area_exec = df_geral[df_geral["area"].str.strip() == area_exec_sel].copy()
        with col_f2:
            executantes_banco = list(df_filtrado_area_exec["executante"].dropna().unique())
            
            # FORÇANDO MANUALMENTE O EXECUTANTE SE A ÁREA FOR LINHA DE FIBRAS
            if area_exec_sel == "LINHA DE FIBRAS":
                if "VITOR POHEN" not in executantes_banco:
                    executantes_banco.append("VITOR POHEN")
            
            lista_executantes_filtrados = ["Selecione executante..."] + sorted(executantes_banco)
            exec_sel = st.selectbox("2. Escolha o Executante:", lista_executantes_filtrados, key="exec_final_v6")
        
        if exec_sel != "Selecione executante...":
            df_exec = df_filtrado_area_exec[df_filtrado_area_exec["executante"] == exec_sel].copy()
            
            # Se for injetado manualmente e o df do banco estiver vazio para ele, simular uma visualização vazia elegante
            if df_exec.empty and exec_sel == "VITOR POHEN":
                st.info(f"O executante {exec_sel} foi adicionado à área {area_exec_sel}. Nenhuma OS pendente localizada para ele no momento.")
            else:
                st.divider()
                df_exec["data_parsed"] = pd.to_datetime(df_exec["data_inicio"], errors="coerce")
                df_exec["dia_nome"] = df_exec["data_parsed"].dt.day_name()
                
                if df_exec["data_parsed"].isna().all():
                    render_cards_operacionais(df_exec, f"ex_v6_{exec_sel}")
                else:
                    for eng_day, pt_day in dias_mapeamento.items():
                        df_dia_especifico = df_exec[df_exec["dia_nome"] == eng_day].copy()
                        if not df_dia_especifico.empty:
                            with st.expander(f"➔ {pt_day} ({len(df_dia_especifico)} Atividades)", expanded=True):
                                render_cards_operacionais(df_dia_especifico, f"v6_ex_{exec_sel}_{eng_day}")

    # --- ABA 3: DISCIPLINA ---
    with aba_disc:
        st.markdown("<h3 style='color:#8AB4F8;'>Cronograma Semanal por Área e Disciplina</h3>", unsafe_allow_html=True)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            area_disc_sel = st.selectbox("1. Escolha a Área para filtrar as especialidades:", todas_areas_reais, key="sel_area_disc_v6")
            df_filtrado_area_disc = df_geral[df_geral["area"].str.strip() == area_disc_sel].copy()
        with col_d2:
            lista_discs_filtradas = sorted(list(df_filtrado_area_disc["disciplina"].dropna().unique()))
            if area_disc_sel == "LINHA DE FIBRAS" and not lista_discs_filtradas:
                lista_discs_filtradas = ["Mecânica", "Elétrica", "Instrumentação"]
                
            if lista_discs_filtradas:
                disc_sel = st.selectbox("2. Selecione a Disciplina de Trabalho:", lista_discs_filtradas, key="disc_final_v6")
            else:
                disc_sel = None
                st.info("Nenhuma disciplina ativa cadastrada para esta Área.")
        
        if disc_sel:
            df_disc = df_filtrado_area_disc[df_filtrado_area_disc["disciplina"] == disc_sel].copy()
            if df_disc.empty and area_disc_sel == "LINHA DE FIBRAS":
                st.info(f"Área {area_disc_sel} habilitada para a disciplina {disc_sel}. Aguardando ordens planejadas.")
            else:
                df_disc["data_parsed"] = pd.to_datetime(df_disc["data_inicio"], errors="coerce")
                df_disc["dia_nome"] = df_disc["data_parsed"].dt.day_name()
                st.divider()
                
                if df_disc["data_parsed"].isna().all():
                    render_cards_operacionais(df_disc, f"disc_v6_{disc_sel}")
                else:
                    for eng_day, pt_day in dias_mapeamento.items():
                        df_dia_disc = df_disc[df_disc["dia_nome"] == eng_day].copy()
                        if not df_dia_disc.empty:
                            with st.expander(f"📅 {pt_day} — {disc_sel} ({len(df_dia_disc)} Ordens)", expanded=True):
                                render_cards_operacionais(df_dia_disc, f"disc_crd_v6_{disc_sel}_{eng_day}")
else:
    st.warning("⬅️ Banco de dados vazio ou desatualizado. Autentique-se no menu lateral para carregar a planilha.")