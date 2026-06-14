import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os

# Mapeamento de Cores
COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A"}

def update_status(idx):
    novo_valor = st.session_state[f"r_{idx}"]
    st.session_state.df.at[idx, "Status_Execucao"] = novo_valor
    st.session_state.df.to_csv("programacao_atualizada.csv", index=False)

# --- FUNÇÃO PARA O NOVO GRÁFICO DE HORAS ---
def renderizar_grafico_horas(df_exec):
    total_previsto = df_exec["Horas"].sum() if "Horas" in df_exec.columns else 40
    total_realizado = df_exec[df_exec["Status_Execucao"] == "Realizada"]["Horas"].sum() if "Horas" in df_exec.columns else 0
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total_realizado,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Horas Dedicadas"},
        gauge={'axis': {'range': [0, total_previsto]}, 'bar': {'color': "#30D158"}}
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

# --- LÓGICA DA ABA DE EXECUTANTE (INTEGRADA) ---
# (Coloque este bloco dentro do seu 'with tab2:' ou 'with aba_exec_ind:')

if exec_sel != "Selecione...":
    df_exec = df_foco[df_foco["Executante"] == exec_sel].copy()
    
    # Cria duas colunas para os gráficos lado a lado
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        # Seu gráfico de Pizza original
        status_exec = df_exec["Status_Execucao"].value_counts().reset_index()
        fig_pizza = px.pie(status_exec, values="count", names="Status_Execucao", color="Status_Execucao", color_discrete_map=COLOR_MAP)
        st.plotly_chart(fig_pizza, use_container_width=True)
        
    with col_graf2:
        # O novo gráfico de Horas
        fig_horas = renderizar_grafico_horas(df_exec)
        st.plotly_chart(fig_horas, use_container_width=True)

    # Listagem de tarefas abaixo dos gráficos...