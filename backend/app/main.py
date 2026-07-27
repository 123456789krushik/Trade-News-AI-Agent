import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
from app.config.settings import settings
from app.utils.logger import logger

from contextlib import asynccontextmanager

from app.models.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=========================================")
    logger.info("TradeFlow AI FastAPI Application Starting")
    logger.info(f"Log Level: {settings.LOG_LEVEL}")
    logger.info("=========================================")
    # Initialize SQLite schema
    await init_db()
    yield
    logger.info("TradeFlow AI FastAPI Application Shutting Down...")

app = FastAPI(
    title="TradeFlow AI Backend",
    description="Intelligent daily financial news aggregation, Jaccard deduplication, and Gemini AI analysis service.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend/n8n integration flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to trusted domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach API endpoints router
app.include_router(api_router)

if __name__ == "__main__":
    # Allow running directly via python app/main.py
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
