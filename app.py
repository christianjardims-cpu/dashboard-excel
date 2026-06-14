import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import os

# Configuração: Sidebar "auto" permite que você a abra quando precisar
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="auto")

# Mapeamento de Cores
COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A"}

# Função de atualização (Callback)
def update_status(idx, new_val):
    st.session_state.df.at[idx, "Status_Execucao"] = new_val
    st.session_state.df.to_csv("programacao_atualizada.csv", index=False)

# Carregamento
if "df" not in st.session_state:
    if os.path.exists("programacao_atualizada.csv"):
        st.session_state.df = pd.read_csv("programacao_atualizada.csv")
    else:
        st.session_state.df = None

# --- SIDEBAR (Upload e Senha) ---
with st.sidebar:
    st.header("Administração")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        st.session_state.df = pd.read_csv(uploaded_file)
        st.session_state.df.to_csv("programacao_atualizada.csv", index=False)
        st.success("Dados carregados!")

# --- TELA PRINCIPAL ---
st.title("⚙️ Painel de Manutenção")

if st.session_state.df is not None:
    df = st.session_state.df
    if 'Horas' not in df.columns: df['Horas'] = 4.0 

    tab1, tab2 = st.tabs(["Geral", "Apontamento por Executante"])
    
    with tab2:
        executantes = sorted(df["Executante"].dropna().unique())
        exec_sel = st.selectbox("Selecione o Executante:", executantes)
        
        if exec_sel:
            df_exec = df[df["Executante"] == exec_sel]
            realizado = df_exec[df_exec["Status_Execucao"] == "Realizada"]["Horas"].sum()
            meta = df_exec["Horas"].sum()
            
            # Gráfico
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=realizado,
                title={'text': "Horas Dedicadas (Realizado vs Meta)"},
                gauge={'axis': {'range': [0, meta]}, 'bar': {'color': "#30D158"}}
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            # Edição Instantânea com Callback
            for idx, row in df_exec.iterrows():
                cols = st.columns([3, 1])
                cols[0].markdown(f"**{row['Ordem']}**: {row['Descrição da Ordem']}")
                cols[1].radio("Status", ["Pendente", "Realizada", "Necessita Reprogramação"], 
                              index=["Pendente", "Realizada", "Necessita Reprogramação"].index(row["Status_Execucao"]),
                              key=f"r_{idx}", label_visibility="collapsed",
                              on_change=update_status, args=(idx, st.session_state[f"r_{idx}"]))
else:
    st.info("Por favor, abra a barra lateral (setinha no canto superior esquerdo) e faça o upload do arquivo.")