import os
import sqlite3
import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
from langchain_groq import ChatGroq


st.set_page_config(page_title="QueryBotL", page_icon=":guardsman:", layout="wide")
import streamlit as st
from langchain.chains import ConversationalRetrievalChain
# Other imports...

# ⬇️ Add the background styling code HERE ⬇️
gradient_background = """
<style>
body {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white;
    font-family: 'Segoe UI', sans-serif;
}
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
}
[data-testid="stSidebar"] {
    background-color: #1e293b;
    color: white;
}
header, .st-emotion-cache-1dp5vir.ezrtsby2 {
    position: sticky;
    top: 0;
    background: rgba(15, 32, 39, 0.9);
    z-index: 999;
    border-bottom: 1px solid #444;
}
</style>
"""
st.markdown(gradient_background, unsafe_allow_html=True)

# 🧠 Your Streamlit app continues here
st.title("QueryBot – AI-Powered SQL Assistant")




LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQLDB"

options= ["Use Local SQLite Database", "Use MySQL Database"]
choice= st.sidebar.radio("Select Database Type", options)

if choice == options[1]:
    db_uri=MYSQL
    mysql_host = st.sidebar.text_input("MySQL Host")
    mysql_user = st.sidebar.text_input("MySQL User")
    mysql_password = st.sidebar.text_input("MySQL Password", type="password")
    mysql_db = st.sidebar.text_input("MySQL Database Name")

else:
    db_uri=LOCALDB
    

api_key = st.sidebar.text_input("Groq API Key", type="password").strip()    
# st.sidebar.write(f"API key length: {len(api_key)}")


if not db_uri:
    st.info("Please select a database type.")

if not api_key:
    st.info("Please enter your Groq API Key.")

## LLM model
llm = None
if api_key:
    try:
        llm = ChatGroq(
            api_key=api_key,
            model="gemma2-9b-it",
            streaming=True,
        )
    except Exception as e:
        st.error(f"Failed to initialize ChatGroq: {e}")
        st.stop()
else:
    st.warning("Please enter your Groq API Key to continue.")
    st.stop()


@st.cache_resource(ttl="2h")
def configure_database(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
       dbfilepath=(Path(__file__).parent / "student.db").absolute()
       print(dbfilepath)
       creator = lambda: sqlite3.connect(str(dbfilepath))
       return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        if not all([mysql_host, mysql_user, mysql_password, mysql_db]):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        return SQLDatabase(
            create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}")
        )

if db_uri==MYSQL:
    db = configure_database(db_uri, mysql_host, mysql_user, mysql_password, mysql_db)
else:
    db = configure_database(db_uri)

#Toolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    prefix="You are an intelligent SQL assistant. You can retrieve data and also modify the database if asked. Always ensure the command is safe before running."
)


if "messages" not in st.session_state or st.sidebar.button("Clear Chat"):
    st.session_state["messages"] = [{"role": "Assistant", "content": "How can I assist you today?"}]

for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

user_query = st.chat_input(placeholder="Ask a question about the database...")

if user_query:
    st.session_state["messages"].append({"role": "User", "content": user_query})
    st.chat_message("User").write(user_query)

    with st.chat_message("Assistant"):
        streamlit_callback=StreamlitCallbackHandler(st.container())
        response = agent.run(
            user_query,
            callbacks=[streamlit_callback],
        )
        st.session_state["messages"].append({"role": "Assistant", "content": response})
        st.write(response)