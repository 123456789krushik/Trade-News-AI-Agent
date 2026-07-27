import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.models.db import get_db, Base
from app.models.schemas import MarketReportResponse, CompanyImpactResponse, ArticleResponse

# Setup test DB file
TEST_DB_FILE = "test_api.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Override get_db dependency
async def override_get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def run_db_setup():
    """
    Initializes database tables before module tests run and cleans up afterwards.
    """
    # Force sync schema creation for test setup using a separate sync sqlite engine connection helper
    import asyncio
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(create_tables())

    yield

    # Dispose connection pools and remove file
    async def cleanup_db():
        await engine.dispose()
    asyncio.run(cleanup_db())
    
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

def test_root_endpoint():
    """
    Verify GET / returns API welcome status.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "TradeFlow" in response.json()["message"]

def test_health_endpoint():
    """
    Verify GET /health checks DB connectivity and reports healthy.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"

@patch("app.api.endpoints.NewsPipeline.run")
def test_run_news_agent_integration(mock_pipeline_run):
    """
    Verify POST /run-news-agent triggers pipeline, persists database record, and serializes response.
    """
    # 1. Setup mock pipeline return
    dt = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    mock_pipeline_run.return_value = MarketReportResponse(
        overall_summary="The market surged led by strong earnings beats.",
        market_sentiment="BULLISH",
        impacted_companies=[
            CompanyImpactResponse(
                ticker="AAPL",
                company_name="Apple Inc.",
                sentiment="BULLISH",
                sentiment_score=0.9,
                confidence=0.95,
                reasoning="Earnings beats expectations.",
                risk_level=1
            )
        ],
        trending_sectors=["Tech"],
        articles=[
            ArticleResponse(
                title="Apple reports record earnings beat",
                description="Strong quarterly performance.",
                url="https://source.com/aapl",
                source="CNBC",
                published_at=dt
            )
        ]
    )

    # 2. Trigger endpoint POST
    payload = {"query": "tech", "threshold": 0.5}
    response = client.post("/run-news-agent", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["market_sentiment"] == "BULLISH"
    assert data["overall_summary"].startswith("The market surged")
    assert len(data["impacted_companies"]) == 1
    assert data["impacted_companies"][0]["ticker"] == "AAPL"

    # 3. Call GET /reports to assert database persistence
    response_reports = client.get("/reports?limit=5")
    assert response_reports.status_code == 200
    reports = response_reports.json()
    
    # Assert database query retrieved the report we just ran and saved
    assert len(reports) == 1
    assert reports[0]["market_sentiment"] == "BULLISH"
    assert reports[0]["trending_sectors"] == ["Tech"]
    assert len(reports[0]["articles"]) == 1
    assert reports[0]["articles"][0]["title"] == "Apple reports record earnings beat"
