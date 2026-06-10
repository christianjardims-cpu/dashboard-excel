import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, date
import pytz

# Configuração da página - Layout Wide
st.set_page_config(page_title="Gestão de Manutenção", layout="wide", initial_sidebar_state="expanded")

# Mapeamento de Cores Exatas e Limpas (Tema Dark iOS)
COLOR_MAP = {
    "Realizada": "#30D158",                # Verde (Suave)
    "Pendente": "#FF453A",                 # Vermelho (Acento)
    "Necessita Reprogramação": "#FF9F0A",  # Amarelo/Laranja
    "Outros": "#8E8E93"                    # Cinza
}

HEX_BG_MAP = {
    "Realizada": "rgba(48, 209, 88, 0.08)",
    "Pendente": "rgba(255, 69, 58, 0.08)",
    "Necessita Reprogramação": "rgba(255, 159, 10, 0.08)",
    "Outros": "rgba(142, 142, 147, 0.08)"
}

# Injeção de CSS - Design System iOS Dark Mode
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="st-emotion-cache"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Sidebar Premium */
    [data-testid="stSidebar"] { 
        background-color: #1C1C1E; 
        border-right: 1px solid rgba(255, 255, 255, 0.05); 
        padding: 24px 16px; 
    }
    
    /* Blocos de Conteúdo - Efeito Glassmorphism / iOS Card Style */
    [data-testid="stVerticalBlock"] > div > div.stContainer {
        background: rgba(28, 28, 30, 0.65);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 18px;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5);
        padding: 24px;
        color: #FFFFFF;
        margin-bottom: 20px;
    }
    
    /* Expansores estilo Lista Agrupada iOS */
    div[data-testid="stExpander"] details {
        background: rgba(28, 28, 30, 0.4);
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 8px;
    }
    
    p, label, div[data-testid="stMarkdownContainer"] { color: #F2F2F7; }
    h1, h2, h3, h4, h5 { color: #FFFFFF; letter-spacing: -0.5px; }
    
    /* Inputs, Selectors e Rádios redesenhados */
    div[data-testid="stselectbox"] > div > div { 
        background-color: #1C1C1E; 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 12px; 
        color: white; 
    }
    
    /* KPI Cards Topo */
    .kpi-container { display: flex; gap: 1.5rem; margin-bottom: 2rem; margin-top: 1rem; }
    .kpi-card { 
        background: rgba(255, 255, 255, 0.03); 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 16px; 
        padding: 1.5rem; 
        flex: 1; 
        text-align: center; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .kpi-value { font-size: 2.2rem; font-weight: 700; color: #0A84FF; margin-bottom: 0.2rem; }
    .kpi-label { font-size: 0.85rem; color: #8E8E93; text-transform: uppercase; letter-spacing: 1px; font-weight: 500; }

    /* Botão Premium estilo App Store */
    .stButton > button {
        background: linear-gradient(135deg, #0A84FF, #5E5CE6) !important; 
        color: white !important; 
        border-radius: 12px !important; 
        border: none !important; 
        font-weight: 600 !important; 
        padding: 12px 24px !important;
        box-shadow: 0 4px 20px rgba(10, 132, 255, 0.3) !important; 
        transition: all 0.3s ease !important; 
        width: 100% !important;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 25px rgba(10, 132, 255, 0.5) !important; }
    
    hr { border-color: rgba(255, 255, 255, 0.06); }
</style>
""", unsafe_allow_html=True)

# Persistência de Dados
ARQUIVO_SALVO = "programacao_atualizada.csv"
ARQUIVO_HISTORICO = "historico_semanal.csv"
AREAS_FOCO = ["CALD.RECUP/EVAPORAÇÃO", "ENERGIA"]

def carregar_dados():
    if os.path.exists(ARQUIVO_SALVO):
        try: return pd.read_csv(ARQUIVO_SALVO)
        except Exception: return None
    return None

def salvar_dados(df):
    df.to_csv(ARQUIVO_SALVO, index=False)

def update_plotly_ios_layout(fig):
    """Remove linhas de grade e aplica fundo perfeitamente transparente para dashboard escuro."""
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
    """Agrupa categorias com menos de 5% em 'Outros' para evitar poluição visual."""
    freq = series.value_counts(normalize=True)
    pequenos = freq[freq < threshold].index
    return series.apply(lambda x: 'Outros' if x in pequenos else x)

if "df" not in st.session_state or st.session_state.df is None:
    st.session_state.df = carregar_dados()

# Cabeçalho com Relógio Brasília
col_tit1, col_tit2 = st.columns([3, 1])
with col_tit1:
    st.markdown("<h1 style='font-weight: 700; font-size: 2.4rem;'>⚙️ Painel de Acompanhamento</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8E93; margin-top: -5px; font-size: 1.1rem;'>Gestão de Manutenção Semanal</p>", unsafe_allow_html=True)
with col_tit2:
    tz_brasilia = pytz.timezone("America/Sao_Paulo")
    now_brasilia = datetime.now(tz_brasilia)
    st.markdown(f"<div style='text-align: right; background: rgba(255,255,255,0.03); padding: 14px; border-radius: 14px; border: 1px solid rgba(255,255,255,0.08);'><small style='color: #8E8E93; font-weight: 600; letter-spacing: 0.5px;'>HORÁRIO DE BRASÍLIA</small><br><strong style='font-size: 1.1rem;'>{now_brasilia.strftime('%d/%m/%Y')}</strong><br><span style='color: #0A84FF; font-weight: 700; font-size: 1.3rem;'>{now_brasilia.strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

st.divider()

with st.sidebar:
    st.markdown("<h2 style='font-weight: 600; font-size: 1.3rem; margin-bottom: 15px;'>Área de Administração</h2>", unsafe_allow_html=True)
    senha_inserida = st.text_input("Senha de acesso:", type="password")
    
    if senha_inserida == "Programacao@2026":
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Selecione a programação (.csv ou .xlsx)", type=["csv", "xlsx"])
        if uploaded_file is not None:
            nome_arquivo = uploaded_file.name.lower()
            try:
                with st.spinner("Processando base de dados..."):
                    if nome_arquivo.endswith(".csv"): df_temp = pd.read_csv(uploaded_file, skiprows=1)
                    elif nome_arquivo.endswith(".xlsx"): df_temp = pd.read_excel(uploaded_file, skiprows=1)
                    df_temp.columns = df_temp.columns.str.strip()
                    if "Status_Execucao" not in df_temp.columns: df_temp["Status_Execucao"] = "Pendente"
                    if "Comentario" not in df_temp.columns: df_temp["Comentario"] = ""
                    st.session_state.df = df_temp
                    salvar_dados(df_temp)
                    atualizar_historico(df_temp)
                st.success("Base atualizada com sucesso!")
            except Exception as e: st.error(f"Erro ao ler arquivo: {e}")
    elif senha_inserida != "": st.error("Senha incorreta.")

df = st.session_state.df

def render_cards_com_busca(sub_df, prefix_key):
    busca = st.text_input(f"🔍 Pesquisar Ordem ou Descrição ({prefix_key})", "", placeholder="Digite o número da Ordem ou palavra-chave...", label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    if busca:
        sub_df = sub_df[sub_df["Ordem"].astype(str).str.contains(busca, case=False, na=False) | 
                         sub_df["Descrição da Ordem"].astype(str).str.contains(busca, case=False, na=False)]

    for idx, row in sub_df.iterrows():
        row_actual = st.session_state.df.loc[idx]
        ordem = row_actual["Ordem"]
        desc = row_actual["Descrição da Ordem"]
        operacao = row_actual["Texto Breve da Operação"]
        status_atual = row_actual["Status_Execucao"]
        tempo_exec = row_actual.get(col_tempo, "N/D")
        comentario_atual = row_actual.get("Comentario", "")
        data_inicio = row_actual["Data_Inicio_Parsed"]
        
        opcoes_status = ["Pendente", "Realizada", "Necessita Reprogramação"]
        idx_status = 0
        if status_atual in opcoes_status: idx_status = opcoes_status.index(status_atual)
        
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
        
        novo_comentario = comentario_atual
        if novo_status in ["Pendente", "Necessita Reprogramação"]:
            motivos = ["Selecione motivo...", "Falta de Material", "Falta de Acesso", "Mão de Obra", "Outros"]
            motivo_sel = st.selectbox(f"Motivo / Justificativa ({ordem})", motivos, key=f"mot_{prefix_key}_{idx}", label_visibility="collapsed")
            if motivo_sel != "Selecione motivo...":
                novo_comentario = st.text_input(f"Detalhes adicionais ({ordem})", value=comentario_atual if "Selecione" not in comentario_atual else "", key=f"det_{prefix_key}_{idx}")
                novo_comentario = f"{motivo_sel}: {novo_comentario}"
        elif novo_status == "Realizada":
            if comentario_atual:
                st.markdown(f"<small>💬 <i>Histórico: {comentario_atual}</i></small>", unsafe_allow_html=True)
            novo_comentario = ""

        if novo_status != status_atual or novo_comentario != comentario_atual:
            st.session_state.df.loc[idx, "Status_Execucao"] = novo_status
            st.session_state.df.loc[idx, "Comentario"] = novo_comentario
            salvar_dados(st.session_state.df)
            atualizar_historico(st.session_state.df)
            st.rerun()
        
        st.markdown("<hr style='margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

if df is not None:
    if "Centro de Trabalho Op." in df.columns:
        df["Disciplina"] = df["Centro de Trabalho Op."].astype(str).apply(lambda x: "Elétrica" if "E" in x else ("Instrumentação" if "I" in x else "Mecânica"))
    else: df["Disciplina"] = "Mecânica"

    df["Data_Inicio_Parsed"] = pd.to_datetime(df["Data de Início"], errors="coerce")
    df["Dia_da_Semana"] = df["Data_Inicio_Parsed"].dt.day_name()
    df["Área"] = df["Área"].astype(str).str.strip()
    
    df_foco = df[df["Área"].isin(AREAS_FOCO)].copy()

    col_tempo = "Tempo de Execução" if "Tempo de Execução" in df.columns else ("Tempo" if "Tempo" in df.columns else None)
    if col_tempo is None:
        df["Tempo_Execucao_Ficticio"] = "4h"
        col_tempo = "Tempo_Execucao_Ficticio"

    aba_geral, aba_exec_ind, aba_exec_disc = st.tabs(["📊 Acompanhamento Geral", "🛠️ Apontamento por Executante", "⚙️ Apontamento por Disciplina"])
    
    with aba_geral:
        st.markdown("<h2 style='font-weight: 600; margin-bottom: 20px;'>Visão Macro: Caldeira de Recuperação e Energia</h2>", unsafe_allow_html=True)
        
        # --- KPI CARDS (Blocos Numéricos Premium) ---
        total_ordens = len(df_foco)
        realizadas_tot = len(df_foco[df_foco["Status_Execucao"] == "Realizada"])
        aderencia_pct = (realizadas_tot / total_ordens * 100) if total_ordens > 0 else 0.0
        atrasos_tot = len(df_foco[(df_foco["Status_Execucao"] == "Pendente") & (df_foco["Data_Inicio_Parsed"] < pd.to_datetime(date.today()))])
        
        st.markdown(f"""
            <div class="kpi-container">
                <div class="kpi-card"><div class="kpi-value">{total_ordens}</div><div class="kpi-label">Ordens Totais (Foco)</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:#30D158">{aderencia_pct:.1f}%</div><div class="kpi-label">Aderência de Execução</div></div>
                <div class="kpi-card"><div class="kpi-value" style="color:#FF453A">{atrasos_tot}</div><div class="kpi-label">Atrasos Críticos</div></div>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("<h4>Aderência / Distribuição Geral (Áreas Foco)</h4>", unsafe_allow_html=True)
            status_agrupado = agrupar_pequenos_rotulos(df_foco["Status_Execucao"])
            status_geral = status_agrupado.value_counts().reset_index()
            status_geral.columns = ["Status", "Quantidade"]
            
            fig_pizza_geral = px.pie(status_geral, values="Quantidade", names="Status", hole=0.55, color="Status", color_discrete_map=COLOR_MAP)
            fig_pizza_geral = update_plotly_ios_layout(fig_pizza_geral)
            fig_pizza_geral.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_geral, use_container_width=True)
            
        with col_g2:
            st.markdown("<h4>Aderência por Disciplina</h4>", unsafe_allow_html=True)
            total_por_disc = df_foco.groupby(["Disciplina", "Status_Execucao"]).size().reset_index(name="Qtd")
            disc_sel_pizza = st.selectbox("Selecione a Disciplina:", sorted(list(df_foco["Disciplina"].unique())), key="pizza_disc_drop")
            
            df_filtrado_pizza = total_por_disc[total_por_disc["Disciplina"] == disc_sel_pizza]
            df_filtrado_pizza["Status_Execucao"] = agrupar_pequenos_rotulos(df_filtrado_pizza["Status_Execucao"])
            fig_pizza_disc = px.pie(df_filtrado_pizza, values="Qtd", names="Status_Execucao", hole=0.55, color="Status_Execucao", color_discrete_map=COLOR_MAP)
            fig_pizza_disc = update_plotly_ios_layout(fig_pizza_disc)
            fig_pizza_disc.update_traces(textinfo='percent+label', textfont_size=14)
            st.plotly_chart(fig_pizza_disc, use_container_width=True)

        st.divider()
        st.markdown("<h3>📋 Relatório Final de Apontamentos (Áreas de Foco)</h3>", unsafe_allow_html=True)
        
        resumo_areas_final = df_foco.groupby(["Área", "Status_Execucao"]).size().unstack(fill_value=0).reset_index()
        if "Realizada" not in resumo_areas_final: resumo_areas_final["Realizada"] = 0
        if "Necessita Reprogramação" not in resumo_areas_final: resumo_areas_final["Necessita Reprogramação"] = 0
        if "Pendente" not in resumo_areas_final: resumo_areas_final["Pendente"] = 0
        
        # Botão de Exportação de Relatório (CSV consolidado)
        csv_resumo = resumo_areas_final.to_csv(index=False)
        st.download_button(
            label="📥 Exportar Resumo Consolidado (CSV)",
            data=csv_resumo,
            file_name="resumo_apontamentos.csv",
            mime="text/csv"
        )
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
            # Gráfico de Linha com área sombreada gradiente e linha de meta (Target Line em 85%)
            fig_evolucao = go.Figure()
            fig_evolucao.add_trace(go.Scatter(
                x=hist_df["Data"], y=hist_df["Taxa"], 
                mode='lines+markers', name="Taxa Realizada", 
                fill='tozeroy', fillcolor='rgba(10, 132, 255, 0.15)',
                line=dict(color='#0A84FF', width=4)
            ))
            # Meta de 85% - Linha tracejada
            fig_evolucao.add_shape(
                type="line", x0=hist_df["Data"].iloc[0], y0=85, 
                x1=hist_df["Data"].iloc[-1], y1=85, 
                line=dict(color="#FF453A", width=2.5, dash="dash"),
                name="Meta (85%)"
            )
            fig_evolucao = update_plotly_ios_layout(fig_evolucao)
            fig_evolucao.update_layout(
                yaxis=dict(title="Taxa de Realização (%)", range=[0, 100]),
                showlegend=False
            )
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.info("O gráfico de linha de evolução será formado após a primeira atualização ou carga de dados.")

    with aba_exec_ind:
        st.markdown("<h2 style='font-weight: 600;'>Apontamento Diário por Executante</h2>", unsafe_allow_html=True)
        executantes_validos = sorted([str(e) for e in df_foco["Executante"].dropna().unique()])
        executantes = ["Selecione..."] + executantes_validos
        exec_sel = st.selectbox("Escolha o Executante da Área:", executantes, key="exec_sel_combo")
        
        if exec_sel != "Selecione...":
            df_exec = df_foco[df_foco["Executante"] == exec_sel].copy()
            st.divider()
            st.markdown(f"<h4>Aderência de Execução: {exec_sel}</h4>", unsafe_allow_html=True)
            status_exec = agrupar_pequenos_rotulos(df_exec["Status_Execucao"]).value_counts().reset_index()
            status_exec.columns = ["Status", "Quantidade"]
            fig_pizza_exec = px.pie(status_exec, values="Quantidade", names="Status", hole=0.55, color="Status", color_discrete_map=COLOR_MAP)
            fig_pizza_exec = update_plotly_ios_layout(fig_pizza_exec)
            fig_pizza_exec.update_layout(height=280, margin=dict(t=0, b=0))
            fig_pizza_exec.update_traces(textinfo='percent+label', textfont_size=12)
            st.plotly_chart(fig_pizza_exec)

            st.divider()
            st.markdown("<h4>Divisão Semanal de Atividades</h4>", unsafe_allow_html=True)
            dias_da_semana_ordem = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dias_pt = {"Monday": "Segunda-feira", "Tuesday": "Terça-feira", "Wednesday": "Quarta-feira", "Thursday": "Quinta-feira", "Friday": "Sexta-feira", "Saturday": "Sábado", "Sunday": "Domingo"}
            
            for dia in dias_da_semana_ordem:
                df_dia = df_exec[df_exec["Data_Inicio_Parsed"].dt.day_name() == dia].copy()
                if not df_dia.empty:
                    with st.expander(f"📅 {dias_pt[dia]} ({len(df_dia)} ordens)"):
                        render_cards_com_busca(df_dia, f"ind_{dia}")

    with aba_exec_disc:
        st.markdown("<h2 style='font-weight: 600;'>Apontamento por Disciplina (Caldeira e Energia)</h2>", unsafe_allow_html=True)
        disciplinas_disp = sorted(list(df_foco["Disciplina"].dropna().unique()))
        disc_sel = st.selectbox("Selecione a Disciplina:", disciplinas_disp, key="disc_sel_combo_main")
        
        if disc_sel:
            df_disc = df_foco[df_foco["Disciplina"] == disc_sel].copy()
            st.markdown(f"<h4>Ordens de Serviço - {disc_sel}</h4>", unsafe_allow_html=True)
            render_cards_com_busca(df_disc, f"disc_{disc_sel}")

else: 
    st.warning("⬅️ Por favor, insira a senha e faça o upload do arquivo base no menu lateral para inicializar o painel.")