"""
FastAPI Main Application

Production-grade F1 Analytics API
"""
from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import asyncio
from datetime import datetime

from config import settings
from database import get_db, init_db
from models import Event, Session as DBSession, Driver, Prediction
from api import seasons, events, sessions, predictions, replay, telemetry, analysis, drivers, ingest, news, live, external_data, strategy, chat

# Initialize FastAPI app
app = FastAPI(
    title="F1 Analytics API",
    version="2.0.0",
    description="Production-grade F1 race prediction and replay platform",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(seasons.router, prefix="/api", tags=["Seasons"])
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(drivers.router, tags=["Drivers"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(replay.router, prefix="/api", tags=["Replay"])
app.include_router(telemetry.router, prefix="/api", tags=["Telemetry"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(live.router, prefix="/api/live", tags=["Live"])
app.include_router(external_data.router, prefix="/api/external", tags=["External Data"])
app.include_router(strategy.router, prefix="/api/strategy", tags=["Strategy"])
app.include_router(chat.router, tags=["Chatbot"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    print("Starting F1 Analytics API...")
    print(f"Database: {settings.database_url}")
    
    # Initialize database
    init_db()
    print("✓ Database initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down F1 Analytics API...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "F1 Analytics API",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "docs": "/docs",
            "seasons": "/api/seasons",
            "predictions": "/api/predictions",
            "replay": "/api/replay",
            "telemetry": "/api/telemetry"
        }
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "api": "healthy"
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1
    )
