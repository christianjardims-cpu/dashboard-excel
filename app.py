import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date
import pytz

# Configuração da página - Layout Wide
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="expanded")

# Mapeamento de Cores Exatas e Limpas (Tema Dark)
COLOR_MAP = {
    "Realizada": "#30D158",                # Verde (Suave)
    "Pendente": "#FF453A",                 # Vermelho (Acento)
    "Necessita Reprogramação": "#FF9F0A"   # Amarelo/Laranja
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.15)",
    "Pendente": "rgba(255, 69, 58, 0.15)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.15)"
}

# Injeção de CSS 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0F0F11; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #1C1C1E; border-right: 1px solid rgba(255, 255, 255, 0.05); padding: 24px 16px; }
    [data-testid="stVerticalBlock"] > div > div.stContainer {
        background: rgba(28, 28, 30, 0.6);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        padding: 24px;
        color: #FFFFFF;
        margin-bottom: 16px;
    }
    p, label, div[data-testid="stMarkdownContainer"] { color: #EBEBEB; }
    h1, h2, h3, h4, h5 { color: #FFFFFF; letter-spacing: -0.5px; }
    div[data-testid="stselectbox"] > div > div { background-color: #2C2C2E; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; color: white; }
    .stButton > button {
        background: linear-gradient(135deg, #0A84FF, #5E5CE6); color: white; border-radius: 12px; border: none; font-weight: 600; padding: 12px 24px;
        box-shadow: 0 4px 15px rgba(10, 132, 255, 0.3); transition: all 0.3s ease; width: 100%;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(10, 132, 255, 0.5); }
    hr { border-color: rgba(255, 255, 255, 0.08); }
</style>
""", unsafe_allow_html=True)

# Persistência de Dados
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try: return pd.read_csv(ARQUIVO_SALVO)
        except Exception: return None
    return None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

def atualizar_historico(df):
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz_brasilia).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    total = len(df_f)
    realizadas = len(df_f[df_f["Status_Execucao"] == "Realizada"])
    taxa = (realizadas / total * 100) if total > 0 else 0
    
    novo_registro = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = hist[hist["Data"] != hoje]
        hist = pd.concat([hist, novo_registro], ignore_index=True)
    else: hist = novo_registro
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados()

# Cabeçalho com Relógio Brasília
col_tit1, col_tit2 = st.columns([3, 1])
with col_tit1:
    st.markdown("<h1 style='font-weight: 700; font-size: 2.2rem;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8E93; margin-top: -10px; font-size: 1.1rem;'>Gestão de Manutenção Semanal</p>", unsafe_allow_html=True)
with col_tit2:
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    now_brasilia = datetime.now(tz_brasilia)
    st.markdown(f"<div style='text-align: right; background: rgba(255,255,255,0.05); padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);'><small style='color: #8E8E93; font-weight: 600; letter-spacing: 0.5px;'>HORÁRIO DE BRASÍLIA</small><br><strong>{now_brasilia.strftime('%d/%m/%Y')}</strong><br><span style='color: #0A84FF; font-weight: 700; font-size: 1.2rem;'>{now_brasilia.strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("<h2 style='font-weight: 600; font-size: 1.3rem; margin-bottom: 15px;'>Área de Administração</h2>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Senha de acesso:", type="password")
    
    if senha_inserida == "Programacao@2026":
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Selecione a programação (.csv ou .xlsx)", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                if nome_arquivo.endswith(".csv"): df_temp = pd.read_csv(uploaded_file, skiprows=1)
                elif nome_arquivo.endswith(".xlsx"): df_temp = pd.read_excel(uploaded_file, skiprows=1)
                df_temp.columns = df_temp.columns.str.strip()
                if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                st.session_state.df = df_temp
                salvar_dados(df_temp)
                atualizar_historico(df_temp)
                st.success("Base atualizada com sucesso!")
            except Exception as e: st.error(f"Erro ao ler arquivo: {e}")
    elif senha_inserida != "": st.error("Senha incorreta.")

df = st.session_state.df

def render_cards_com_busca(sub_df, prefix_key):
    busca = st.text_input(f"🔍 Pesquisar Ordem ou Descrição ({prefix_key})", "", placeholder="Digite o número da Ordem ou palavra-chave...")
    if busca:
        sub_df = sub_df[sub_df["Ordem"].astype(str).str.contains(busca, case=False, na=False) | 
                         sub_df["Descrição da Ordem"].astype(str).str.contains(busca, case=False, na=False)]

    for idx, row in sub_df.iterrows():
        # Pega a linha atualizada diretamente do st.session_state.df para garantir sincronia
        row_actual = st.session_state.df.loc[idx]
        ordem = row_actual["Ordem"]
        desc = row_actual["Descrição da Ordem"]
        operacao = row_actual["Texto Breve da Operação"]
        status_atual = row_actual["Status_Execucao"]
        tempo_exec = row_actual.get(col_tempo, "N/D")
        comentario_atual = row_actual.get("Comentario", "")
        data_inicio = row_actual["Data_Inicio_Parsed"]
        
        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
        idx_status = 0
        if status_atual in opcoes_status: idx_status = opcoes_status.index(status_atual)
        
        bg_card = HEX_BG_MAP.get(status_atual, "#1C1C1E")
        border_color = COLOR_MAP.get(status_atual, "#0A84FF")
        
        alerta_atraso = ""
        hoje = pd.to_datetime(date.today())
        if pd.notnull(data_inicio) and data_inicio < hoje and status_atual == "Pendente":
            border_color = "#FF453A"
            alerta_atraso = "<br>🚨 <strong style='color:#FF453A;'>ATIVIDADE CRÍTICA EM ATRASO</strong>"

        st.markdown(f"""
        <div style="background: {bg_card}; border-left: 6px solid {border_color}; padding: 18px; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
            <strong>Ordem:</strong> <code>{ordem}</code> | <strong>Área:</strong> {row_actual['Área']} | <strong>Tempo de Execução:</strong> {tempo_exec}<br>
            <em>{desc}</em> - {operacao}
            {alerta_atraso}
        </div>
        """, unsafe_allow_html=True)
        
        novo_status = st.radio(f"Status_{prefix_key}_{ordem}_{idx}", options=opcoes_status, index=idx_status, horizontal=True, key=f"rad_{prefix_key}_{ordem}_{idx}", label_visibility="collapsed")
        
        novo_comentario = comentario_atual
        if novo_status in ["Pendente", "Necessita Reprogramação"]:
            motivos = ["Selecione motivo...", "Falta de Material", "Falta de Acesso", "Mão de Obra", "Outros"]
            motivo_sel = st.selectbox(f"Motivo / Justificativa ({ordem})", motivos, key=f"mot_{prefix_key}_{idx}")
            if motivo_sel != "Selecione motivo...":
                novo_comentario = st.text_input(f"Detalhes adicionais ({ordem})", value=comentario_atual if "Selecione" not in comentario_atual else "", key=f"det_{prefix_key}_{idx}")
                novo_comentario = f"{motivo_sel}: {novo_comentario}"
        elif novo_status == "Realizada":
            if comentario_atual:
                st.markdown(f"<small>💬 <i>Histórico: {comentario_atual}</i></small>", unsafe_allow_html=True)
            novo_comentario = ""

        if novo_status != status_atual or novo_comentario != comentario_atual:
            st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
            st.session_state.df.loc[idx, "Comentario"] = novo_comentario
            salvar_dados(st.session_state.df)
            atualizar_historico(st.session_state.df)
            st.rerun()

if df is not None:
    if "Centro de Trabalho Op." in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica"))
    else: df["Disciplina"] = "Mecânica"

    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Dia_da_Semana"] = df["Data_Inicio_Parsed"].dt.day_name()
    df["Área"] = df["Área"].astype(str).str.strip()
    
    df_foco = df[df["Área"].isin(AREAS_FOCO)].copy()

    col_tempo = "Tempo de Execução" if "Tempo de Execução" in df.columns else ("Tempo" if "Tempo" in df.columns else None)
    if col_tempo is None:
        df["Tempo_Execucao_Ficticio"] = "4h"
        col_tempo = "Tempo_Execucao_Ficticio"

    aba_geral, aba_exec_ind, aba_exec_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 600; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Aderência / Distribuição Geral (Áreas Foco)</h4>", unsafe_allow_html=True)
            status_geral = df_foco["Status_Execucao"].value_counts().reset_index()
            status_geral.columns = ["Status", "Quantidade"]
            
            fig_pizza_geral = px.pie(status_geral, values="Quantidade", names="Status", hole=0.5, color="Status", color_discrete_map=COLOR_MAP)
            fig_pizza_geral.update_layout(template="plotly_dark", margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_geral.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_geral, use_container_width=True)
            
        with col_g2:
            st.markdown("<h4>Aderência por Disciplina</h4>", unsafe_allow_html=True)
            total_por_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().reset_index(name="Qtd")
            disc_sel_pizza = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["Disciplina"].unique())), key="pizza_disc_drop")
            
            df_filtrado_pizza = total_por_disc[total_por_disc["Disciplina"] == disc_sel_pizza]
            fig_pizza_disc = px.pie(df_filtrado_pizza, values="Qtd", names="Status_Execucao", hole=0.5, color="Status_Execucao", color_discrete_map=COLOR_MAP)
            fig_pizza_disc.update_layout(template="plotly_dark", margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_disc.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_disc, use_container_width=True)

        st.divider()
        st.markdown("<h3>📋 Relatório Final de Apontamentos (Áreas de Foco)</h3>", unsafe_allow_html=True)
        
        resumo_areas_final = df_foco.groupby(["Área", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
        if "Realizada" not in resumo_areas_final: resumo_areas_final["Realizada"] = 0
        if "Necessita Reprogramação" not in resumo_areas_final: resumo_areas_final["Necessita Reprogramação"] = 0
        if "Pendente" not in resumo_areas_final: resumo_areas_final["Pendente"] = 0
        
        for idx, row in resumo_areas_final.iterrows():
            col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 2])
            with col_a1: st.markdown(f"**Área:** {row['Área']}")
            with col_a2: st.markdown(f"✅ **Realizadas:** <span style='color:{COLOR_MAP['Realizada']}; font-weight:700;'>{row['Realizada']}</span>", unsafe_allow_html=True)
            with col_a3: st.markdown(f"⚠️ **Reprogramadas:** <span style='color:{COLOR_MAP['Necessita Reprogramação']}; font-weight:700;'>{row['Necessita Reprogramação']}</span>", unsafe_allow_html=True)
            with col_a4: st.markdown(f"🔴 **Pendentes:** <span style='color:{COLOR_MAP['Pendente']}; font-weight:700;'>{row['Pendente']}</span>", unsafe_allow_html=True)
            st.divider()

        st.markdown("<br><h3>📈 Indicador de Evolução Semanal (Taxa de Realização)</h3>", unsafe_allow_html=True)
        if os.path.exists(ARQUIVO_HISTORICO):
            hist_df = pd.read_csv(ARQUIVO_HISTORICO)
            fig_evolucao = px.line(hist_df, x="Data", y="Taxa", markers=True, 
                                   labels={"Taxa": "Taxa de Realização (%)", "Data": "Data"})
            fig_evolucao.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("O gráfico de linha de evolução será formado após a primeira atualização ou carga de dados.")

    with aba_exec_ind:
        st.markdown("<h2 style='font-weight: 600;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        executantes_validos = sorted([str(e) for e in df_foco["Executante"].dropna().unique()])
        executantes = ["Selecione..."] + executantes_validos
        exec_sel = st.selectbox("Escolha o Executante da Área:", executantes, key="exec_sel_combo")
        
        if exec_sel != "Selecione...":
            df_exec = df_foco[df_foco["Executante"] == exec_sel].copy()
            st.divider()
            st.markdown(f"<h4>Aderência de Execução: {exec_sel}</h4>", unsafe_allow_html=True)
            status_exec = df_exec["Status_Execucao"].value_counts().reset_index()
            status_exec.columns = ["Status", "Quantidade"]
            fig_pizza_exec = px.pie(status_exec, values="Quantidade", names="Status", hole=0.5, color="Status", color_discrete_map=COLOR_MAP)
            fig_pizza_exec.update_layout(template="plotly_dark", height=280, margin=dict(t=10, b=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_exec.update_traces(textinfo='percent+label', textfont_size=12)
            st.plotly_chart(fig_pizza_exec)

            st.divider()
            st.markdown("<h4>Divisão Semanal de Atividades</h4>", unsafe_allow_html=True)
            dias_da_semana_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
            
            for dia in dias_da_semana_ordem:
                df_dia = df_exec[df_exec["Data_Inicio_Parsed"].dt.day_name() == dia]
                if not df_dia.empty:
                    st.markdown(f"<h5 style='font-weight: 600; color: #0A84FF; margin-top: 15px;'>📅 {dias_pt[dia]}</h5>", unsafe_allow_html=True)
                    render_cards_com_busca(df_dia, f"ind_{dia}")

    with aba_exec_disc:
        st.markdown("<h2 style='font-weight: 600;'>Apontamento por Disciplina (Caldeira e Energia)</h2>", unsafe_allow_html=True)
        # Mostra apenas as disciplinas das áreas de foco (Caldeira e Energia)
        disciplinas_disp = sorted(list(df_foco["Disciplina"].dropna().unique()))
        disc_sel = st.selectbox("Selecione a Disciplina:", disciplinas_disp, key="disc_sel_combo_main")
        
        if disc_sel:
            df_disc = df_foco[df_foco["Disciplina"] == disc_sel].copy()
            st.markdown(f"<h4>Ordens de Serviço - {disc_sel}</h4>", unsafe_allow_html=True)
            render_cards_com_busca(df_disc, f"disc_{disc_sel}")

else: 
    st.warning("⬅️ Por favor, insira a senha e faça o upload do arquivo base no menu lateral para inicializar o painel.")