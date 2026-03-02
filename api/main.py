"""FastAPI application entry point."""

import sys

from fastapi import FastAPI
from loguru import logger

from api.routes import router
from core.config import get_settings
from core.telemetry import _get_provider

# Configure loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)

# Initialize telemetry
try:
    _get_provider()
except Exception as e:
    logger.warning("Telemetry setup failed: {}", e)

app = FastAPI(
    title="NL2SQL Agent Pipeline",
    description="Event-driven multi-agent analytics platform for natural language to Looker queries",
    version="0.1.0",
)

# Instrument FastAPI for tracing
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass

app.include_router(router, prefix="/api/v1", tags=["analytics"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
