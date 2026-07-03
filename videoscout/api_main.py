"""
FastAPI main application for VideoScout hybrid backend.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

from videoscout.db import init_db
from videoscout.api import (
    suggestions,
    scan,
    discovery,
    sources,
    learning,
    settings,
    experiments,
    performance,
    cascade,
    downloads,
    batch,
    merge,
    feedback,
    profiles,
    pools,
)
from videoscout.scheduler import init_scheduler, shutdown_scheduler

load_dotenv()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/videoscout"
    )
    init_db(database_url)
    logger.info(f"Database initialized: {database_url}")

    sched = init_scheduler()
    if sched:
        sched.start()
        logger.info("APScheduler started")

    yield

    # Shutdown
    shutdown_scheduler()
    logger.info("Shutting down gracefully")


app = FastAPI(
    title="VideoScout API",
    description="Hybrid backend for keyword suggestion and learning",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", str(exc.detail))
        code = exc.detail.get("code", "UNKNOWN_ERROR")
        details = {
            key: value
            for key, value in exc.detail.items()
            if key not in ("message", "code")
        } or None
    else:
        message = str(exc.detail)
        code = exc.detail if isinstance(exc.detail, str) else "UNKNOWN_ERROR"
        details = None

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat(), "version": "0.1.0"}


app.include_router(suggestions.router, prefix="/api/v1", tags=["suggestions"])
app.include_router(discovery.router, prefix="/api/v1", tags=["discovery"])
app.include_router(scan.router, prefix="/api/v1", tags=["scan (deprecated)"])
app.include_router(sources.router, prefix="/api/v1", tags=["sources"])
app.include_router(learning.router, prefix="/api/v1", tags=["learning"])
app.include_router(settings.router, prefix="/api/v1", tags=["settings"])
app.include_router(experiments.router, prefix="/api/v1", tags=["experiments"])
app.include_router(performance.router, prefix="/api/v1", tags=["performance"])
app.include_router(cascade.router, prefix="/api/v1", tags=["cascade"])
app.include_router(downloads.router, prefix="/api/v1", tags=["downloads"])
app.include_router(batch.router, prefix="/api/v1", tags=["batch"])
app.include_router(merge.router, prefix="/api/v1", tags=["merge"])
app.include_router(feedback.router, prefix="/api/v1", tags=["feedback"])
app.include_router(profiles.router, prefix="/api/v1", tags=["profiles"])
app.include_router(pools.router, prefix="/api/v1", tags=["pools"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
