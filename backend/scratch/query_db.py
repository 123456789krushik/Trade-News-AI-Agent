import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.db import fetch_historical_reports_db, DATABASE_URL

async def query_db():
    print("=========================================")
    print("TradeFlow AI: Querying SQLite Database Records")
    print("=========================================")
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        reports = await fetch_historical_reports_db(session, limit=5)
        
        print(f"Total reports found in database: {len(reports)}\n")
        
        for idx, r in enumerate(reports, 1):
            print(f"[{idx}] REPORT ID: {r.id} | Generated at: {r.created_at}")
            print(f"    Market Sentiment: {r.market_sentiment}")
            print(f"    Summary: {r.overall_summary[:120]}...")
            
            print(f"    Trending Sectors: {r.trending_sectors}")
            
            print(f"    Impacted Companies ({len(r.impacted_companies)}):")
            for c in r.impacted_companies:
                print(f"      - {c.ticker} ({c.company_name}): {c.sentiment} (Score: {c.sentiment_score}) | Risk: {c.risk_level}/10")
                print(f"        Reasoning: {c.reasoning}")
                
            print(f"    Referenced Articles archived: {len(r.articles)}")
            print("-" * 50)
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(query_db())
