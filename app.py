# =============================================================================
# MAINTENANCE CONTROL CENTER
# ChatGPT Edition V3
# =============================================================================

import streamlit as st

import pandas as pd

import plotly.express as px

import plotly.graph_objects as go

import sqlite3

import requests

from datetime import datetime

import pytz



# =============================================================================
# CONFIGURAÇÃO STREAMLIT
# =============================================================================


st.set_page_config(

page_title="Maintenance Control Center",

page_icon="⚙️",

layout="wide",

initial_sidebar_state="expanded"

)



DB_NAME = "maintenance.db"



STATUS_COLORS = {


"Pendente":"#ef4444",

"Realizada":"#22c55e",

"Necessita Reprogramação":"#f59e0b"


}



DISC_COLORS = {


"Mecânica":"#3b82f6",

"Elétrica":"#8b5cf6",

"Instrumentação":"#10b981"


}



# =============================================================================
# CSS PREMIUM
# =============================================================================


st.markdown("""

<style>


@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');


html, body, [class*="css"]{

font-family:'Inter',sans-serif;

}



.stApp{

background:#09090b;

color:white;

}



section[data-testid="stSidebar"]{


background:#111827;

border-right:1px solid #27272a;


}



.block-container{


padding-top:1rem;

padding-bottom:2rem;

padding-left:2rem;

padding-right:2rem;


}




.kpi{


background:#18181b;

padding:20px;

border-radius:20px;

border:1px solid #27272a;

text-align:center;

transition:0.2s;


}



.kpi:hover{


transform:translateY(-3px);


}



.card{


background:rgba(24,24,27,0.85);

backdrop-filter:blur(15px);

border:1px solid rgba(255,255,255,0.08);

padding:22px;

border-radius:22px;

margin-bottom:18px;

box-shadow:

0 8px 30px rgba(0,0,0,0.35);


}



.badge{


padding:6px 12px;

border-radius:15px;

font-size:0.75rem;

font-weight:600;

color:white;


}




.header{


background:#111827;

padding:28px;

border-radius:25px;

border:1px solid #27272a;

margin-bottom:25px;


}



.timeline{


background:#111827;

padding:18px;

border-radius:18px;

border:1px solid #27272a;

text-align:center;


}



</style>

""",

unsafe_allow_html=True)



# =============================================================================
# SQLITE
# =============================================================================



@st.cache_resource

def conectar():



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




conn = conectar()



# =============================================================================
# FUNÇÕES DO BANCO
# =============================================================================



def carregar_dados():



    return pd.read_sql(

    "SELECT * FROM programacao",

    conn

    )





def salvar_dataframe(df):



    cursor = conn.cursor()



    for _,row in df.iterrows():



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


        VALUES(

        ?,?,?,?,?,?,?,?,?,?

        )


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


        """


        ,

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




def atualizar_status(

ordem,

status,

comentario

):



    conn.execute(

    """

    UPDATE programacao

    SET

    status=?,

    comentario=?

    WHERE ordem=?

    """

    ,

    (

    status,

    comentario,

    ordem

    )

    )



    conn.commit()
# =============================================================================
# UPLOAD INTELIGENTE
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



        def disciplina(x):



            x = str(x).upper()



            if "ELE" in x:

                return "Elétrica"



            elif "INS" in x:

                return "Instrumentação"



            else:

                return "Mecânica"




        df["disciplina"] = df[

        "Centro de Trabalho Op."

        ].apply(

        disciplina

        )



    else:



        df["disciplina"] = "Mecânica"




    if "status" not in df:

        df["status"]="Pendente"



    if "comentario" not in df:

        df["comentario"]=""



    if "horas" not in df:

        df["horas"]=4




    colunas=[

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
# CLIMA
# =============================================================================


@st.cache_data(ttl=300)

def obter_clima():



    try:



        url=(

        "https://api.open-meteo.com/v1/forecast?"

        "latitude=-30.03&"

        "longitude=-51.23&"

        "current_weather=true"

        )




        resposta = requests.get(

        url,

        timeout=5

        ).json()




        temperatura = (

        resposta

        ["current_weather"]

        ["temperature"]

        )




        codigo = (

        resposta

        ["current_weather"]

        ["weathercode"]

        )




        mapa = {


        0:"☀️",

        1:"🌤️",

        2:"⛅",

        3:"☁️",

        61:"🌧️",

        63:"🌧️",

        95:"⛈️"

        }




        return (

        temperatura,

        mapa.get(

        codigo,

        "☁️"

        )

        )



    except:



        return (

        "--",

        "☁️"

        )





temperatura,

icone_clima = obter_clima()




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



# =============================================================================
# SIDEBAR
# =============================================================================


with st.sidebar:



    st.markdown(

    """

    <h1 style='

    color:white;

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

    f"{temperatura}°C",

    icone_clima

    )



    st.metric(

    "Data",

    agora.strftime(

    "%d/%m/%Y"

    ),

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

            "Programação importada"

            )



        except Exception as e:



            st.error(

            str(e)

            )



# =============================================================================
# HEADER PREMIUM
# =============================================================================


st.markdown(

f"""

<div class='header'>


<div style='

display:flex;

justify-content:space-between;

align-items:center;

'>




<div>



<p style='

color:#71717a;

margin:0;

letter-spacing:2px;

'>

CMPC

</p>




<h1 style='

color:white;

font-size:2.6rem;

margin:0;

'>

Maintenance Control Center

</h1>




<p style='

color:#71717a;

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

'>

{dia_semana}

</div>




<div style='

margin-top:10px;

font-size:1.1rem;

color:#60a5fa;

'>

📍 Porto Alegre - RS

</div>




<div style='

margin-top:8px;

font-size:1.2rem;

color:white;

'>

{icone_clima}

{temperatura}°C

</div>



</div>



</div>

</div>

""",

unsafe_allow_html=True
)



# =============================================================================
# CARREGAR DADOS
# =============================================================================


df = carregar_dados()



if df.empty:



    st.info(

    "Importe uma programação para começar."

    )



    st.stop()
if df.empty:

    st.info(

    "Importe uma programação para começar."

    )

    st.stop()
st.write("")

# =============================================================================
# EXPORTAÇÃO EXCEL
# =============================================================================

st.write("")


st.markdown("""

<h2 style='

color:white;

margin-top:25px;

'>

📥 Exportação

</h2>

""",

unsafe_allow_html=True)



excel = df_filtrado.to_csv(

index=False

).encode(

"utf-8"

)



st.download_button(

label="⬇️ Exportar CSV",

data=excel,

file_name="programacao.csv",

mime="text/csv"

)




# =============================================================================
# RANKING EXECUTANTES
# =============================================================================


st.write("")



st.markdown("""

<h2 style='

color:white;

margin-top:25px;

'>

🏆 Ranking dos Executantes

</h2>

""",

unsafe_allow_html=True)




ranking = (

df_filtrado

.groupby(

"executante"

)

.size()

.reset_index()

)



ranking.columns=[

"Executante",

"OMS"

]



ranking = ranking.sort_values(

"OMS",

ascending=False

)





for i,row in ranking.head(10).iterrows():



    percentual = (

    row["OMS"]

    /

    max(

    ranking["OMS"].max(),

    1

    )

    )*100




    st.markdown(

    f"""

    <div class='card'>



    <div style='

    display:flex;

    justify-content:space-between;

    align-items:center;

    '>




        <div>



            <div style='

            color:white;

            font-size:1rem;

            font-weight:600;

            '>


            {row["Executante"]}



            </div>



            <div style='

            color:#71717a;

            font-size:0.85rem;

            '>


            {row["OMS"]} OMS



            </div>



        </div>





        <div style='

        width:50%;

        '>



            <div style='

            background:#27272a;

            height:10px;

            border-radius:10px;

            overflow:hidden;

            '>



                <div style='

                width:{percentual}%;

                background:#3b82f6;

                height:10px;

                '>

                </div>



            </div>



        </div>





    </div>



    </div>

    """,

    unsafe_allow_html=True

    )






# =============================================================================
# MODO TV
# =============================================================================


st.write("")



modo_tv = st.toggle(

"📺 Ativar Modo TV"

)



if modo_tv:



    st.markdown(

    """

    <style>


    .card{


    padding:35px;


    }


    .kpi{


    padding:35px;


    }


    html{


    zoom:1.25;


    }


    </style>


    """,

    unsafe_allow_html=True

    )



    st.success(

    "Modo TV Ativado"

    )






# =============================================================================
# BARRA DE PROGRESSO
# =============================================================================



st.write("")



st.markdown("""

<h2 style='

color:white;

margin-top:20px;

'>

📈 Progresso Geral

</h2>

""",

unsafe_allow_html=True)




st.progress(

aderencia/100

)




st.markdown(

f"""

<div style='

text-align:center;

color:#60a5fa;

font-size:1.2rem;

margin-top:10px;

'>



{aderencia:.1f}% de aderência



</div>

""",

unsafe_allow_html=True

)






# =============================================================================
# NOTIFICAÇÃO ESTILO DYNAMIC ISLAND
# =============================================================================



if aderencia >= 90:



    st.markdown(

    """

    <div style='

    position:fixed;

    top:20px;

    left:50%;

    transform:translateX(-50%);

    background:#18181b;

    border:1px solid #22c55e;

    padding:14px 28px;

    border-radius:30px;

    color:white;

    z-index:9999;

    box-shadow:

    0 10px 30px rgba(0,0,0,0.5);

    '>


    ✅ Excelente desempenho da equipe


    </div>

    """,

    unsafe_allow_html=True

    )






# =============================================================================
# RODAPÉ
# =============================================================================


st.write("")



st.markdown("---")



st.markdown(

"""

<div style='

text-align:center;

color:#71717a;

padding-bottom:20px;

'>


Maintenance Control Center


<br>


Versão ChatGPT V3 Premium


<br>


Streamlit + SQLite + Plotly



</div>

""",

unsafe_allow_html=True

)
