import httpx
import json

def test_api():
    print("=========================================")
    print("TradeFlow AI: Querying FastAPI Backend API")
    print("=========================================")
    
    url = "http://127.0.0.1:8000/run-news-agent"
    payload = {
        "query": "stocks",
        "threshold": 0.45
    }
    
    try:
        print("Sending POST request to /run-news-agent...")
        response = httpx.post(url, json=payload, timeout=30.0)
        
        if response.status_code == 200:
            print("\n[SUCCESS] Received 200 OK from TradeFlow API.")
            data = response.json()
            print("\n--- STRUCTURED MARKET REPORT RESPONSE ---")
            print(f"Overall Sentiment: {data.get('market_sentiment')}")
            print(f"Summary: {data.get('overall_summary')}\n")
            
            print("Impacted Companies:")
            for company in data.get("impacted_companies", []):
                print(f"- {company.get('ticker')} ({company.get('company_name')}):")
                print(f"  Sentiment: {company.get('sentiment')} ({company.get('sentiment_score')}) | Risk: {company.get('risk_level')}/10")
                print(f"  Reason: {company.get('reasoning')}\n")
                
            print(f"Referenced Articles Count: {len(data.get('articles', []))}")
        else:
            print(f"\n[FAILED] Status code: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n[FAILED] Connection error: {e}")
        print("Make sure the FastAPI server is running on http://127.0.0.1:8000 (run: python app/main.py)")

if __name__ == "__main__":
    test_api()
