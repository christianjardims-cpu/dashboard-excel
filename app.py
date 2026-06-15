import pandas as pd, streamlit as st, plotly.express as px, plotly.graph_objects as go, os, pytz
from datetime import datetime, date, timedelta

st.set_page_config(page_title="Gestão de Manutenção | CMPC", layout="wide", initial_sidebar_state="expanded")

COLOR_MAP = {"Realizada": "#30D158", "Pendente": "#FF453A", "Necessita Reprogramação": "#FF9F0A", "Outros": "#8E8E93"}
HEX_BG_MAP = {"Realizada": "rgba(48, 209, 88, 0.08)", "Pendente": "rgba(255, 69, 58, 0.08)", "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)", "Outros": "rgba(142, 142, 147, 0.08)"}

# CSS Ajustado: Mantém os ícones de colapso de menu (arrows) visíveis e funcionais
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Google Sans', sans-serif; }
    .stApp { background-color: #0E0E11; color: #E3E3E3; }
    [data-testid="stSidebar"] { background-color: #1E1E24 !important; border-right: 1px solid rgba(255, 255, 255, 0.04) !important; padding: 24px 14px; }
    
    /* Correção das setas (arrows) do menu lateral */
    [data-testid="stSidebarCollapseButton"] button { background-color: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 50% !important; color: #FFFFFF !important; transition: all 0.25s ease; width: 32px; height: 32px; display: flex !important; align-items: center; justify-content: center; }
    [data-testid="stSidebarCollapseButton"] button:hover { background-color: rgba(255, 255, 255, 0.15) !important; transform: scale(1.05); }
    [data-testid="stSidebarCollapseButton"] svg { width: 18px !important; height: 18px !important; fill: #FFFFFF !important; color: #FFFFFF !important; display: block !important; }
    
    .stFileUploader button span, .stDetails summary span { font-size: 0px !important; color: transparent !important; display: none !important; }
    [data-testid="stSidebar"] div[data-testid="stTextInput"] > div > div input { background-color: #131314 !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 12px !important; color: #E3E3E3 !important; padding-left: 14px; }
    [data-testid="stSidebar"] section[data-testid="stFileUploader"] { background-color: #131314 !important; border: 1px dashed rgba(255, 255, 255, 0.15) !important; border-radius: 14px !important; padding: 10px; }
    .weather-card-today { background: linear-gradient(135deg, rgba(34, 34, 42, 0.8), rgba(20, 20, 28, 0.95)); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 16px; padding: 16px; margin-bottom: 12px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
    .weather-row { display: flex; justify-content: space-between; align-items: center; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 8px 12px; margin-bottom: 6px; }
    [data-testid="stSidebar"] .stDetails summary { font-size: 0.95rem !important; font-weight: 500 !important; color: #E3E3E3 !important; position: relative; }
    [data-testid="stSidebar"] .stDetails summary::after { content: "Previsão Semanal (Seg - Sex)"; color: #E3E3E3 !important; font-size: 0.88rem !important; display: inline-block; }
    .ios-clock-widget { background: linear-gradient(145deg, #1E1E24, #141419); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 14px 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); display: flex; flex-direction: column; gap: 8px; }
    .ios-clock-top { display: flex; justify-content: space-between; align-items: center; }
    .ios-time { font-size: 1.6rem; font-weight: 700; color: #0A84FF; font-variant-numeric: tabular-nums; letter-spacing: -0.5px; }
    .ios-date-badge { background: rgba(10, 132, 255, 0.12); color: #0A84FF; font-size: 0.75rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; text-transform: uppercase; }
    .ios-clock-bottom { display: flex; justify-content: space-between; font-size: 0.8rem; color: #9AA0A6; }
    .ios-progress-container { background: rgba(255, 255, 255, 0.05); border-radius: 4px; height: 5px; width: 100%; overflow: hidden; margin-top: 2px; }
    .ios-progress-bar { background: linear-gradient(90deg, #0A84FF, #30D158); height: 100%; border-radius: 4px; }
    [data-testid="stVerticalBlock"] > div > div.stContainer { background: rgba(22, 22, 26, 0.7); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05) !important; box-shadow: 0 12px 45px -10 rgba(0, 0, 0, 0.6); padding: 24px; margin-bottom: 20px; }
    div[data-testid="stselectbox"] > div > div { background-color: #1E1E24; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 14px; color: white; }
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { background: rgba(30, 30, 36, 0.5); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 18px; padding: 1.5rem; flex: 1; text-align: center; }
    .kpi-value { font-size: 2.3rem; font-weight: 700; color: #1A73E8; margin-bottom: 0.2rem; }
    .kpi-label { font-size: 0.85rem; color: #9AA0A6; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 500; }
    .stButton > button { background: linear-gradient(135deg, #1A73E8, #4285F4) !important; color: white !important; border-radius: 14px !important; border: none !important; font-weight: 500 !important; padding: 10px 20px !important; transition: all 0.2s ease !important; width: 100% !important; }
    .stButton > button:hover { transform: scale(1.01); background: linear-gradient(135deg, #1557B0, #1A73E8) !important; }
    hr { border-color: rgba(255, 255, 255, 0.05); }
</style>""", unsafe_allow_html=True)

ARQUIVO_SALVO, ARQUIVO_HISTORICO, AREAS_FOCO = "programacao_atualizada.csv", "historico_semanal.csv", ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

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
    fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20, l=20, r=20))
    fig.update_xaxes(showgrid=False, zeroline=False).update_yaxes(showgrid=False, zeroline=False)
    return fig

def atualizar_historico(df):
    tz_br = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(tz_br).strftime('%Y-%m-%d')
    df_f = df[df["Área"].astype(str).str.strip().isin(AREAS_FOCO)]
    taxa = (len(df_f[df_f["Status_Execucao"] == "Realizada"]) / len(df_f) * 100) if len(df_f) > 0 else 0
    novo_reg = pd.DataFrame([{"Data": hoje, "Taxa": taxa}])
    if os.path.exists(ARQUIVO_HISTORICO):
        hist = pd.read_csv(ARQUIVO_HISTORICO)
        hist = pd.concat([hist[hist["Data"] != hoje], novo_reg], ignore_index=True)
    else: hist = novo_reg
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

def agrupar_pequenos_rotulos(series, threshold=0.05):
    if series.empty: return series
    freq = series.value_counts(normalize=True)
    pequenos = freq[freq < threshold].index
    return series.apply(lambda x: 'Outros' if x in pequenos else x)

if "df" not in st.session_state: st.session_state.df = carregar_dados()
if "necessita_salvar" not in st.session_state: st.session_state.necessita_salvar = False

tz_brasilia = pytz.timezone("America/Sao_Paulo")
now_brasilia = datetime.now(tz_brasilia)
hoje_dt = now_brasilia.date()
numero_semana = now_brasilia.isocalendar()[1]
pct_dia_decorrido = min(100.0, max(0.0, ((now_brasilia.hour * 60 + now_brasilia.minute) / 1440.0) * 100))

def obtener_previsao_semana(referencia):
    previsoes_base = [
        {"dia": "Segunda", "status": "☀️ Ensolarado", "temp": "24°C / 14°C", "vento": "12 km/h", "chuva": "0%"},
        {"dia": "Terça", "status": "⛅ Parcialmente Nublado", "temp": "23°C / 15°C", "vento": "16 km/h", "chuva": "10%"},
        {"dia": "Quarta", "status": "☁️ Encoberto", "temp": "20°C / 13°C", "vento": "18 km/h", "chuva": "25%"},
        {"dia": "Quinta", "status": "🌧️ Chuva Isolada", "temp": "18°C / 11°C", "vento": "22 km/h", "chuva": "70%"},
        {"dia": "Sexta", "status": "☀️ Limpo e Frio", "temp": "17°C / 9°C", "vento": "14 km/h", "chuva": "5%"}
    ]
    dia_semana_num = referencia.weekday()
    cronograma_atualizado = []
    segunda_da_semana = referencia - timedelta(days=dia_semana_num)
    for i in range(5):
        data_alvo = segunda_da_semana + timedelta(days=i)
        base = previsoes_base[i]
        cronograma_atualizado.append({**base, "data_str": data_alvo.strftime("%d/%m"), "hoje": (data_alvo == referencia), "nome": base["dia"]})
    return cronograma_atualizado

dados_clima = obtener_previsao_semana(hoje_dt)

with st.sidebar:
    st.markdown("<div style='display: flex; align-items: center; gap: 12px; margin-bottom: 25px; margin-top: 5px;'><div style='background: linear-gradient(135deg, #30D158, #1A73E8); width: 14px; height: 26px; border-radius: 4px;'></div><span style='font-family: \"Google Sans\"; font-size: 1.6rem; font-weight: 700; color: #FFFFFF; letter-spacing: -0.5px;'>CMPC</span></div>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:6px; letter-spacing:0.5px;'>ADMINISTRAÇÃO BASE</p>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Chave operacional:", type="password", placeholder="Insira a senha...", label_visibility="collapsed")
    if senha_inserida == "Programacao@2026":
        uploaded_file = st.file_uploader("Upload da Programação:", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                with st.spinner("Modificando registros..."):
                    df_temp = pd.read_csv(uploaded_file, skiprows=1) if nome_arquivo.endswith(".csv") else pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    df_temp["Comentario"] = df_temp["Comentario"].fillna("").astype(str)
                    st.session_state.df = df_temp
                    salvar_dados(df_temp)
                    atualizar_historico(df_temp)
                st.success("Base updated!")
            except Exception as e: st.error(f"Erro no processamento: {e}")
    elif senha_inserida != "": st.markdown("<p style='color:#FF453A; font-size:0.75rem; margin-top:2px;'>Token inválido.</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 18px 0;'>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:0.75rem; color:#9AA0A6; text-transform:uppercase; font-weight:600; margin-bottom:8px; letter-spacing:0.5px;'>PREVISÃO DO TEMPO</p><p style='font-size:1.15rem; font-weight:500; color:#FFFFFF; margin-top:-5px; margin-bottom:12px;'>Guaíba - RS</p>", unsafe_allow_html=True)
    hoje_clima = next((d for d in dados_clima if d["hoje"]), dados_clima[0])
    st.markdown(f"<div class='weather-card-today'><div style='display: flex; justify-content: space-between; align-items: flex-start;'><div><h3 style='margin:0; font-size:1.8rem; font-weight:500; color:#FFF;'>{hoje_clima['temp'].split(' / ')[0]}</h3><p style='margin:2px 0 0 0; font-size:0.85rem; color:#C4C7C5;'>{hoje_clima['status']}</p></div><span style='font-size:1.8rem;'>{hoje_clima['status'].split(' ')[0]}</span></div><div style='margin-top:14px; display:flex; gap:12px; font-size:0.75rem; color:#9AA0A6;'><span>💨 {hoje_clima['vento']}</span><span>💧 {hoje_clima['chuva']}</span></div></div>", unsafe_allow_html=True)
    with st.expander("", expanded=False):
        for d in dados_clima:
            pf = "font-weight: 600; color: #1A73E8;" if d["hoje"] else "color: #E3E3E3;"
            st.markdown(f"<div class='weather-row'><span style='font-size:0.8rem; {pf}'>{d['nome']}{' •' if d['hoje'] else ''} <small style='color:#80868B;'>({d['data_str']})</small></span><span style='font-size:0.8rem; color:#E3E3E3;'>{d['temp'].split(' / ')[0]} | <small style='color:#9AA0A6;'>{d['status'].split(' ')[0]}</small></span></div>", unsafe_allow_html=True)

col_tit1, col_tit2 = st.columns([2.8, 1.2])
with col_tit1:
    st.markdown("<h1 style='font-weight: 500; font-size: 2.2rem; margin-bottom: 4px;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9AA0A6; margin: 0; font-size: 1.05rem;'>Gestão Integrada de Atividades • Unidade Guaíba</p>", unsafe_allow_html=True)
with col_tit2:
    st.markdown(f"<div class='ios-clock-widget'><div class='ios-clock-top'><span class='ios-time'>{now_brasilia.strftime('%H:%M:%S')}</span><span class='ios-date-badge'>{now_brasilia.strftime('%d %b %y')}</span></div><div class='ios-progress-container'><div class='ios-progress-bar' style='width: {pct_dia_decorrido}%;'></div></div><div class='ios-clock-bottom'><span>🗓️ Semana {numero_semana}</span><span>🕒 Horário Brasília</span></div></div>", unsafe_allow_html=True)

st.divider()

def render_cards_com_busca(sub_df, prefix_key, local_col_tempo):
    busca_termo = st.text_input(f"🔍 Filtrar Ordens Ativas ({prefix_key})", "", placeholder="Digite ordem, tag ou escopo de trabalho...", key=f"search_box_{prefix_key}")
    st.markdown("<br>", unsafe_allow_html=True)
    df_f_busca = sub_df.copy()
    if busca_termo:
        df_f_busca = df_f_busca[df_f_busca["Ordem"].astype(str).str.contains(busca_termo, case=False, na=False) | df_f_busca["Descrição da Ordem"].astype(str).str.contains(busca_termo, case=False, na=False)]
    if df_f_busca.empty:
        st.info("Nenhuma ordem encontrada para os filtros aplicados.")
        return
    for idx, row in df_f_busca.iterrows():
        row_actual = st.session_state.df.loc[idx]
        ordem, desc, operacao, status_atual, tempo_exec = row_actual["Ordem"], row_actual["Descrição da Ordem"], row_actual["Texto Breve da Operação"], row_actual["Status_Execucao"], row_actual.get(local_col_tempo, "N/D")
        comentario_actual = "" if str(row_actual.get("Comentario", "")) in ["nan", "None"] else str(row_actual.get("Comentario", ""))
        data_inicio = row_actual["Data_Inicio_Parsed"]
        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
        bg_card, border_color, alerta_atraso = HEX_BG_MAP.get(status_atual, "#1C1C1E"), COLOR_MAP.get(status_atual, "#0A84FF"), ""
        if pd.notnull(data_inicio) and data_inicio < pd.to_datetime(date.today()) and status_atual == "Pendente":
            border_color, alerta_atraso = "#FF453A", "<br>🚨 <strong style='color:#FF453A;'>ATIVIDADE CRÍTICA EM ATRASO</strong>"
        st.markdown(f"<div style='background: {bg_card}; border-left: 6px solid {border_color}; padding: 20px; border-radius: 14px; margin-bottom: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.25);'><strong>Ordem:</strong> <code>{ordem}</code> | <strong>Área:</strong> {row_actual['Área']} | <strong>Tempo de Execução:</strong> {tempo_exec}<br><em>{desc}</em> - {operacao}{alerta_atraso}</div>", unsafe_allow_html=True)
        
        novo_status = st.radio(f"Status_{prefix_key}_{ordem}_{idx}", options=opcoes_status, index=opcoes_status.index(status_atual) if status_atual in opcoes_status else 0, horizontal=True, key=f"rad_{prefix_key}_{ordem}_{idx}", label_visibility="collapsed")
        novo_comentario = comentario_actual
        if novo_status in ["Pendente", "Necessita Reprogramação"]:
            motivos = ["Selecione motivo...", "Falta de Material", "Falta de Acesso", "Mão de Obra", "Não liberado pela operação", "Condição climática não favorável", "Corretivas emergênciais", "Outros"]
            idx_motivo = next((m_idx for m_idx, m_val in enumerate(motivos) if comentario_actual.startswith(m_val)), 0)
            motivo_sel = st.selectbox(f"Motivo / Justificativa ({ordem})", motivos, index=idx_motivo, key=f"mot_{prefix_key}_{idx}", label_visibility="collapsed")
            if motivo_sel != "Selecione motivo...":
                default_detalhe = comentario_actual.replace(f"{motivo_sel}: ", "") if comentario_actual.startswith(motivo_sel) else comentario_actual
                novo_comentario = f"{motivo_sel}: {st.text_input(f'Detalhes adicionais ({ordem})', value=default_detalhe, key=f'det_{prefix_key}_{idx}')}"
        elif novo_status == "Realizada":
            if comentario_actual: st.markdown(f"<small>💬 <i>Histórico anterior: {comentario_actual}</i></small>", unsafe_allow_html=True)
            novo_comentario = ""
            
        # Modifica no estado persistente apenas se houver real alteração humana, prevenindo saltos de página indesejados
        if novo_status != status_atual or novo_comentario != comentario_actual:
            st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
            st.session_state.df.loc[idx, "Comentario"] = str(novo_comentario)
            st.session_state.necessita_salvar = True

if st.session_state.df is not None:
    df = st.session_state.df
    df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica")) if "Centro de Trabalho Op." in df.columns else "Mecânica"
    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Dia_da_Semana"] = df["Data_Inicio_Parsed"].dt.day_name()
    df["Área"] = df["Área"].astype(str).str.strip()
    df_foco = df[df["Área"].isin(AREAS_FOCO)].copy()
    col_tempo = "Tempo de Execução" if "Tempo de Execução" in df.columns else ("Tempo" if "Tempo" in df.columns else None)
    if col_tempo is None:
        df["Tempo_Execucao_Ficticio"] = "4h"
        col_tempo = "Tempo_Execucao_Ficticio"
        
    # Removido o st.rerun() automático para reter a viewport e a aba atual em foco do usuário
    if st.session_state.necessita_salvar:
        col_btn1, col_btn2 = st.columns([3, 1])
        with col_btn1: st.warning("⚠️ Existem alterações pendentes de salvamento em disco.")
        with col_btn2:
            if st.button("💾 SALVAR ALTERAÇÕES", key="btn_salvar_global"):
                salvar_dados(st.session_state.df)
                atualizar_historico(st.session_state.df)
                st.session_state.necessita_salvar = False
                st.success("Alterações salvas!")
                
    aba_geral, aba_exec_ind, aba_exec_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    with aba_geral:
        st.markdown("<h2 style='font-weight: 500; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        total_ordens, realizadas_tot = len(df_foco), len(df_foco[df_foco["Status_Execucao"] == "Realizada"])
        aderencia_pct = (realizadas_tot / total_ordens * 100) if total_ordens > 0 else 0.0
        atrasos_tot = len(df_foco[(df_foco["Status_Execucao"] == "Pendente") & (df_foco["Data_Inicio_Parsed"] < pd.to_datetime(date.today()))])
        st.markdown(f"<div class='kpi-container'><div class='kpi-card'><div class='kpi-value'>{total_ordens}</div><div class='kpi-label'>Ordens Totais (Foco)</div></div><div class='kpi-card'><div class='kpi-value' style='color:#30D158'>{aderencia_pct:.1f}%</div><div class='kpi-label'>Aderência de Execução</div></div><div class='kpi-card'><div class='kpi-value' style='color:#FF453A'>{atrasos_tot}</div><div class='kpi-label'>Atrasos Críticos</div></div></div>", unsafe_allow_html=True)
        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Aderência / Distribuição Geral (Áreas Foco)</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                status_geral = agrupar_pequenos_rotulos(df_foco["Status_Execucao"]).value_counts().reset_index()
                status_geral.columns = ["Status", "Quantidade"]
                st.plotly_chart(update_plotly_ios_layout(px.pie(status_geral, values="Quantidade", names="Status", hole=0.55, color="Status", color_discrete_map=COLOR_MAP)).update_traces(textinfo='percent+label', textfont_size=14), use_container_width=True)
        with col_g2:
            st.markdown("<h4>Aderência por Disciplina</h4>", unsafe_allow_html=True)
            if not df_foco.empty:
                total_por_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().reset_index(name="Qtd")
                disc_sel_pizza = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["Disciplina"].unique())), key="pizza_disc_drop")
                df_filtrado_pizza = total_por_disc[total_por_disc["Disciplina"] == disc_sel_pizza].copy()
                if not df_filtrado_pizza.empty:
                    df_filtrado_pizza["Status_Execucao"] = agrupar_pequenos_rotulos(df_filtrado_pizza["Status_Execucao"])
                    st.plotly_chart(update_plotly_ios_layout(px.pie(df_filtrado_pizza, values="Qtd", names="Status_Execucao", hole=0.55, color="Status_Execucao", color_discrete_map=COLOR_MAP)).update_traces(textinfo='percent+label', textfont_size=14), use_container_width=True)
        st.divider()
        st.markdown("<h3>📋 Relatório Final de Apontamentos (Áreas de Foco)</h3>", unsafe_allow_html=True)
        if not df_foco.empty:
            resumo_areas_final = df_foco.groupby(["Área", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
            for st_col in ["Realizada", "Necessita Reprogramação", "Pendente"]:
                if st_col not in resumo_areas_final: resumo_areas_final[st_col] = 0
            st.download_button(label="📥 Exportar Resumo Consolidado (CSV)", data=resumo_areas_final.to_csv(index=False), file_name="resumo_apontamentos.csv", mime="text/csv", key="btn_download_csv")
            st.markdown("<br>", unsafe_allow_html=True)
            for idx, row in resumo_areas_final.iterrows():
                col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 2])
                with col_a1: st.markdown(f"**Área:** {row['Área']}")
                with col_a2: st.markdown(f"✅ **Realizadas:** <span style='color:{COLOR_MAP['Realizada']}; font-weight:700;'>{row['Realizada']}</span>", unsafe_allow_html=True)
                with col_a3: st.markdown(f"⚠️ **Reprogramadas:** <span style='color:{COLOR_MAP['Necessita Reprogramação']}; font-weight:700;'>{row['Necessita Reprogramação']}</span>", unsafe_allow_html=True)
                with col_a4: st.markdown(f"🔴 **Pendentes:** <span style='color:{COLOR_MAP['Pendente']}; font-weight:700;'>{row['Pendente']}</span>", unsafe_allow_html=True)
                st.divider()
        st.markdown("<br><h3>📈 Indicador de Evolução Semanal (Taxa de Realização)</h3>", unsafe_allow_html=True)
        if os.path.exists(ARQUIVO_HISTORICO):
            hist_df = pd.read_csv(ARQUIVO_HISTORICO)
            if not hist_df.empty:
                fig_evolucao = go.Figure()
                fig_evolucao.add_trace(go.Scatter(x=hist_df["Data"], y=hist_df["Taxa"], mode='lines+markers', name="Taxa Realizada", fill='tozeroy', fillcolor='rgba(26, 115, 232, 0.15)', line=dict(color='#1A73E8', width=4)))
                fig_evolucao.add_shape(type="line", x0=hist_df["Data"].iloc[0], y0=85, x1=hist_df["Data"].iloc[-1], y1=85, line=dict(color="#FF453A", width=2.5, dash="dash"), name="Meta (85%)")
                st.plotly_chart(update_plotly_ios_layout(fig_evolucao).update_layout(yaxis=dict(title="Taxa de Realização (%)", range=[0, 100]), showlegend=False), use_container_width=True)
    with aba_exec_ind:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        exec_sel = st.selectbox("Escolha o Executante da Área:", ["Selecione..."] + sorted([str(e) for e in df_foco["Executante"].dropna().unique()]), key="exec_sel_combo")
        if exec_sel != "Selecione...":
            df_exec = df_foco[df_foco["Executante"] == exec_sel].copy()
            st.divider()
            st.markdown(f"<h4>Aderência de Execução: {exec_sel}</h4>", unsafe_allow_html=True)
            status_exec = agrupar_pequenos_rotulos(df_exec["Status_Execucao"]).value_counts().reset_index()
            status_exec.columns = ["Status", "Quantidade"]
            st.plotly_chart(update_plotly_ios_layout(px.pie(status_exec, values="Quantidade", names="Status", hole=0.55, color="Status", color_discrete_map=COLOR_MAP)).update_layout(height=280, margin=dict(t=0, b=0)).update_traces(textinfo='percent+label', textfont_size=12))
            st.divider()
            st.markdown("<h4>Divisão Semanal de Atividades</h4>", unsafe_allow_html=True)
            dias_ordem, dias_pt = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
            for dia in dias_ordem:
                df_dia = df_exec[df_exec["Data_Inicio_Parsed"].dt.day_name() == dia].copy()
                if not df_dia.empty:
                    st.markdown(f"### 📅 {dias_pt[dia]} <span style='font-size: 1.1rem; color: #9AA0A6; font-weight: 400;'>({len(df_dia)} ordens)</span>", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    render_cards_com_busca(df_dia, f"ind_{dia}", col_tempo)
                    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 30px 0;'>", unsafe_allow_html=True)
    with aba_exec_disc:
        st.markdown("<h2 style='font-weight: 500;'>Apontamento por Disciplina (Caldeira e Energia)</h2>", unsafe_allow_html=True)
        disc_sel = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["Disciplina"].dropna().unique())), key="disc_sel_combo_main")
        if disc_sel:
            st.markdown(f"<h4>Ordens de Serviço - {disc_sel}</h4>", unsafe_allow_html=True)
            render_cards_com_busca(df_foco[df_foco["Disciplina"] == disc_sel].copy(), f"disc_{disc_sel}", col_tempo)
else:
    st.warning("⬅️ Por favor, utilize o painel lateral para inserir as credenciais e carregar o arquivo de programação.")