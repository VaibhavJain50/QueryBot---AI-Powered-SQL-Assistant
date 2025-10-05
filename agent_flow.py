import operator
from typing import TypedDict, Union, Dict, Any, List

# Core LangChain and LangGraph imports
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, START
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
load_dotenv()

# Import our database manager utility
from db_manager import ACTIVE_DATABASES

# --- 1. Define the Agent's Structured Output Schema ---
class AgentAction(BaseModel):
    database_name: str = Field(description="The database to use (must match ACTIVE_DATABASES keys).")
    sql_query: str = Field(description="Complete SQL statement for MySQL.")
    intent: str = Field(description="'read' (SELECT) or 'write' (INSERT/UPDATE/DELETE).")

# --- 2. Initialize the LLM ---
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# --- 3. Define Agent Nodes ---
def generate_sql_and_intent(state: dict) -> dict:
    """
    Node 1: Decide database, intent, and generate SQL.
    Returns updated dict state.
    """
    print(f"\n[AGENT NODE] Deciding action for query: '{state['query']}'")

    # Gather schema info
    db_info_list = []
    for name, db in ACTIVE_DATABASES.items():
        db_info_list.append(f"Database Name: {name}\nTables:\n{db.get_table_info()}")
    db_info_str = "\n---\n".join(db_info_list)

    # System prompt
    system_prompt = f"""
    You are a SQL agent. Output a JSON object with 'database_name', 'sql_query', 'intent'.
    Available databases (use lowercase names exactly as shown):
    {db_info_str}
    Rules:
    1. Use only one database from the list.
    2. sql_query must be complete.
    3. intent: 'read' for SELECT, 'write' for others.
    """

    sql_only = "sql query" in state["query"].lower()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "User Query: {query}")
    ]).partial(query=state["query"])

    try:
        structured_chain = prompt | llm.with_structured_output(AgentAction)
        action: AgentAction = structured_chain.invoke({"query": state["query"]})

        print(f"[AGENT NODE] Generated Intent: {action.intent.upper()}")
        print(f"[AGENT NODE] Target DB: {action.database_name}")
        print(f"[AGENT NODE] Proposed SQL: {action.sql_query}")

        # Normalize database name
        db_name = action.database_name.strip().lower()

        new_state = {
            "query": state["query"],
            "sql_query": action.sql_query,
            "database_name": db_name,
            "response": "",
            "intent": action.intent.lower(),
            "verification_status": "pending" if action.intent.lower() == "write" else "approved",
            "sql_only_request": sql_only
        }

        return new_state

    except Exception as e:
        print(f" Error during SQL generation: {e}")
        new_state = state.copy()
        new_state.update({
            "sql_query": None,
            "database_name": None,
            "response": f"Error: Could not generate SQL. Details: {e}",
            "intent": None,
            "verification_status": "failed",
            "sql_only_request": sql_only
        })
        return new_state

def requires_verification(state: dict) -> str:
    """Conditional routing based on intent."""
    if state.get("intent") == "write" and state.get("verification_status") == "pending":
        print("[CONDITIONAL EDGE] -> Verification Required!")
        return "verify_human"
    elif state.get("intent") == "read" or state.get("verification_status") == "approved":
        print("[CONDITIONAL EDGE] -> Proceeding to SQL Execution.")
        return "execute_sql"
    else:
        print("[CONDITIONAL EDGE] -> Operation failed or rejected.")
        return "end_with_response"

def execute_sql_query(state: dict) -> dict:
    """Node 2: Executes SQL and formats final answer."""
    db_name = (state.get("database_name") or "").strip().lower()
    sql = state.get("sql_query")

    print(f"\n[EXECUTION NODE] Running SQL against '{db_name}'...")

    if not db_name or db_name not in ACTIVE_DATABASES:
        state["response"] = f"Error: Database '{db_name}' not found."
        return state

    db = ACTIVE_DATABASES[db_name]

    try:
        result = db.run(sql)
        print(f"[EXECUTION NODE] Query successful. Result: {result}")

        # Format final answer
        answer_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at converting raw database results into concise natural language."),
            ("human", f"Original Query: {state['query']}\nSQL Query: {sql}\nRaw Results: {result}")
        ])

        final_answer_chain = answer_prompt | llm

        if state.get("sql_only_request"):
            final_response = f"SQL Query:\n```sql\n{sql}\n```\n\nFinal Answer:\n" + final_answer_chain.invoke({"query": state['query'], "sql": sql, "result": result}).content
        else:
            final_response = final_answer_chain.invoke({"query": state['query'], "sql": sql, "result": result}).content

        state["response"] = final_response
        return state

    except Exception as e:
        print(f"SQL Execution Error: {e}")
        state["response"] = f"Database Error: '{e}'\nSQL: {sql}"
        return state

def prepare_verification_message(state: dict) -> dict:
    """Node 3: Prepares message for human verification."""
    print("\n[HIL NODE] Action pending human verification.")
    message = (
        "⚠️ **HUMAN-IN-THE-LOOP REQUIRED** ⚠️\n\n"
        "Proposed data modification requires your approval.\n"
        f"**Database Target:** `{state['database_name']}`\n"
        f"**Proposed SQL:** `{state['sql_query']}`\n"
        "Please confirm by providing your session ID and 'approved' status."
    )
    state["response"] = message
    return state

# --- 4. Build the LangGraph Workflow ---
def build_agent_workflow():
    workflow = StateGraph(dict)
    workflow.add_node("agent_decision", generate_sql_and_intent)
    workflow.add_node("execute_sql", execute_sql_query)
    workflow.add_node("verify_human", prepare_verification_message)

    workflow.set_entry_point("agent_decision")

    workflow.add_conditional_edges(
        "agent_decision",
        requires_verification,
        {
            "verify_human": "verify_human",
            "execute_sql": "execute_sql",
            "end_with_response": END
        }
    )

    workflow.add_edge("execute_sql", END)
    workflow.add_edge("verify_human", END)

    app = workflow.compile()
    print("\n--- LangGraph Agent Compiled Successfully. ---")
    return app
