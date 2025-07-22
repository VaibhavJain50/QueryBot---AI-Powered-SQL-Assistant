# 💬 QueryBot – AI-Powered SQL Assistant
QueryBot is an interactive AI agent built with LangChain, Streamlit, and Groq’s Gemma model that allows users to chat directly with SQL databases. It supports selecting, inserting, deleting, and updating records through natural language — no SQL knowledge required.

# 🚀 Features
🔍 Conversational SQL Access — Query data from your SQLite or MySQL database using plain English.

🛠️ Modifies the Database — Supports INSERT, UPDATE, and DELETE operations with safety checks.

🤖 Agentic Intelligence — Powered by LangChain agents and SQLDatabaseToolkit.

🎨 Beautiful UI — Responsive chat interface with a gradient background and sticky header.

🧠 LLM-Backed — Uses Groq's Gemma-2-9b-IT model for fast and accurate responses.

🔒 Secure & Local — No data leaves your machine unless using a remote database.

🔄 Session Memory — Maintains chat history during interaction for multi-turn conversations.

# 🛠️ Technologies Used
Streamlit — UI framework

LangChain — LLM orchestration and SQL agent

Groq + Gemma — LLM backend

SQLite / MySQL — Supported databases

SQLAlchemy — Database abstraction

# ⚙️ How to Run
1. Clone the Repo
2. 
3. Install Dependencies

pip install -r requirements.txt
4. Add Your Database
For SQLite: Place your student.db in the project directory.

For MySQL: Provide host, user, password, and DB name in the sidebar.

4. Run Streamlit App

streamlit run app.py
5. Enter Your Groq API Key
You can get your API key from Groq Console.


# 💡 Use Cases
Internal data exploration tools for analysts

AI customer support for database queries

Teaching SQL concepts interactively

Natural language admin tools for small DBs
