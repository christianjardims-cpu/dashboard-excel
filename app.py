import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Gestão de Manutenção", layout="wide")

# Inicialização do State
if "df" not in st.session_state:
    st.session_state.df = None
if "status_edicoes" not in st.session_state:
    st.session_state.status_edicoes = {}

st.title("⚙️ Painel de Acompanhamento - Programação Semanal")

# 1. Painel Lateral: Upload e Senha
with st.sidebar:
    st.header("Upload da Programação Base")
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
    st.markdown("### Exportação")
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
    # Criação de abas para separar Visão Geral e Execução
    aba_geral, aba_execucao = st.tabs(["📊 Acompanhamento Geral (Dashboard)", "🛠️ Execução / Apontamento"])
    
    # Identificar disciplinas baseadas no Centro de Trabalho / Operação
    if "Centro de Trabalho Op." in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(
            lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")
        )
    else:
        df["Disciplina"] = "Mecânica"

    with aba_geral:
        st.header("Visão Macro de Acompanhamento (Áreas e Disciplinas)")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Progresso Geral por Área")
            # Correção aplicada: "Área " (com espaço) alterado para "Área" (sem espaço)
            resumo_area = df.groupby(["Área", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
            if "Realizada" not in resumo_area: resumo_area["Realizada"] = 0
            if "Pendente" not in resumo_area: resumo_area["Pendente"] = 0
            if "Necessita Reprogramação" not in resumo_area: resumo_area["Necessita Reprogramação"] = 0
            
            resumo_area["Total"] = resumo_area["Realizada"] + resumo_area["Pendente"] + resumo_area["Necessita Reprogramação"]
            resumo_area["% Realizado"] = (resumo_area["Realizada"] / resumo_area["Total"] * 100).round(2)
            
            fig_area = px.bar(resumo_area, x="Área", y="% Realizado", text_auto=True, title="Taxa de Realização por Área", color="Área")
            st.plotly_chart(fig_area, use_container_width=True)
            
        with col_g2:
            st.subheader("Acumulado de Status (Todas as áreas)")
            status_geral = df["Status_Execucao"].value_counts().reset_index()
            status_geral.columns = ["Status", "Quantidade"]
            fig_pizza = px.pie(status_geral, values="Quantidade", names="Status", title="Distribuição de Ordens", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pizza, use_container_width=True)

        st.divider()
        st.subheader("Desempenho por Disciplina (Mecânica, Elétrica, Instrumentação)")
        resumo_disc = df.groupby(["Disciplina", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
        fig_disc = px.bar(resumo_disc, x="Disciplina", y=["Realizada", "Pendente", "Necessita Reprogramação"], title="Status por Disciplina", barmode="group")
        st.plotly_chart(fig_disc, use_container_width=True)

    with aba_execucao:
        st.header("Apontamento e Edição de Status")
        
        # Filtros de Seleção
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            areas_disp = ["Todas"] + sorted([str(a).strip() for a in df["Área"].dropna().unique()])
            area_sel = st.selectbox("Filtrar por Área:", areas_disp)
        with col_f2:
            disciplinas = ["Todas"] + sorted(list(df["Disciplina"].unique()))
            disc_sel = st.selectbox("Filtrar por Disciplina:", disciplinas)
        with col_f3:
            # Tratamento de datas
            df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
            dias_disp = ["Todos"] + sorted([str(d)[:10] for d in df["Data_Inicio_Parsed"].dropna().unique()])
            dia_sel = st.selectbox("Filtrar por Data Específica:", dias_disp)

        # Aplicar filtros
        df_filtrado = df.copy()
        if area_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Área"].astype(str).str.strip() == area_sel]
        if disc_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Disciplina"] == disc_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Data_Inicio_Parsed"].astype(str).str.contains(dia_sel)]

        st.info(f"Mostrando {len(df_filtrado)} ordens de serviço filtradas.")

        # Tabela interativa para edição
        st.write("Edite a coluna 'Status_Execucao' diretamente na tabela abaixo:")
        
        colunas_exibicao = ["Ordem", "Descrição da Ordem", "Texto Breve da Operação", "Executante", "Disciplina", "Data de Início", "Status_Execucao"]
        
        # Validação para garantir que colunas existem
        disponiveis = [c for c in colunas_exibicao if c in df_filtrado.columns]
        df_edicao = df_filtrado[disponiveis].copy()
        
        df_atualizado = st.data_editor(
            df_edicao, 
            num_rows="fixed",
            hide_index=True,
            column_config={
                "Status_Execucao": st.column_config.SelectboxColumn(
                    "Status Atual",
                    help="Altere o status da atividade",
                    width="medium",
                    options=["Pendente", "Realizada", "Necessita Reprogramação"],
                    required=True,
                )
            }
        )
        
        # Sincronizar edições da tabela com o DataFrame principal na sessão
        if st.button("Salvar Alterações no Banco de Dados"):
            for idx, row in df_atualizado.iterrows():
                ordem_linha = row["Ordem"]
                novo_status = row["Status_Execucao"]
                original_idx = df[df["Ordem"] == ordem_linha].index
                if len(original_idx) > 0:
                    st.session_state.df.loc[original_idx, "Status_Execucao"] = novo_status
            st.success("Status salvos com sucesso no banco de dados!")
            st.rerun()

        # Visualização de Gráfico de Pizza Individual do Executante
        st.divider()
        st.subheader("Produtividade Individual por Executante")
        executantes = ["Selecione..."] + sorted([str(e) for e in df_filtrado["Executante"].dropna().unique()])
        exec_sel = st.selectbox("Selecione o Executante para ver o gráfico de pizza:", executantes)
        
        if exec_sel != "Selecione...":
            df_exec = df_filtrado[df_filtrado["Executante"] == exec_sel]
            status_exec = df_exec["Status_Execucao"].value_counts().reset_index()
            status_exec.columns = ["Status", "Quantidade"]
            
            fig_pizza_exec = px.pie(status_exec, values="Quantidade", names="Status", title=f"Progresso de {exec_sel}", hole=0.3)
            st.plotly_chart(fig_pizza_exec)

else:
    st.warning("⬅️ Por favor, insira a senha e faça o upload do arquivo base `.csv` ou `.xlsx` na barra lateral para começar.")