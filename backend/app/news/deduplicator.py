import re
from app.models.schemas import ArticleResponse
from app.utils.logger import logger

# Set of standard English stopwords to filter during Jaccard similarity tokenization
STOP_WORDS = {
    'the', 'a', 'and', 'in', 'of', 'to', 'for', 'is', 'on', 'at', 'by', 'an', 
    'with', 'that', 'its', 'as', 'are', 'from', 'it', 'about', 'has', 'will',
    'after', 'before', 'this', 'was', 'were', 'be', 'or', 'but'
}

def tokenize(text: str) -> set[str]:
    """
    Cleans text, splits into alphanumeric tokens, and filters out stopwords and single-character terms.
    """
    if not text:
        return set()
    
    # Normalize to lowercase and remove non-alphanumeric punctuation
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    tokens = cleaned.split()
    
    # Filter stopwords and single characters (keeps tickers like T, but filters single letters)
    filtered = {t for t in tokens if t not in STOP_WORDS and len(t) > 1}
    return filtered

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """
    Computes Jaccard Similarity index between two text blocks.
    Value ranges from 0.0 (completely distinct) to 1.0 (identical tokens).
    """
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)
    
    if not tokens1 or not tokens2:
        return 0.0
        
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    return len(intersection) / len(union)

def deduplicate_articles(articles: list[ArticleResponse], threshold: float = 0.45) -> list[ArticleResponse]:
    """
    Assembles, compares, and filters out articles that are highly similar to each other.
    Articles are sorted by date so the earliest publisher of a story is preserved.
    """
    if not articles:
        return []

    unique_articles = []
    
    # Sort articles earliest first to preserve original reporting source
    sorted_articles = sorted(articles, key=lambda x: x.published_at)
    
    for article in sorted_articles:
        is_duplicate = False
        
        for unique in unique_articles:
            similarity = calculate_jaccard_similarity(article.title, unique.title)
            
            if similarity >= threshold:
                logger.debug(
                    f"Duplicate filtered: '{article.title}' ({article.source}) is similar to "
                    f"'{unique.title}' ({unique.source}) with score {similarity:.2f}"
                )
                is_duplicate = True
                break
                
        if not is_duplicate:
            unique_articles.append(article)
            
    logger.info(f"Deduplicated news list. Count reduced from {len(articles)} to {len(unique_articles)}.")
    return unique_articles
