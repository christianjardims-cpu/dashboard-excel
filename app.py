import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# Configuração da página (Estilo Apple / Minimalista)
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="expanded")

# Injeção de CSS para um design mais limpo e moderno (Estilo iOS/macOS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    /* Aplicação da fonte globalmente */
    html, body, [class*="st-emotion-cache"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Fundo da página estilo Apple (cinza muito claro) */
    .stApp {
        background-color: #F5F5F7;
        color: #1D1D1F;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid rgba(0, 0, 0, 0.08);
    }
    
    /* Cartões / Containers */
    [data-testid="stVerticalBlock"] > div > div.stContainer {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid rgba(0, 0, 0, 0.08) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        padding: 16px;
    }
    
    /* Botões */
    .stButton > button {
        background-color: #007AFF;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stButton > button:hover {
        background-color: #0056B3;
        border: none;
    }
    
    /* Tabs */
    [data-testid="stTabs"] button {
        font-weight: 500;
        border-radius: 8px 8px 0 0;
    }
    
</style>
""", unsafe_allow_html=True)

# Inicialização do State
if "df" not in st.session_state:
    st.session_state.df = None

st.markdown("<h1 style='font-weight: 600; letter-spacing: -0.5px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #86868B; margin-top: -10px;'>Programação Semanal de Manutenção</p>", unsafe_allow_html=True)

# 1. Painel Lateral: Upload e Senha
with st.sidebar:
    st.markdown("<h3 style='font-weight: 500;'>Upload da Programação Base</h3>", unsafe_allow_html=True)
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
                st.success("Base carregada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
    elif senha_inserida != "":
        st.error("Senha incorreta.")

    st.divider()
    st.markdown("<h3 style='font-weight: 500;'>Exportação</h3>", unsafe_allow_html=True)
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

    # Filtro nativo para as áreas solicitadas
    df["Área"] = df["Área"].astype(str).str.strip()
    areas_foco = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]
    df_foco = df[df["Área"].isin(areas_foco)].copy()

    aba_geral, aba_execucao = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento Diário"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Progresso Geral por Área")
            resumo_area = df_foco.groupby(["Área", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
            for s in ["Realizada", "Pendente", "Necessita Reprogramação"]:
                if s not in resumo_area: resumo_area[s] = 0
            
            resumo_area["Total"] = resumo_area["Realizada"] + resumo_area["Pendente"] + resumo_area["Necessita Reprogramação"]
            resumo_area["% Realizado"] = (resumo_area["Realizada"] / resumo_area["Total"] * 100).round(2)
            
            fig_area = px.bar(resumo_area, x="Área", y="% Realizado", text_auto=True, title="", color="Área", color_discrete_sequence=["#007AFF", "#5856D6"])
            fig_area.update_layout(margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_area, use_container_width=True)
            
        with col_g2:
            st.markdown("#### Acumulado de Status (Áreas Selecionadas)")
            status_geral = df_foco["Status_Execucao"].value_counts().reset_index()
            status_geral.columns = ["Status", "Quantidade"]
            fig_pizza = px.pie(status_geral, values="Quantidade", names="Status", title="", hole=0.5, color_discrete_sequence=["#34C759", "#FF9500", "#FF3B30"])
            fig_pizza.update_layout(margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_pizza, use_container_width=True)

        st.divider()
        st.markdown("#### Desempenho por Disciplina")
        resumo_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
        fig_disc = px.bar(resumo_disc, x="Disciplina", y=["Realizada", "Pendente", "Necessita Reprogramação"], barmode="group", color_discrete_sequence=["#007AFF", "#FF9500", "#FF3B30"])
        fig_disc.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_disc, use_container_width=True)

    with aba_execucao:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento de Ordens por Executante</h2>", unsafe_allow_html=True)
        
        executantes = ["Selecione..."] + sorted([str(e) for e in df["Executante"].dropna().unique()])
        exec_sel = st.selectbox("Escolha o Executante:", executantes)
        
        if exec_sel != "Selecione...":
            df_exec = df[df["Executante"] == exec_sel]
            
            dias_da_semana_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
            
            for dia in dias_da_semana_ordem:
                df_dia = df_exec[df_exec["Data_Inicio_Parsed"].dt.day_name() == dia]
                
                if not df_dia.empty:
                    st.divider()
                    st.markdown(f"<h4 style='font-weight: 500; color: #007AFF;'>📅 {dias_pt[dia]}</h4>", unsafe_allow_html=True)
                    
                    for idx, row in df_dia.iterrows():
                        ordem = row["Ordem"]
                        desc = row["Descrição da Ordem"]
                        operacao = row["Texto Breve da Operação"]
                        status_atual = row["Status_Execucao"]
                        
                        # Mapear status atual para index do radio
                        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
                        idx_status = 0
                        if status_atual in opcoes_status:
                            idx_status = opcoes_status.index(status_atual)
                        
                        with st.container():
                            col_info, col_status = st.columns([4, 2])
                            with col_info:
                                st.markdown(f"**Ordem:** {ordem} | **Área:** {row['Área']}")
                                st.markdown(f"*{desc}* - {operacao}")
                            
                            with col_status:
                                novo_status = st.radio(
                                    f"Status {ordem}_{idx}",
                                    options=opcoes_status,
                                    index=idx_status,
                                    horizontal=False,
                                    key=f"radio_{ordem}_{idx}"
                                )
                                
                                # Salvar alteração na sessão imediatamente
                                if novo_status != status_atual:
                                    st.session_state.df.loc[idx, "Status_Execucao"] = novo_status

else:
    st.warning("⬅️ Por favor, insira a senha e faça o upload do arquivo base `.csv` ou `.xlsx` no menu lateral para inicializar.")