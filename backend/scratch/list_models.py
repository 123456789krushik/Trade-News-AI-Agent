import asyncio
import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config.settings import settings
from google import genai

async def main():
    api_key = settings.GEMINI_API_KEY
    print(f"Using API Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 10 else ''}")
    
    try:
        client = genai.Client(api_key=api_key)
        print("Listing available models from Google Gemini API...")
        
        # In google-genai SDK, listing models is sync or async
        # We can list models using client.models.list()
        models = client.models.list()
        for m in models:
            print(f"- {m.name} (actions: {m.supported_actions})")
            
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    asyncio.run(main())
