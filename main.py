from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import uuid

# Import our custom modules
from db_manager import MySQLCredentials, initialize_databases, ACTIVE_DATABASES
from agent_flow import build_agent_workflow

# --- Pydantic Schemas for API Endpoints ---
class InitRequest(BaseModel):
    """Schema for initializing the databases."""
    databases: List[MySQLCredentials] = Field(
        ...,
        description="A list of MySQL database credentials (at least two)."
    )

class QueryRequest(BaseModel):
    """Schema for a user query or HIL approval."""
    query: Optional[str] = Field(
        None,
        description="The natural language query (required for new queries)."
    )
    session_id: Optional[str] = Field(
        None,
        description="The unique session ID for pending verification requests."
    )
    verification_status: Optional[str] = Field(
        None,
        description="Must be 'approved' to execute a pending write operation."
    )

class AgentResponse(BaseModel):
    """Schema for the agent's response."""
    session_id: str = Field(
        description="A unique ID to track the conversation, especially for verification."
    )
    status: str = Field(
        description="The status of the operation: 'success', 'pending_verification', 'rejected', or 'error'."
    )
    response_message: str = Field(
        description="The final result or the message requesting human approval."
    )
    proposed_sql: Optional[str] = Field(
        None,
        description="The SQL query proposed by the agent (only for pending_verification)."
    )
    database_name: Optional[str] = Field(
        None,
        description="The database targeted by the query (only for pending_verification)."
    )

# --- FastAPI Application Setup ---
app = FastAPI(
    title="Mini Agentic SQL Bot",
    description="A LangGraph agent that interacts with multiple MySQL databases with human-in-the-loop verification."
)

# Global store for active agent states awaiting human verification.
AGENT_SESSIONS: Dict[str, dict] = {}
AGENT_APP = None  # Will be initialized once the databases are ready


@app.on_event("startup")
async def startup_event():
    """Initializes the agent workflow at application startup."""
    global AGENT_APP
    print("---  FastAPI server starting. Waiting for database initialization. ---")


@app.post("/init", summary="Initialize Databases", response_model=str)
async def init_databases(request: InitRequest):
    """
    Initializes the agent's databases with the provided MySQL credentials.
    This must be called successfully before any queries.
    """
    global ACTIVE_DATABASES, AGENT_APP
    try:
        # --- FIX: Update ACTIVE_DATABASES in-place ---
        new_databases = initialize_databases(request.databases)
        ACTIVE_DATABASES.clear()
        ACTIVE_DATABASES.update(new_databases)

        # Compile the agent workflow
        AGENT_APP = build_agent_workflow()

        print(f"ACTIVE_DATABASES keys: {list(ACTIVE_DATABASES.keys())}")
        return "Databases initialized successfully. You can now send queries to the /ask endpoint."
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ask", summary="Query the Agent", response_model=AgentResponse)
async def ask_agent(request: QueryRequest):
    """
    Sends a natural language query to the agent or confirms a pending write operation.
    """
    if not AGENT_APP or not ACTIVE_DATABASES:
        raise HTTPException(
            status_code=400,
            detail="Agent is not initialized. Please call the /init endpoint first."
        )

    # --- Handle HIL approval ---
    if request.session_id and request.verification_status:
        return handle_verification_request(request)

    # --- Handle a new query ---
    if not request.query:
        raise HTTPException(status_code=400, detail="Query is required for new requests")

    new_session_id = str(uuid.uuid4())
    initial_state = {
        "query": request.query,
        "sql_query": None,
        "database_name": None,
        "response": "",
        "intent": None,
        "verification_status": None
    }

    try:
        final_state: dict = AGENT_APP.invoke(initial_state)

        if final_state.get("intent") == "write" and final_state.get("verification_status") == "pending":
            AGENT_SESSIONS[new_session_id] = final_state
            return AgentResponse(
                session_id=new_session_id,
                status="pending_verification",
                response_message=final_state.get("response", ""),
                proposed_sql=final_state.get("sql_query"),
                database_name=final_state.get("database_name")
            )
        else:
            # This is a 'read' query or immediate result
            return AgentResponse(
                session_id=new_session_id,
                status="success" if "Error" not in final_state.get("response", "") else "error",
                response_message=final_state.get("response", ""),
                proposed_sql=None,
                database_name=None
            )

    except Exception as e:
        print(f" Unhandled Error during AGENT_APP.invoke: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


def handle_verification_request(request: QueryRequest) -> AgentResponse:
    """Helper function to re-enter the graph after human approval."""
    session_id = request.session_id
    if session_id not in AGENT_SESSIONS:
        raise HTTPException(status_code=404, detail="Session ID not found or expired.")

    pending_state = AGENT_SESSIONS[session_id]

    print(f"---  Verification Request for Session: {session_id} ---")

    if request.verification_status and request.verification_status.lower() == "approved":
        pending_state["verification_status"] = "approved"
        print("[HIL] Human Approved! Re-entering graph to execute SQL.")

        final_state = AGENT_APP.invoke(pending_state)
        del AGENT_SESSIONS[session_id]

        return AgentResponse(
            session_id=session_id,
            status="success",
            response_message=final_state.get("response", "")
        )

    else:
        # Human rejected the write
        del AGENT_SESSIONS[session_id]
        return AgentResponse(
            session_id=session_id,
            status="rejected",
            response_message=" Agent action rejected. Database modification aborted.",
            proposed_sql=pending_state.get("sql_query"),
            database_name=pending_state.get("database_name")
        )
