import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import os

# Configuração de performance e layout
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="collapsed")

# Mapeamento de Cores
COLOR_MAP = {
    "Realizada": "#30D158",
    "Pendente": "#FF453A",
    "Necessita Reprogramação": "#FF9F0A"
}

# --- FUNÇÕES DE DADOS ---
def carregar_dados():
    if os.path.exists("programacao_atualizada.csv"):
        return pd.read_csv("programacao_atualizada.csv")
    return None

def salvar_e_recarregar(df):
    df.to_csv("programacao_atualizada.csv", index=False)
    st.session_state.df = df
    st.rerun() # Garante a atualização instantânea da interface

# Inicialização do estado
if "df" not in st.session_state:
    st.session_state.df = carregar_dados()

df = st.session_state.df

# --- INTERFACE ---
st.title("⚙️ Painel de Manutenção")

if df is not None:
    # Garantir que a coluna 'Horas' exista (ajuste conforme seu CSV)
    if 'Horas' not in df.columns: df['Horas'] = 4.0 

    tabs = st.tabs(["Acompanhamento Geral", "Apontamento por Executante"])
    
    with tabs[1]:
        executantes = sorted(df["Executante"].dropna().unique())
        exec_sel = st.selectbox("Selecione o Executante:", executantes)
        
        if exec_sel:
            df_exec = df[df["Executante"] == exec_sel]
            realizado = df_exec[df_exec["Status_Execucao"] == "Realizada"]["Horas"].sum()
            total = df_exec["Horas"].sum()
            
            # Gráfico de Horas
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=realizado,
                title={'text': "Horas Dedicadas (Realizado vs Meta)"},
                gauge={'axis': {'range': [0, total if total > 0 else 10]},
                       'bar': {'color': "#30D158"}}
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            # Cards de Edição com Ação Instantânea
            for idx, row in df_exec.iterrows():
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{row['Ordem']}**: {row['Descrição da Ordem']}")
                with cols[1]:
                    novo_status = st.radio(f"st_{idx}", ["Pendente", "Realizada", "Necessita Reprogramação"], 
                                         index=["Pendente", "Realizada", "Necessita Reprogramação"].index(row["Status_Execucao"]),
                                         key=f"r_{idx}", label_visibility="collapsed")
                    
                    if novo_status != row["Status_Execucao"]:
                        df.at[idx, "Status_Execucao"] = novo_status
                        salvar_e_recarregar(df)
else:
    st.error("Arquivo 'programacao_atualizada.csv' não encontrado. Verifique o caminho.")