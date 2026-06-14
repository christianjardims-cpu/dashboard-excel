import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os

# Configuração da página
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="auto")

# Mapeamento de Cores
COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A"}

# Função de atualização (Callback)
def update_status(idx):
    st.session_state.df.at[idx, "Status_Execucao"] = st.session_state[f"r_{idx}"]
    st.session_state.df.to_csv("programacao_atualizada.csv", index=False)

# Inicialização
if "df" not in st.session_state:
    if os.path.exists("programacao_atualizada.csv"):
        st.session_state.df = pd.read_csv("programacao_atualizada.csv")
    else:
        st.session_state.df = None

# --- SIDEBAR ---
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
    # Garante que a coluna Horas exista
    if 'Horas' not in df.columns: df['Horas'] = 4.0 

    tab1, tab2 = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante"])
    
    with tab2:
        executantes = ["Selecione..."] + sorted(df["Executante"].dropna().unique().tolist())
        exec_sel = st.selectbox("Escolha o Executante:", executantes, key="exec_sel_combo")
        
        if exec_sel != "Selecione...":
            df_exec = df[df["Executante"] == exec_sel].copy()
            
            # Gráficos lado a lado
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown("#### Status das Tarefas")
                status_exec = df_exec["Status_Execucao"].value_counts().reset_index()
                fig_pizza = px.pie(status_exec, values="count", names="Status_Execucao", 
                                   color="Status_Execucao", color_discrete_map=COLOR_MAP)
                st.plotly_chart(fig_pizza, use_container_width=True)
                
            with col_graf2:
                st.markdown("#### Horas Dedicadas (Realizado vs Meta)")
                total_previsto = df_exec["Horas"].sum()
                total_realizado = df_exec[df_exec["Status_Execucao"] == "Realizada"]["Horas"].sum()
                
                fig_horas = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=total_realizado,
                    gauge={'axis': {'range': [0, total_previsto if total_previsto > 0 else 10]}, 
                           'bar': {'color': "#30D158"}}
                ))
                fig_horas.update_layout(height=250)
                st.plotly_chart(fig_horas, use_container_width=True)
            
            st.divider()
            
            # Listagem de tarefas com rádio instantâneo
            for idx, row in df_exec.iterrows():
                cols = st.columns([3, 1])
                cols[0].markdown(f"**{row['Ordem']}**: {row['Descrição da Ordem']}")
                cols[1].radio(
                    "Status", ["Pendente", "Realizada", "Necessita Reprogramação"], 
                    index=["Pendente", "Realizada", "Necessita Reprogramação"].index(row["Status_Execucao"]),
                    key=f"r_{idx}", 
                    label_visibility="collapsed",
                    on_change=update_status, 
                    args=(idx,)
                )
else:
    st.info("Abra a barra lateral (setinha no canto superior esquerdo) e faça o upload do arquivo para começar.")