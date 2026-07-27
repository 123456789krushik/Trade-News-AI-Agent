from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class ArticleResponse(BaseModel):
    """
    Pydantic schema representing a processed source article.
    """
    model_config = ConfigDict(from_attributes=True)
    
    title: str = Field(..., description="Title of the article")
    description: str = Field(..., description="Short text description or snippet")
    url: str = Field(..., description="Original news URL")
    source: str = Field(..., description="Publisher name (e.g. CNBC, Bloomberg)")
    published_at: datetime = Field(..., description="Time the article was published")

class CompanyImpactResponse(BaseModel):
    """
    Pydantic schema representing sentiment and risk details for a company.
    """
    model_config = ConfigDict(from_attributes=True)

    ticker: str = Field(..., description="Uppercase stock ticker symbol")
    company_name: str = Field(..., description="Official corporate name")
    sentiment: str = Field(..., description="Sentiment classification: BULLISH, BEARISH, or NEUTRAL")
    sentiment_score: float = Field(..., description="Sentiment rating from -1.0 to +1.0")
    confidence: float = Field(..., description="LLM assessment confidence from 0.0 to 1.0")
    reasoning: str = Field(..., description="Key insights explaining why this company is impacted")
    risk_level: int = Field(..., description="Volatility risk scale from 0 to 10")

class MarketReportResponse(BaseModel):
    """
    The full analysis report returned by the FastAPI backend to n8n.
    """
    model_config = ConfigDict(from_attributes=True)

    overall_summary: str = Field(..., description="High-quality executive summary of market updates")
    market_sentiment: str = Field(..., description="Consolidated sentiment: BULLISH, BEARISH, or NEUTRAL")
    impacted_companies: List[CompanyImpactResponse] = Field(..., description="List of companies affected by the news")
    trending_sectors: List[str] = Field(..., description="List of sectors highlighted in the news")
    articles: List[ArticleResponse] = Field(default=[], description="Source articles referenced to generate this report")

class RunAgentRequest(BaseModel):
    """
    Optional request parameters when triggering the news agent cycle.
    """
    query: str = Field(default="stocks", description="Search terms for finding relevant financial news")
    threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Jaccard similarity threshold for deduplication")
