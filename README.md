# 💬 QueryBot – AI-Powered SQL Assistant

A FastAPI-based SQL agent that interacts with multiple MySQL databases using **LangGraph** and **LangChain**. 
The agent can handle natural language queries, generate SQL automatically, execute it, and return results in human-readable format.
Write queries use a **Human-in-the-Loop (HIL)** verification process to ensure safe database modifications.

---

## Table of Contents

1. [System Design]
2. [LangGraph Workflow]
3. [Tools & Libraries]
4. [Project Structure]
5. [Installation](#installation)  
6. [Running the Application]  
7. [API Endpoints]
8. [Example Queries] 

---

## System Design

The system consists of three main components:

1. **FastAPI Server**  
   - Serves `/init` to initialize databases and `/ask` to process user queries.
   - Handles Human-in-the-Loop verification for write queries.

2. **Database Manager (`db_manager.py`)**  
   - Connects to multiple MySQL databases.
   - Maintains a global `ACTIVE_DATABASES` dictionary accessible by the agent workflow.
   - Uses SQLAlchemy and `mysql-connector-python` for database connections.

3. **LangGraph Agent (`agent_flow.py`)**  
   - Defines a **state machine workflow** for processing queries.
   - Steps include:
     1. Generating SQL and intent from natural language query (`generate_sql_and_intent`)
     2. Conditional check for HIL if the query is a write operation (`requires_verification`)
     3. Executing SQL on the target database (`execute_sql_query`)
     4. Preparing HIL message for human approval (`prepare_verification_message`)
   - Structured LLM output enforced using `AgentAction` schema.

---

## LangGraph Workflow

```text
           ┌──────────────────────────┐
           │     agent_decision       │
           │  (Generate SQL & Intent) │
           └─────────────┬────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
   intent = write                  intent = read
verification_status=pending             │
         │                              │
         │                              ▼
         │                    ┌────────────────┐
         │                    │   execute_sql  │
         │                    │ (Run SQL &     │
         │                    │ format result) │
         │                    └───────┬────────┘
         │                            │
         │                            ▼
         │                          END
         │
         ▼
┌─────────────────────────┐
│      verify_human       │
│ (HIL required)          │
│ Show proposed SQL & ask │
│   for human approval    │
└─────────────┬───────────┘
              │
   approved? ──┴─────► execute_sql
              │
   rejected?  ▼
           ┌─────────┐
           │   END   │
           │ (Abort) │
           └─────────┘
```



- **Nodes**: Functions in `agent_flow.py`.  
- **Edges**: Conditional routing depending on query type and verification status.  
- **Global Variables**: `ACTIVE_DATABASES` and `AGENT_SESSIONS` are shared across modules for state consistency.  

---

## Tools & Libraries

| Component        | Library / Tool                     | Purpose                                        |
|------------------|------------------------------------|------------------------------------------------|
| Web server       | FastAPI                            | API server for user interaction                |
| Database ORM     | SQLAlchemy                         | Connect to MySQL databases                     |
| MySQL driver     | mysql-connector-python             | MySQL connection backend                       |
| Environment vars | python-dotenv                      | Load `.env` configuration                      |
| LLM Integration  | langchain / langchain-google-genai | Query parsing & SQL generation                 |
| Multi-DB workflow| langgraph                          | State machine for agent decisions              |
| Pydantic         | pydantic                           | Input validation & structured output           |
| UUID             | uuid                               | Session IDs for HIL (Human-in-the-Loop) tracking |


---

## Project Structure

project/

├─ main.py # FastAPI app and endpoints

├─ db_manager.py # Database connection manager

├─ agent_flow.py # LangGraph workflow & LLM agent logic

├─ requirements.txt # Python dependencies

├─ .env # Environment variables (optional)

└─ README.md # Project documentation



---

## Installation

1. Clone the repository:

2. Create a virtual environment:

python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows


3. Install dependencies:

pip install -r requirements.txt


4. Create a .env file if your LLM API requires credentials:

LLM_API_KEY="your_api_key_here"



# Running the Application

1. Start the FastAPI server using Uvicorn:

uvicorn main:app --reload


2. Access the interactive API docs at http://127.0.0.1:8000/docs

Server is ready for /init and /ask requests.

API Endpoints
1. /init - Initialize Databases

POST payload:

{
  "databases": [
    {
      "host": "localhost",
      "user": "root",
      "password": "password",
      "database": "database-name"
    },
    {
      "host": "localhost",
      "user": "root",
      "password": "password",
      "database": "database-name"
    }
  ]
}


Response:

"Databases initialized successfully. You can now send queries to the /ask endpoint."

2. /ask - Query the Agent
Read Query:
{
  "query": "Show me the top 5 customers by total purchases in database-name"
}


Response Example:

{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "success",
  "response_message": "Here are the top 5 customers by total purchases: ...",
  "proposed_sql": null,
  "database_name": null
}

Write Query (HIL Pending):
{
  "query": "Update the cost of product 'Laptop' to 1200 in datawarehouseanalytics"
}


Response Example:

{
  "session_id": "123e4567-e89b-12d3-a456-426614174001",
  "status": "pending_verification",
  "response_message": "⚠️ HUMAN-IN-THE-LOOP REQUIRED ...",
  "proposed_sql": "UPDATE dim_products SET cost = 1200 WHERE product_name = 'Laptop';",
  "database_name": "database_name"
}

Approving a Pending Write:
{
  "session_id": "123e4567-e89b-12d3-a456-426614174001",
  "verification_status": "approved"
}


Response:

{
  "session_id": "123e4567-e89b-12d3-a456-426614174001",
  "status": "success",
  "response_message": "Query executed successfully: ..."
}

Example Queries

Read Query:

{
  "query": "List the top 5 products by revenue in chinook"
}


Write Query (HIL):

{
  "query": "Update the maintenance cost of product 'Laptop' to 500 in datawarehouseanalytics"
}


Agent returns "pending_verification"

Approve using the same session_id:

{
  "session_id": "HIL_SESSION_ID",
  "verification_status": "approved"
}

## Notes

Always call /init first to initialize databases.

Read queries execute immediately, write queries go through HIL verification.

ACTIVE_DATABASES is updated in-place to maintain references across modules.

Ensure your MySQL user has SELECT, INSERT, UPDATE, DELETE permissions as needed.



## Use of AI Tools

During the development of the Mini Agentic SQL Bot, AI tools (such as ChatGPT, claude) were used selectively for:

Code Structuring & Suggestions – AI assisted with planning and organizing workflow ideas.

Debugging Guidance – Provided hints for resolving database connection and SQL execution issues.

Documentation & README Drafting – Assisted in creating clean and structured explanations for the system design, workflow, and API usage.

