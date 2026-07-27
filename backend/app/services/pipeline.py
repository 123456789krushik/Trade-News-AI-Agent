import asyncio
from app.utils.logger import logger
from app.news.newsapi import NewsAPICollector
from app.news.google_rss import GoogleNewsRSSCollector
from app.news.yahoo import YahooFinanceCollector
from app.services.cleaner import clean_text
from app.news.deduplicator import deduplicate_articles
from app.ai.client import GeminiClient
from app.models.schemas import MarketReportResponse

class NewsPipeline:
    """
    Coordinates the end-to-end async stock market news analysis pipeline:
    1. Fetches news concurrently from RSS feeds and NewsAPI
    2. Scrubs and normalizes texts
    3. Deduplicates using Jaccard Similarity index
    4. Generates structured JSON market intelligence report via Google Gemini AI.
    """
    def __init__(self) -> None:
        self.collectors = [
            GoogleNewsRSSCollector(),
            YahooFinanceCollector(),
            NewsAPICollector()
        ]
        self.ai_client = GeminiClient()

    async def run(self, query: str = "stocks", deduplication_threshold: float = 0.45) -> MarketReportResponse:
        """
        Asynchronously executes the ingestion, cleaning, deduplication, and AI summary pipeline.
        """
        logger.info(f"Starting async news aggregation pipeline query: '{query}'")

        # 1. Fetch from all collectors concurrently using asyncio.gather
        tasks = [collector.fetch_news(query) for collector in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_articles = []
        for collector, result in zip(self.collectors, results):
            if isinstance(result, Exception):
                logger.error(f"Collector {collector.name} raised an exception during fetch: {result}")
            else:
                all_articles.extend(result)

        if not all_articles:
            logger.warning("No articles collected from news sources.")
            return MarketReportResponse(
                overall_summary="No news articles were collected today.",
                market_sentiment="NEUTRAL",
                impacted_companies=[],
                trending_sectors=[],
                articles=[]
            )

        logger.info(f"Retrieved {len(all_articles)} raw articles from all feeds.")

        # 2. Clean article content
        for article in all_articles:
            article.title = clean_text(article.title)
            article.description = clean_text(article.description)

        # 3. Deduplicate
        deduplicated = deduplicate_articles(all_articles, threshold=deduplication_threshold)
        logger.info(f"Retained {len(deduplicated)} unique articles after Jaccard deduplication.")

        if not deduplicated:
            logger.warning("All articles were filtered as duplicates.")
            return MarketReportResponse(
                overall_summary="All collected articles were flagged as duplicates.",
                market_sentiment="NEUTRAL",
                impacted_companies=[],
                trending_sectors=[],
                articles=[]
            )

        # 4. Perform async AI Ingestion & Analysis
        try:
            report = await self.ai_client.analyze_news_batch(deduplicated)
            logger.info("News pipeline completed successfully.")
            return report
        except Exception as e:
            logger.error(f"AI news analysis failed: {e}")
            raise e
