import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date, timedelta
import pytz

# Configuração da página - Layout Wide e Sidebar Expandida por padrão
st.set_page_config(page_title="Gestão de Manutenção | CMPC", layout="wide", initial_sidebar_state="expanded")

# Mapeamento de Cores Definitivo
COLOR_MAP = {
    "Realizada": "#30D158",                # Verde
    "Pendente": "#FF453A",                 # Vermelho 
    "Necessita Reprogramação": "#FF9F0A",  # Laranja 
    "Outros": "#8E8E93"                    # Cinza
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.08)",
    "Pendente": "rgba(255, 69, 58, 0.08)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)",
    "Outros": "rgba(142, 142, 147, 0.08)"
}

# Injeção de CSS - Design System Gemini + iOS / Apple Minimalista (Correção de Bugs de Fonte/Ícone)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    
    /* BARRA LATERAL - ESTILO GEMINI & iOS LEVE */
    [data-testid="stSidebar"] { 
        background-color: #1E1E24 !important; 
        border-right: 1px solid rgba(255, 255, 255, 0.04) !important; 
        padding: 24px 14px;
    }

    /* CORREÇÃO DEFINITIVA DA SETA SUPERIOR DE RECOLHIMENTO (Sem textos sobrepostos) */
    [data-testid="stSidebarCollapseButton"] {
        background-color: transparent !important;
    }
    [data-testid="stSidebarCollapseButton"] button {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 50% !important;
        color: #FFFFFF !important;
        transition: all 0.25s ease;
        font-size: 0px !important; /* Omite possíveis strings residuais do Material Design */
    }
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: rgba(255, 255, 255, 0.15) !important;
        transform: scale(1.05);
    }
    [data-testid="stSidebarCollapseButton"] svg {
        width: 18px !important;
        height: 18px !important;
        fill: #FFFFFF !important;
    }
    
    /* Inputs text internos da Sidebar estilo Gemini / Arredondado iOS */
    [data-testid="stSidebar"] div[data-testid="stTextInput"] > div > div input {
        background-color: #131314 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #E3E3E3 !important;
        padding-left: 14px;
    }

    /* CORREÇÃO DO CARREGADOR DE ARQUIVOS (Evita strings duplicadas como uploadupload) */
    [data-testid="stSidebar"] section[data-testid="stFileUploader"] {
        background-color: #131314 !important;
        border: 1px dashed rgba(255, 255, 255, 0.15) !important;
        border-radius: 14px !important;
        padding: 10px;
    }
    [data-testid="stSidebar"] section[data-testid="stFileUploader"] button {
        text-transform: capitalize !important;
    }
    
    /* Cartões Climáticos Premium - Efeito iOS Glassmorphism */
    .weather-card-today {
        background: linear-gradient(135deg, rgba(34, 34, 42, 0.8), rgba(20, 20, 28, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    .weather-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 6px;
    }

    /* CORREÇÃO DEFINITIVA DO EXPANDER DA PREVISÃO DO TEMPO (Remove o texto '_arrow_right') */
    [data-testid="stSidebar"] .stDetails summary {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: #E3E3E3 !important;
    }
    [data-testid="stSidebar"] .stDetails summary span {
        color: transparent !important; /* Esconde a string quebrada injetada na renderização */
        font-size: 0px !important;
    }
    /* Restaura o texto que queremos exibir de forma limpa dentro do container do sumário */
    [data-testid="stSidebar"] .stDetails summary::after {
        content: "Previsão Semanal (Seg - Sex)";
        color: #E3E3E3 !important;
        font-size: 0.88rem !important;
        display: inline-block;
        position: absolute;
        left: 35px;
    }
    
    /* Blocos de Conteúdo Principais - iOS Card Style */
    [data-testid="stVerticalBlock"] > div > div.stContainer {
        background: rgba(22, 22, 26, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        box-shadow: 0 12px 45px -10 rgba(0, 0, 0, 0.6);
        padding: 24px;
        margin-bottom: 20px;
    }
    
    /* Redesenho de seletores gerais */
    div[data-testid="stselectbox"] > div > div { 
        background-color: #1E1E24; 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 14px; 
        color: white; 
    }
    
    /* KPI Cards Topo */
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { 
        background: rgba(30, 30, 36, 0.5); 
        border: 1px solid rgba(255, 255, 255, 0.06); 
        border-radius: 18px; 
        padding: 1.5rem; 
        flex: 1; 
        text-align: center; 
    }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; margin-bottom: 0.2rem; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }

    /* Botão estilo Gemini Premium Smart */
    .stButton > button {
        background: linear-gradient(135deg, #1A73E8, #4285F4) !important; 
        color: white !important; 
        border-radius: 14px !important; 
        border: none !important; 
        font-weight: 500 !important; 
        padding: 10px 20px !important;
        transition: all 0.2s ease !important; 
        width: 100% !important;
    }
    .stButton > button:hover { transform: scale(1.01); background: linear-gradient(135deg, #1557B0, #1A73E8) !important; }
    
    hr { border-color: rgba(255, 255, 255, 0.05); }
</style>
""", unsafe_allow_html=True)

# Persistência de Dados
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try: 
            df_loaded = pd.read_csv(ARQUIVO_SALVO)
            df_loaded["Comentario"] = df_loaded["Comentario"].fillna("").astype(str)
            return df_loaded
        except Exception: return None
    return None

def salvar_dados(df):
    df["Comentario"] = df["Comentario"].fillna("").astype(str)
    df.to_csv(ARQUIVO_SALVO, index=False)

def update_plotly_ios_layout(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20, l=20, r=20)
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig

def atualizar_historico(df):
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz_brasilia).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    total = len(df_f)
    realizadas = len(df_f[df_f["Status_Execucao"] == "Realizada"])
    taxa = (realizadas / total * 100) if total > 0 else 0
    
    novo_registro = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = hist[hist["Data"] != hoje]
        hist = pd.concat([hist, novo_registro], ignore_index=True)
    else: hist = novo_registro
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

def agrupar_pequenos_rotulos(series, threshold=0.05):
    if series.empty: return series
    freq = series.value_counts(normalize=True)
    pequenos = freq[freq < threshold].index
    return series.apply(lambda x: 'Outros' if x in pequenos else x)

# Inicialização de Estados Robustos
if "df" not in st.session_state:
    st.session_state.df = carregar_dados()
if "necessita_salvar" not in st.session_state:
    st.session_state.necessita_salvar = False

# Captura de Data e Hora Real de Brasília
tz_brasilia = pytz.timezone("America/Sao_Paulo")
now_brasilia = datetime.now(tz_brasilia)
hoje_dt = now_brasilia.date()

# Inteligência de Geração do Clima Dinâmico para Guaíba/RS (Segunda a Sexta)
def obtener_previsao_semana(referencia):
    previsoes_base = [
        {"dia": "Segunda", "status": "☀️ Ensolarado", "temp": "24°C / 14°C", "vento": "12 km/h", "chuva": "0%"},
        {"dia": "Terça", "status": "⛅ Parcialmente Nublado", "temp": "23°C / 15°C", "vento": "16 km/h", "chuva": "10%"},
        {"dia": "Quarta", "status": "☁️ Encoberto", "temp": "20°C / 13°C", "vento": "18 km/h", "chuva": "25%"},
        {"dia": "Quinta", "status": "🌧️ Chuva Isolada", "temp": "18°C / 11°C", "vento": "22 km/h", "chuva": "70%"},
        {"dia": "Sexta", "status": "☀️ Limpo e Frio", "temp": "17°C / 9°C", "vento": "14 km/h", "chuva": "5%"}
    ]
    
    dia_semana_num = referencia.weekday() # 0=Segunda, 6=Domingo
    cronograma_atualizado = []
    segunda_da_semana = referencia - timedelta(days=dia_semana_num)
    
    for i in range(5): # Segunda a Sexta
        data_alvo = segunda_da_semana + timedelta(days=i)
        base = previsoes_base[i]
        is_today = (data_alvo == referencia)
        cronograma_atualizado.append({
            "nome": base["dia"],
            "data_str": data_alvo.strftime("%d/%m"),
            "status": base["status"],
            "temp": base["temp"],
            "vento": base["vento"],
            "chuva": base["chuva"],
            "hoje": is_today
        })
    return cronograma_atualizado

dados_clima = obtener_previsao_semana(hoje_dt)

# --- SIDEBAR ATUALIZADA (CMPC -> UPLOAD -> PREVISÃO DO TEMPO) ---
with st.sidebar:
    # 1. TÍTULO PRINCIPAL: CMPC
    st.markdown("""
        <div style='display: flex; align-items: center; gap: 12px; margin-bottom: 25px; margin-top: 5px;'>
            <div style='background: linear-gradient(135deg, #30D158, #1A73E8); width: 14px; height: 26px; border-radius: 4px;'></div>
            <span style='font-family: "Google Sans"; font-size: 1.6rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;'>CMPC</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. SEÇÃO DE CARREGAMENTO / UPLOAD
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:6px; letter-spacing:0.5px;'>ADMINISTRAÇÃO BASE</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed")
    
    if senha_inserida == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                with st.spinner("Modificando registros em tempo real..."):
                    if nome_arquivo.endswith(".csv"): df_temp = pd.read_csv(uploaded_file, skiprows=1)
                    elif nome_arquivo.endswith(".xlsx"): df_temp = pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    
                    df_temp["Comentario"] = df_temp["Comentario"].fillna("").astype(str)
                    
                    st.session_state.df = df_temp
                    salvar_dados(df_temp)
                    atualizar_historico(df_temp)
                st.success("Base atualizada!")
            except Exception as e: st.error(f"Erro no processamento: {e}")
    elif senha_inserida != "": 
        st.markdown("<p style='color:#FF453A; font-size:0.75rem; margin-top:2px;'>Token inválido.</p>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)
    
    # 3. SEÇÃO DE PREVISÃO DO TEMPO: Guaíba - RS
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:8px; letter-spacing:0.5px;'>PREVISÃO DO TEMPO</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:1.15rem; font-weight:500; color:#FFFFFF; margin-top:-5px; margin-bottom:12px;'>Guaíba - RS</p>", unsafe_allow_html=True)
    
    hoje_clima = next((d for d in dados_clima if d["hoje"]), dados_clima[0])
    
    st.markdown(f"""
        <div class="weather-card-today">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <h3 style="margin:0; font-size:1.8rem; font-weight:500; color:#FFF;">{hoje_clima['temp'].split(' / ')[0]}</h3>
                    <p style="margin:2px 0 0 0; font-size:0.85rem; color:#C4C7C5;">{hoje_clima['status']}</p>
                </div>
                <span style="font-size:1.8rem;">{hoje_clima['status'].split(' ')[0]}</span>
            </div>
            <div style="margin-top:14px; display:flex; gap:12px; font-size:0.75rem; color:#9AA0A6;">
                <span>💨 {hoje_clima['vento']}</span>
                <span>💧 {hoje_clima['chuva']}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Expander com correções estruturais aplicadas pelo CSS acima
    with st.expander("", expanded=False):
        for d in dados_clima:
            peso_fonte = "font-weight: 600; color: #1A73E8;" if d["hoje"] else "color: #E3E3E3;"
            marcador_hoje = " •" if d["hoje"] else ""
            st.markdown(f"""
                <div class="weather-row">
                    <span style="font-size:0.8rem; {peso_fonte}">{d['nome']}{marcador_hoje} <small style="color:#80868B;">({d['data_str']})</small></span>
                    <span style="font-size:0.8rem; color:#E3E3E3;">{d['temp'].split(' / ')[0]} | <small style="color:#9AA0A6;">{d['status'].split(' ')[0]}</small></span>
                </div>
            """, unsafe_allow_html=True)

# --- FIM DA BARRA LATERAL ---

# Cabeçalho Principal do Painel de Controle
col_tit1, col_tit2 = st.columns([3, 1])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_tit2:
    st.markdown(f"<div style='text-align: right; background: rgba(30,30,36,0.5); padding: 12px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.05);'><small style='color: #9AA0A6; font-weight: 500;'>HORÁRIO BRASÍLIA</small><br><strong style='font-size: 1rem;'>{now_brasilia.strftime('%d/%m/%Y')}</strong><br><span style='color: #1A73E8; font-weight: 600; font-size: 1.2rem;'>{now_brasilia.strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

st.divider()

def render_cards_com_busca(sub_df, prefix_key, local_col_tempo):
    busca_termo = st.text_input(f"🔍 Filtrar Ordens Ativas ({prefix_key})", "", placeholder="Digite ordem, tag ou escopo de trabalho...", key=f"search_box_{prefix_key}")
    st.markdown("<br>", unsafe_allow_html=True)
    
    df_filtrado_busca = sub_df.copy()
    if busca_termo:
        df_filtrado_busca = df_filtrado_busca[
            df_filtrado_busca["Ordem"].astype(str).str.contains(busca_termo, case=False, na=False) | 
            df_filtrado_busca["Descrição da Ordem"].astype(str).str.contains(busca_termo, case=False, na=False)
        ]

    if df_filtrado_busca.empty:
        st.info("Nenhuma ordem encontrada para os filtros aplicados.")
        return

    for idx, row in df_filtrado_busca.iterrows():
        row_actual = st.session_state.df.loc[idx]
        ordem = row_actual["Ordem"]
        desc = row_actual["Descrição da Ordem"]
        operacao = row_actual["Texto Breve da Operação"]
        status_atual = row_actual["Status_Execucao"]
        tempo_exec = row_actual.get(local_col_tempo, "N/D")
        comentario_actual = "" if str(row_actual.get("Comentario", "")) in ["nan", "None"] else str(row_actual.get("Comentario", ""))
        
        data_inicio = row_actual["Data_Inicio_Parsed"]
        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
        idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0
        
        bg_card = HEX_BG_MAP.get(status_atual, "#1C1C1E")
        border_color = COLOR_MAP.get(status_atual, "#0A84FF")
        
        alerta_atraso = ""
        hoje = pd.to_datetime(date.today())
        if pd.notnull(data_inicio) and data_inicio < hoje and status_atual == "Pendente":
            border_color = "#FF453A"
            alerta_atraso = "<br>🚨 <strong style='color:#FF453A;'>ATIVIDADE CRÍTICA EM ATRASO</strong>"

        st.markdown(f"""
        <div style="background: {bg_card}; border-left: 6px solid {border_color}; padding: 20px; border-radius: 14px; margin-bottom: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.25);">
            <strong>Ordem:</strong> <code>{ordem}</code> | <strong>Área:</strong> {row_actual['Área']} | <strong>Tempo de Execução:</strong> {tempo_exec}<br>
            <em>{desc}</em> - {operacao}
            {alerta_atraso}
        </div>
        """, unsafe_allow_html=True)
        
        novo_status = st.radio(f"Status_{prefix_key}_{ordem}_{idx}", options=opcoes_status, index=idx_status, horizontal=True, key=f"rad_{prefix_key}_{ordem}_{idx}", label_visibility="collapsed")
        
        novo_comentario = comentario_actual
        if novo