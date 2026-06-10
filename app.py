import pandas as pd
import streamlit as st
import plotly.express as px
import os
from datetime import datetime

# Configuração da página - Layout Wide
st.set_page_config(page_title="Gestão de Manutenção Premium", layout="wide", initial_sidebar_state="expanded")

# Injeção de CSS - Tema Escuro Premium / Glassmorphism (Visual de Alto Nível)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="st-emotion-cache"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #0F0F11;
        color: #FFFFFF;
    }
    
    [data-testid="stSidebar"] {
        background-color: #1C1C1E;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Cartões Premium (Glassmorphism sutil) */
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
    
    p, label, div[data-testid="stMarkdownContainer"] {
        color: #EBEBEB;
    }
    
    h1, h2, h3, h4 {
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }
    
    /* Selectbox e Radio Buttons Premium */
    div[data-testid="stselectbox"] > div > div {
        background-color: #2C2C2E;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        color: white;
    }
    
    div.row-widget.stRadio > div {
        background-color: #1C1C1E;
        padding: 12px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Botões Premium */
    .stButton > button {
        background: linear-gradient(135deg, #0A84FF, #5E5CE6);
        color: white;
        border-radius: 12px;
        border: none;
        font-weight: 600;
        padding: 12px 24px;
        box-shadow: 0 4px 15px rgba(10, 132, 255, 0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(10, 132, 255, 0.5);
    }
    
    hr {
        border-color: rgba(255, 255, 255, 0.08);
    }
    
</style>
""", unsafe_allow_html=True)

# Persistência de Dados no Servidor
ARQUIVO_SALVO = "programacao_atualizada.csv"

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try:
            return pd.read_csv(ARQUIVO_SALVO)
        except Exception:
            return None
    return None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

# Inicialização do State a partir do servidor
if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados()

st.markdown("<h1 style='font-weight: 700; font-size: 2.2rem;'>⚙️ Painel de Acompanhamento Premium</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #8E8E93; margin-top: -10px; font-size: 1.1rem;'>Gestão de Manutenção Semanal - Alta Performance</p>", unsafe_allow_html=True)
st.divider()

# 1. Painel Lateral: Upload e Senha
with st.sidebar:
    st.markdown("<h3 style='font-weight: 600;'>Upload da Programação Base</h3>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Senha de acesso:", type="password")
    
    if senha_inserida == "Programacao@2026":
        uploaded_file = st.file_uploader("Carregue o arquivo (.csv ou .xlsx)", type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                if nome_arquivo.endswith(".csv"):
                    df_temp = pd.read_csv(uploaded_file, skiprows=1)
                elif nome_arquivo.endswith(".xlsx"):
                    df_temp = pd.read_excel(uploaded_file, skiprows=1)
                
                # Limpeza básica de colunas
                df_temp.columns = df_temp.columns.str.strip()
                
                # Adiciona coluna de status padrão se não existir
                if "Status_Execucao" not in df_temp.columns:
                    df_temp["Status_Execucao"] = "Pendente"
                
                st.session_state.df = df_temp
                salvar_dados(df_temp)
                st.success("Base carregada e salva com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
    elif senha_inserida != "":
        st.error("Senha incorreta.")

    st.divider()
    st.markdown("<h3 style='font-weight: 600;'>Exportação</h3>", unsafe_allow_html=True)
    if st.session_state.df is not None:
        csv = st.session_state.df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar Planilha Atualizada",
            data=csv,
            file_name='programacao_atualizada.csv',
            mime='text/csv',
        )

# 2. Fluxo Principal da Aplicação
df = st.session_state.df

if df is not None:
    # Identificar disciplinas baseadas no Centro de Trabalho / Operação
    if "Centro de Trabalho Op." in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(
            lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
        )
    else:
        df["Disciplina"] = "Mecânica"

    # Tratamento de datas
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Dia_da_Semana"] = df["Data_Inicio_Parsed"].dt.day_name()

    # Filtro nativo para as áreas de foco solicitadas
    df["Área"] = df["Área"].astype(str).str.strip()
    areas_foco = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]
    df_foco = df[df["Área"].isin(areas_foco)].copy()

    aba_geral, aba_execucao = st.tabs(["📊 Acompanhamento Geral (Dashboard)", "🛠️ Apontamento Diário (Individual)"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 600; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        # Gráficos em formato de Pizza (Donut chart premium) para Aderência / Status
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Aderência / Distribuição de Ordens (Áreas Foco)")
            status_geral = df_foco["Status_Execucao"].value_counts().reset_index()
            status_geral.columns = ["Status", "Quantidade"]
            
            fig_pizza_geral = px.pie(status_geral, values="Quantidade", names="Status", hole=0.5, color_discrete_sequence=["#30D158", "#FF9F0A", "#FF453A"])
            fig_pizza_geral.update_layout(template="plotly_dark", margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_geral.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_geral, use_container_width=True)
            
        with col_g2:
            st.markdown("#### Aderência por Disciplina (Mecânica, Elétrica, Instrumentação)")
            resumo_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
            
            # Para visualização em Pizza, agregamos o total realizado vs pendente/reprogramado das áreas
            total_por_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().reset_index(name="Qtd")
            disc_sel_pizza = st.selectbox("Selecione a Disciplina para visualizar em Pizza:", sorted(list(df_foco["Disciplina"].unique())))
            
            df_filtrado_pizza = total_por_disc[total_por_disc["Disciplina"] == disc_sel_pizza]
            fig_pizza_disc = px.pie(df_filtrado_pizza, values="Qtd", names="Status_Execucao", title=f"Aderência: {disc_sel_pizza}", hole=0.5, color_discrete_sequence=["#0A84FF", "#FF9F0A", "#FF453A"])
            fig_pizza_disc.update_layout(template="plotly_dark", margin=dict(t=40, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_disc.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_disc, use_container_width=True)

    with aba_execucao:
        st.markdown("<h2 style='font-weight: 600;'>Apontamento de Ordens Diárias por Executante</h2>", unsafe_allow_html=True)
        
        executantes = ["Selecione..."] + sorted([str(e) for e in df["Executante"].dropna().unique()])
        exec_sel = st.selectbox("Escolha o Executante:", executantes)
        
        if exec_sel != "Selecione...":
            df_exec = df[df["Executante"] == exec_sel].copy()
            
            # Indicador de Progresso (Gráfico de Pizza Individual)
            st.divider()
            st.markdown(f"#### Progresso de Execução: {exec_sel}")
            status_exec = df_exec["Status_Execucao"].value_counts().reset_index()
            status_exec.columns = ["Status", "Quantidade"]
            fig_pizza_exec = px.pie(status_exec, values="Quantidade", names="Status", hole=0.5, color_discrete_sequence=["#30D158", "#FF9F0A", "#FF453A"])
            fig_pizza_exec.update_layout(template="plotly_dark", height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            fig_pizza_exec.update_traces(textinfo='percent+label', textfont_size=12)
            st.plotly_chart(fig_pizza_exec)

            st.divider()
            st.markdown("#### Divisão Semanal de Atividades")
            
            dias_da_semana_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
            
            for dia in dias_da_semana_ordem:
                df_dia = df_exec[df_exec["Data_Inicio_Parsed"].dt.day_name() == dia]
                
                if not df_dia.empty:
                    st.markdown(f"<h5 style='font-weight: 600; color: #0A84FF; margin-top: 15px;'>📅 {dias_pt[dia]}</h5>", unsafe_allow_html=True)
                    
                    for idx, row in df_dia.iterrows():
                        ordem = row["Ordem"]
                        desc = row["Descrição da Ordem"]
                        operacao = row["Texto Breve da Operação"]
                        status_atual = row["Status_Execucao"]
                        
                        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
                        idx_status = 0
                        if status_atual in opcoes_status:
                            idx_status = opcoes_status.index(status_atual)
                        
                        with st.container():
                            col_info, col_status = st.columns([4, 2])
                            with col_info:
                                st.markdown(f"**Ordem:** `{ordem}` | **Área:** {row['Área']}")
                                st.markdown(f"*{desc}* <br> Operação: {operacao}", unsafe_allow_html=True)
                            
                            with col_status:
                                novo_status = st.radio(
                                    f"Status_{ordem}_{idx}",
                                    options=opcoes_status,
                                    index=idx_status,
                                    horizontal=False,
                                    key=f"radio_{ordem}_{idx}",
                                    label_visibility="collapsed"
                                )
                                
                                if novo_status != status_atual:
                                    # Atualiza sessão e salva no arquivo local imediatamente
                                    st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
                                    salvar_dados(st.session_state.df)

else:
    st.warning("⬅️ Por favor, insira a senha e faça o upload do arquivo base no menu lateral para inicializar o painel.")