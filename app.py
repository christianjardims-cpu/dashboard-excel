import streamlit as st
import pandas as pd
import sqlite3
import requests
import os

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestão Premium", layout="wide")

# --- BANCO DE DADOS (SQLite) ---
def init_db():
    conn = sqlite3.connect("manutencao.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS ordens 
                      (Ordem TEXT PRIMARY KEY, Descricao TEXT, Status TEXT, 
                       Area TEXT, Data_Inicio DATE, Comentario TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- IMPORTAÇÃO DE DADOS (Para migrar seu CSV antigo) ---
def importar_csv_para_db(uploaded_file):
    df = pd.read_csv(uploaded_file)
    conn = sqlite3.connect("manutencao.db")
    df.to_sql('ordens', conn, if_exists='replace', index=False)
    conn.close()
    st.success("Dados importados com sucesso para o banco!")

# --- TEMPO (GUAÍBA) ---
def get_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=-30.11&longitude=-51.32&daily=temperature_2m_max&timezone=America/Sao_Paulo"
    try:
        data = requests.get(url).json()['daily']
        return [{"dia": data['time'][i], "max": data['temperature_2m_max'][i]} for i in range(3)]
    except: return []

# --- DESIGN (CSS) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #0F0F0F; border-right: 1px solid #282828; }
    .stApp { background-color: #000000; color: #FFFFFF; }
    .weather-card { background: #1A1A1A; padding: 10px; border-radius: 12px; margin-bottom: 8px; border: 1px solid #333; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### ⚙️ Engine Ops")
    if st.button("📊 Dashboard Geral"): st.session_state.page = "Geral"
    if st.button("🛠️ Apontamentos"): st.session_state.page = "Apontamento"
    
    st.markdown("<br><h5>🌤️ Guaíba, RS</h5>", unsafe_allow_html=True)
    for w in get_weather():
        st.markdown(f"<div class='weather-card'><b>{w['dia']}</b>: {w['max']}°C</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    uploaded_file = st.file_uploader("Upload CSV Base", type=["csv"])
    if uploaded_file: importar_csv_para_db(uploaded_file)

# --- NAVEGAÇÃO ---
if 'page' not in st.session_state: st.session_state.page = "Geral"

if st.session_state.page == "Geral":
    st.title("Painel de Performance")
    st.write("Visão macro do seu sistema de manutenção.")

elif st.session_state.page == "Apontamento":
    st.title("Apontamentos de Manutenção")
    conn = sqlite3.connect("manutencao.db")
    df = pd.read_sql("SELECT * FROM ordens", conn)
    conn.close()
    
    if not df.empty:
        busca = st.text_input("🔍 Buscar Ordem")
        if busca: df = df[df['Ordem'].astype(str).str.contains(busca)]
        
        for _, row in df.iterrows():
            cols = st.columns([3, 1, 1])
            with cols[0]: st.write(f"**{row['Ordem']}** - {row['Descricao']}")
            with cols[1]: st.write(row['Status'])
            with cols[2]: st.button("Detalhes", key=row['Ordem'])
            st.divider()
    else:
        st.info("O banco de dados está vazio. Faça o upload do seu CSV na barra lateral.")