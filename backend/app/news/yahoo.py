import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from app.utils.logger import logger
from app.models.schemas import ArticleResponse
from app.news.collector import BaseNewsCollector
from typing import List

class YahooFinanceCollector(BaseNewsCollector):
    """
    Asynchronous news collector that fetches and parses the Yahoo Finance RSS feed.
    """
    def __init__(self) -> None:
        super().__init__(name="YahooFinance")
        self.general_rss_url = "https://finance.yahoo.com/news/rss"
        self.symbol_rss_url = "https://finance.yahoo.com/rss/headline"

    async def fetch_news(self, query: str = "stocks") -> List[ArticleResponse]:
        """
        Asynchronously fetches and parses XML alerts from Yahoo Finance feed.
        """
        is_ticker = query.isupper() and query.isalpha() and 1 <= len(query) <= 5
        
        if is_ticker:
            url = self.symbol_rss_url
            params = {"s": query}
            logger.info(f"Querying Yahoo Finance RSS async for ticker: '{query}'")
        else:
            url = self.general_rss_url
            params = {}
            logger.info("Querying general Yahoo Finance RSS async news")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=headers, timeout=10.0)
                
            if response.status_code != 200:
                logger.error(f"Yahoo Finance RSS returned status code {response.status_code}")
                return []
                
            root = ET.fromstring(response.content)
            articles = []
            
            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                url_link = item.findtext("link") or ""
                description = item.findtext("description") or ""
                pub_date_str = item.findtext("pubDate")
                
                source = "Yahoo Finance"
                source_el = item.find("source")
                if source_el is not None and source_el.text:
                    source = source_el.text

                if not title or not url_link:
                    continue

                try:
                    if pub_date_str:
                        published_at = parsedate_to_datetime(pub_date_str)
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)
                except Exception as ex:
                    logger.debug(f"Could not parse Yahoo RSS date '{pub_date_str}': {ex}. Defaulting to now.")
                    published_at = datetime.now(timezone.utc)

                articles.append(ArticleResponse(
                    title=title,
                    description=description,
                    url=url_link,
                    source=source,
                    published_at=published_at
                ))
                
            logger.info(f"Yahoo Finance RSS async collector retrieved {len(articles)} articles.")
            return articles

        except Exception as e:
            logger.error(f"Exception during Yahoo Finance RSS async request: {e}")
            return []
