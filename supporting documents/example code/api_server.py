#!/usr/bin/env python3
"""
FastAPI backend server for Lifeboard application.

This module provides the main FastAPI application with health checks,
database connections, and API endpoints for accessing lifelog data.
"""

import os
import sys
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Any, Dict, Set
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

# Initialize logging first
from lifeboard.logging_config import setup_logging
setup_logging()  # Ensure logging is properly initialized

from lifeboard.data_manager import load_config, load_secrets
from lifeboard.encryption_utils import encryption_manager
from lifeboard.bee_client import BeeAPIClient
from lifeboard.limitless_client import LimitlessAPIClient
from lifeboard.date_scanner import DateScanner
from lifeboard.port_manager import get_backend_port, get_cors_origins, save_runtime_port_info, cleanup_runtime_config
from .constants import (
    LOGS_DIR,
    FRONTEND_LOG_PATH,
    DEFAULT_DATABASE_PATH,
    DEFAULT_CONFIG_FILE,
    DEFAULT_SECRETS_FILE,
    HTTP_INTERNAL_SERVER_ERROR,
    DEFAULT_API_SERVER_PORT,
    DEFAULT_API_SERVER_HOST,
    API_SERVER_PORT_ENV,
    API_SERVER_HOST_ENV,
    MAX_PAGE_LIMIT,
    LIMITLESS_API_BASE_URL,
    BEE_API_BASE_URL,
    DEFAULT_FRONTEND_PORT,
)

# Initialize frontend_logger with error handling
try:
    frontend_logger = logger.bind(source="frontend")
    frontend_logger.add(
        FRONTEND_LOG_PATH,
        rotation="00:00",
        retention="7 days",
        level="DEBUG",
        format="{time:MM-DD-YYYY HH:mm:ss} | {level} | {message}",
        enqueue=False,  # Disable multiprocessing queue to avoid semaphore issues
        backtrace=True,
        diagnose=True,
        catch=True  # Catch and log exceptions in the handler
    )
    frontend_logger.info("Frontend logger initialized")
except Exception as e:
    # Fallback to stderr if file logging fails
    print(f"Warning: Could not initialize frontend file logger: {e}", file=sys.stderr)
    frontend_logger = logger.bind(source="frontend")
    frontend_logger.add(
        sys.stderr,
        level="DEBUG",
        format="{time:MM-DD-YYYY HH:mm:ss} | {level} | {message}",
        enqueue=False
    )
    frontend_logger.error(f"Falling back to stderr logging due to: {e}")

# Pydantic models for API responses
class ConversationSummary(BaseModel):
    """Summary model for conversation list responses."""

    id: int
    start_time: str
    end_time: Optional[str]
    short_summary: Optional[str]
    device_type: Optional[str]
    state: Optional[str]


class ConversationDetail(BaseModel):
    """Detailed model for individual conversation responses."""

    id: int
    start_time: str
    end_time: Optional[str]
    summary: Optional[str]
    short_summary: Optional[str]
    device_type: Optional[str]
    state: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class PaginatedResponse(BaseModel):
    """Generic paginated response model."""

    total: int
    page: int
    limit: int
    data: List[Any]


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    database_connected: bool
    version: str = "1.0.0"


class FactSummary(BaseModel):
    """Summary model for facts list responses."""

    id: int
    text: str
    tags: Optional[List[str]]
    created_at: Optional[str]
    visibility: Optional[str]


class TodoSummary(BaseModel):
    """Summary model for todos list responses."""

    id: int
    text: str
    completed: Optional[bool]
    created_at: Optional[str]
    alarm_at: Optional[str]


class ApiKeyRequest(BaseModel):
    """Request model for API key validation."""

    service_name: str
    api_key: str


class ApiKeyResponse(BaseModel):
    """Response model for API key operations."""

    service_name: str
    is_valid: bool
    last_validated_at: Optional[str]
    message: str
    api_key: Optional[str] = None  # Include API key for status responses


class ApiKeyStatus(BaseModel):
    """Status model for API key validation state."""

    limitless: Optional[ApiKeyResponse]
    bee: Optional[ApiKeyResponse]


class LogEntry(BaseModel):
    """Model for log entries from frontend."""
    level: str
    message: str
    timestamp: str
    source: str = "frontend"


class DataFetchResponse(BaseModel):
    """Response model for data fetch operations."""
    service_name: str
    total_count: int
    message: str


class EditSessionRequest(BaseModel):
    """Request model for creating a new edit session."""
    item_type: str
    item_id: str
    edit_name: str = Field(..., description="Edit Name - must be unique")
    original_date: str


class EditSessionResponse(BaseModel):
    """Response model for edit session operations."""
    id: int
    item_type: str
    item_id: str
    edit_name: str
    original_date: str
    created_at: str
    updated_at: str
    is_active: bool
    original_content: Optional[str]
    current_content: Optional[str]
    content_format: str


class EditHistoryEntry(BaseModel):
    """Model for edit history entries."""
    id: int
    edit_session_id: int
    content: str
    saved_at: str
    is_current: bool
    save_comment: Optional[str]


class SaveEditRequest(BaseModel):
    """Request model for saving edit content."""
    content: str
    save_comment: Optional[str] = None


class EditSessionListResponse(BaseModel):
    """Response model for listing edit sessions."""
    edit_sessions: List[EditSessionResponse]


class UserViewPreferenceRequest(BaseModel):
    """Request model for setting user view preferences."""
    item_type: str
    item_id: str
    current_edit_session_id: Optional[int] = None  # -1 for Original, None for default, positive for edit session


class UserViewPreferenceResponse(BaseModel):
    """Response model for user view preferences."""
    id: int
    item_type: str
    item_id: str
    current_edit_session_id: Optional[int]
    updated_at: str


class UserSettingsRequest(BaseModel):
    """Request model for updating user settings."""
    timezone: Optional[str] = None
    default_landing_page: Optional[str] = None


class UserSettingsResponse(BaseModel):
    """Response model for user settings."""
    id: int
    timezone: str
    default_landing_page: str


# Global variables for configuration
app_config = None
app_secrets = None
database_path = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.

    Handles startup and shutdown events for the FastAPI application,
    including runtime configuration cleanup, configuration loading,
    and resource cleanup.

    Args:
        app: The FastAPI application instance

    Yields:
        None: Control back to the application
    """
    # Startup
    global app_config, app_secrets, database_path

    logger.info("Starting Lifeboard API server...")
    logger.info(f"Logs directory: {LOGS_DIR}")

    # Clean up any stale runtime configurations from previous runs
    # This prevents port persistence issues and ensures clean startup state
    try:
        cleanup_runtime_config()
        logger.info("Cleaned up stale runtime configurations from previous runs")
    except Exception as e:
        logger.warning(f"Could not clean up stale runtime configs during startup: {e}")

    try:
        # Load configuration and secrets
        app_config = load_config(DEFAULT_CONFIG_FILE)
        app_secrets = load_secrets(DEFAULT_SECRETS_FILE)

        # Set database path
        database_path = app_config.get("database_path", DEFAULT_DATABASE_PATH)
        logger.info(f"Using database at: {database_path}")

        # Initialize database if it doesn't exist
        from lifeboard.process_json_to_db import setup_database
        schema_path = os.path.join("supporting_documents", "schema.sql")
        setup_database(schema_path, database_path)
        logger.info("Database initialization complete")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Lifeboard API server...")
    cleanup_runtime_config()


# Create FastAPI application
app = FastAPI(
    title="Lifeboard API",
    description="Personal lifelog application API for conversation transcripts and lifelog data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # Dynamic CORS origins from config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_database():
    """
    Get database connection dependency.

    Provides a SQLite database connection for dependency injection
    into API endpoints.

    Returns:
        sqlite3.Connection: Database connection

    Raises:
        HTTPException: If database connection fails
    """
    if not database_path:
        raise HTTPException(
            status_code=503,
            detail="Database path not configured",
        )

    db_path = Path(database_path)
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail="Database not available. Please run data ingestion first.",
        )

    try:
        # Configure SQLite for thread safety and allow sharing across threads
        conn = sqlite3.connect(
            str(db_path),
            check_same_thread=False,  # Allow cross-thread usage
            timeout=30.0,  # 30 second timeout for busy database
        )
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.

    Args:
        request: The incoming request
        exc: The exception that occurred

    Returns:
        JSONResponse: Standardized error response
    """
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=HTTP_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "type": "internal_error"},
    )


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Provides basic health status and database connectivity check.

    Returns:
        dict: Health status information
    """
    health_status = {
        "status": "healthy",
        "service": "lifeboard-api",
        "version": "1.0.0",
    }

    # Check database connectivity
    try:
        if database_path:
            db_path = Path(database_path)
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM BeeConversations")
                conversation_count = cursor.fetchone()[0]
                conn.close()

                health_status["database"] = {
                    "status": "connected",
                    "conversations": conversation_count,
                }
            else:
                health_status["database"] = {
                    "status": "not_found",
                    "message": "Database file not found",
                }
        else:
            health_status["database"] = {
                "status": "not_configured",
                "message": "Database path not configured",
            }
    except Exception as e:
        logger.error(f"Health check database error: {e}")
        health_status["database"] = {"status": "error", "message": str(e)}

    return health_status


@app.get("/api/v1/status")
async def api_status():
    """
    API status endpoint with detailed information.

    Returns:
        dict: Detailed API status and configuration
    """
    return {
        "api_version": "v1",
        "service": "lifeboard-api",
        "endpoints": {
            "conversations": "/api/v1/conversations",
            "conversation_details": "/api/v1/conversations/{id}",
            "recent_conversations": "/api/v1/conversations/recent",
            "facts": "/api/v1/facts",
            "fact_details": "/api/v1/facts/{id}",
            "todos": "/api/v1/todos",
            "todo_details": "/api/v1/todos/{id}",
            "search": "/api/v1/search",
            "user_settings": "/api/v1/user-settings",
        },
        "documentation": {"swagger": "/docs", "redoc": "/redoc"},
    }


@app.get("/api/v1/conversations", response_model=PaginatedResponse)
async def get_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(
        10, ge=1, le=MAX_PAGE_LIMIT, description="Items per page"
    ),
    db: sqlite3.Connection = Depends(get_database),
):
    """Get paginated list of conversations."""
    try:
        offset = (page - 1) * limit

        # Get total count
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM BeeConversations")
        total = cursor.fetchone()[0]

        # Get paginated conversations
        cursor.execute(
            """
            SELECT id, start_time, end_time, short_summary, device_type, state
            FROM BeeConversations
            ORDER BY start_time DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        conversations = []
        for row in cursor.fetchall():
            # Get the appropriate content based on user's edit session preference
            short_summary_content = get_conversation_content_with_preference(cursor, row["id"], "short_summary")
            
            conversations.append(
                ConversationSummary(
                    id=row["id"],
                    start_time=row["start_time"],
                    end_time=row["end_time"],
                    short_summary=short_summary_content,
                    device_type=row["device_type"],
                    state=row["state"],
                )
            )

        db.close()
        logger.info(
            f"Retrieved {len(conversations)} conversations (page {page}, total {total})"
        )

        return PaginatedResponse(
            total=total, page=page, limit=limit, data=conversations
        )

    except Exception as e:
        logger.error(f"Error retrieving conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversations")


@app.get("/api/v1/conversations/recent")
async def get_recent_conversations(
    limit: int = Query(5, ge=1, le=20, description="Number of recent conversations"),
    db: sqlite3.Connection = Depends(get_database),
):
    """Get most recent conversations."""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, start_time, end_time, short_summary, device_type, state
            FROM BeeConversations
            ORDER BY start_time DESC
            LIMIT ?
        """,
            (limit,),
        )

        conversations = []
        for row in cursor.fetchall():
            # Get the appropriate content based on user's edit session preference
            short_summary_content = get_conversation_content_with_preference(cursor, row["id"], "short_summary")
            
            conversations.append(
                ConversationSummary(
                    id=row["id"],
                    start_time=row["start_time"],
                    end_time=row["end_time"],
                    short_summary=short_summary_content,
                    device_type=row["device_type"],
                    state=row["state"],
                )
            )

        db.close()
        logger.info(f"Retrieved {len(conversations)} recent conversations")
        return {"recent_conversations": conversations}

    except Exception as e:
        logger.error(f"Error retrieving recent conversations: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recent conversations"
        )


@app.get("/api/v1/conversations/date/{date}")
async def get_conversations_by_date(
    date: str, 
    timezone: str = Query(default="UTC", description="Timezone for date filtering (e.g., 'America/New_York')"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get conversations for a specific date (YYYY-MM-DD format) in the specified timezone."""
    try:
        cursor = db.cursor()
        
        # Convert the date to timezone-aware start and end timestamps
        from datetime import datetime
        
        # Parse the input date
        input_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Set timezone
        if timezone == "UTC":
            user_tz = ZoneInfo('UTC')
        else:
            user_tz = ZoneInfo(timezone)
        
        # Create start and end of day in user's timezone
        start_of_day = input_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
        end_of_day = input_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=user_tz)
        
        # Convert to UTC for database query
        start_utc = start_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        end_utc = end_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        
        logger.info(f"Filtering conversations for {date} in {timezone}: {start_utc} to {end_utc}")
        
        # Query conversations where start_time falls within the specified date in user's timezone
        cursor.execute(
            """
            SELECT id, start_time, end_time, summary, short_summary, device_type, state
            FROM BeeConversations
            WHERE start_time >= ? AND start_time < ?
            ORDER BY start_time ASC
        """,
            (start_utc, end_utc),
        )

        conversations = []
        for row in cursor.fetchall():
            # Get the appropriate content based on user's edit session preference
            summary_content = get_conversation_content_with_preference(cursor, row["id"], "summary")
            short_summary_content = get_conversation_content_with_preference(cursor, row["id"], "short_summary")
            
            conversations.append({
                "id": row["id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "summary": summary_content,
                "short_summary": short_summary_content,
                "device_type": row["device_type"],
                "state": row["state"]
            })

        db.close()
        logger.info(f"Retrieved {len(conversations)} conversations for date {date}")
        return {"conversations": conversations}

    except Exception as e:
        logger.error(f"Error retrieving conversations for date {date}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve conversations for date {date}"
        )


@app.get("/api/v1/todos/date/{date}")
async def get_todos_by_date(
    date: str, 
    timezone: str = Query(default="UTC", description="Timezone for date filtering (e.g., 'America/New_York')"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get todos for a specific date (YYYY-MM-DD format) in the specified timezone."""
    try:
        cursor = db.cursor()
        
        # Convert the date to timezone-aware start and end timestamps
        from datetime import datetime
        
        # Parse the input date
        input_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Set timezone
        if timezone == "UTC":
            user_tz = ZoneInfo('UTC')
        else:
            user_tz = ZoneInfo(timezone)
        
        # Create start and end of day in user's timezone
        start_of_day = input_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
        end_of_day = input_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=user_tz)
        
        # Convert to UTC for database query
        start_utc = start_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        end_utc = end_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        
        # Query todos where created_at falls within the specified date in user's timezone
        cursor.execute(
            """
            SELECT id, text, completed, created_at, alarm_at
            FROM BeeTodos
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at ASC
        """,
            (start_utc, end_utc),
        )

        todos = []
        for row in cursor.fetchall():
            todos.append({
                "id": row["id"],
                "text": row["text"],
                "completed": bool(row["completed"]),
                "created_at": row["created_at"],
                "alarm_at": row["alarm_at"]
            })

        db.close()
        logger.info(f"Retrieved {len(todos)} todos for date {date}")
        return {"todos": todos}

    except Exception as e:
        logger.error(f"Error retrieving todos for date {date}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve todos for date {date}"
        )


@app.get("/api/v1/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: int, db: sqlite3.Connection = Depends(get_database)
):
    """Get detailed view of a specific conversation."""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, start_time, end_time, summary, short_summary,
                   device_type, state, created_at, updated_at
            FROM BeeConversations
            WHERE id = ?
        """,
            (conversation_id,),
        )

        row = cursor.fetchone()
        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Get the appropriate content based on user's edit session preference
        summary_content = get_conversation_content_with_preference(cursor, conversation_id, "summary")
        short_summary_content = get_conversation_content_with_preference(cursor, conversation_id, "short_summary")

        conversation = ConversationDetail(
            id=row["id"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            summary=summary_content,
            short_summary=short_summary_content,
            device_type=row["device_type"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

        db.close()
        logger.info(f"Retrieved conversation detail for ID {conversation_id}")
        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation")


@app.get("/api/v1/search")
async def search_conversations(
    q: str = Query(..., description="Search query"),
    limit: int = Query(
        50, ge=1, le=50, description="Maximum results to return"
    ),
    db: sqlite3.Connection = Depends(get_database),
):
    """Search conversations by text content."""
    try:
        cursor = db.cursor()

        # Search in summary and short_summary fields
        search_query = f"%{q}%"
        cursor.execute(
            """
            SELECT id, start_time, end_time, short_summary, device_type, state
            FROM BeeConversations
            WHERE (summary LIKE ? OR short_summary LIKE ?)
            AND state = 'COMPLETED'
            ORDER BY start_time DESC
            LIMIT ?
        """,
            (search_query, search_query, limit),
        )

        conversations = []
        for row in cursor.fetchall():
            conversations.append(
                ConversationSummary(
                    id=row["id"],
                    start_time=row["start_time"],
                    end_time=row["end_time"],
                    short_summary=row["short_summary"],
                    device_type=row["device_type"],
                    state=row["state"],
                )
            )

        db.close()
        logger.info(f"Search for '{q}' returned {len(conversations)} results")

        return {
            "query": q,
            "total_results": len(conversations),
            "results": conversations,
        }

    except Exception as e:
        logger.error(f"Error searching conversations for '{q}': {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/api/v1/facts", response_model=PaginatedResponse)
async def get_facts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(
        10, ge=1, le=MAX_PAGE_LIMIT, description="Items per page"
    ),
    confirmed: bool = Query(True, description="Filter by confirmed facts only"),
    db: sqlite3.Connection = Depends(get_database),
):
    """Get paginated list of facts."""
    try:
        offset = (page - 1) * limit

        # Build query based on confirmed filter
        where_clause = "WHERE visibility = 'private'" if confirmed else ""

        # Get total count
        cursor = db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM BeeFacts {where_clause}")
        total = cursor.fetchone()[0]

        # Get paginated facts
        cursor.execute(
            f"""
            SELECT id, text, tags, created_at, visibility
            FROM BeeFacts
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        facts = []
        for row in cursor.fetchall():
            # Parse tags JSON if present
            tags = None
            if row["tags"]:
                try:
                    import json

                    tags = json.loads(row["tags"])
                except (json.JSONDecodeError, TypeError):
                    tags = None

            facts.append(
                FactSummary(
                    id=row["id"],
                    text=row["text"],
                    tags=tags,
                    created_at=row["created_at"],
                    visibility=row["visibility"],
                )
            )

        db.close()
        logger.info(f"Retrieved {len(facts)} facts (page {page}, total {total})")

        return PaginatedResponse(total=total, page=page, limit=limit, data=facts)

    except Exception as e:
        logger.error(f"Error retrieving facts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve facts")


@app.get("/api/v1/facts/{fact_id}", response_model=FactSummary)
async def get_fact_detail(fact_id: int, db: sqlite3.Connection = Depends(get_database)):
    """Get detailed view of a specific fact."""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, text, tags, created_at, visibility
            FROM BeeFacts
            WHERE id = ?
        """,
            (fact_id,),
        )

        row = cursor.fetchone()
        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Fact not found")

        # Parse tags JSON if present
        tags = None
        if row["tags"]:
            try:
                import json

                tags = json.loads(row["tags"])
            except (json.JSONDecodeError, TypeError):
                tags = None

        fact = FactSummary(
            id=row["id"],
            text=row["text"],
            tags=tags,
            created_at=row["created_at"],
            visibility=row["visibility"],
        )

        db.close()
        logger.info(f"Retrieved fact detail for ID {fact_id}")
        return fact

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving fact {fact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve fact")


@app.get("/api/v1/todos", response_model=PaginatedResponse)
async def get_todos(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(
        10, ge=1, le=MAX_PAGE_LIMIT, description="Items per page"
    ),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    db: sqlite3.Connection = Depends(get_database),
):
    """Get paginated list of todos."""
    try:
        offset = (page - 1) * limit

        # Build query based on completed filter
        where_clause = ""
        params = []
        if completed is not None:
            where_clause = "WHERE completed = ?"
            params.append(completed)

        # Get total count
        cursor = db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM BeeTodos {where_clause}", params)
        total = cursor.fetchone()[0]

        # Get paginated todos
        query_params = params + [limit, offset]
        cursor.execute(
            f"""
            SELECT id, text, completed, created_at, alarm_at
            FROM BeeTodos
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """,
            query_params,
        )

        todos = []
        for row in cursor.fetchall():
            todos.append(
                TodoSummary(
                    id=row["id"],
                    text=row["text"],
                    completed=(
                        bool(row["completed"]) if row["completed"] is not None else None
                    ),
                    created_at=row["created_at"],
                    alarm_at=row["alarm_at"],
                )
            )

        db.close()
        logger.info(f"Retrieved {len(todos)} todos (page {page}, total {total})")

        return PaginatedResponse(total=total, page=page, limit=limit, data=todos)

    except Exception as e:
        logger.error(f"Error retrieving todos: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve todos")


@app.get("/api/v1/todos/{todo_id}", response_model=TodoSummary)
async def get_todo_detail(todo_id: int, db: sqlite3.Connection = Depends(get_database)):
    """Get detailed view of a specific todo."""
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, text, completed, created_at, alarm_at
            FROM BeeTodos
            WHERE id = ?
        """,
            (todo_id,),
        )

        row = cursor.fetchone()
        if not row:
            db.close()
            raise HTTPException(status_code=404, detail="Todo not found")

        todo = TodoSummary(
            id=row["id"],
            text=row["text"],
            completed=bool(row["completed"]) if row["completed"] is not None else None,
            created_at=row["created_at"],
            alarm_at=row["alarm_at"],
        )

        db.close()
        logger.info(f"Retrieved todo detail for ID {todo_id}")
        return todo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving todo {todo_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve todo")


# API Key Management Endpoints

@app.post("/api/v1/settings/api-keys/validate", response_model=ApiKeyResponse)
async def validate_api_key(
    request: ApiKeyRequest, db: sqlite3.Connection = Depends(get_database)
):
    """Validate and store an API key."""
    try:
        from lifeboard.encryption_utils import encryption_manager
        from lifeboard.limitless_client import LimitlessAPIClient
        from lifeboard.bee_client import BeeAPIClient
        from datetime import datetime
        
        logger.info("="*80)
        logger.info("🔑 API KEY VALIDATION STARTED")
        logger.info("="*80)
        logger.info(f"📋 Service Name: {request.service_name}")
        logger.info(f"🔐 API Key Length: {len(request.api_key)} characters")
        logger.info(f"🔐 API Key Preview: {request.api_key[:8]}...{request.api_key[-4:] if len(request.api_key) > 8 else '***'}")
        logger.info(f"🕐 Timestamp: {datetime.utcnow().isoformat()}")
        
        service_name = request.service_name.lower()
        api_key = request.api_key.strip()

        # Input validation
        logger.info("🔍 VALIDATING INPUT...")
        if not api_key:
            logger.error("❌ VALIDATION FAILED: Empty API key provided")
            raise HTTPException(status_code=400, detail="API key cannot be empty")
        logger.info("✅ API key is not empty")

        if service_name not in ["limitless", "bee"]:
            error_msg = f"Invalid service name: {service_name}"
            logger.error(f"❌ VALIDATION FAILED: {error_msg}")
            raise HTTPException(
                status_code=400, detail="Service name must be 'limitless' or 'bee'"
            )
        logger.info(f"✅ Service name '{service_name}' is valid")
            
        logger.info("✅ Input validation passed")

        # API key validation against external service
        logger.info("🌐 VALIDATING API KEY WITH EXTERNAL SERVICE...")
        is_valid = False
        message = "Invalid API key"
        api_response_details = {}

        try:
            if service_name == "limitless":
                logger.info("🔗 Validating against Limitless API...")
                import requests
                headers = {"x-api-key": api_key, "Content-Type": "application/json"}
                api_url = f"{LIMITLESS_API_BASE_URL}/v1/lifelogs"
                params = {"limit": 1}
                
                # Log curl equivalent
                curl_cmd = f"curl -X GET '{api_url}?limit=1'"
                for k, v in headers.items():
                    curl_cmd += f" -H '{k}: {v}'"
                logger.info(f"API Request (curl):\n{curl_cmd}")
                
                logger.info(f"📡 Making request to: {api_url}")
                logger.debug(f"📋 Request headers: {headers}")
                
                response = requests.get(
                    api_url,
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                api_response_details = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "response_time": "N/A"  # requests doesn't easily provide this
                }
                logger.info(f"📊 API Response Status: {response.status_code}")
                logger.debug(f"📋 API Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    is_valid = True
                    message = "API key validated successfully"
                    logger.info("✅ Limitless API key validation SUCCESSFUL")
                    try:
                        response_data = response.json()
                        logger.debug(f"📄 API Response Data: {response_data}")
                    except:
                        logger.debug("📄 Could not parse API response as JSON")
                else:
                    is_valid = False
                    message = f"API validation failed with status {response.status_code}"
                    logger.warning(f"❌ Limitless API key validation FAILED: {message}")
                    try:
                        error_data = response.text
                        logger.debug(f"📄 API Error Response: {error_data}")
                    except:
                        logger.debug("📄 Could not read API error response")
                        
            elif service_name == "bee":
                logger.info("🐝 Validating against Bee API...")
                import requests
                headers = {"x-api-key": api_key, "Content-Type": "application/json"}
                api_url = f"{BEE_API_BASE_URL}/conversations"
                params = {"limit": 1}
                
                # Log curl equivalent
                curl_cmd = f"curl -X GET '{api_url}?limit=1'"
                for k, v in headers.items():
                    curl_cmd += f" -H '{k}: {v}'"
                logger.info(f"API Request (curl):\n{curl_cmd}")
                
                logger.info(f"📡 Making request to: {api_url}")
                logger.debug(f"📋 Request headers: {headers}")
                
                response = requests.get(
                    api_url,
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                api_response_details = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "response_time": "N/A"
                }
                logger.info(f"📊 API Response Status: {response.status_code}")
                logger.debug(f"📋 API Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    is_valid = True
                    message = "API key validated successfully"
                    logger.info("✅ Bee API key validation SUCCESSFUL")
                    try:
                        response_data = response.json()
                        logger.debug(f"📄 API Response Data: {response_data}")
                    except:
                        logger.debug("📄 Could not parse API response as JSON")
                else:
                    is_valid = False
                    message = f"API validation failed with status {response.status_code}"
                    logger.warning(f"❌ Bee API key validation FAILED: {message}")
                    try:
                        error_data = response.text
                        logger.debug(f"📄 API Error Response: {error_data}")
                    except:
                        logger.debug("📄 Could not read API error response")
        except Exception as e:
            error_msg = f"API key validation failed for {service_name}: {str(e)}"
            logger.error(f"💥 EXCEPTION during API validation: {error_msg}", exc_info=True)
            is_valid = False
            message = f"API key validation failed: {str(e)}"

        # Database operations
        logger.info("💾 STORING RESULTS IN DATABASE...")
        cursor = db.cursor()
        current_time = datetime.utcnow().isoformat() + "Z"
        logger.info(f"🕐 Current timestamp: {current_time}")

        try:
            if is_valid:
                logger.info("🔐 Encrypting valid API key...")
                encrypted_key = encryption_manager.encrypt(api_key)
                logger.info("✅ API key encrypted successfully")
                logger.debug(f"🔐 Encrypted key length: {len(encrypted_key)} characters")
                
                logger.info(f"💾 Storing valid API key for {service_name}...")
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ApiKeys
                    (service_name, encrypted_key, is_valid, last_validated_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (service_name, encrypted_key, is_valid, current_time, current_time),
                )
                logger.info("✅ Valid API key stored successfully in database")
            else:
                logger.warning(f"❌ Not storing invalid API key for {service_name}")
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO ApiKeys
                    (service_name, encrypted_key, is_valid, last_validated_at, updated_at)
                    VALUES (?, NULL, ?, ?, ?)
                """,
                    (service_name, is_valid, current_time, current_time),
                )
                logger.info("📝 Invalid API key status updated in database")
                
            # Verify database operation
            logger.info("🔍 Verifying database storage...")
            cursor.execute("SELECT * FROM ApiKeys WHERE service_name = ?", (service_name,))
            stored_key = cursor.fetchone()
            if stored_key:
                logger.info(f"✅ Database verification successful for {service_name}")
                logger.debug(f"📋 Stored record: service={stored_key[0]}, is_valid={stored_key[2]}, last_validated={stored_key[3]}")
            else:
                logger.error(f"❌ Database verification FAILED for {service_name}")
                
        except Exception as e:
            logger.error(f"💥 DATABASE ERROR: {str(e)}", exc_info=True)
            raise

        db.commit()
        logger.info("✅ Database transaction committed")
        db.close()
        logger.info("🔐 Database connection closed")

        # Prepare response
        response_data = ApiKeyResponse(
            service_name=service_name,
            is_valid=is_valid,
            last_validated_at=current_time if is_valid else None,
            message=message,
        )
        
        logger.info("📤 PREPARING RESPONSE...")
        logger.info(f"📋 Response: {response_data.dict()}")
        logger.info("="*80)
        logger.info("🎉 API KEY VALIDATION COMPLETED")
        logger.info("="*80)
        
        return response_data

    except HTTPException:
        logger.error("🚫 HTTP Exception occurred during API key validation")
        raise
    except Exception as e:
        logger.error(f"💥 UNEXPECTED ERROR during API key validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to validate API key")


@app.get("/api/v1/settings/api-keys/status", response_model=ApiKeyStatus)
async def get_api_key_status(db: sqlite3.Connection = Depends(get_database)):
    """Get the validation status of all API keys."""
    try:
        from lifeboard.encryption_utils import encryption_manager

        logger.info("📊 API KEY STATUS REQUEST STARTED")
        logger.info("🔍 Querying database for API key status...")

        cursor = db.cursor()
        cursor.execute(
            """
            SELECT service_name, encrypted_key, is_valid, last_validated_at
            FROM ApiKeys
            WHERE service_name IN ('limitless', 'bee')
        """
        )

        rows = cursor.fetchall()
        logger.info(f"📋 Found {len(rows)} API key records in database")

        for i, row in enumerate(rows):
            logger.debug(f"   Record {i+1}: service={row['service_name']}, valid={row['is_valid']}, last_validated={row['last_validated_at']}")

        db.close()
        logger.info("🔐 Database connection closed")

        # Build response
        status = ApiKeyStatus(limitless=None, bee=None)
        logger.info("🏗️ Building status response...")

        for row in rows:
            service_name = row["service_name"]

            # Decrypt the API key for the response
            decrypted_key = None
            if row["encrypted_key"]:
                try:
                    decrypted_key = encryption_manager.decrypt(row["encrypted_key"])
                    logger.debug(f"Successfully decrypted API key for {service_name}")
                except Exception as e:
                    logger.error(f"Failed to decrypt API key for {service_name}: {e}")

            api_response = ApiKeyResponse(
                service_name=service_name,
                is_valid=bool(row["is_valid"]),
                last_validated_at=row["last_validated_at"],
                message="Valid" if row["is_valid"] else "Not validated",
                api_key=decrypted_key
            )

            if service_name == "limitless":
                status.limitless = api_response
            elif service_name == "bee":
                status.bee = api_response

        return status

    except Exception as e:
        logger.error(f"Error retrieving API key status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API key status")


@app.delete("/api/v1/settings/api-keys/{service_name}")
async def delete_api_key(
    service_name: str, db: sqlite3.Connection = Depends(get_database)
):
    """Delete an API key for a specific service."""
    try:
        service_name = service_name.lower()

        if service_name not in ["limitless", "bee"]:
            raise HTTPException(
                status_code=400, detail="Service name must be 'limitless' or 'bee'"
            )

        cursor = db.cursor()
        cursor.execute("DELETE FROM ApiKeys WHERE service_name = ?", (service_name,))

        if cursor.rowcount == 0:
            db.close()
            raise HTTPException(status_code=404, detail="API key not found")

        db.commit()
        db.close()

        return {"message": f"API key for {service_name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


# Calendar Endpoints

@app.get("/api/v1/calendar/dates")
async def get_calendar_dates(
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    refresh: Optional[bool] = Query(False, description="Force refresh of calendar data"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get all dates that have data in the database for calendar display."""
    try:
        logger.info(f"Calendar dates requested - start: {start_date}, end: {end_date}, refresh: {refresh}")
        
        # Initialize date scanner
        config = load_config()
        db_path = config.get('DATABASE_PATH', DEFAULT_DATABASE_PATH)
        scanner = DateScanner(db_path, DEFAULT_CONFIG_FILE)
        
        # Force refresh if requested or if calendar_dates table is empty
        should_refresh = refresh
        if not should_refresh:
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM calendar_dates")
            count = cursor.fetchone()[0]
            should_refresh = count == 0
            logger.info(f"Calendar dates table has {count} entries, refresh needed: {should_refresh}")
        
        if should_refresh:
            logger.info("Refreshing calendar dates by scanning all database tables")
            scan_stats = scanner.scan_all_tables()
            logger.info(f"Calendar date scan completed: {scan_stats}")
        
        # Get the dates for the requested range
        dates_with_data = scanner.get_dates_for_calendar(start_date, end_date)
        
        logger.info(f"Returning {len(dates_with_data)} calendar dates")
        return {
            "dates": dates_with_data,
            "count": len(dates_with_data),
            "start_date": start_date,
            "end_date": end_date,
            "refreshed": should_refresh
        }
        
    except Exception as e:
        logger.error(f"Error getting calendar dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve calendar dates")


@app.post("/api/v1/calendar/refresh")
async def refresh_calendar_dates(db: sqlite3.Connection = Depends(get_database)):
    """Force refresh of calendar dates by scanning all database tables."""
    try:
        logger.info("Manual calendar refresh requested")
        
        # Initialize date scanner
        config = load_config()
        db_path = config.get('DATABASE_PATH', DEFAULT_DATABASE_PATH)
        scanner = DateScanner(db_path, DEFAULT_CONFIG_FILE)
        
        # Perform the scan
        scan_stats = scanner.scan_all_tables()
        
        logger.info(f"Manual calendar refresh completed: {scan_stats}")
        return {
            "message": "Calendar dates refreshed successfully",
            "stats": scan_stats
        }
        
    except Exception as e:
        logger.error(f"Error refreshing calendar dates: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh calendar dates")


def build_curl_command_from_request(request: Request, body: bytes = None) -> str:
    """Build a curl command from FastAPI request."""
    method = request.method
    url = str(request.url)
    headers = dict(request.headers)
    
    # Build curl command
    curl_cmd = f"curl -X {method} '{url}'"
    
    # Add headers (no redaction)
    for key, value in headers.items():
        curl_cmd += f" -H '{key}: {value}'"
    
    # Add body if present
    if body and len(body) > 0:
        try:
            # Try to parse as JSON for better formatting
            body_json = json.loads(body)
            body_str = json.dumps(body_json, indent=2)
            curl_cmd += f" -d '{body_str}'"
        except:
            try:
                body_str = body.decode('utf-8')
                curl_cmd += f" -d '{body_str}'"
            except:
                curl_cmd += f" -d '[BINARY_DATA:{len(body)}_bytes]'"
    
    return curl_cmd


@app.middleware("http")
async def log_request_curl(request: Request, call_next):
    """Log incoming requests in curl format without consuming body."""
    # Store the original receive function
    receive_ = request._receive
    
    # Create a new receive function that captures the body
    body_parts = []
    
    async def receive():
        message = await receive_()
        if message["type"] == "http.request" and "body" in message:
            body_parts.append(message["body"])
        return message
    
    # Replace the receive function
    request._receive = receive
    
    # Get request details
    method = request.method
    url = str(request.url)
    
    # Process the request first
    response = await call_next(request)
    
    # Now build curl command with captured body
    body = b"".join(body_parts) if body_parts else b""
    curl_cmd = build_curl_command_from_request(request, body)
    
    # Log the curl command
    logger.info(f"API Request (curl):\n{curl_cmd}")
    
    return response


@app.post("/api/v1/logs")
async def log_frontend_message(log_entries: List[LogEntry]):
    """
    Endpoint to receive and log messages from the frontend.
    
    Args:
        log_entries: List of log entries from the frontend
        
    Returns:
        JSONResponse: Success or error response
    """
    try:
        for entry in log_entries:
            # Map frontend log levels to logger methods
            log_method = getattr(frontend_logger, entry.level.lower(), frontend_logger.info)
            log_method(f"[{entry.source}] {entry.message}")
            
        return JSONResponse(
            content={"status": "success", "message": "Logs received and processed"},
            status_code=200
        )
    except Exception as e:
        logger.error(f"Error processing frontend logs: {str(e)}")
        return JSONResponse(
            content={"status": "error", "message": "Failed to process logs"},
            status_code=HTTP_INTERNAL_SERVER_ERROR
        )


# Add comprehensive logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with detailed information."""
    import time
    import json
    
    # Log incoming request
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log request details
    logger.info(f"🔵 INCOMING REQUEST")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   URL: {request.url}")
    logger.info(f"   Client IP: {client_ip}")
    logger.info(f"   User-Agent: {user_agent}")
    logger.info(f"   Headers: {dict(request.headers)}")
    
    # For POST/PUT requests, try to log the body (for API key operations)
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # Read request body
            body = await request.body()
            if body:
                try:
                    body_json = json.loads(body.decode())
                    # Mask sensitive data like API keys
                    if "api_key" in body_json:
                        masked_body = body_json.copy()
                        api_key = masked_body["api_key"]
                        if len(api_key) > 8:
                            masked_body["api_key"] = api_key[:4] + "***" + api_key[-4:]
                        else:
                            masked_body["api_key"] = "***"
                        logger.info(f"   Request Body: {masked_body}")
                    else:
                        logger.info(f"   Request Body: {body_json}")
                except json.JSONDecodeError:
                    logger.info(f"   Request Body (raw): {body.decode()[:500]}...")
            
            # Reconstruct request for downstream processing
            async def receive():
                return {"type": "http.request", "body": body}
            
            request._receive = receive
        except Exception as e:
            logger.warning(f"   Could not read request body: {e}")
    
    # Process the request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response details
        logger.info(f"🟢 RESPONSE SENT")
        logger.info(f"   Status Code: {response.status_code}")
        logger.info(f"   Process Time: {process_time:.3f}s")
        logger.info(f"   Response Headers: {dict(response.headers)}")
        
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"🔴 REQUEST FAILED")
        logger.error(f"   Error: {str(e)}")
        logger.error(f"   Process Time: {process_time:.3f}s")
        raise


async def get_user_timezone(db: sqlite3.Connection) -> str:
    """Get user's timezone preference from the database.

    Args:
        db: Database connection

    Returns:
        User's timezone preference or "UTC" as fallback

    Example:
        >>> timezone = await get_user_timezone(db)
        >>> # Returns "America/New_York" or "UTC" if not set
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            "SELECT timezone FROM UserSettings ORDER BY id ASC LIMIT 1"
        )
        row = cursor.fetchone()

        if row and row["timezone"]:
            timezone = row["timezone"]
            logger.info(f"Retrieved user timezone preference: {timezone}")
            return timezone
        else:
            logger.info("No user timezone preference found, using UTC as fallback")
            return "UTC"

    except Exception as e:
        logger.warning(f"Error retrieving user timezone preference: {e}, using UTC as fallback")
        return "UTC"


async def get_existing_limitless_ids(db: sqlite3.Connection) -> Set[str]:
    """
    Retrieve existing Limitless lifelog IDs from database for duplicate detection.

    Args:
        db: Database connection

    Returns:
        Set of existing lifelog ID strings

    Example:
        >>> existing_ids = await get_existing_limitless_ids(db)
        >>> # Returns {"lifelog_123", "lifelog_456", ...}
    """
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id FROM LimitlessLifelogs")
        rows = cursor.fetchall()

        existing_ids = {str(row["id"]) for row in rows}
        logger.info(f"Found {len(existing_ids)} existing Limitless lifelog IDs in database")
        return existing_ids

    except Exception as e:
        logger.error(f"Error retrieving existing Limitless IDs: {e}")
        return set()


async def get_existing_bee_ids(db: sqlite3.Connection, data_type: str) -> Set[str]:
    """
    Retrieve existing Bee data IDs from database for duplicate detection.

    Args:
        db: Database connection
        data_type: Type of Bee data ('conversations', 'facts', 'todos', 'locations')

    Returns:
        Set of existing ID strings for the specified data type

    Example:
        >>> existing_ids = await get_existing_bee_ids(db, 'conversations')
        >>> # Returns {"123", "456", ...}
    """
    try:
        cursor = db.cursor()

        # Map data types to table names
        table_mapping = {
            'conversations': 'BeeConversations',
            'facts': 'BeeFacts',
            'todos': 'BeeTodos',
            'locations': 'BeeLocations'
        }

        table_name = table_mapping.get(data_type)
        if not table_name:
            logger.error(f"Unknown Bee data type: {data_type}")
            return set()

        cursor.execute(f"SELECT id FROM {table_name}")
        rows = cursor.fetchall()

        existing_ids = {str(row["id"]) for row in rows}
        logger.info(f"Found {len(existing_ids)} existing Bee {data_type} IDs in database")
        return existing_ids

    except Exception as e:
        logger.error(f"Error retrieving existing Bee {data_type} IDs: {e}")
        return set()


# Update fetch_data endpoint
@app.post("/api/v1/{service_name}/fetch-data", response_model=DataFetchResponse)
async def fetch_data(
    service_name: str,
    db: sqlite3.Connection = Depends(get_database)
):
    """Fetch data for a service."""
    try:
        # Get API key from database
        cursor = db.cursor()
        cursor.execute(
            "SELECT encrypted_key FROM ApiKeys WHERE service_name = ? AND is_valid = 1",
            (service_name,)
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="No valid API key found")

        # Decrypt API key
        api_key = encryption_manager.decrypt(row["encrypted_key"])

        # Get user timezone preference for API calls
        user_timezone = await get_user_timezone(db)
        logger.info(f"Using timezone '{user_timezone}' for {service_name} API calls")
        
        try:
            if service_name == "limitless":
                # Initialize Limitless client
                client = LimitlessAPIClient(api_key)

                # Get existing IDs from database for duplicate detection
                logger.info("Retrieving existing Limitless lifelog IDs for duplicate detection...")
                existing_ids = await get_existing_limitless_ids(db)
                logger.info(f"Found {len(existing_ids)} existing Limitless lifelogs in database")

                # Get total count first
                try:
                    total_count = client.get_total_count()
                    logger.info(f"Got total count for Limitless: {total_count}")
                except Exception as e:
                    logger.error(f"Failed to get total count from Limitless API: {e}")
                    raise HTTPException(status_code=500, detail=f"Failed to get total count: {str(e)}")

                # Fetch data using cursor-based pagination with duplicate detection
                logger.info(f"Fetching Limitless lifelogs with timezone: {user_timezone} and duplicate detection enabled")
                try:
                    # Create query with user timezone preference
                    from lifeboard.limitless_client import LifelogQuery
                    query = LifelogQuery(timezone=user_timezone)

                    # Use the client's built-in pagination with duplicate detection
                    all_lifelogs = client.fetch_lifelogs(query=query, existing_ids=existing_ids)

                    if all_lifelogs:
                        await store_limitless_batch(db, all_lifelogs)
                        actual_count = len(all_lifelogs)
                        logger.info(f"Fetched {actual_count} Limitless lifelogs using timezone {user_timezone}")

                        # Refresh calendar dates after storing Limitless data
                        try:
                            logger.info("Refreshing calendar dates after storing Limitless data...")
                            config = load_config()
                            db_path = config.get('DATABASE_PATH', DEFAULT_DATABASE_PATH)
                            scanner = DateScanner(db_path, DEFAULT_CONFIG_FILE)
                            scan_stats = scanner.scan_all_tables()
                            logger.info(f"Calendar refresh after Limitless data fetch completed: {scan_stats}")
                        except Exception as e:
                            logger.error(f"Failed to refresh calendar dates after storing Limitless data: {e}")
                    else:
                        logger.info("No Limitless lifelogs found")
                        actual_count = 0

                except Exception as e:
                    logger.error(f"Error fetching Limitless lifelogs: {e}")
                    raise HTTPException(status_code=500, detail=f"Error fetching lifelogs: {str(e)}")

                return DataFetchResponse(
                    service_name=service_name,
                    total_count=actual_count,
                    message=f"Successfully fetched {actual_count} lifelogs using timezone {user_timezone}"
                )
                
            elif service_name == "bee":
                # Initialize Bee client
                client = BeeAPIClient(api_key)

                # Get existing IDs from database for duplicate detection
                logger.info("Retrieving existing Bee data IDs for duplicate detection...")
                existing_conversation_ids = await get_existing_bee_ids(db, 'conversations')
                logger.info(f"Found {len(existing_conversation_ids)} existing Bee conversations in database")

                total_items_fetched = 0

                # Fetch conversations with duplicate detection
                logger.info("Fetching Bee conversations with duplicate detection enabled...")
                try:
                    conversations = client.fetch_conversations(existing_ids=existing_conversation_ids)
                    if conversations:
                        await store_bee_batch(db, conversations)
                        total_items_fetched += len(conversations)
                        logger.info(f"Fetched {len(conversations)} new Bee conversations (duplicate detection stopped early fetch)")
                    else:
                        logger.info("No new Bee conversations found (all existing data already in database)")
                except Exception as e:
                    logger.error(f"Error fetching conversations: {e}")
                    raise HTTPException(status_code=500, detail=f"Error fetching conversations: {str(e)}")
                
                # Fetch facts with duplicate detection
                logger.info("Fetching Bee facts with duplicate detection enabled...")
                try:
                    existing_fact_ids = await get_existing_bee_ids(db, 'facts')
                    logger.info(f"Found {len(existing_fact_ids)} existing Bee facts in database")

                    facts = client.fetch_facts(existing_ids=existing_fact_ids)
                    if facts:
                        await store_bee_facts(db, facts)
                        total_items_fetched += len(facts)
                        logger.info(f"Fetched {len(facts)} new Bee facts (duplicate detection stopped early fetch)")
                    else:
                        logger.info("No new Bee facts found (all existing data already in database)")
                except Exception as e:
                    logger.error(f"Error fetching facts: {e}")
                    # Continue with other data types even if facts fail

                # Fetch locations with duplicate detection
                logger.info("Fetching Bee locations with duplicate detection enabled...")
                try:
                    existing_location_ids = await get_existing_bee_ids(db, 'locations')
                    logger.info(f"Found {len(existing_location_ids)} existing Bee locations in database")

                    locations = client.fetch_locations(existing_ids=existing_location_ids)
                    if locations:
                        await store_bee_locations(db, locations)
                        total_items_fetched += len(locations)
                        logger.info(f"Fetched {len(locations)} new Bee locations (duplicate detection stopped early fetch)")
                    else:
                        logger.info("No new Bee locations found (all existing data already in database)")
                except Exception as e:
                    logger.error(f"Error fetching locations: {e}")
                    # Continue with other data types even if locations fail

                # Fetch todos with duplicate detection
                logger.info("Fetching Bee todos with duplicate detection enabled...")
                try:
                    existing_todo_ids = await get_existing_bee_ids(db, 'todos')
                    logger.info(f"Found {len(existing_todo_ids)} existing Bee todos in database")

                    todos = client.fetch_todos(existing_ids=existing_todo_ids)
                    if todos:
                        await store_bee_todos(db, todos)
                        total_items_fetched += len(todos)
                        logger.info(f"Fetched {len(todos)} new Bee todos (duplicate detection stopped early fetch)")
                    else:
                        logger.info("No new Bee todos found (all existing data already in database)")
                except Exception as e:
                    logger.error(f"Error fetching todos: {e}")
                    # Continue even if todos fail
                
                return DataFetchResponse(
                    service_name=service_name,
                    total_count=total_items_fetched,
                    message=f"Successfully fetched {total_items_fetched} total items"
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid service name")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during data fetch: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in fetch_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def store_bee_batch(db: sqlite3.Connection, batch: List[Dict[str, Any]]) -> None:
    """Store a batch of Bee conversations directly in the database, with progress tracking."""
    try:
        total_processed = 0
        for conversation in batch:
            # Store the main conversation record
            db.execute(
                """
                INSERT OR REPLACE INTO BeeConversations 
                (id, start_time, end_time, device_type, summary, short_summary, state, created_at, updated_at, utterances)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation['id'],
                    conversation.get('start_time'),
                    conversation.get('end_time'),
                    conversation.get('device_type'),
                    conversation.get('summary'),
                    conversation.get('short_summary'),
                    conversation.get('state'),
                    conversation.get('created_at'),
                    conversation.get('updated_at'),
                    json.dumps(conversation.get('utterances', []))
                )
            )
            
            # Store the primary_location if present
            primary_location = conversation.get('primary_location')
            if primary_location:
                # First, delete existing primary location for this conversation to avoid duplicates
                db.execute("DELETE FROM BeePrimaryLocations WHERE conversation_id = ?", (conversation['id'],))
                
                # Insert the primary location
                db.execute(
                    """
                    INSERT INTO BeePrimaryLocations 
                    (conversation_id, address, latitude, longitude, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        conversation['id'],  # conversation_id (foreign key)
                        primary_location.get('address'),
                        primary_location.get('latitude'),
                        primary_location.get('longitude'),
                        primary_location.get('created_at')
                    )
                )
                
                logger.info(f"Stored conversation {conversation['id']} with primary location in database")
            else:
                logger.info(f"Stored conversation {conversation['id']} without primary location in database")
            
            db.commit()
            total_processed += 1
        
        logger.info(f"Finished writing {total_processed} Bee conversations")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing Bee batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def store_limitless_batch(db: sqlite3.Connection, batch: List[Dict[str, Any]]) -> None:
    """Store a batch of Limitless lifelogs directly in the database, with progress tracking."""
    try:
        total_processed = 0
        for lifelog in batch:
            # Store the main lifelog record
            db.execute(
                """
                INSERT OR REPLACE INTO LimitlessLifelogs 
                (id, title, markdown, startTime, endTime, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lifelog['id'],
                    lifelog.get('title'),
                    lifelog.get('markdown'),
                    lifelog.get('startTime'),
                    lifelog.get('endTime'),
                    lifelog.get('updated_at')
                )
            )
            
            # Store the contents array
            contents = lifelog.get('contents', [])
            if contents:
                # First, delete existing contents for this lifelog to avoid duplicates
                db.execute("DELETE FROM LimitlessContents WHERE lifelog_id = ?", (lifelog['id'],))
                
                # Insert each content item
                for content_item in contents:
                    db.execute(
                        """
                        INSERT INTO LimitlessContents 
                        (lifelog_id, type, content, startTime, endTime, startOffsetMs, endOffsetMs, speakerName, speakerIdentifier)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            lifelog['id'],  # lifelog_id (foreign key)
                            content_item.get('type'),
                            content_item.get('content'),
                            content_item.get('startTime'),
                            content_item.get('endTime'),
                            content_item.get('startOffsetMs'),
                            content_item.get('endOffsetMs'),
                            content_item.get('speakerName'),
                            content_item.get('speakerIdentifier')
                        )
                    )
            
            db.commit()
            total_processed += 1
        
        logger.info(f"Finished writing {total_processed} Limitless lifelogs")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing Limitless batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def store_bee_facts(db: sqlite3.Connection, facts: List[Dict[str, Any]]) -> None:
    """Store a batch of Bee facts directly in the database."""
    try:
        # Store in database
        try:
            for fact in facts:
                db.execute(
                    """
                    INSERT OR REPLACE INTO BeeFacts 
                    (id, text, tags, created_at, visibility)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        fact['id'],
                        fact.get('text'),
                        json.dumps(fact.get('tags', [])),
                        fact.get('created_at'),
                        fact.get('visibility')
                    )
                )
                db.commit()
                logger.info(f"Stored fact {fact['id']} in database")
        except Exception as e:
            logger.error(f"Failed to store facts in database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store facts in database: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing Bee facts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def store_bee_locations(db: sqlite3.Connection, locations: List[Dict[str, Any]]) -> None:
    """Store a batch of Bee locations directly in the database."""
    try:
        # Store in database
        try:
            for location in locations:
                db.execute(
                    """
                    INSERT OR REPLACE INTO BeeLocations 
                    (id, latitude, longitude, address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        location['id'],
                        location.get('latitude'),
                        location.get('longitude'),
                        location.get('address'),
                        location.get('created_at')
                    )
                )
                db.commit()
                logger.info(f"Stored location {location['id']} in database")
        except Exception as e:
            logger.error(f"Failed to store locations in database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store locations in database: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing Bee locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def store_bee_todos(db: sqlite3.Connection, todos: List[Dict[str, Any]]) -> None:
    """Store a batch of Bee todos directly in the database."""
    try:
        # Store in database
        try:
            for todo in todos:
                db.execute(
                    """
                    INSERT OR REPLACE INTO BeeTodos 
                    (id, text, completed, created_at, alarm_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        todo['id'],
                        todo.get('text'),
                        todo.get('completed', False),
                        todo.get('created_at'),
                        todo.get('alarm_at')
                    )
                )
                db.commit()
                logger.info(f"Stored todo {todo['id']} in database")
        except Exception as e:
            logger.error(f"Failed to store todos in database: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store todos in database: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error storing Bee todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/facts/date/{date}")
async def get_facts_by_date(
    date: str, 
    timezone: str = Query(default="UTC", description="Timezone for date filtering (e.g., 'America/New_York')"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get facts for a specific date (YYYY-MM-DD format) in the specified timezone."""
    try:
        cursor = db.cursor()
        
        # Convert the date to timezone-aware start and end timestamps
        from datetime import datetime
        
        # Parse the input date
        input_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Set timezone
        if timezone == "UTC":
            user_tz = ZoneInfo('UTC')
        else:
            user_tz = ZoneInfo(timezone)
        
        # Create start and end of day in user's timezone
        start_of_day = input_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
        end_of_day = input_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=user_tz)
        
        # Convert to UTC for database query
        start_utc = start_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        end_utc = end_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        
        # Query facts where created_at falls within the specified date in user's timezone
        cursor.execute(
            """
            SELECT id, text, tags, created_at, visibility
            FROM BeeFacts
            WHERE created_at >= ? AND created_at < ?
            ORDER BY created_at ASC
        """,
            (start_utc, end_utc),
        )

        facts = []
        for row in cursor.fetchall():
            # Parse tags JSON if it exists
            tags = []
            if row["tags"]:
                try:
                    import json
                    tags = json.loads(row["tags"])
                except (json.JSONDecodeError, TypeError):
                    tags = []
            
            facts.append({
                "id": row["id"],
                "text": row["text"],
                "tags": tags,
                "created_at": row["created_at"],
                "visibility": row["visibility"]
            })

        db.close()
        logger.info(f"Retrieved {len(facts)} facts for date {date}")
        return {"facts": facts}

    except Exception as e:
        logger.error(f"Error fetching facts by date {date}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch facts: {str(e)}")


# Edit functionality endpoints

@app.post("/api/v1/edit-sessions", response_model=EditSessionResponse)
async def create_edit_session(
    request: EditSessionRequest,
    db: sqlite3.Connection = Depends(get_database)
):
    """Create a new edit session for an item."""
    logger.info(f"🔧 Creating edit session - item_type: {request.item_type}, item_id: {request.item_id}, edit_name: '{request.edit_name}', original_date: {request.original_date}")
    
    try:
        cursor = db.cursor()
        
        # Check if edit session name already exists for this item
        logger.debug(f"🔧 Checking for existing edit session with name '{request.edit_name}' for {request.item_type} {request.item_id}")
        cursor.execute("""
            SELECT id FROM EditSessions 
            WHERE item_type = ? AND item_id = ? AND edit_name = ? AND is_active = 1
        """, (request.item_type, request.item_id, request.edit_name))
        
        existing_session = cursor.fetchone()
        if existing_session:
            logger.warning(f"🔧 Edit session name '{request.edit_name}' already exists for {request.item_type} {request.item_id}")
            raise HTTPException(
                status_code=409, 
                detail=f"Edit session name '{request.edit_name}' already exists for this {request.item_type}. Please choose a different name."
            )
        
        # Get original content based on item type
        original_content = None
        logger.debug(f"🔧 Fetching original content for {request.item_type} with ID {request.item_id}")
        
        if request.item_type == "conversation":
            cursor.execute("SELECT summary FROM BeeConversations WHERE id = ?", (request.item_id,))
            row = cursor.fetchone()
            if row:
                original_content = row["summary"]
                logger.debug(f"🔧 Found conversation content, length: {len(original_content) if original_content else 0} characters")
            else:
                logger.warning(f"🔧 Conversation with ID {request.item_id} not found")
        elif request.item_type == "fact":
            cursor.execute("SELECT text FROM BeeFacts WHERE id = ?", (request.item_id,))
            row = cursor.fetchone()
            if row:
                original_content = row["text"]
                logger.debug(f"🔧 Found fact content, length: {len(original_content) if original_content else 0} characters")
            else:
                logger.warning(f"🔧 Fact with ID {request.item_id} not found")
        elif request.item_type == "lifelog":
            cursor.execute("SELECT markdown FROM LimitlessLifelogs WHERE id = ?", (request.item_id,))
            row = cursor.fetchone()
            if row:
                original_content = row["markdown"]
                logger.debug(f"🔧 Found lifelog content, length: {len(original_content) if original_content else 0} characters")
            else:
                logger.warning(f"🔧 Lifelog with ID {request.item_id} not found")
        # Add more item types as needed
        
        if original_content is None:
            logger.error(f"🔧 {request.item_type.title()} with ID {request.item_id} not found")
            raise HTTPException(status_code=404, detail=f"{request.item_type.title()} not found")
        
        # Create edit session
        now = datetime.now(ZoneInfo('UTC')).isoformat()
        logger.debug(f"🔧 Creating edit session record in database at {now}")
        
        try:
            cursor.execute("""
                INSERT INTO EditSessions (
                    item_type, item_id, edit_name, original_date, created_at, updated_at,
                    is_active, original_content, current_content, content_format
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                request.item_type, request.item_id, request.edit_name, request.original_date,
                now, now, True, original_content, original_content, "markdown"
            ))
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed" in str(e):
                logger.warning(f"🔧 Database constraint violation: Edit session name '{request.edit_name}' already exists for {request.item_type} {request.item_id}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Edit session name '{request.edit_name}' already exists for this {request.item_type}. Please choose a different name."
                )
            else:
                logger.error(f"🔧 Database integrity error: {e}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        
        edit_session_id = cursor.lastrowid
        logger.info(f"🔧 Created edit session with ID {edit_session_id}")
        db.commit()
        
        # Create initial history entry
        logger.debug(f"🔧 Creating initial history entry for edit session {edit_session_id}")
        cursor.execute("""
            INSERT INTO EditHistory (edit_session_id, content, saved_at, is_current, save_comment)
            VALUES (?, ?, ?, ?, ?)
        """, (edit_session_id, original_content, now, True, "Initial version"))
        
        db.commit()
        logger.info(f"🔧 Successfully created edit session '{request.edit_name}' for {request.item_type} {request.item_id}")
        
        return EditSessionResponse(
            id=edit_session_id,
            item_type=request.item_type,
            item_id=request.item_id,
            edit_name=request.edit_name,
            original_date=request.original_date,
            created_at=now,
            updated_at=now,
            is_active=True,
            original_content=original_content,
            current_content=original_content,
            content_format="markdown"
        )
        
    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except Exception as e:
        logger.error(f"🔧 Error creating edit session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create edit session: {str(e)}")


@app.get("/api/v1/edit-sessions/history/{session_id}")
async def get_edit_history(
    session_id: int,
    db: sqlite3.Connection = Depends(get_database)
):
    """Get edit history for a session."""
    logger.info(f"📜 Fetching edit history for session {session_id}")
    
    try:
        cursor = db.cursor()
        
        # First get session info for context
        cursor.execute("SELECT edit_name, item_type, item_id FROM EditSessions WHERE id = ?", (session_id,))
        session_info = cursor.fetchone()
        if session_info:
            edit_name, item_type, item_id = session_info
            logger.info(f"📜 Edit session {session_id}: {edit_name} for {item_type} {item_id}")
        else:
            raise HTTPException(status_code=404, detail="Edit session not found")
        
        # Get all history entries for this session
        cursor.execute("""
            SELECT id, content, saved_at, is_current, save_comment
            FROM EditHistory
            WHERE edit_session_id = ?
            ORDER BY saved_at ASC
        """, (session_id,))
        
        history_entries = []
        for row in cursor.fetchall():
            history_entries.append({
                "id": row["id"],
                "content": row["content"],
                "saved_at": row["saved_at"],
                "is_current": row["is_current"],
                "save_comment": row["save_comment"]
            })
        
        return {
            "edit_session_id": session_id,
            "edit_name": edit_name,
            "item_type": item_type,
            "item_id": item_id,
            "history": history_entries
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"📜 Error fetching edit history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch edit history")


@app.get("/api/v1/limitless-contents/date/{date}")
async def get_limitless_contents_by_date(
    date: str,
    timezone: str = Query("UTC", description="Timezone for date parsing"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get all Limitless contents for a specific date with proper hierarchy."""
    try:
        # Validate date format
        try:
            input_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Please use YYYY-MM-DD.")

        # Convert the date to timezone-aware start and end timestamps
        if timezone == "UTC":
            user_tz = ZoneInfo('UTC')
        else:
            user_tz = ZoneInfo(timezone)

        start_of_day = input_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=user_tz)
        end_of_day = input_date.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=user_tz)

        # Convert to UTC for database query
        start_utc = start_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')
        end_utc = end_of_day.astimezone(ZoneInfo('UTC')).isoformat().replace('+00:00', 'Z')

        # First get all top-level content items (depth=0)
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT lc.id, lc.lifelog_id, lc.type, lc.content, lc.startTime, lc.endTime,
                   lc.startOffsetMs, lc.endOffsetMs, lc.speakerName, lc.speakerIdentifier,
                   lc."order", lc.depth, lc.parent_id, lc.original_json
            FROM LimitlessContents lc
            JOIN LimitlessLifelogs ll ON lc.lifelog_id = ll.id
            WHERE date(ll.startTime) = ? AND lc.depth = 0
            ORDER BY lc.startTime ASC, lc."order" ASC
            """,
            (date,)
        )
        
        top_level_rows = cursor.fetchall()
        
        # Function to recursively get children
        def get_children(parent_id):
            cursor.execute(
                """
                SELECT id, lifelog_id, type, content, startTime, endTime,
                       startOffsetMs, endOffsetMs, speakerName, speakerIdentifier,
                       "order", depth, parent_id, original_json
                FROM LimitlessContents
                WHERE parent_id = ?
                ORDER BY "order" ASC
                """,
                (parent_id,)
            )
            children = []
            for row in cursor.fetchall():
                child = {
                    "id": row["id"],
                    "lifelog_id": row["lifelog_id"],
                    "type": row["type"],
                    "content": row["content"],
                    "startTime": row["startTime"],
                    "endTime": row["endTime"],
                    "startOffsetMs": row["startOffsetMs"],
                    "endOffsetMs": row["endOffsetMs"],
                    "speakerName": row["speakerName"],
                    "speakerIdentifier": row["speakerIdentifier"],
                    "order": row["order"],
                    "depth": row["depth"]
                }
                # Recursively get this child's children
                child_children = get_children(row["id"])
                if child_children:
                    child["children"] = child_children
                children.append(child)
            return children
        
        # Build the hierarchical structure
        contents = []
        for row in top_level_rows:
            content = {
                "id": row["id"],
                "lifelog_id": row["lifelog_id"],
                "type": row["type"],
                "content": row["content"],
                "startTime": row["startTime"],
                "endTime": row["endTime"],
                "startOffsetMs": row["startOffsetMs"],
                "endOffsetMs": row["endOffsetMs"],
                "speakerName": row["speakerName"],
                "speakerIdentifier": row["speakerIdentifier"],
                "order": row["order"],
                "depth": row["depth"],
                "parent_id": row["parent_id"],
                "original_json": row["original_json"]
            }
            # Recursively get this content's children
            child_children = get_children(row["id"])
            if child_children:
                content["children"] = child_children
            contents.append(content)

        logger.info(f"Found {len(contents)} limitless contents for date {date}")

        return {
            "date": date,
            "timezone": timezone,
            "contents": contents
        }

    except Exception as e:
        logger.error(f"Error retrieving limitless contents for date {date}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve limitless contents: {str(e)}"
        )


@app.get("/api/v1/edit-sessions/{item_type}/{item_id}", response_model=EditSessionListResponse)
async def get_edit_sessions(
    item_type: str,
    item_id: str,
    db: sqlite3.Connection = Depends(get_database)
):
    """Get all edit sessions for a specific item."""
    logger.info(f"🔍 Fetching edit sessions for {item_type} {item_id}")
    
    try:
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT id, item_type, item_id, edit_name, original_date, created_at, updated_at,
                   is_active, original_content, current_content, content_format
            FROM EditSessions
            WHERE item_type = ? AND item_id = ?
            ORDER BY created_at DESC
        """, (item_type, item_id))
        
        edit_sessions = []
        rows = cursor.fetchall()
        logger.debug(f"🔍 Found {len(rows)} edit sessions for {item_type} {item_id}")
        
        # Get original content and date for the "Original" option
        original_content = None
        original_date = None
        
        if item_type == "conversation":
            cursor.execute("SELECT summary, start_time FROM BeeConversations WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                original_content = row["summary"]
                # Extract date from start_time (format: YYYY-MM-DD)
                if row["start_time"]:
                    original_date = row["start_time"][:10]  # Extract YYYY-MM-DD part
        elif item_type == "fact":
            cursor.execute("SELECT text, created_at FROM BeeFacts WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if row:
                original_content = row["text"]
                # Extract date from created_at (format: YYYY-MM-DD)
                if row["created_at"]:
                    original_date = row["created_at"][:10]  # Extract YYYY-MM-DD part
        
        # Add an "Original" entry at the top if we have original content
        if original_content and original_date:
            logger.debug(f"🔍 Adding 'Original' option with content length: {len(original_content)}, date: {original_date}")
            original_entry = EditSessionResponse(
                id=-1,  # Special ID for original content
                item_type=item_type,
                item_id=item_id,
                edit_name="Original",
                original_date=original_date,  # Use the actual date from the item
                created_at=original_date + "T00:00:00Z",  # Use item's date as created_at
                updated_at=original_date + "T00:00:00Z",  # Use item's date as updated_at
                is_active=True,
                original_content=original_content,
                current_content=original_content,
                content_format="markdown"
            )
            edit_sessions.append(original_entry)
        
        for row in rows:
            session = EditSessionResponse(
                id=row["id"],
                item_type=row["item_type"],
                item_id=row["item_id"],
                edit_name=row["edit_name"],
                original_date=row["original_date"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                is_active=row["is_active"],
                original_content=row["original_content"],
                current_content=row["current_content"],
                content_format=row["content_format"]
            )
            edit_sessions.append(session)
            logger.debug(f"🔍 Edit session: {session.edit_name} (ID: {session.id}, active: {session.is_active})")
        
        logger.info(f"🔍 Successfully retrieved {len(edit_sessions)} total options (including Original) for {item_type} {item_id}")
        return EditSessionListResponse(edit_sessions=edit_sessions)
        
    except Exception as e:
        logger.error(f"🔍 Error fetching edit sessions for {item_type} {item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch edit sessions: {str(e)}")


@app.get("/api/v1/edit-sessions/{session_id}", response_model=EditSessionResponse)
async def get_edit_session(
    session_id: int,
    db: sqlite3.Connection = Depends(get_database)
):
    """Get a specific edit session by ID."""
    logger.info(f"🔍 Fetching edit session with ID {session_id}")
    
    try:
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT id, item_type, item_id, edit_name, original_date, created_at, updated_at,
                   is_active, original_content, current_content, content_format
            FROM EditSessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"🔍 Edit session with ID {session_id} not found")
            raise HTTPException(status_code=404, detail="Edit session not found")

        session = EditSessionResponse(
            id=row["id"],
            item_type=row["item_type"],
            item_id=row["item_id"],
            edit_name=row["edit_name"],
            original_date=row["original_date"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_active=row["is_active"],
            original_content=row["original_content"],
            current_content=row["current_content"],
            content_format=row["content_format"]
        )
        
        logger.info(f"🔍 Successfully retrieved edit session '{session.edit_name}' for {session.item_type} {session.item_id}")
        logger.debug(f"🔍 Session details - Active: {session.is_active}, Content length: {len(session.current_content or '') if session.current_content else 0}")
        
        return session
        
    except Exception as e:
        logger.error(f"🔍 Error fetching edit session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch edit session: {str(e)}")


@app.put("/api/v1/edit-sessions/{session_id}/save")
async def save_edit_content(
    session_id: int,
    request: SaveEditRequest,
    db: sqlite3.Connection = Depends(get_database)
):
    """Save content for an edit session."""
    logger.info(f"💾 Saving content for edit session {session_id}")
    logger.debug(f"💾 Content length: {len(request.content)} characters, Save comment: '{request.save_comment}'")
    
    try:
        cursor = db.cursor()
        now = datetime.now(ZoneInfo('UTC')).isoformat()
        
        # First, get the current session info for logging
        cursor.execute("SELECT edit_name, item_type, item_id FROM EditSessions WHERE id = ?", (session_id,))
        session_info = cursor.fetchone()
        if session_info:
            logger.debug(f"💾 Saving '{session_info['edit_name']}' for {session_info['item_type']} {session_info['item_id']}")
        
        # Update current content in edit session
        cursor.execute("""
            UPDATE EditSessions 
            SET current_content = ?, updated_at = ?
            WHERE id = ?
        """, (request.content, now, session_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"💾 Edit session {session_id} not found during save attempt")
            raise HTTPException(status_code=404, detail="Edit session not found")
        
        logger.debug(f"💾 Updated edit session {session_id} with new content")
        
        # Mark previous history entries as not current
        cursor.execute("""
            UPDATE EditHistory 
            SET is_current = FALSE
            WHERE edit_session_id = ?
        """, (session_id,))
        
        previous_count = cursor.rowcount
        logger.debug(f"💾 Marked {previous_count} previous history entries as not current")
        
        # Add new history entry
        cursor.execute("""
            INSERT INTO EditHistory (edit_session_id, content, saved_at, is_current, save_comment)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, request.content, now, True, request.save_comment))
        
        history_id = cursor.lastrowid
        logger.debug(f"💾 Created new history entry with ID {history_id}")
        
        db.commit()
        
        logger.info(f"💾 Successfully saved edit session {session_id} at {now}")
        if session_info:
            logger.info(f"💾 Edit '{session_info['edit_name']}' saved for {session_info['item_type']} {session_info['item_id']}")
        
        return {"message": "Edit saved successfully", "saved_at": now, "history_id": history_id}
        
    except Exception as e:
        logger.error(f"💾 Error saving edit content for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save edit content: {str(e)}")


# User View Preferences endpoints

@app.get("/api/v1/user-preferences/{item_type}/{item_id}")
async def get_user_view_preference(
    item_type: str,
    item_id: str,
    db: sqlite3.Connection = Depends(get_database)
):
    """Get user's current view preference for an item."""
    logger.info(f"👤 Fetching user view preference for {item_type} {item_id}")
    
    try:
        cursor = db.cursor()
        
        cursor.execute("""
            SELECT id, item_type, item_id, current_edit_session_id, updated_at
            FROM UserViewPreferences
            WHERE item_type = ? AND item_id = ?
        """, (item_type, item_id))
        
        row = cursor.fetchone()
        if row:
            preference = UserViewPreferenceResponse(
                id=row["id"],
                item_type=row["item_type"],
                item_id=row["item_id"],
                current_edit_session_id=row["current_edit_session_id"],
                updated_at=row["updated_at"]
            )
            logger.info(f"👤 Found preference: {item_type} {item_id} → session {preference.current_edit_session_id}")
            return preference
        else:
            logger.debug(f"👤 No preference found for {item_type} {item_id}, will use default (Original)")
            # Return default preference (Original = -1)
            return {
                "item_type": item_type,
                "item_id": item_id,
                "current_edit_session_id": -1,  # Default to Original
                "message": "No preference set, using default (Original)"
            }
        
    except Exception as e:
        logger.error(f"👤 Error fetching user preference for {item_type} {item_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user preference: {str(e)}")


@app.post("/api/v1/user-preferences", response_model=UserViewPreferenceResponse)
async def set_user_view_preference(
    request: UserViewPreferenceRequest,
    db: sqlite3.Connection = Depends(get_database)
):
    """Set user's current view preference for an item."""
    logger.info(f"👤 Setting user view preference: {request.item_type} {request.item_id} → session {request.current_edit_session_id}")
    
    try:
        cursor = db.cursor()
        now = datetime.now(ZoneInfo('UTC')).isoformat()
        
        # Use UPSERT (INSERT OR REPLACE) to handle both new and existing preferences
        cursor.execute("""
            INSERT OR REPLACE INTO UserViewPreferences 
            (item_type, item_id, current_edit_session_id, updated_at)
            VALUES (?, ?, ?, ?)
        """, (request.item_type, request.item_id, request.current_edit_session_id, now))
        
        preference_id = cursor.lastrowid
        db.commit()
        
        logger.info(f"👤 Successfully set preference: {request.item_type} {request.item_id} → session {request.current_edit_session_id}")
        
        return UserViewPreferenceResponse(
            id=preference_id,
            item_type=request.item_type,
            item_id=request.item_id,
            current_edit_session_id=request.current_edit_session_id,
            updated_at=now
        )
        
    except Exception as e:
        logger.error(f"👤 Error setting user preference: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set user preference: {str(e)}")


def get_conversation_content_with_preference(cursor: sqlite3.Cursor, conversation_id: int, field_name: str = "summary") -> str:
    """
    Get conversation content respecting user's edit session preference.

    Args:
        cursor: Database cursor
        conversation_id: ID of the conversation
        field_name: Field to return ('summary' or 'short_summary')

    Returns:
        str: Content from preferred edit session or original content
    """
    try:
        # Check if user has a preference for this conversation
        cursor.execute("""
            SELECT current_edit_session_id
            FROM UserViewPreferences
            WHERE item_type = 'conversation' AND item_id = ?
        """, (str(conversation_id),))

        preference = cursor.fetchone()

        if preference and preference["current_edit_session_id"] and preference["current_edit_session_id"] != -1:
            # User has selected a custom edit session
            edit_session_id = preference["current_edit_session_id"]
            logger.debug(f"🎯 Using edit session {edit_session_id} for conversation {conversation_id}")

            # Get the current content from the edit session
            cursor.execute("""
                SELECT current_content
                FROM EditSessions
                WHERE id = ? AND item_type = 'conversation' AND item_id = ? AND is_active = 1
            """, (edit_session_id, str(conversation_id)))

            edit_session = cursor.fetchone()
            if edit_session and edit_session["current_content"]:
                # Edit sessions currently only edit the 'summary' field
                # If requesting 'summary', return the edited content
                # If requesting other fields like 'short_summary', fall back to original
                if field_name == "summary":
                    logger.debug(f"🎯 Found edited content for conversation {conversation_id} (length: {len(edit_session['current_content'])})")
                    return edit_session["current_content"]
                else:
                    logger.debug(f"🎯 Edit session exists but field '{field_name}' not edited, falling back to original")
            else:
                logger.warning(f"🎯 Edit session {edit_session_id} not found for conversation {conversation_id}, falling back to original")

        # Fall back to original content
        logger.debug(f"🎯 Using original content for conversation {conversation_id}")
        cursor.execute(f"SELECT {field_name} FROM BeeConversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row and row[field_name]:
            return row[field_name]

        return ""

    except Exception as e:
        logger.error(f"🎯 Error getting conversation content with preference for {conversation_id}: {e}")
        # Fall back to original content on error
        cursor.execute(f"SELECT {field_name} FROM BeeConversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        if row and row[field_name]:
            return row[field_name]
        return ""
    

@app.get("/api/v1/lifelogs/date/{date}")
async def get_lifelogs_by_date(
    date: str,
    timezone: str = Query("UTC", description="Timezone for date parsing"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get all Limitless lifelogs for a specific date from the local database."""
    try:
        logger.info(f"Retrieving lifelogs for date: {date} (timezone: {timezone})")
        
        # Validate date format
        try:
            year, month, day = date.split("-")
            datetime(int(year), int(month), int(day))  # Validate date
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid date format: {date}. Expected YYYY-MM-DD."
            )
            
        # Validate timezone
        try:
            tz = ZoneInfo(timezone)
        except:
            logger.warning(f"Invalid timezone: {timezone}, falling back to UTC")
            tz = ZoneInfo("UTC")
            
        # Calculate the start and end of the day in the specified timezone
        user_date = datetime.fromisoformat(f"{date}T00:00:00").replace(tzinfo=tz)
        start_dt = user_date.astimezone(ZoneInfo("UTC"))
        end_dt = (user_date.replace(hour=23, minute=59, second=59)).astimezone(ZoneInfo("UTC"))
        
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")
        
        logger.info(f"Querying lifelogs between {start_date} and {end_date} (UTC)")
        
        # Query lifelogs from the database that have start time on the specified date
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT id, title, markdown, startTime, endTime, updated_at 
            FROM LimitlessLifelogs
            WHERE date(startTime) = ?
            ORDER BY startTime ASC
            """,
            (date,)
        )
        
        rows = cursor.fetchall()
        lifelogs = []
        
        for row in rows:
            lifelog = {
                "id": row["id"],
                "title": row["title"],
                "markdown": row["markdown"],
                "startTime": row["startTime"],
                "endTime": row["endTime"],
                "updated_at": row["updated_at"]
            }
            lifelogs.append(lifelog)
            
        logger.info(f"Found {len(lifelogs)} lifelogs for date {date}")
            
        return {
            "date": date,
            "timezone": timezone,
            "lifelogs": lifelogs
        }
        
    except Exception as e:
        logger.error(f"Error retrieving lifelogs for date {date}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve lifelogs: {str(e)}"
        )


@app.get("/api/v1/limitless-contents/date/{date}")
async def get_limitless_contents_by_date(
    date: str,
    timezone: str = Query("UTC", description="Timezone for date parsing"),
    db: sqlite3.Connection = Depends(get_database)
):
    """Get all Limitless contents for a specific date from the local database."""
    try:
        logger.info(f"Retrieving limitless contents for date: {date} (timezone: {timezone})")

        # Validate date format
        try:
            year, month, day = date.split("-")
            datetime(int(year), int(month), int(day))  # Validate date
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: {date}. Expected YYYY-MM-DD."
            )

        # Validate timezone
        try:
            tz = ZoneInfo(timezone)
        except:
            logger.warning(f"Invalid timezone: {timezone}, falling back to UTC")
            tz = ZoneInfo("UTC")

        # Query limitless contents from the database that have start time on the specified date
        cursor = db.cursor()
        cursor.execute(
            """
            SELECT lc.id, lc.lifelog_id, lc.type, lc.content, lc.startTime, lc.endTime,
                   lc.startOffsetMs, lc.endOffsetMs, lc.speakerName, lc.speakerIdentifier
            FROM LimitlessContents lc
            JOIN LimitlessLifelogs ll ON lc.lifelog_id = ll.id
            WHERE date(ll.startTime) = ?
            ORDER BY lc.startTime ASC, lc."order" ASC
            """,
            (date,)
        )

        rows = cursor.fetchall()
        contents = []

        for row in rows:
            content = {
                "id": row["id"],
                "lifelog_id": row["lifelog_id"],
                "type": row["type"],
                "content": row["content"],
                "startTime": row["startTime"],
                "endTime": row["endTime"],
                "startOffsetMs": row["startOffsetMs"],
                "endOffsetMs": row["endOffsetMs"],
                "speakerName": row["speakerName"],
                "speakerIdentifier": row["speakerIdentifier"]
            }
            contents.append(content)

        logger.info(f"Found {len(contents)} limitless contents for date {date}")

        return {
            "date": date,
            "timezone": timezone,
            "contents": contents
        }

    except Exception as e:
        logger.error(f"Error retrieving limitless contents for date {date}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve limitless contents: {str(e)}"
        )


if __name__ == "__main__":
    """
    Main entry point for running the API server directly.

    This allows the server to be started with: python -m lifeboard.api_server
    or: python lifeboard/api_server.py
    """
    import os

    # Get configuration from environment or use defaults
    API_SERVER_PORT = int(os.environ.get(API_SERVER_PORT_ENV, DEFAULT_API_SERVER_PORT))
    API_SERVER_HOST = os.environ.get(API_SERVER_HOST_ENV, DEFAULT_API_SERVER_HOST)

    logger.info(f"Starting Lifeboard API server on {API_SERVER_HOST}:{API_SERVER_PORT}")

    # Run the server
    uvicorn.run(
        "lifeboard.api_server:app",
        host=API_SERVER_HOST,
        port=API_SERVER_PORT,
        reload=False,  # Set to True for development
        log_level="info"
    )


# UserSettings API Endpoints

@app.get("/api/v1/user-settings", response_model=UserSettingsResponse)
async def get_user_settings(db: sqlite3.Connection = Depends(get_database)):
    """Get user settings from the database."""
    try:
        cursor = db.cursor()

        # Get the first (and should be only) user settings record
        cursor.execute("""
            SELECT id, timezone, default_landing_page
            FROM UserSettings
            ORDER BY id ASC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row:
            return UserSettingsResponse(
                id=row['id'],
                timezone=row['timezone'],
                default_landing_page=row['default_landing_page']
            )
        else:
            # No settings exist, create default settings
            default_timezone = "UTC"
            default_landing_page = "/dashboard"

            cursor.execute("""
                INSERT INTO UserSettings (timezone, default_landing_page)
                VALUES (?, ?)
            """, (default_timezone, default_landing_page))

            settings_id = cursor.lastrowid
            db.commit()

            logger.info(f"Created default user settings with ID: {settings_id}")

            return UserSettingsResponse(
                id=settings_id,
                timezone=default_timezone,
                default_landing_page=default_landing_page
            )

    except Exception as e:
        logger.error(f"Error retrieving user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user settings")


@app.put("/api/v1/user-settings", response_model=UserSettingsResponse)
async def update_user_settings(
    request: UserSettingsRequest,
    db: sqlite3.Connection = Depends(get_database)
):
    """Update user settings in the database."""
    try:
        cursor = db.cursor()

        # Get existing settings or create if none exist
        cursor.execute("""
            SELECT id, timezone, default_landing_page
            FROM UserSettings
            ORDER BY id ASC
            LIMIT 1
        """)

        row = cursor.fetchone()

        if row:
            # Update existing settings
            current_timezone = row['timezone']
            current_landing_page = row['default_landing_page']
            settings_id = row['id']

            # Use provided values or keep current ones
            new_timezone = request.timezone if request.timezone is not None else current_timezone
            new_landing_page = request.default_landing_page if request.default_landing_page is not None else current_landing_page

            cursor.execute("""
                UPDATE UserSettings
                SET timezone = ?, default_landing_page = ?
                WHERE id = ?
            """, (new_timezone, new_landing_page, settings_id))

            logger.info(f"Updated user settings: timezone={new_timezone}, landing_page={new_landing_page}")

        else:
            # Create new settings
            new_timezone = request.timezone if request.timezone is not None else "UTC"
            new_landing_page = request.default_landing_page if request.default_landing_page is not None else "/dashboard"

            cursor.execute("""
                INSERT INTO UserSettings (timezone, default_landing_page)
                VALUES (?, ?)
            """, (new_timezone, new_landing_page))

            settings_id = cursor.lastrowid
            logger.info(f"Created new user settings with ID: {settings_id}")

        db.commit()

        return UserSettingsResponse(
            id=settings_id,
            timezone=new_timezone,
            default_landing_page=new_landing_page
        )

    except Exception as e:
        logger.error(f"Error updating user settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user settings")
