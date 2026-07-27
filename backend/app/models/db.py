import json
from datetime import datetime, timezone
from typing import List, Generator
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.config.settings import settings
from app.utils.logger import logger
from app.models.schemas import MarketReportResponse, CompanyImpactResponse, ArticleResponse

# Declare Base class for declarative mapping
class Base(DeclarativeBase):
    pass

class ReportDB(Base):
    """
    SQLAlchemy model representing saved reports.
    """
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    overall_summary: Mapped[str] = mapped_column(String, nullable=False)
    market_sentiment: Mapped[str] = mapped_column(String, nullable=False)
    trending_sectors_raw: Mapped[str] = mapped_column(String, nullable=False)  # Saved as JSON string

    # Relationships
    impacted_companies: Mapped[List["CompanyImpactDB"]] = relationship(
        back_populates="report", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    articles: Mapped[List["ArticleDB"]] = relationship(
        back_populates="report", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    @property
    def trending_sectors(self) -> List[str]:
        return json.loads(self.trending_sectors_raw) if self.trending_sectors_raw else []

class CompanyImpactDB(Base):
    """
    SQLAlchemy model representing individual company sentiment metrics.
    """
    __tablename__ = "company_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    sentiment: Mapped[str] = mapped_column(String, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[int] = mapped_column(Integer, nullable=False)

    report: Mapped[ReportDB] = relationship(back_populates="impacted_companies")

class ArticleDB(Base):
    """
    SQLAlchemy model representing referenced news sources.
    """
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    report: Mapped[ReportDB] = relationship(back_populates="articles")

# 1. Create engine and session factories
DATABASE_URL = settings.DATABASE_URL
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 2. FastAPI Async Database dependency injection provider
async def get_db() -> Generator[AsyncSession, None, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# 3. Schema initializations
async def init_db() -> None:
    """
    Initializes SQL tables.
    """
    logger.info("Initializing SQLAlchemy database tables asynchronously...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas verified.")
    except Exception as e:
        logger.error(f"Error during schema initialization: {e}")
        raise e

# 4. Helper persistence database functions
async def save_market_report_db(session: AsyncSession, report: MarketReportResponse) -> int:
    """
    Saves a MarketReportResponse, including relations, under a transaction.
    """
    db_report = ReportDB(
        overall_summary=report.overall_summary,
        market_sentiment=report.market_sentiment,
        trending_sectors_raw=json.dumps(report.trending_sectors)
    )
    
    session.add(db_report)
    await session.flush()  # Populates db_report.id

    for company in report.impacted_companies:
        db_company = CompanyImpactDB(
            report_id=db_report.id,
            ticker=company.ticker,
            company_name=company.company_name,
            sentiment=company.sentiment,
            sentiment_score=company.sentiment_score,
            confidence=company.confidence,
            reasoning=company.reasoning,
            risk_level=company.risk_level
        )
        session.add(db_company)

    for article in report.articles:
        db_article = ArticleDB(
            report_id=db_report.id,
            title=article.title,
            description=article.description,
            url=article.url,
            source=article.source,
            published_at=article.published_at
        )
        session.add(db_article)

    await session.commit()
    return db_report.id

async def fetch_historical_reports_db(session: AsyncSession, limit: int = 10) -> List[ReportDB]:
    """
    Retrieves latest reports from database.
    """
    stmt = select(ReportDB).order_by(ReportDB.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
