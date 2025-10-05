from typing import Dict, Any, List
from langchain_community.utilities import SQLDatabase
from sqlalchemy.engine import Engine
import sqlalchemy
import os

# Pydantic model for database credentials (for FastAPI input)
from pydantic import BaseModel, Field

class MySQLCredentials(BaseModel):
    """Schema for MySQL connection details."""
    host: str = Field(..., description="The MySQL server hostname.")
    user: str = Field(..., description="The MySQL username.")
    password: str = Field(..., description="The MySQL user's password.")
    database: str = Field(..., description="The name of the database.")

def get_db_engine(credentials: MySQLCredentials) -> Engine:
    """
    Creates a SQLAlchemy engine for a single MySQL database.
    """
    try:
        connection_uri = (
            f"mysql+mysqlconnector://{credentials.user}:"
            f"{credentials.password}@{credentials.host}/"
            f"{credentials.database}"
        )
        engine = sqlalchemy.create_engine(connection_uri)
        # Test the connection to ensure it's valid
        engine.connect()
        return engine
    except Exception as e:
        print(f" Error connecting to database '{credentials.database}': {e}")
        raise ValueError(f"Failed to connect to MySQL database: {e}")

def initialize_databases(db_list: List[MySQLCredentials]) -> Dict[str, SQLDatabase]:
    """
    Initializes a dictionary of LangChain SQLDatabase objects
    from a list of user-provided credentials.
    """
    if len(db_list) < 2:
        raise ValueError("Must provide at least two databases.")

    print("---  Initializing databases from provided credentials ---")
    
    databases: Dict[str, SQLDatabase] = {}
    
    for creds in db_list:
        db_name = creds.database.lower()
        try:
            engine = get_db_engine(creds)
            db = SQLDatabase(engine=engine)
            databases[db_name] = db
            print(f" Connection successful for database '{db_name}'.")
        except ValueError as e:
            print(f" Could not initialize database '{db_name}'. Skipping.")

    if not databases:
        raise RuntimeError("No databases were successfully initialized.")

    return databases

# Global variable to hold our initialized databases and their tools.
# This will be populated by the FastAPI endpoint.
ACTIVE_DATABASES: Dict[str, SQLDatabase] = {}