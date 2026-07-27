import json
from google import genai
from google.genai import types
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config.settings import settings
from app.utils.logger import logger
from app.models.schemas import MarketReportResponse
from app.prompts.templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, format_articles_for_prompt

class GeminiClient:
    """
    Asynchronous client for interacting with the Google Gemini API using structured JSON output.
    Implements model fallback strategies and input token capping to prevent 429 rate limit issues.
    """
    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        # Fallback list of models (ordered from highest performance/priority to legacy stable fallback)
        self.models_to_try = [
            "gemini-flash-latest",  # standard stable 1.5 Flash (free and always available)
            "gemini-2.0-flash"      # stable 2.0 Flash fallback
        ]
        self._client = None

    @property
    def client(self) -> genai.Client:
        """
        Lazily instantiates the Google GenAI Client.
        """
        if self._client is None:
            if not self.api_key or self.api_key == "mock_gemini_key":
                raise ValueError("GEMINI_API_KEY is not configured or is set to mock.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        # Increase backoff waiting duration to allow rate limit windows to clear
        wait=wait_exponential(multiplier=3, min=5, max=60),
        retry=retry_if_exception_type((APIError, ConnectionError)),
        reraise=True
    )
    async def analyze_news_batch(self, articles: list) -> MarketReportResponse:
        """
        Asynchronously sends formatted articles to Gemini for structured JSON analysis.
        Implements automatic fallback across multiple model tiers if a 429 Rate Limit occurs.
        """
        if not articles:
            logger.warning("No articles supplied for Gemini analysis.")
            return MarketReportResponse(
                overall_summary="No articles were available to analyze.",
                market_sentiment="NEUTRAL",
                impacted_companies=[],
                trending_sectors=[],
                articles=[]
            )

        # CAP the number of articles sent to the LLM to fit within free tier TPM rate limit budgets.
        # Top 15 articles are sufficient to extract core market updates.
        capped_articles = articles[:15]
        logger.info(f"Preparing AI prompt with {len(capped_articles)} articles (capped from {len(articles)} total unique articles).")
        
        # Prepare inputs
        formatted_text = format_articles_for_prompt(capped_articles)
        user_prompt = USER_PROMPT_TEMPLATE.format(articles_formatted=formatted_text)

        last_exception = None

        for model in self.models_to_try:
            try:
                logger.info(f"Submitting query asynchronously to Gemini model: '{model}'...")
                
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=MarketReportResponse,
                        temperature=0.1
                    )
                )

                # Check parsed response (automatically populated by the SDK when response_schema is set)
                report = None
                if response.parsed:
                    logger.info(f"Successfully received and parsed structured response from model: '{model}'.")
                    report = response.parsed
                else:
                    logger.warning(f"SDK response.parsed is empty for '{model}'. Fallback to manual parsing.")
                    data = json.loads(response.text)
                    report = MarketReportResponse.model_validate(data)

                if report:
                    # Attach the full set of deduplicated unique articles to the report object
                    # so they can all be logged in the database history
                    report.articles = articles
                    return report

            except APIError as api_err:
                # Catch 429 rate limit / quota exhaustion errors and try the next model
                if api_err.code == 429:
                    logger.warning(
                        f"Gemini API model '{model}' rate limited (429 RESOURCE_EXHAUSTED). "
                        f"Error: {api_err.message}. Attempting model fallback..."
                    )
                    last_exception = api_err
                    continue
                else:
                    logger.error(f"Gemini API error (code {api_err.code}) for model '{model}': {api_err.message}")
                    raise api_err
            except Exception as e:
                logger.error(f"Unexpected error with model '{model}': {e}")
                raise e

        # If we exhausted the entire models list and still encountered failures
        if last_exception:
            raise last_exception
        raise ValueError("All configured Gemini models failed to analyze the news batch.")
