import re
import html

# Regex to find and remove HTML tags
HTML_TAG_RE = re.compile(r'<[^>]+>')

def strip_html(text: str) -> str:
    """
    Decodes HTML entities and strips HTML tags from input text.
    """
    if not text:
        return ""
    # Decode XML/HTML entities like &amp; &lt; &quot;
    unescaped = html.unescape(text)
    # Remove tags like <p> <b> <br/>
    stripped = HTML_TAG_RE.sub("", unescaped)
    return stripped

def clean_whitespace(text: str) -> str:
    """
    Replaces tabs, newlines, and multiple sequential spaces with a single space.
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()

def clean_text(text: str) -> str:
    """
    Applies unified HTML stripping and whitespace normalization to text.
    """
    return clean_whitespace(strip_html(text))
