"""
FastAPI REST API for IRIS Chat System.

This module provides a FastAPI interface to the IRIS chat system,
exposing the core functionality as REST endpoints.

Endpoints:
    POST /chat: Process a conversation through IRIS agents
    GET /health: Health check endpoint
    GET /: Root endpoint with API info
    GET /databases: List available databases
    POST /reset: Clear server caches

Functions:
    get_chat_processor: Lazy import for async chat model
    get_streaming_chat_processor: Lazy import for streaming chat model
    stream_chat_response: Async generator for streaming responses
    chat_endpoint: Main chat endpoint handler
    health_check: Health check handler
    root: Root endpoint handler
    get_databases: Database listing handler
    reset_server: Cache reset handler
    startup_event: FastAPI startup hook
    shutdown_event: FastAPI shutdown hook

Classes:
    ChatMessage: Single message in a conversation
    ChatRequest: Incoming chat request payload
    ChatResponse: Non-streaming response payload
    HealthResponse: Health check response payload
"""

from typing import Any, Callable, Dict, List, Optional
import asyncio
import importlib
import logging
import queue
import threading

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .utils.logging_format import configure_root_logger
from .utils.env_config import config

API_VERSION = "1.0.0"

configure_root_logger()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IRIS Chat API",
    description=(
        "RBC IRIS Intelligent Response System - AI-powered financial chat assistant"
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    """Single message in a conversation."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    messages: List[ChatMessage] = Field(..., description="Conversation history")
    stream: bool = Field(default=False, description="Enable streaming response")
    db_names: Optional[List[str]] = Field(
        default=None, description="List of database names to query"
    )


class ChatResponse(BaseModel):
    """Non-streaming chat response payload."""

    response: str = Field(..., description="IRIS response")


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str
    environment: str
    version: str


def _lazy_import(module_path: str, attr_name: str) -> Any:
    """
    Perform a lazy import to avoid circular dependencies.

    Args:
        module_path: The module path to import from.
        attr_name: The attribute name to import from the module.

    Returns:
        The imported attribute.

    Raises:
        ImportError: If the module or attribute cannot be imported.
    """
    module = importlib.import_module(module_path, package="services.src")
    return getattr(module, attr_name)


def get_chat_processor() -> Callable:
    """
    Lazily import the async chat model to avoid circular dependencies.

    Returns:
        The process_conversation_request_async function from chat_model.model.

    Raises:
        ImportError: If the chat model module cannot be imported.
    """
    try:
        return _lazy_import(
            ".chat_model.model", "process_conversation_request_async"
        )
    except (ImportError, AttributeError) as exc:
        logger.error(
            "Failed to import chat model. "
            "Make sure to add the async wrapper to model.py"
        )
        raise ImportError(
            "Chat model not properly configured for async operation"
        ) from exc


def get_streaming_chat_processor() -> Callable:
    """
    Lazily import the streaming chat model to avoid circular dependencies.

    Returns:
        The streaming model generator function from chat_model.model.

    Raises:
        ImportError: If the streaming chat model module cannot be imported.
    """
    try:
        return _lazy_import(".chat_model.model", "stream_model_response")
    except (ImportError, AttributeError) as exc:
        logger.error("Failed to import streaming chat model")
        raise ImportError("Streaming chat model not properly configured") from exc


class StreamingError(Exception):
    """Exception raised during streaming response generation."""


async def stream_chat_response(
    conversation: List[Dict[str, str]], db_names: Optional[List[str]] = None
):
    """
    Async generator that streams chat responses from the IRIS model.

    Uses a thread-based queue to bridge the synchronous model generator
    with the async FastAPI streaming response.

    Args:
        conversation: List of message dictionaries with 'role' and 'content' keys.
        db_names: Optional list of database names to restrict the search scope.

    Yields:
        String chunks of the response as they are generated.
    """
    try:
        model_func = get_streaming_chat_processor()
        conversation_dict = {"messages": conversation}
        chunk_queue: queue.Queue = queue.Queue()
        exception_container: List[Optional[Exception]] = [None]

        def run_sync_generator():
            """Execute the synchronous model generator in a background thread."""
            try:
                for chunk in model_func(
                    conversation_dict, debug_mode=False, db_names=db_names
                ):
                    if isinstance(chunk, str):
                        chunk_queue.put(chunk)
                chunk_queue.put(None)
            except (
                ImportError,
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
                AttributeError,
                OSError,
                ConnectionError,
                TimeoutError,
            ) as exc:
                exception_container[0] = exc
                chunk_queue.put(None)

        thread = threading.Thread(target=run_sync_generator)
        thread.start()

        while True:
            try:
                chunk = chunk_queue.get(timeout=0.1)
                if chunk is None:
                    break
                yield chunk
                await asyncio.sleep(0)
            except queue.Empty:
                stored_exception = exception_container[0]
                if stored_exception is not None:
                    raise StreamingError(str(stored_exception)) from stored_exception
                await asyncio.sleep(0.01)
                continue

        thread.join(timeout=1)

        stored_exception = exception_container[0]
        if stored_exception is not None:
            raise StreamingError(str(stored_exception)) from stored_exception

    except (ImportError, RuntimeError, ValueError, StreamingError) as exc:
        logger.error("Streaming error: %s", str(exc), exc_info=True)
        yield f"Error: {exc}"


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Process a conversation through the IRIS system.

    Accepts a conversation history and routes it through the appropriate
    IRIS agents to generate a response.

    Args:
        request: ChatRequest containing messages, stream flag, and optional db_names.

    Returns:
        StreamingResponse if stream=True, otherwise ChatResponse with full response.

    Raises:
        HTTPException: 500 error if processing fails.
    """
    try:
        logger.info(
            "Received chat request with %d messages, stream=%s",
            len(request.messages),
            request.stream,
        )

        conversation = [
            {"role": msg.role, "content": msg.content} for msg in request.messages
        ]

        if request.stream:
            logger.info("Returning streaming response")
            return StreamingResponse(
                stream_chat_response(conversation, request.db_names),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        logger.info("Returning complete response")
        process_conversation_request_async = get_chat_processor()
        result = await process_conversation_request_async(
            conversation, stream=False, db_names=request.db_names
        )

        logger.info("Chat request processed successfully")
        return ChatResponse(response=result.get("response", ""))

    except (ImportError, RuntimeError, ValueError) as exc:
        logger.error("Chat endpoint error: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        ) from exc


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Verify the API is running and properly configured.

    Returns:
        HealthResponse with status, environment, and version.

    Raises:
        HTTPException: 503 error if configuration validation fails.
    """
    try:
        config.validate_required_environment()

        return HealthResponse(
            status="healthy", environment=config.ENVIRONMENT, version=API_VERSION
        )
    except (ValueError, RuntimeError, AttributeError) as exc:
        logger.error("Health check failed: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {exc}",
        ) from exc


@app.get("/")
async def root():
    """
    Return basic information about the API.

    Returns:
        Dictionary with API name, documentation URL, health URL, and version.
    """
    return {
        "message": "IRIS Chat API",
        "docs": "/docs",
        "health": "/health",
        "version": API_VERSION,
    }


@app.get("/databases")
async def get_databases():
    """
    Return available databases from the registry.

    Used by the frontend to dynamically populate database filter checkboxes.

    Returns:
        Dictionary with 'databases' key containing list of database info dicts.

    Raises:
        HTTPException: 500 error if database retrieval fails.
    """
    try:
        fetch_available_databases = _lazy_import(
            ".agent.tools.database_metadata", "fetch_available_databases"
        )
        databases = fetch_available_databases()

        result = []
        for db_source, db_config in databases.items():
            result.append(
                {
                    "id": db_source,
                    "name": db_config.get("name", db_source),
                    "is_internal": db_source.startswith("internal_"),
                }
            )

        result.sort(key=lambda x: (not x["is_internal"], x["name"]))

        logger.info("Returning %d databases", len(result))
        return {"databases": result}

    except (ImportError, RuntimeError, ValueError) as exc:
        logger.error("Failed to get databases: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve databases: {exc}",
        ) from exc


@app.post("/reset")
async def reset_server():
    """
    Clear all server caches and reload configurations.

    Invalidates the database metadata cache, forcing a fresh load
    from PostgreSQL on the next request.

    Returns:
        Dictionary with reset status and message.

    Raises:
        HTTPException: 500 error if cache invalidation fails.
    """
    try:
        get_metadata_repository = _lazy_import(
            ".agent.tools.database_metadata", "get_metadata_repository"
        )
        repo = get_metadata_repository()
        repo.invalidate_cache()

        logger.info("Server caches cleared successfully")
        return {"status": "reset", "message": "Server caches cleared successfully"}

    except (ImportError, RuntimeError, ValueError, AttributeError) as exc:
        logger.error("Failed to reset server: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset server: {exc}",
        ) from exc


@app.on_event("startup")
async def startup_event():
    """
    Perform startup validation and initialization.

    Validates environment configuration and logs startup status.

    Raises:
        ValueError: If configuration validation fails.
    """
    logger.info("Starting IRIS Chat API...")

    if not config.validate_required_environment():
        raise ValueError("Configuration validation failed")

    logger.info(
        "IRIS Chat API started successfully in %s environment",
        config.ENVIRONMENT,
    )


@app.on_event("shutdown")
async def shutdown_event():
    """
    Perform cleanup on application shutdown.

    Logs shutdown message for monitoring purposes.
    """
    logger.info("Shutting down IRIS Chat API...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
