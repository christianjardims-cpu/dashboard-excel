import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date
import pytz

# Configuração da página - Layout Wide e Sidebar Recolhida
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="collapsed")

# Mapeamento de Cores
COLOR_MAP = {
    "Realizada": "#30D158",
    "Pendente": "#FF453A",
    "Necessita Reprogramação": "#FF9F0A",
    "Outros": "#8E8E93"
}

# --- FUNÇÕES AUXILIARES ---
def salvar_dados(df):
    df.to_csv("programacao_atualizada.csv", index=False)

def atualizar_app():
    st.rerun() # Força a atualização imediata da interface

# --- LÓGICA DE DADOS ---
if "df" not in st.session_state:
    st.session_state.df = pd.read_csv("programacao_atualizada.csv") if os.path.exists("programacao_atualizada.csv") else None

df = st.session_state.df

# --- RENDERIZAÇÃO DOS CARDS ---
def render_cards_com_busca(sub_df, prefix_key):
    for idx, row in sub_df.iterrows():
        ordem = row["Ordem"]
        status_atual = row["Status_Execucao"]
        
        # Estilo do Card
        st.markdown(f"""
        <div style="background: rgba(28, 28, 30, 0.6); border-left: 6px solid {COLOR_MAP.get(status_atual)}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
            <strong>Ordem: {ordem}</strong> - {row['Descrição da Ordem']}
        </div>
        """, unsafe_allow_html=True)
        
        # Botão instantâneo
        novo_status = st.radio(f"st_{prefix_key}_{idx}", ["Pendente", "Realizada", "Necessita Reprogramação"], 
                               index=["Pendente", "Realizada", "Necessita Reprogramação"].index(status_atual), 
                               horizontal=True, key=f"radio_{idx}")
        
        if novo_status != status_atual:
            st.session_state.df.at[idx, "Status_Execucao"] = novo_status
            salvar_dados(st.session_state.df)
            atualizar_app() # Atualiza a cor instantaneamente

# --- ABA DE EXECUTANTE COM GRÁFICO DE HORAS ---
if df is not None:
    # Garantir que temos uma coluna de horas (exemplo: 'Horas_Previstas')
    if 'Horas' not in df.columns: df['Horas'] = 4.0 # Fallback
    
    # ... (código das abas) ...
    with st.expander("📊 Acompanhamento de Horas do Executante"):
        df_exec = df[df["Executante"] == exec_sel]
        total_previsto = df_exec["Horas"].sum()
        total_realizado = df_exec[df_exec["Status_Execucao"] == "Realizada"]["Horas"].sum()
        
        fig_horas = go.Figure(go.Indicator(
            mode="gauge+number",
            value=total_realizado,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Horas Dedicadas (Realizado vs Meta)"},
            gauge={'axis': {'range': [0, total_previsto]},
                   'bar': {'color': "#30D158"}}
        ))
        st.plotly_chart(fig_horas, use_container_width=True)