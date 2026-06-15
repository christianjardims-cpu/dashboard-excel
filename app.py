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

# ----------------------------------------------------------------------------
# 1. CONFIGURAÇÕES INICIAIS E ARQUITETURA VISUAL (GEMINI SPACE + iOS)
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestão de Manutenção | CMPC",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Forçar destruição de caches antigos do Streamlit injetando novos estados
if "versao_layout" not in st.session_state:
    st.session_state.clear()  # Limpa o estado residual antigo travado
    st.session_state.versao_layout = "4.0_gemini_expanded"

COLOR_MAP = {
    "Realizada": "#30D158",
    "Pendente": "#FF453A",
    "Necessita Reprogramação": "#FF9F0A",
    "Outros": "#8E8E93"
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.06)",
    "Pendente": "rgba(255, 69, 58, 0.06)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.06)"
}

DB_NAME = "data_cmpc.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS apontamentos (
                chave TEXT PRIMARY KEY,
                status TEXT,
                comentario TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()

init_db()

# Injeção de CSS Premium (Estilo iOS Dark + Gemini Glow)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
        background-color: #0A0A0C;
        color: #F5F5F7;
    }
    
    /* Customização dos Expander estilo iOS Container */
    .stCard, div[data-testid="stExpander"] {
        background: rgba(28, 28, 30, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4) !important;
        margin-bottom: 12px;
    }
    
    /* Alinhamento de KPIs */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.03em;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 2. INTEGRAÇÃO REATIVA DE APIS EXTERNAS (WEATHER)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=900)
def obter_previsao_real_guaiba():
    """Consome dados georreferenciados reais da unidade Guaíba-RS via Open-Meteo"""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-30.1139&longitude=-51.3250&current_weather=true"
        response = requests.get(url, timeout=5)
        if response.status_with == 200:
            data = response.json()
            cw = data.get("current_weather", {})
            temp = cw.get("temperature", 22.0)
            ws = cw.get("windspeed", 12.0)
            return {"temp": temp, "vento": ws, "status": "Disponível"}
    except Exception:
        pass
    return {"temp": 21.5, "vento": 10.2, "status": "Padrão Estimado"}

# ----------------------------------------------------------------------------
# 3. INTERFACE OPERACIONAL LATERAL (UPLOAD & AUTH)
# ----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://www.cmpc.com/wp-content/themes/cmpc/img/logo-cmpc.png", width=120)
    st.markdown("<h2 style='font-weight:600; margin-top:0;'>Painel de Controle</h2>", unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Carregar Programação Semanal (CSV/XLSX):", type=["csv", "xlsx"])
    
    st.divider()
    st.markdown("### Autenticação Operacional")
    senha_inserida = st.text_input("Chave de Segurança:", type="password")
    
    is_authenticated = (senha_inserida == "Programacao@2026")
    if is_authenticated:
        st.success("🔒 Acesso de Escrita Liberado")
    else:
        st.info("🔓 Modo de Visualização Ativo")

# ----------------------------------------------------------------------------
# 4. ENGINE DE PROCESSAMENTO DE DADOS COM MAPEAMENTO DINÂMICO
# ----------------------------------------------------------------------------
def extrair_disciplina(ct):
    ct_str = str(ct).upper()
    if "MEC" in ct_str or "LUB" in ct_str or "VUL" in ct_str: return "Mecânica"
    if "ELE" in ct_str: return "Elétrica"
    if "INS" in ct_str or "AUT" in ct_str: return "Instrumentação / Automação"
    if "CAL" in ct_str or "SOL" in ct_str: return "Caldeiraria"
    if "ALP" in ct_str: return "Alpinismo"
    if "AND" in ct_str: return "Andaimes"
    if "CIV" in ct_str: return "Civil"
    return "Outros"

@st.cache_data
def processar_arquivo_manutencao(file_obj):
    if file_obj is None:
        return pd.DataFrame()
    
    nome_arq = file_obj.name
    try:
        # Tenta ler inspecionando se a linha 0 possui metadados vazios comuns em exports SAP
        if nome_arq.endswith(".csv"):
            df_primeiro = pd.read_csv(file_obj, nrows=2)
            skip = 1 if df_primeiro.columns[0] == "" or "PROGRAMAÇÃO" in str(df_primeiro.columns) else 0
            file_obj.seek(0)
            df_temp = pd.read_csv(file_obj, skiprows=skip)
        else:
            df_primeiro = pd.read_excel(file_obj, nrows=2)
            skip = 1 if df_primeiro.columns[0] == "" or "PROGRAMAÇÃO" in str(df_primeiro.columns) else 0
            df_temp = pd.read_excel(file_obj, skiprows=skip)
            
        # Limpar espaços das colunas
        df_temp.columns = [c.strip() for c in df_temp.columns]
        
        # Mapeamento e normalização estrita de colunas mandatórias
        col_mapping = {
            "Chave": "chave", "Área": "area", "Área ": "area", 
            "Centro de Trabalho Op.": "ct_op", "Descrição da Ordem": "descricao",
            "Texto Breve da Operação": "texto_operacao", "Executante": "executante",
            "Data de Início": "data_inicio", "Trabalho": "trabalho", "Status": "status"
        }
        df_temp = df_temp.rename(columns=col_mapping)
        
        required = ["chave", "descricao", "ct_op"]
        for r in required:
            if r not in df_temp.columns:
                # Fallback agressivo se colunas mudarem de nome
                for col_real in df_temp.columns:
                    if r.lower() in col_real.lower() or col_real.lower() in r.lower():
                        df_temp = df_temp.rename(columns={col_real: r})
        
        # Injeção de colunas inteligentes
        if "chave" not in df_temp.columns:
            df_temp["chave"] = df_temp.index.astype(str)
        df_temp["chave"] = df_temp["chave"].astype(str).str.strip()
        
        if "ct_op" in df_temp.columns:
            df_temp["disciplina"] = df_temp["ct_op"].apply(extrair_disciplina)
        else:
            df_temp["disciplina"] = "Outros"
            
        if "area" not in df_temp.columns:
            df_temp["area"] = "GERAL"
        df_temp["area"] = df_temp["area"].fillna("GERAL").astype(str).str.strip()
            
        if "executante" not in df_temp.columns:
            df_temp["executante"] = "Não Alocado"
        df_temp["executante"] = df_temp["executante"].fillna("Não Alocado")
            
        if "trabalho" not in df_temp.columns:
            df_temp["trabalho"] = 8.0
        df_temp["trabalho"] = pd.to_numeric(df_temp["trabalho"], errors="coerce").fillna(8.0)
        
        return df_temp
    except Exception as e:
        st.error(f"Erro crítico no processamento do arquivo estrutural: {e}")
        return pd.DataFrame()

df_base = processar_arquivo_manutencao(uploaded_file)

# Sincronização em tempo real da camada SQLite com o DataFrame em cache
def carregar_dados_persitidos(df_input):
    if df_input.empty:
        return df_input
    
    with sqlite3.connect(DB_NAME) as conn:
        df_db = pd.read_sql_query("SELECT * FROM apontamentos", conn)
        
    if not df_db.empty:
        df_db["chave"] = df_db["chave"].astype(str).str.strip()
        df_merged = df_input.merge(df_db, on="chave", how="left", suffixes=("", "_db"))
        
        if "status_db" in df_merged.columns:
            df_merged["status"] = df_merged["status_db"].fillna(df_merged["status"] if "status" in df_merged.columns else "Pendente")
        if "comentario_db" in df_merged.columns:
            df_merged["comentario"] = df_merged["comentario_db"].fillna("")
            
        df_merged.drop(columns=[c for c in df_merged.columns if "_db" in c], errors="ignore")
        return df_merged
    else:
        if "status" not in df_input.columns:
            df_input["status"] = "Pendente"
        df_input["comentario"] = ""
        return df_input

if not df_base.empty:
    df_foco_completo = carregar_dados_persitidos(df_base)
else:
    df_foco_completo = pd.DataFrame()

# Callback reativo para escrita segura no banco SQLite
def tratar_mudanca_status(chave_id, key_status, key_comentario):
    novo_status = st.session_state.get(key_status)
    novo_comentario = st.session_state.get(key_comentario, "")
    timestamp = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO apontamentos (chave, status, comentario, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chave) DO UPDATE SET
                status=excluded.status,
                comentario=excluded.comentario,
                updated_at=excluded.updated_at
        """, (str(chave_id).strip(), novo_status, novo_comentario, timestamp))
        conn.commit()

# ----------------------------------------------------------------------------
# 5. CORE DA LOGICA DE RENDERIZAÇÃO DOS CARDS OPERACIONAIS (STYLE iOS)
# ----------------------------------------------------------------------------
def render_cards_operacionais(df_cards, escopo_id):
    if df_cards.empty:
        st.info("Nenhuma ordem operacional encontrada para os filtros aplicados.")
        return
        
    for idx, row in df_cards.iterrows():
        ch = str(row["chave"]).strip()
        status_atual = row.get("status", "Pendente")
        if status_atual not in COLOR_MAP:
            status_atual = "Pendente"
            
        cor_borda = COLOR_MAP.get(status_atual, "#8E8E93")
        bg_card = HEX_BG_MAP.get(status_atual, "rgba(255,255,255,0.02)")
        
        desc_ordem = row.get("descricao", "Sem descrição")
        txt_op = row.get("texto_operacao", row.get("texto_breve_da_operação", ""))
        txt_op_exibir = f" | <span style='color:#A1A1AA;'>{txt_op}</span>" if pd.notna(txt_op) and txt_op != "" else ""
        
        ct_exibir = row.get("ct_op", "N/A")
        exec_exibir = row.get("executante", "Não Alocado")
        horas_exibir = row.get("trabalho", 8.0)
        
        # Container HTML com injeção de estilo customizado para cada Card
        card_html = f"""
        <div style="border-left: 5px solid {cor_borda}; background: {bg_card}; padding: 16px; border-radius: 10px; margin-bottom: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.85rem; font-weight: 600; color: {cor_borda}; text-transform: uppercase; letter-spacing: 0.05em;">🔑 CHAVE: {ch}</span>
                <span style="font-size: 0.85rem; background: rgba(255,255,255,0.1); padding: 3px 8px; border-radius: 20px; font-weight:500;">⏱️ {horas_exibir}h Alocadas</span>
            </div>
            <h4 style="margin: 8px 0 4px 0; font-weight: 600; font-size: 1.05rem; color:#FFFFFF;">{desc_ordem}{txt_op_exibir}</h4>
            <div style="margin-top: 6px; font-size: 0.9rem; color: #D1D1D6;">
                <span>🏭 <b>CT:</b> {ct_exibir}</span> &nbsp;&nbsp;•&nbsp;&nbsp; <span>👥 <b>Executante:</b> {exec_exibir}</span>
            </div>
        </div>
        """
        st.html(card_html)
        
        # Zona de interação inteligente do Card (Inputs)
        c_sel, c_txt = st.columns([1, 2])
        
        k_status = f"status_{ch}_{escopo_id}"
        k_comm = f"comm_{ch}_{escopo_id}"
        
        if k_status not in st.session_state:
            st.session_state[k_status] = status_atual
        if k_comm not in st.session_state:
            st.session_state[k_comm] = row.get("comentario", "")
            
        with c_sel:
            st.selectbox(
                "Status da Atividade:",
                options=["Pendente", "Realizada", "Necessita Reprogramação"],
                key=k_status,
                disabled=not is_authenticated,
                on_change=tratar_mudanca_status,
                args=(ch, k_status, k_comm),
                label_visibility="collapsed"
            )
        with c_txt:
            st.text_input(
                "Observações / Impedimentos:",
                placeholder="Insira notas de campo ou motivos de atraso...",
                key=k_comm,
                disabled=not is_authenticated,
                on_change=tratar_mudanca_status,
                args=(ch, k_status, k_comm),
                label_visibility="collapsed"
            )
        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 6. INTERFACE PRINCIPAL - ACESSOS E WIDGETS GLOBAIS
# ----------------------------------------------------------------------------
c_title, c_weather = st.columns([3, 1])
with c_title:
    st.markdown("<h1 style='font-weight: 700; letter-spacing: -0.04em; margin-bottom:0;'>Acompanhamento de Paradas e Rotina</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8E93; font-size:1.1rem; margin-top:4px;'>Unidade Industrial CMPC Guaíba — Monitoramento Integrado</p>", unsafe_allow_html=True)

with c_weather:
    w_data = obter_previsao_real_guaiba()
    st.markdown(f"""
    <div style="background: rgba(44, 44, 46, 0.6); padding: 10px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); text-align: right;">
        <span style="font-size: 0.8rem; color: #8E8E93; text-transform: uppercase;">Clima Guaíba-RS</span><br>
        <span style="font-size: 1.3rem; font-weight:600; color: #5AC8FA;">🌡️ {w_data['temp']}°C</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

if df_foco_completo.empty:
    st.warning("⚠️ Aguardando carregamento do arquivo mestre de manutenção industrial na barra lateral para inicializar os seletores.")
else:
    # ----------------------------------------------------------------------------
    # 7. NOVO INCREMENTO SELETOR DE ÁREA GLOBAL (ACOMPANHAMENTO GERAL)
    # ----------------------------------------------------------------------------
    lista_areas = sorted(list(df_foco_completo["area"].unique()))
    opcoes_area = ["FÁBRICA COMPLETA (Geral)"] + lista_areas
    
    area_selecionada = st.selectbox(
        "📍 Selecione a Área para Visualização e Acompanhamento:",
        options=opcoes_area,
        index=0,
        key="seletor_area_global"
    )
    
    # Filtragem do dataframe base com base no seletor dinâmico
    if area_selecionada == "FÁBRICA COMPLETA (Geral)":
        df_foco = df_foco_completo.copy()
    else:
        df_foco = df_foco_completo[df_foco_completo["area"] == area_selecionada].copy()
        
    st.markdown(f"### Visualização Atual: <span style='color:#30D158;'>{area_selecionada}</span>", unsafe_allow_html=True)

    # ----------------------------------------------------------------------------
    # 8. CÁLCULO DE MÉTRICAS REATIVAS DE PRODUTIVIDADE
    # ----------------------------------------------------------------------------
    total_atividades = len(df_foco)
    realizadas = len(df_foco[df_foco["status"] == "Realizada"])
    pendentes = len(df_foco[df_foco["status"] == "Pendente"])
    reprogramadas = len(df_foco[df_foco["status"] == "Necessita Reprogramação"])
    
    taxa_adesao = (realizadas / total_atividades * 100) if total_atividades > 0 else 0.0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Ordens", f"{total_atividades} un", help="Volume de ordens na área selecionada")
    m2.metric("Concluídas", f"{realizadas} un", "✓", delta_color="normal")
    m3.metric("Reprogramações", f"{reprogramadas} un", "⚠️", delta_color="inverse")
    m4.metric("Adesão à Programação", f"{taxa_adesao:.1f}%", f"{taxa_adesao - 100:.1f}%" if taxa_adesao < 100 else "Meta Atingida")

    st.markdown("<br>", unsafe_allow_html=True)

    # ----------------------------------------------------------------------------
    # 9. ESTRUTURA DE NAVEGAÇÃO DE TRÊS ABAS (MANTIDA ORIGINAL)
    # ----------------------------------------------------------------------------
    aba_dash, aba_oper, aba_disc = st.tabs([
        "📊 Dashboard de Performance", 
        "📋 Cartões de Controle Operacional", 
        "🛠️ Visão por Disciplina Semanal"
    ])

    # --- ABA 1: DASHBOARDS GRÁFICOS ---
    with aba_dash:
        st.markdown("<h2 style='font-weight: 500;'>Indicadores Estratégicos</h2>", unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        
        with g1:
            st.markdown("#### Distribuição de Status Real")
            df_status_count = df_foco["status"].value_counts().reset_index()
            df_status_count.columns = ["Status", "Quantidade"]
            
            fig_status = px.pie(
                df_status_count, names="Status", values="Quantidade",
                hole=0.5, color="Status", color_discrete_map=COLOR_MAP
            )
            fig_status.update_layout(
                margin=dict(t=10, b=10, l=10, r=10), height=300,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#F5F5F7")
            )
            st.plotly_chart(fig_status, use_container_width=True)
            
        with g2:
            st.markdown("#### Distribuição por Disciplina Alocada")
            df_disc_count = df_foco["disciplina"].value_counts().reset_index()
            df_disc_count.columns = ["Disciplina", "Quantidade"]
            
            fig_disc = px.pie(
                df_disc_count, names="Disciplina", values="Quantidade",
                hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_disc.update_layout(
                margin=dict(t=10, b=10, l=10, r=10), height=300,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#F5F5F7")
            )
            st.plotly_chart(fig_disc, use_container_width=True)
            
        st.divider()
        st.markdown("#### Análise de Capacidade de Executantes (Baseado no Excel)")
        
        # Mapeamento dinâmico de todos os executantes do arquivo Excel
        lista_executantes = sorted(list(df_foco["executante"].dropna().unique()))
        exec_sel = st.selectbox("Selecione o Técnico para Análise de Carga:", lista_executantes)
        
        if exec_sel:
            df_exec = df_foco[df_foco["executante"] == exec_sel]
            horas_totais_alocadas = df_exec["trabalho"].sum()
            horas_concluidas = df_exec[df_exec["status"] == "Realizada"]["trabalho"].sum()
            
            c_g1, c_g2 = st.columns([1, 2])
            with c_g1:
                st.metric(f"Horas Alocadas ({exec_sel})", f"{horas_totais_alocadas:.1f} hrs")
                st.metric("Horas Liquidadas", f"{horas_concluidas:.1f} hrs")
            with c_g2:
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=horas_concluidas,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': f"Progresso de Execução - {exec_sel}", 'font': {'color': '#F5F5F7'}},
                    gauge={
                        'axis': {'range': [0, max(horas_totais_alocadas, 1)]},
                        'bar': {'color': "#30D158"},
                        'bgcolor': "rgba(255,255,255,0.05)"
                    }
                ))
                fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', height=220, margin=dict(t=30, b=10))
                st.plotly_chart(fig_gauge, use_container_width=True)

    # --- ABA 2: CARTÕES OPERACIONAIS ---
    with aba_oper:
        st.markdown("<h2 style='font-weight: 500;'>Filtro de Avanço em Campo</h2>", unsafe_allow_html=True)
        
        status_filtro = st.segmented_control(
            "Filtrar Bloco de Trabalho por Status:",
            options=["Todas", "Pendente", "Realizada", "Necessita Reprogramação"],
            default="Todas"
        )
        
        df_oper_cards = df_foco.copy()
        if status_filtro and status_filtro != "Todas":
            df_oper_cards = df_oper_cards[oper_cards["status"] == status_filtro]
            
        render_cards_operacionais(df_oper_cards, "aba_operacional")

    # --- ABA 3: APONTAMENTO POR DISCIPLINA COM DIVISÃO SEMANAL ---
    dias_mapeamento = {
        "Monday": "Segunda-Feira", "Tuesday": "Terça-Feira", "Wednesday": "Quarta-Feira",
        "Thursday": "Quinta-Feira", "Friday": "Sexta-Feira", "Saturday": "Sábado", "Sunday": "Domingo"
    }

    with aba_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina com Divisão Semanal</h2>", unsafe_allow_html=True)
        
        # Mapeamento dinâmico de todas as disciplinas incluídas no arquivo excel
        lista_disciplinas_dinamicas = sorted(list(df_foco["disciplina"].dropna().unique()))
        disc_sel = st.selectbox("Selecione a Disciplina para Filtragem Semanal:", lista_disciplinas_dinamicas, key="c_disc_page_v4_expanded")
        
        if disc_sel:
            df_disc = df_foco[df_foco["disciplina"] == disc_sel].copy()
            df_disc["data_parsed"] = pd.to_datetime(df_disc["data_inicio"], errors="coerce")
            df_disc["dia_nome"] = df_disc["data_parsed"].dt.day_name()
            st.divider()
            
            if df_disc["data_parsed"].isna().all():
                st.warning("As atividades desta disciplina não contêm datas válidas configuradas no arquivo original. Mostrando listagem geral:")
                render_cards_operacionais(df_disc, f"disc_full_list_{disc_sel}")
            else:
                for eng_day, pt_day in dias_mapeamento.items():
                    df_dia_disc = df_disc[df_disc["dia_nome"] == eng_day].copy()
                    if not df_dia_disc.empty:
                        with st.expander(f"📅 {pt_day} — {disc_sel} ({len(df_dia_disc)} Atividades Atribuidas)"):
                            render_cards_operacionais(df_dia_disc, f"disc_day_{eng_day}_{disc_sel}")