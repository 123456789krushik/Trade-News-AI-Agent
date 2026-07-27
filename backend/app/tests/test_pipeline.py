import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.models.schemas import ArticleResponse, MarketReportResponse, CompanyImpactResponse
from app.services.pipeline import NewsPipeline

@pytest.mark.asyncio
async def test_news_pipeline_async_mock():
    """
    Verify the orchestrator pipeline properly coordinates async ingestion,
    cleaning, deduplication, and mock AI processing.
    """
    dt = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    
    # 1. Setup mock raw articles (with tags, extra spacing, and a duplicate)
    google_mock_articles = [
        ArticleResponse(
            title="<b>AAPL</b> stock surges 3%  ",
            description="Apple reported strong quarters",
            url="https://source.com/aapl",
            source="Google News",
            published_at=dt
        )
    ]
    
    yahoo_mock_articles = [
        # Duplicate of AAPL article
        ArticleResponse(
            title="AAPL stock surges 3% on beat",
            description="Apple beats quarterly expectations",
            url="https://source.com/aapl-dup",
            source="Yahoo Finance",
            published_at=dt
        ),
        # Unique article
        ArticleResponse(
            title="Microsoft announces new AI tooling integration",
            description="Microsoft introduces Copilot updates.",
            url="https://source.com/msft",
            source="Yahoo Finance",
            published_at=dt
        )
    ]

    # Create mock report response
    mock_report = MarketReportResponse(
        overall_summary="Gains led by Apple and Microsoft announcements.",
        market_sentiment="BULLISH",
        impacted_companies=[
            CompanyImpactResponse(
                ticker="AAPL",
                company_name="Apple Inc.",
                sentiment="BULLISH",
                sentiment_score=0.8,
                confidence=0.9,
                reasoning="Stock surges 3% on earnings beat.",
                risk_level=1
            )
        ],
        trending_sectors=["Tech"],
        articles=[]
    )

    # 2. Patch collector fetch tasks and AI analyze call
    with patch("app.news.google_rss.GoogleNewsRSSCollector.fetch_news") as mock_gnews, \
         patch("app.news.yahoo.YahooFinanceCollector.fetch_news") as mock_yahoo, \
         patch("app.news.newsapi.NewsAPICollector.fetch_news") as mock_newsapi, \
         patch("app.ai.client.GeminiClient.analyze_news_batch") as mock_gemini:

        async def mock_gnews_fetch(*args, **kwargs):
            return google_mock_articles
            
        async def mock_yahoo_fetch(*args, **kwargs):
            return yahoo_mock_articles
            
        async def mock_newsapi_fetch(*args, **kwargs):
            return []
            
        async def mock_gemini_analyze(*args, **kwargs):
            return mock_report

        mock_gnews.side_effect = mock_gnews_fetch
        mock_yahoo.side_effect = mock_yahoo_fetch
        mock_newsapi.side_effect = mock_newsapi_fetch
        mock_gemini.side_effect = mock_gemini_analyze

        # Run pipeline
        pipeline = NewsPipeline()
        pipeline.ai_client.api_key = "dummy" # bypass validation
        
        report = await pipeline.run(query="tech", deduplication_threshold=0.45)

        # 3. Assertions
        mock_gnews.assert_called_once_with("tech")
        mock_yahoo.assert_called_once_with("tech")
        mock_newsapi.assert_called_once_with("tech")

        # Verify Gemini is called with only 2 unique articles (Google AAPL article + MSFT article)
        # Check argument passed to mock_gemini call
        mock_gemini.assert_called_once()
        called_articles = mock_gemini.call_args[0][0]
        
        assert len(called_articles) == 2
        # Verify cleaning was performed
        assert called_articles[0].title == "AAPL stock surges 3%"
        assert called_articles[1].title == "Microsoft announces new AI tooling integration"
        
        assert report.market_sentiment == "BULLISH"
        assert len(report.impacted_companies) == 1
