import pandas as pd
import streamlit as st

# Configuração da página (deve ser a primeira instrução do Streamlit)
st.set_page_config(
    page_title="Meu Dashboard", page_icon="📊", layout="wide"
)

# --- DESIGN: Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Configurações")
    st.write("Faça o upload do seu arquivo Excel abaixo.")
    uploaded_file = st.file_uploader(
        "Selecione o arquivo (.xlsx)", type=["xlsx"]
    )

    st.divider()
    st.write("App adaptado para desktop e mobile.")

# --- DESIGN: Tela Principal ---
st.title("📊 Dashboard Interativo")

if uploaded_file is not None:
    # Ler o arquivo Excel
    df = pd.read_excel(uploaded_file)

    # Criando colunas para métricas (Cartões/Cards)
    total_linhas = len(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total de Registros", value=total_linhas)
    with col2:
        st.metric(label="Outra Métrica", value="Exemplo")
    with col3:
        st.metric(label="Mais uma métrica", value="Exemplo")

    st.markdown("---")  # Linha divisória visual

    # Prévia dos dados
    st.subheader("Prévia dos Dados")
    st.dataframe(df.head(10), use_container_width=True)

    # Gráficos
    st.subheader("Análise Gráfica")
    columns = df.columns.tolist()

    c1, c2 = st.columns(2)
    with c1:
        x_column = st.selectbox("Eixo X:", columns)
    with c2:
        y_column = st.selectbox("Eixo Y (Valores):", columns)

    if pd.api.types.is_numeric_dtype(df[y_column]):
        dados_agrupados = (
            df.groupby(x_column)[y_column].sum().reset_index()
        )
        st.bar_chart(
            dados_agrupados.set_index(x_column),
            use_container_width=True,
        )
    else:
        st.warning("A coluna do Eixo Y precisa conter valores numéricos.")

else:
    # Mensagem inicial quando o app está sem arquivo
    st.info(
        "👋 Bem-vindo! Por favor, utilize o menu na **barra lateral esquerda** para fazer o upload do seu arquivo Excel e começar."
    )