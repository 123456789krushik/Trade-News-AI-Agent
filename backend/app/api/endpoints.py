from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import MarketReportResponse, RunAgentRequest
from app.utils.logger import logger
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db import get_db, save_market_report_db, fetch_historical_reports_db
from app.services.pipeline import NewsPipeline

router = APIRouter()

@router.get("/")
async def root():
    """
    Root endpoint verifying the TradeFlow AI REST API is running.
    """
    return {
        "message": "Welcome to TradeFlow AI Stock News Agent API",
        "version": "1.0.0",
        "status": "online"
    }

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Performs standard health verification, checking the database connectivity.
    """
    try:
        # Simple query to verify SQLite connection is active
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status
    }

@router.post("/run-news-agent", response_model=MarketReportResponse)
async def run_news_agent(request: RunAgentRequest, db: AsyncSession = Depends(get_db)):
    """
    Executes the ingestion, Jaccard cleaning, deduplication, and AI news analysis.
    Saves results to the SQLite database and returns the structured JSON report.
    """
    logger.info(f"Triggered news agent execution. Query: '{request.query}', Dedup Threshold: {request.threshold}")
    
    pipeline = NewsPipeline()
    try:
        report = await pipeline.run(query=request.query, deduplication_threshold=request.threshold)
    except Exception as e:
        logger.error(f"Ingestion pipeline failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis pipeline execution failed: {str(e)}"
        )

    # Persist the output in the relational database
    try:
        report_id = await save_market_report_db(db, report)
        logger.info(f"Successfully saved generated report to DB with ID: {report_id}")
    except Exception as e:
        logger.error(f"Report persistence failed: {e}")
        # We still return the report to the n8n caller even if database save fails
        
    return report

@router.get("/reports", response_model=List[MarketReportResponse])
async def get_historical_reports(limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a list of historically saved reports.
    """
    logger.info(f"Fetching historical reports. Limit: {limit}")
    try:
        db_reports = await fetch_historical_reports_db(db, limit=limit)
        
        # SQLAlchemy selectin loaded relationship properties map automatically to Pydantic
        # because we added config = ConfigDict(from_attributes=True)
        reports = []
        for r in db_reports:
            reports.append(MarketReportResponse.model_validate(r))
            
        return reports
    except Exception as e:
        logger.error(f"Failed to fetch historical reports: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load reports from database: {str(e)}"
        )
