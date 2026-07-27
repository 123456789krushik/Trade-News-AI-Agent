import os
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config.settings import settings
from app.models.schemas import MarketReportResponse, CompanyImpactResponse, ArticleResponse
from app.models.db import (
    Base, init_db, save_market_report_db, fetch_historical_reports_db
)

# Overwrite settings to redirect database during testing
TEST_DB_FILE = "test_tradeflow.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """
    Cleans up the test database file and initializes tables before every test.
    """
    settings.DATABASE_URL = TEST_DATABASE_URL
    
    # Force rebuild engine for new DB URL target
    from app.models import db
    db.DATABASE_URL = TEST_DATABASE_URL
    db.engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    db.AsyncSessionLocal = async_sessionmaker(
        bind=db.engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )

    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    await init_db()
    
    yield
    
    # Close connections
    await db.engine.dispose()
    
    # Cleanup file
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.mark.asyncio
async def test_save_and_query_report_async():
    """
    Verify async report insertions and relationship queries.
    """
    from app.models.db import AsyncSessionLocal
    
    # 1. Setup mock data
    report = MarketReportResponse(
        overall_summary="Tech earnings beat estimates.",
        market_sentiment="BULLISH",
        impacted_companies=[
            CompanyImpactResponse(
                ticker="AAPL",
                company_name="Apple Inc.",
                sentiment="BULLISH",
                sentiment_score=0.9,
                confidence=0.95,
                reasoning="Strong sales growth.",
                risk_level=1
            )
        ],
        trending_sectors=["Tech", "Hardware"],
        articles=[
            ArticleResponse(
                title="Apple Sales Rise",
                description="Earnings show solid consumer demand.",
                url="https://source.com/aapl",
                source="Reuters",
                published_at=datetime.now(timezone.utc)
            )
        ]
    )

    # 2. Insert report
    async with AsyncSessionLocal() as session:
        report_id = await save_market_report_db(session, report)
        assert isinstance(report_id, int)
        assert report_id > 0
        
    # 3. Retrieve and assert relations
    async with AsyncSessionLocal() as session:
        reports = await fetch_historical_reports_db(session, limit=5)
        assert len(reports) == 1
        
        db_report = reports[0]
        assert db_report.id == report_id
        assert db_report.overall_summary == "Tech earnings beat estimates."
        assert db_report.market_sentiment == "BULLISH"
        
        # Verify JSON list deserialization property
        assert db_report.trending_sectors == ["Tech", "Hardware"]
        
        # Verify selectin loaded relationships
        assert len(db_report.impacted_companies) == 1
        assert db_report.impacted_companies[0].ticker == "AAPL"
        assert db_report.impacted_companies[0].sentiment_score == 0.9
        
        assert len(db_report.articles) == 1
        assert db_report.articles[0].title == "Apple Sales Rise"
