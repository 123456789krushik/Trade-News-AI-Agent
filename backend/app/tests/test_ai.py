import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.models.schemas import ArticleResponse, MarketReportResponse, CompanyImpactResponse
from app.ai.client import GeminiClient

@pytest.mark.asyncio
async def test_async_gemini_client_mock():
    """
    Verify the async Gemini client formats prompts and parses the return schema correctly.
    """
    dt = datetime(2026, 7, 26, 12, 0, 0, tzinfo=timezone.utc)
    articles = [
        ArticleResponse(
            title="Microsoft Azure growth accelerates",
            description="Cloud revenues exceed targets by 20%.",
            url="https://source.com/msft",
            source="Reuters",
            published_at=dt
        )
    ]

    # Create mock response matching generate_content return signature
    mock_response = MagicMock()
    mock_response.parsed = MarketReportResponse(
        overall_summary="Tech led the market today, highlighted by Azure cloud gains.",
        market_sentiment="BULLISH",
        impacted_companies=[
            CompanyImpactResponse(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                sentiment="BULLISH",
                sentiment_score=0.8,
                confidence=0.9,
                reasoning="Azure cloud beats expectations.",
                risk_level=1
            )
        ],
        trending_sectors=["Technology"],
        articles=[]
    )
    mock_response.text = "{}"

    # Mock the Client constructor
    with patch("google.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        
        # In the SDK, the call is client.aio.models.generate_content, which is a coroutine
        # So we mock aio.models.generate_content to return a coroutine that resolves to mock_response
        async def mock_async_generate(*args, **kwargs):
            return mock_response
            
        mock_client.aio.models.generate_content = mock_async_generate
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        client.api_key = "dummy_key"
        
        report = await client.analyze_news_batch(articles)
        
        # Verify assertions
        assert report.market_sentiment == "BULLISH"
        assert len(report.impacted_companies) == 1
        assert report.impacted_companies[0].ticker == "MSFT"
        assert len(report.articles) == 1
        assert report.articles[0].source == "Reuters"
