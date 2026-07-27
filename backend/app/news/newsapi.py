import httpx
from datetime import datetime, timezone
from app.config.settings import settings
from app.utils.logger import logger
from app.models.schemas import ArticleResponse
from app.news.collector import BaseNewsCollector
from typing import List

class NewsAPICollector(BaseNewsCollector):
    """
    Asynchronous news collector for the NewsAPI.org service.
    """
    def __init__(self) -> None:
        super().__init__(name="NewsAPI")
        self.api_key = settings.NEWS_API_KEY
        self.base_url = "https://newsapi.org/v2/everything"

    async def fetch_news(self, query: str = "stocks") -> List[ArticleResponse]:
        """
        Asynchronously fetches articles matching the search term from NewsAPI.
        """
        if not self.api_key or self.api_key == "mock_newsapi_key":
            logger.warning("NewsAPI key is missing or set to mock. Skipping fetch.")
            return []

        params = {
            "q": query,
            "sortBy": "publishedAt",
            "pageSize": 20,
            "language": "en",
            "apiKey": self.api_key
        }

        try:
            logger.info(f"Querying NewsAPI async for query: '{query}'")
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                
            if response.status_code != 200:
                logger.error(f"NewsAPI returned status code {response.status_code}: {response.text}")
                return []
                
            data = response.json()
            articles = []
            
            for item in data.get("articles", []):
                title = item.get("title")
                description = item.get("description") or ""
                url = item.get("url")
                source = item.get("source", {}).get("name") or "NewsAPI"
                published_at_str = item.get("publishedAt")
                
                if not title or not url:
                    continue

                try:
                    if published_at_str:
                        if published_at_str.endswith("Z"):
                            published_at_str = published_at_str[:-1] + "+00:00"
                        published_at = datetime.fromisoformat(published_at_str)
                    else:
                        published_at = datetime.now(timezone.utc)
                except Exception as ex:
                    logger.debug(f"Failed to parse datetime '{published_at_str}': {ex}. Defaulting to now.")
                    published_at = datetime.now(timezone.utc)

                articles.append(ArticleResponse(
                    title=title,
                    description=description,
                    url=url,
                    source=source,
                    published_at=published_at
                ))
                
            logger.info(f"NewsAPI async collector fetched {len(articles)} articles.")
            return articles

        except Exception as e:
            logger.error(f"Exception during NewsAPI async fetch: {e}")
            return []
