# iris/src/api.py
"""
FastAPI REST API for IRIS Chat System

This module provides a minimal FastAPI interface to the IRIS chat system,
exposing the core functionality as REST endpoints while keeping the existing
folder structure and logic intact.

Endpoints:
    POST /chat - Process a conversation through IRIS agents
    GET /health - Health check endpoint
    GET /docs - Automatic API documentation

Dependencies:
    - fastapi
    - pydantic
    - uvicorn
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
import time
import asyncio

# Import your existing modules
from .initial_setup.logging_config import configure_logging
from .initial_setup.env_config import config

# Configure logging
configure_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="IRIS Chat API",
    description="RBC IRIS Intelligent Response System - AI-powered financial chat assistant",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for RBC environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for RBC security
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    stream: bool = Field(default=False, description="Enable streaming response")

class ChatResponse(BaseModel):
    response: str = Field(..., description="IRIS response")

class HealthResponse(BaseModel):
    status: str
    environment: str
    version: str

# Import chat model function after FastAPI setup to avoid circular imports
def get_chat_processor():
    """Lazy import to avoid circular dependencies"""
    try:
        from .chat_model.model import process_request_async
        return process_request_async
    except ImportError:
        logger.error("Failed to import chat model. Make sure to add the async wrapper to model.py")
        raise ImportError("Chat model not properly configured for async operation")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Process a conversation through the IRIS system.
    
    This endpoint accepts a conversation history and routes it through the
    appropriate IRIS agents to generate a response.
    """
    try:
        logger.info(f"Received chat request with {len(request.messages)} messages")
        
        # Convert Pydantic models to dict format expected by existing code
        conversation = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.messages
        ]
        
        # Get the async chat processor
        process_request_async = get_chat_processor()
        
        # Process through existing IRIS system
        result = await process_request_async(conversation, stream=request.stream)
        
        logger.info("Chat request processed successfully")
        
        return ChatResponse(
            response=result.get("response", "")
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify the API is running and properly configured.
    """
    try:
        # Validate configuration
        config.validate()
        
        return HealthResponse(
            status="healthy",
            environment=config.ENVIRONMENT,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )

@app.get("/")
async def root():
    """
    Root endpoint with basic information about the API.
    """
    return {
        "message": "IRIS Chat API",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

# Startup event to validate configuration
@app.on_event("startup")
async def startup_event():
    """
    Perform startup validation and initialization.
    """
    logger.info("Starting IRIS Chat API...")
    
    try:
        # Validate environment configuration
        if not config.validate():
            raise ValueError("Configuration validation failed")
        
        logger.info(f"IRIS Chat API started successfully in {config.ENVIRONMENT} environment")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown.
    """
    logger.info("Shutting down IRIS Chat API...")

if __name__ == "__main__":
    import uvicorn
    
    # Development server
    uvicorn.run(
        "iris.src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )