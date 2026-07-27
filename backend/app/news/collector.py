from app.models.schemas import ArticleResponse
from typing import List

class BaseNewsCollector:
    """
    Abstract base class for all asynchronous news collectors.
    Defines the contract that must be implemented by individual sources.
    """
    def __init__(self, name: str) -> None:
        self.name = name

    async def fetch_news(self, query: str = "stocks") -> List[ArticleResponse]:
        """
        Asynchronously fetches articles from the source matching the query term.
        """
        raise NotImplementedError("Subclasses must implement fetch_news method")
