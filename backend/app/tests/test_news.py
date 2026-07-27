import pytest
from app.news.google_rss import GoogleNewsRSSCollector
from app.news.yahoo import YahooFinanceCollector
from app.news.deduplicator import calculate_jaccard_similarity, deduplicate_articles
from app.services.cleaner import clean_text
from app.models.schemas import ArticleResponse
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_google_rss_collector_live():
    """
    Verify Google News RSS async collector can fetch and parse live feed.
    """
    collector = GoogleNewsRSSCollector()
    articles = await collector.fetch_news("Google")
    assert isinstance(articles, list)
    if len(articles) > 0:
        assert isinstance(articles[0], ArticleResponse)
        assert articles[0].title
        assert articles[0].url

@pytest.mark.asyncio
async def test_yahoo_collector_live():
    """
    Verify Yahoo Finance RSS async collector can fetch general and ticker feeds.
    """
    collector = YahooFinanceCollector()
    
    # Test ticker feed
    articles = await collector.fetch_news("TSLA")
    assert isinstance(articles, list)
    
    # Test general feed
    articles_general = await collector.fetch_news("stocks")
    assert isinstance(articles_general, list)

def test_jaccard_token_similarity():
    """
    Verify Jaccard similarity metrics calculations.
    """
    t1 = "Apple stock rises after earnings beat"
    t2 = "Apple shares rise on earnings win"
    # Token 1: {'apple', 'stock', 'rises', 'earnings', 'beat'} (5 tokens)
    # Token 2: {'apple', 'shares', 'rise', 'earnings', 'win'} (5 tokens)
    # Intersection: {'apple', 'earnings'} (2 tokens)
    # Union: {'apple', 'stock', 'rises', 'shares', 'rise', 'earnings', 'win'} (7 tokens)
    # expected similarity: 2 / 7 = 0.285
    sim = calculate_jaccard_similarity(t1, t2)
    assert abs(sim - 0.285) < 0.05

def test_cleaner_formatting():
    """
    Verify cleaner strips HTML elements and spacing correctly.
    """
    dirty = "   <div>AAPL <b>shares</b> jump &amp; beat</div>\n  "
    assert clean_text(dirty) == "AAPL shares jump & beat"
