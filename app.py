# =============================================================================
# MAINTENANCE CONTROL CENTER
# Versão ChatGPT Premium
# Desenvolvido para Streamlit
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sqlite3
import requests
import pytz
import os
import re

from datetime import datetime


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

st.set_page_config(
    page_title="Maintenance Control Center",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


DB_NAME = "maintenance.db"


STATUS_COLORS = {

    "Realizada":"#22c55e",

    "Pendente":"#ef4444",

    "Necessita Reprogramação":"#f59e0b"

}


DISC_COLORS = {

    "Mecânica":"#3b82f6",

    "Elétrica":"#8b5cf6",

    "Instrumentação":"#10b981"

}



# =============================================================================
# TEMA PREMIUM
# =============================================================================

st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"]{

font-family:'Inter',sans-serif;

}


.stApp{

background:#09090b;

}


section[data-testid="stSidebar"]{

background:#111827;

border-right:1px solid #27272a;

}


.block-container{

padding-top:1rem;

padding-bottom:2rem;

}


.main-title{

font-size:2.2rem;

font-weight:700;

color:white;

margin-bottom:0;

}


.sub-title{

color:#71717a;

font-size:1rem;

margin-bottom:20px;

}


.kpi-card{

background:#18181b;

border:1px solid #27272a;

padding:22px;

border-radius:18px;

}


.kpi-value{

font-size:2rem;

font-weight:700;

color:white;

}


.kpi-label{

font-size:0.8rem;

color:#71717a;

text-transform:uppercase;

letter-spacing:1px;

}


.os-card{

background:#18181b;

border:1px solid #27272a;

padding:18px;

border-radius:18px;

margin-bottom:15px;

transition:0.2s;

}


.os-card:hover{

transform:translateY(-3px);

border:1px solid #3f3f46;

}


.badge{

padding:5px 10px;

border-radius:12px;

font-size:0.75rem;

font-weight:600;

color:white;

}


.timeline-card{

background:#111827;

padding:15px;

border-radius:15px;

border:1px solid #27272a;

text-align:center;

}


</style>

""",unsafe_allow_html=True)



# =============================================================================
# BANCO DE DADOS SQLITE
# =============================================================================


@st.cache_resource

def conectar_db():

    conn = sqlite3.connect(

        DB_NAME,

        check_same_thread=False

    )



    conn.execute("""

    CREATE TABLE IF NOT EXISTS programacao(


        ordem TEXT PRIMARY KEY,

        area TEXT,

        descricao TEXT,

        operacao TEXT,

        executante TEXT,

        disciplina TEXT,

        data_inicio TEXT,

        horas REAL,

        status TEXT,

        comentario TEXT


    )

    """)



    conn.commit()

    return conn



conn = conectar_db()
# =============================================================================
# FUNÇÕES DO BANCO
# =============================================================================

def carregar_dados():

    query = "SELECT * FROM programacao"

    return pd.read_sql(query, conn)



def salvar_dataframe(df):

    cursor = conn.cursor()


    for _, row in df.iterrows():

        cursor.execute("""

        INSERT INTO programacao(

            ordem,

            area,

            descricao,

            operacao,

            executante,

            disciplina,

            data_inicio,

            horas,

            status,

            comentario

        )

        VALUES(?,?,?,?,?,?,?,?,?,?)

        ON CONFLICT(ordem)

        DO UPDATE SET


        area=excluded.area,

        descricao=excluded.descricao,

        operacao=excluded.operacao,

        executante=excluded.executante,

        disciplina=excluded.disciplina,

        data_inicio=excluded.data_inicio,

        horas=excluded.horas,

        status=excluded.status,

        comentario=excluded.comentario

        """,

        (

            str(row["ordem"]),

            str(row["area"]),

            str(row["descricao"]),

            str(row["operacao"]),

            str(row["executante"]),

            str(row["disciplina"]),

            str(row["data_inicio"]),

            float(row["horas"]),

            str(row["status"]),

            str(row["comentario"])

        )

        )


    conn.commit()




def atualizar_status(ordem,status,comentario=""):


    conn.execute(

        """

        UPDATE programacao

        SET

        status=?,

        comentario=?

        WHERE ordem=?

        """,

        (

            status,

            comentario,

            ordem

        )

    )


    conn.commit()




# =============================================================================
# UPLOAD DE ARQUIVO
# =============================================================================


def tratar_upload(arquivo):


    nome = arquivo.name.lower()



    if nome.endswith(".csv"):


        df = pd.read_csv(

            arquivo,

            skiprows=1

        )



    else:


        df = pd.read_excel(

            arquivo,

            skiprows=1

        )



    df.columns = df.columns.str.strip()



    mapa = {


        "Ordem":"ordem",

        "Área":"area",

        "Descrição da Ordem":"descricao",

        "Texto Breve da Operação":"operacao",

        "Executante":"executante",

        "Data de Início":"data_inicio"

    }



    df = df.rename(

        columns=mapa

    )



    if "Centro de Trabalho Op." in df.columns:


        def descobrir_disciplina(x):


            x = str(x)


            if "E" in x:

                return "Elétrica"


            elif "I" in x:

                return "Instrumentação"


            else:

                return "Mecânica"



        df["disciplina"] = df[

            "Centro de Trabalho Op."

        ].apply(

            descobrir_disciplina

        )



    else:


        df["disciplina"] = "Mecânica"



    if "status" not in df:

        df["status"] = "Pendente"



    if "comentario" not in df:

        df["comentario"] = ""



    if "horas" not in df:

        df["horas"] = 4.0



    colunas = [

        "ordem",

        "area",

        "descricao",

        "operacao",

        "executante",

        "disciplina",

        "data_inicio",

        "horas",

        "status",

        "comentario"

    ]



    return df[colunas]



# =============================================================================
# CLIMA OPEN METEO
# =============================================================================

@st.cache_data(ttl=300)

def obter_clima():

    try:


        url = (

        "https://api.open-meteo.com/v1/forecast?"

        "latitude=-30.1139&"

        "longitude=-51.3250&"

        "current_weather=true&"

        "timezone=America/Sao_Paulo"

        )



        r = requests.get(

            url,

            timeout=5

        ).json()



        temp = int(

            r["current_weather"]["temperature"]

        )



        codigo = r["current_weather"]["weathercode"]



        icones = {


            0:"☀️",

            1:"⛅",

            2:"⛅",

            3:"☁️",

            61:"🌧️",

            63:"🌧️",

            95:"⚡"

        }



        icone = icones.get(

            codigo,

            "☁️"

        )



        return f"{temp}°C",icone



    except:


        return "18°C","☁️"



temperatura,icone_clima = obter_clima()



# =============================================================================
# DATA E HORA
# =============================================================================


tz = pytz.timezone(

    "America/Sao_Paulo"

)


agora = datetime.now(

    tz

)



dia_semana = [

    "Segunda",

    "Terça",

    "Quarta",

    "Quinta",

    "Sexta",

    "Sábado",

    "Domingo"

][

    agora.weekday()

]



semana_ano = agora.strftime(

    "%U"

)





# =============================================================================
# SIDEBAR PREMIUM
# =============================================================================


with st.sidebar:


    st.markdown(

    """

    <h1 style='

    color:white;

    font-size:1.7rem;

    margin-bottom:0;

    '>

    ⚙️ CMPC

    </h1>


    """,

    unsafe_allow_html=True

    )



    st.markdown(

    """

    <p style='

    color:#71717a;

    margin-top:0;

    '>

    Maintenance Control Center

    </p>

    """,

    unsafe_allow_html=True

    )



    st.markdown("---")



    st.metric(

        "Temperatura",

        temperatura,

        icone_clima

    )



    st.metric(

        "Semana",

        semana_ano,

        dia_semana

    )



    st.markdown("---")



    arquivo = st.file_uploader(

        "Importar programação",

        type=[

            "csv",

            "xlsx"

        ]

    )



    if arquivo:



        try:


            novo_df = tratar_upload(

                arquivo

            )



            salvar_dataframe(

                novo_df

            )



            st.success(

                "Programação atualizada"

            )



        except Exception as e:


            st.error(

                str(e)

            )
# =============================================================================
# CARREGAR DADOS
# =============================================================================

df = carregar_dados()


# =============================================================================
# HEADER PREMIUM
# =============================================================================

st.markdown(

f"""

<div style='

background:#111827;

padding:30px;

border-radius:25px;

border:1px solid #27272a;

margin-bottom:25px;

'>



<div style='display:flex;

justify-content:space-between;

align-items:center;'>



<div>

<p style='

font-size:0.9rem;

color:#71717a;

margin:0;

letter-spacing:2px;

text-transform:uppercase;

'>

CMPC

</p>



<h1 style='

font-size:2.5rem;

color:white;

margin:0;

font-weight:700;

'>

Maintenance Control Center

</h1>



<p style='

color:#71717a;

font-size:1rem;

margin-top:10px;

'>

Gestão Inteligente de Manutenção

</p>

</div>




<div style='text-align:right;'>



<div style='

font-size:3rem;

font-weight:700;

color:white;

'>

{agora.strftime("%H:%M")}

</div>



<div style='

color:#71717a;

font-size:0.95rem;

'>

{dia_semana}

</div>



<div style='

margin-top:10px;

color:#60a5fa;

font-weight:600;

'>

📍 Guaíba - RS

</div>



<div style='

font-size:1.1rem;

color:white;

margin-top:8px;

'>

{icone_clima}

{temperatura}

</div>



</div>

</div>

</div>

""",

unsafe_allow_html=True

)




# =============================================================================
# CASO NÃO TENHA DADOS
# =============================================================================

if df.empty:


    st.info(

    "Faça upload de uma programação na barra lateral."

    )



    st.stop()




# =============================================================================
# KPIs
# =============================================================================

total = len(df)


realizadas = len(

    df[

        df["status"]=="Realizada"

    ]

)


pendentes = len(

    df[

        df["status"]=="Pendente"

    ]

)


aderencia = (

realizadas /

max(total,1)

)*100




c1,c2,c3,c4 = st.columns(4)



with c1:


    st.markdown(

    f"""

    <div class='kpi-card'>


    <div class='kpi-value'>

    {total}

    </div>



    <div class='kpi-label'>

    OMS Totais

    </div>



    </div>

    """,

    unsafe_allow_html=True

    )



with c2:



    st.markdown(

    f"""

    <div class='kpi-card'>


    <div class='kpi-value'

    style='color:#22c55e'>

    {realizadas}

    </div>



    <div class='kpi-label'>

    Realizadas

    </div>



    </div>

    """,

    unsafe_allow_html=True

    )




with c3:



    st.markdown(

    f"""

    <div class='kpi-card'>


    <div class='kpi-value'

    style='color:#ef4444'>

    {pendentes}

    </div>



    <div class='kpi-label'>

    Pendentes

    </div>



    </div>

    """,

    unsafe_allow_html=True

    )




with c4:



    st.markdown(

    f"""

    <div class='kpi-card'>


    <div class='kpi-value'

    style='color:#60a5fa'>

    {aderencia:.1f}%

    </div>



    <div class='kpi-label'>

    Aderência

    </div>



    </div>

    """,

    unsafe_allow_html=True

    )




st.write("")




# =============================================================================
# ALERTAS
# =============================================================================

alertas = []



if pendentes > total*0.4:


    alertas.append(

    f"⚠️ Existem {pendentes} OMS pendentes."

    )




if aderencia < 70:


    alertas.append(

    f"🔴 A aderência está abaixo de 70%."

    )




if len(alertas)>0:



    with st.expander(

    "🔔 Centro de Alertas",

    expanded=True

    ):



        for alerta in alertas:



            st.warning(

                alerta

            )






# =============================================================================
# FILTROS
# =============================================================================


col1,col2,col3 = st.columns(3)



with col1:


    area = st.selectbox(

    "Área",

    sorted(

    df["area"]

    .astype(str)

    .unique()

    )

    )



with col2:



    disciplina = st.selectbox(

    "Disciplina",

    [

    "Todas"

    ]

    +

    sorted(

    df["disciplina"]

    .astype(str)

    .unique()

    )

    )



with col3:



    busca = st.text_input(

    "Pesquisar OMS"

    )





df_filtrado = df[

df["area"]==area

]



if disciplina!="Todas":



    df_filtrado = df_filtrado[

    df_filtrado["disciplina"]

    ==

    disciplina

    ]



if busca:



    busca = busca.lower()



    df_filtrado = df_filtrado[



    df_filtrado["ordem"]

    .astype(str)

    .str.lower()

    .str.contains(busca)



    |



    df_filtrado["descricao"]

    .astype(str)

    .str.lower()

    .str.contains(busca)



    ]




st.write("")
# =============================================================================
# TIMELINE SEMANAL
# =============================================================================

st.markdown("""

<h3 style='

color:white;

margin-top:25px;

margin-bottom:20px;

'>

📅 Timeline Semanal

</h3>

""",

unsafe_allow_html=True)


dias = [

"Seg",

"Ter",

"Qua",

"Qui",

"Sex"

]


cols = st.columns(5)


for i,dia in enumerate(dias):


    with cols[i]:


        st.markdown(

        f"""

        <div class='timeline-card'>


        <div style='

        color:#71717a;

        font-size:0.9rem;

        margin-bottom:12px;

        '>

        {dia}

        </div>



        <div style='

        font-size:1.6rem;

        '>

        📌

        </div>



        </div>

        """,

        unsafe_allow_html=True

        )



st.write("")


# =============================================================================
# GRÁFICOS
# =============================================================================

c1,c2 = st.columns(2)


with c1:


    st.markdown(

    """

    <h3 style='

    color:white;

    '>

    Status das OMS

    </h3>

    """,

    unsafe_allow_html=True

    )


    status_count = (

    df_filtrado

    ["status"]

    .value_counts()

    .reset_index()

    )


    status_count.columns=[

    "status",

    "qtd"

    ]



    fig = px.pie(

    status_count,

    values="qtd",

    names="status",

    hole=.65,

    color="status",

    color_discrete_map=STATUS_COLORS

    )



    fig.update_layout(

    paper_bgcolor="#09090b",

    plot_bgcolor="#09090b",

    font_color="white",

    showlegend=True

    )



    st.plotly_chart(

    fig,

    use_container_width=True

    )



with c2:



    st.markdown(

    """

    <h3 style='

    color:white;

    '>

    Disciplinas

    </h3>

    """,

    unsafe_allow_html=True

    )



    disc_count = (

    df_filtrado

    ["disciplina"]

    .value_counts()

    .reset_index()

    )



    disc_count.columns=[

    "disciplina",

    "qtd"

    ]



    fig2 = px.bar(

    disc_count,

    x="disciplina",

    y="qtd",

    color="disciplina",

    color_discrete_map=DISC_COLORS

    )



    fig2.update_layout(

    paper_bgcolor="#09090b",

    plot_bgcolor="#09090b",

    font_color="white",

    showlegend=False

    )



    st.plotly_chart(

    fig2,

    use_container_width=True

    )





# =============================================================================
# ORDENS DE SERVIÇO
# =============================================================================


st.markdown("""

<h2 style='

color:white;

margin-top:25px;

'>

🛠️ Ordens de Serviço

</h2>

""",

unsafe_allow_html=True)




for _,row in df_filtrado.iterrows():



    status = row["status"]


    cor_status = STATUS_COLORS.get(

    status,

    "#71717a"

    )



    cor_disc = DISC_COLORS.get(

    row["disciplina"],

    "#71717a"

    )



    st.markdown(

    f"""

    <div class='os-card'>


    <div style='

    display:flex;

    justify-content:space-between;

    align-items:center;

    '>


        <div>


            <span style='

            color:#71717a;

            font-size:0.85rem;

            '>

            OMS

            </span>


            <h2 style='

            margin:0;

            color:white;

            '>

            {row["ordem"]}

            </h2>



        </div>



        <div>


            <span

            class='badge'

            style='

            background:{cor_disc};

            '>


            {row["disciplina"]}


            </span>


        </div>


    </div>




    <p style='

    color:white;

    font-size:1rem;

    margin-top:15px;

    margin-bottom:15px;

    '>

    {row["descricao"]}

    </p>





    <div style='

    color:#71717a;

    font-size:0.9rem;

    '>


    👤 {row["executante"]}



    </div>




    <div style='

    color:#71717a;

    font-size:0.9rem;

    margin-top:8px;

    '>


    🗓️ {row["data_inicio"]}


    </div>




    <div style='

    color:#71717a;

    font-size:0.9rem;

    margin-top:8px;

    '>


    ⏱️ {row["horas"]} horas


    </div>




    <div style='

    margin-top:15px;

    '>



    <span

    class='badge'

    style='

    background:{cor_status};

    '>


    {status}



    </span>



    </div>



    </div>


    """,

    unsafe_allow_html=True

    )



    c1,c2 = st.columns(

    [1,2]

    )



    with c1:



        novo_status = st.selectbox(

        "Status",


        [

        "Pendente",

        "Realizada",

        "Necessita Reprogramação"

        ],



        index=

        [

        "Pendente",

        "Realizada",

        "Necessita Reprogramação"

        ].index(status),



        key=f"status_{row['ordem']}"

        )




    with c2:



        comentario = st.text_input(

        "Comentário",


        value=row["comentario"],


        key=f"coment_{row['ordem']}"

        )




    if (


    novo_status!=status


    or


    comentario!=row["comentario"]


    ):



        atualizar_status(

        row["ordem"],

        novo_status,

        comentario

        )



        st.rerun()

# =============================================================================
# PASSO 5 - EXTRAS PREMIUM
# =============================================================================

st.markdown("---")
st.subheader("📈 Indicador de Aderência")
fig = go.Figure(go.Indicator(mode="gauge+number", value=aderencia, number={"suffix":"%"}, title={"text":"Aderência"}, gauge={"axis":{"range":[0,100]}, "bar":{"color":"#22c55e"}, "borderwidth":0}))
fig.update_layout(height=250,paper_bgcolor="#09090b",font_color="white")
st.plotly_chart(fig,use_container_width=True)

st.subheader("👥 OMS por Executante")
execs=(df_filtrado.groupby("executante").size().reset_index(name="OMS"))
if len(execs)>0:
    fig=px.bar(execs,x="executante",y="OMS",text="OMS")
    fig.update_layout(paper_bgcolor="#09090b",plot_bgcolor="#09090b",font_color="white",showlegend=False)
    st.plotly_chart(fig,use_container_width=True)
