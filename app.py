import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestão de Manutenção", layout="wide")

st.title("⚙️ Painel de Acompanhamento - Programação Semanal")

# 1. Upload e Persistência do Arquivo
if "df" not in st.session_state:
    st.session_state.df = None
if "status_ordens" not in st.session_state:
    st.session_state.status_ordens = {}

with st.sidebar:
    st.header("Upload da Programação")
    uploaded_file = st.file_uploader(
        "Carregue o arquivo da programação (.csv ou .xlsx)", type=["csv", "xlsx"]
    )

    if uploaded_file is not None:
        nome_arquivo = uploaded_file.name.lower()
        try:
            # skiprows=1 utilizado para ignorar a linha de título do relatório extraído do SAP
            if nome_arquivo.endswith(".csv"):
                df = pd.read_csv(uploaded_file, skiprows=1)
            elif nome_arquivo.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file, skiprows=1)
                
            st.session_state.df = df
            st.session_state.status_ordens = {}  # Limpa o estado dos status ao carregar nova planilha
            st.success("Planilha carregada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")

# 2. Tela Principal se o arquivo estiver carregado
df = st.session_state.df

if df is not None:
    # Limpar espaços em branco dos nomes de colunas (ex: "Área " vira "Área")
    df.columns = df.columns.str.strip()

    # Verificar se a coluna Área existe
    if "Área" not in df.columns:
        st.error("A coluna 'Área' não foi encontrada. Verifique se o arquivo carregado está correto.")
    else:
        # Garantir que as colunas de data sejam tratadas corretamente
        if "Data de Início" in df.columns:
            df["Data de Início"] = pd.to_datetime(df["Data de Início"], errors="coerce")

        # Filtros na tela inicial
        col_filtro1, col_filtro2 = st.columns(2)

        with col_filtro1:
            areas = ["Todas"] + sorted([str(a) for a in df["Área"].dropna().unique()])
            area_selecionada = st.selectbox("Selecione a Área:", areas)

        # Filtrar executantes com base na área selecionada
        if area_selecionada != "Todas":
            df_filtrado = df[df["Área"] == area_selecionada]
        else:
            df_filtrado = df

        with col_filtro2:
            executantes = ["Selecione..."] + sorted([str(e) for e in df_filtrado["Executante"].dropna().unique()])
            executante_selecionado = st.selectbox("Selecione o Executante:", executantes)

        # Quando um executante for selecionado
        if executante_selecionado != "Selecione...":
            st.divider()
            st.subheader(f"Ordens de Serviço para: {executante_selecionado} (Área: {area_selecionada})")

            df_exec = df_filtrado[df_filtrado["Executante"] == executante_selecionado]

            st.markdown("### Acompanhamento Diário das Atividades")

            # Exibe as ordens detalhadamente
            for index, row in df_exec.iterrows():
                ordem = row.get("Ordem", "N/D")
                descricao = row.get("Descrição da Ordem", "Sem descrição")
                operacao = row.get("Texto Breve da Operação", "")
                duracao = row.get("Duração", "0")
                data_inicio = row.get("Data de Início")
                
                data = str(data_inicio).split(" ")[0] if pd.notna(data_inicio) else "Data não definida"

                with st.container(border=True):
                    col_d1, col_d2, col_d3 = st.columns([3, 1, 2])
                    with col_d1:
                        st.markdown(f"**Ordem:** {ordem} | **Data:** {data}")
                        st.markdown(f"*{descricao}* - {operacao}")
                        st.write(f"⏱️ **Duração (h):** {duracao}")

                    with col_d3:
                        # O índice na chave (key) garante que cada linha seja única
                        status = st.radio(
                            f"Status da Ordem {ordem} {index}",
                            ["Pendente", "Realizada", "Necessita Reprogramação"],
                            key=f"status_{ordem}_{index}",
                            horizontal=True,
                            label_visibility="collapsed"
                        )
                        st.session_state.status_ordens[f"{ordem}_{index}"] = status

            # Gráficos e Porcentagens simples
            st.divider()
            st.subheader("📊 Gráficos de Desempenho")

            status_list = list(st.session_state.status_ordens.values())
            total = len(status_list)
            realizadas = status_list.count("Realizada")

            if total > 0:
                porcentagem = (realizadas / total) * 100
                st.info(f"Taxa de Realização de {executante_selecionado}: {porcentagem:.2f}%")

                dados_grafico = pd.DataFrame({"Status": status_list}).value_counts()
                st.bar_chart(dados_grafico)
            else:
                st.write("Defina o status das ordens acima para visualizar o gráfico.")

else:
    st.warning("⬅️ Por favor, faça o upload do arquivo da sua programação na barra lateral esquerda para começar.")