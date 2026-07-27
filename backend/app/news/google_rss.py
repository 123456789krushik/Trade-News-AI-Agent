import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from app.utils.logger import logger
from app.models.schemas import ArticleResponse
from app.news.collector import BaseNewsCollector
from typing import List

class GoogleNewsRSSCollector(BaseNewsCollector):
    """
    Asynchronous news collector that fetches and parses the Google News RSS search feed.
    """
    def __init__(self) -> None:
        super().__init__(name="GoogleNewsRSS")
        self.base_url = "https://news.google.com/rss/search"

    async def fetch_news(self, query: str = "stocks") -> List[ArticleResponse]:
        """
        Asynchronously fetches and parses XML search alerts from Google RSS feed.
        """
        params = {
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en"
        }

        try:
            logger.info(f"Querying Google News RSS async with terms: '{query}'")
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                
            if response.status_code != 200:
                logger.error(f"Google News RSS returned status code {response.status_code}")
                return []
                
            root = ET.fromstring(response.content)
            articles = []
            
            for item in root.findall(".//item"):
                title = item.findtext("title") or ""
                url = item.findtext("link") or ""
                description = item.findtext("description") or ""
                pub_date_str = item.findtext("pubDate")
                
                source_el = item.find("source")
                source = source_el.text if source_el is not None else "Google News"
                
                if not title or not url:
                    continue

                try:
                    if pub_date_str:
                        published_at = parsedate_to_datetime(pub_date_str)
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    else:
                        published_at = datetime.now(timezone.utc)
                except Exception as ex:
                    logger.debug(f"Could not parse RSS date '{pub_date_str}': {ex}. Defaulting to now.")
                    published_at = datetime.now(timezone.utc)

                articles.append(ArticleResponse(
                    title=title,
                    description=description,
                    url=url,
                    source=source,
                    published_at=published_at
                ))
                
            logger.info(f"Google News RSS async collector retrieved {len(articles)} articles.")
            return articles

        except Exception as e:
            logger.error(f"Exception during Google News RSS async request: {e}")
            return []
