import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestão de Manutenção", layout="wide")

st.title("⚙️ Painel de Acompanhamento - Programação Semanal")

# 1. Upload e Persistência do Arquivo (Fica salvo na sessão)
if "df" not in st.session_state:
    st.session_state.df = None

with st.sidebar:
    st.header("Upload da Programação")
    uploaded_file = st.file_uploader(
        "Carregue o arquivo CSV da programação", type=["csv"]
    )

    if uploaded_file is not None:
        # Lendo o arquivo enviado pelo usuário
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.success("Planilha carregada com sucesso!")

# 2. Tela Principal se o arquivo estiver carregado
df = st.session_state.df

if df is not None:
    # Garantir que as colunas de data sejam tratadas corretamente
    if "Data de Início" in df.columns:
        df["Data de Início"] = pd.to_datetime(
            df["Data de Início"], errors="coerce"
        )

    # Filtros na tela inicial (Área e Executante)
    col_filtro1, col_filtro2 = st.columns(2)

    with col_filtro1:
        areas = ["Todas"] + sorted(
            [str(a) for a in df["Área "].dropna().unique()]
        )
        area_selecionada = st.selectbox("Selecione a Área:", areas)

    # Filtrar executantes com base na área selecionada
    if area_selecionada != "Todas":
        df_filtrado = df[df["Área "] == area_selecionada]
    else:
        df_filtrado = df

    with col_filtro2:
        executantes = ["Selecione..."] + sorted(
            [str(e) for e in df_filtrado["Executante"].dropna().unique()]
        )
        executante_selecionado = st.selectbox(
            "Selecione o Executante:", executantes
        )

    # Quando um executante for selecionado
    if executante_selecionado != "Selecione...":
        st.divider()
        st.subheader(
            f"Ordens de Serviço para: {executante_selecionado} (Área: {area_selecionada})"
        )

        df_exec = df_filtrado[df_filtrado["Executante"] == executante_selecionado]

        # Separando por dia da semana (usando a Data de Início)
        dias_semana = df_exec["Data de Início"].dropna().unique()

        # Criação de um espaço para acompanhar o status
        if "status_ordens" not in st.session_state:
            st.session_state.status_ordens = {}

        st.markdown(
            "### Acompanhamento Diário das Atividades"
        )

        # Exibe as ordens detalhadamente
        for index, row in df_exec.iterrows():
            ordem = row["Ordem"]
            descricao = row["Descrição da Ordem"]
            operacao = row["Texto Breve da Operação"]
            duracao = row["Duração"]
            data = (
                str(row["Data de Início"]).split(" ")[0]
                if pd.notna(row["Data de Início"])
                else "Data não definida"
            )

            with st.container(border=True):
                col_d1, col_d2, col_d3 = st.columns(
                    [3, 1, 2]
                )
                with col_d1:
                    st.markdown(
                        f"**Ordem:** {ordem} | **Data:** {data}"
                    )
                    st.markdown(
                        f"*{descricao}* - {operacao}"
                    )
                    st.write(
                        f"⏱️ **Duração (h):** {duracao}"
                    )

                with col_d3:
                    # Ações para definir se foi realizada ou reprogramada
                    status = st.radio(
                        f"Status da Ordem {ordem}",
                        [
                            "Pendente",
                            "Realizada",
                            "Necessita Reprogramação",
                        ],
                        key=f"status_{ordem}",
                        horizontal=True,
                        label_visibility="collapsed",
                    )
                    st.session_state.status_ordens[ordem] = (
                        status
                    )

        # Gráficos e Porcentagens simples
        st.divider()
        st.subheader("📊 Gráficos de Desempenho")

        # Contagem simples de status para o executante
        status_list = list(
            st.session_state.status_ordens.values()
        )
        total = len(status_list)
        realizadas = status_list.count("Realizada")

        if total > 0:
            porcentagem = (realizadas / total) * 100
            st.info(
                f"Taxa de Realização de {executante_selecionado}: {porcentagem:.2f}%"
            )

            # Exemplo de gráfico de rosca/barra com as atividades
            dados_grafico = pd.DataFrame(
                {"Status": status_list}
            ).value_counts()
            st.bar_chart(dados_grafico)
        else:
            st.write(
                "Defina o status das ordens acima para visualizar o gráfico."
            )

else:
    st.warning(
        "⬅️ Por favor, faça o upload do arquivo CSV na barra lateral esquerda para começar."
    )