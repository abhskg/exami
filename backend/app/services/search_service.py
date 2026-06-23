import html
import logging
import re
import urllib.parse
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# List of domains we exclude from search results to avoid parsing junk/ads
EXCLUDED_DOMAINS = [
    "duckduckgo.com",
    "google.com",
    "bing.com",
    "yahoo.com",
    "yandex.com",
    "w3.org",
    "facebook.com",
    "twitter.com",
    "youtube.com",
    "linkedin.com",
    "pinterest.com",
]


def clean_html(html_text: str) -> str:
    """
    Remove HTML tags, script/style content, comments, and normalize spacing.
    Returns clean plain text.
    """
    if not html_text:
        return ""

    # Remove script, style, noscript tags and their contents
    html_text = re.sub(
        r"<(script|style|noscript)[^>]*>([\s\S]*?)<\/\1>",
        "",
        html_text,
        flags=re.IGNORECASE,
    )

    # Remove HTML comments
    html_text = re.sub(r"<!--[\s\S]*?-->", "", html_text)

    # Replace block-level element tags with newlines
    html_text = re.sub(
        r"</?(p|div|h1|h2|h3|h4|h5|h6|li|tr|section|article|header|footer)[^>]*>",
        "\n",
        html_text,
        flags=re.IGNORECASE,
    )

    # Strip remaining HTML tags
    html_text = re.sub(r"<[^>]+>", "", html_text)

    # Unescape HTML entities (e.g. &amp; -> &, &quot; -> ", etc.)
    html_text = html.unescape(html_text)

    # Clean up excessive newlines and leading/trailing whitespace
    lines = [line.strip() for line in html_text.splitlines()]
    clean_lines = [line for line in lines if len(line) > 20]  # ignore tiny boilerplate lines

    return "\n".join(clean_lines)


def search_wikipedia(query: str) -> str:
    """
    Query Wikipedia search API, fetch the top 2 matching articles,
    extract their plain text content, and return a concatenated string.
    """
    logger.info(f"Searching Wikipedia for query: '{query}'")
    search_url = "https://en.wikipedia.org/w/api.php"
    headers = {"User-Agent": "AIExamPortalWebSearchAgent/1.0"}

    try:
        # Step 1: Search for matching pages
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
        }
        r = httpx.get(search_url, params=search_params, headers=headers, timeout=8.0)
        if r.status_code != 200:
            logger.warning(f"Wikipedia search failed with status code: {r.status_code}")
            return ""

        data = r.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            logger.info(f"No Wikipedia articles found matching: '{query}'")
            return ""

        # Step 2: Retrieve full text extracts for the top 2 matches
        content_blocks = []
        for item in search_results[:2]:
            title = item.get("title")
            logger.debug(f"Fetching Wikipedia article extract for: '{title}'")
            content_params = {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "titles": title,
                "format": "json",
            }
            cr = httpx.get(search_url, params=content_params, headers=headers, timeout=8.0)
            if cr.status_code == 200:
                cdata = cr.json()
                pages = cdata.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    extract = page_info.get("extract", "")
                    if extract:
                        content_blocks.append(f"### Wikipedia Article: {title}\n\n{extract}")

        return "\n\n".join(content_blocks)

    except Exception as e:
        logger.error(f"Error querying Wikipedia for '{query}': {e}")
        return ""


def search_ddg_and_scrape(query: str) -> str:
    """
    Query DuckDuckGo HTML search page, extract top 2 external links,
    scrape their contents, clean the HTML, and return plain texts.
    """
    logger.info(f"Searching DuckDuckGo HTML and scraping pages for query: '{query}'")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"

    try:
        # Step 1: Fetch search results HTML
        r = httpx.get(url, headers=headers, timeout=10.0)
        if r.status_code != 200:
            logger.warning(f"DuckDuckGo search failed with status code: {r.status_code}")
            return ""

        # Step 2: Extract search result URLs
        hrefs = re.findall(r'href="([^"]+)"', r.text)
        external_urls = []
        for href in hrefs:
            if href.startswith(("http://", "https://")):
                # Check that it's not a search engine or track link
                if not any(domain in href for domain in EXCLUDED_DOMAINS):
                    if href not in external_urls:
                        external_urls.append(href)

        logger.info(f"Found {len(external_urls)} candidate URLs for query '{query}'")

        # Step 3: Fetch and clean top 2 target URLs
        page_contents = []
        for target_url in external_urls[:2]:
            try:
                logger.info(f"Scraping external page: {target_url}")
                page_res = httpx.get(
                    target_url, headers=headers, timeout=8.0, follow_redirects=True
                )
                if page_res.status_code == 200:
                    cleaned_text = clean_html(page_res.text)
                    if cleaned_text:
                        # Limit to first 4000 characters to keep context sizes reasonable
                        page_contents.append(
                            f"### Source Web Page: {target_url}\n\n{cleaned_text[:4000]}"
                        )
            except Exception as pe:
                logger.warning(f"Failed to scrape page '{target_url}': {pe}")

        return "\n\n".join(page_contents)

    except Exception as e:
        logger.error(f"Error searching DuckDuckGo and scraping for '{query}': {e}")
        return ""


def research_topic(query: str, syllabus: str) -> str:
    """
    Research a topic from multiple sources.
    1. Try Gemini search grounding if configured and enabled.
    2. Fallback to scraping Wikipedia and DuckDuckGo search results.
    """
    if settings.APP_ENV == "test":
        logger.info(f"Mocking search research for query: '{query}' in test environment.")
        return (
            f"### Mock Search Topic: {query}\n"
            f"This is mock web scraped content for '{query}' under syllabus context: '{syllabus}'."
        )

    # 1. Try Gemini Search Grounding first (imported inside to avoid circular imports)
    from app.services.llm_service import generate_search_grounding

    grounded_context = generate_search_grounding(query, syllabus)
    if grounded_context:
        logger.info(f"Successfully obtained Gemini Search Grounded context for query: '{query}'")
        return grounded_context

    # 2. Fallback to Wikipedia + DuckDuckGo web scraping
    logger.info(
        f"Using fallback search (Wikipedia + DDG scraping) for query: '{query}'"
    )
    retrieved_blocks = []

    wiki_result = search_wikipedia(query)
    if wiki_result:
        retrieved_blocks.append(wiki_result)

    ddg_result = search_ddg_and_scrape(query)
    if ddg_result:
        retrieved_blocks.append(ddg_result)

    if retrieved_blocks:
        return "\n\n".join(retrieved_blocks)

    return f"No search results could be retrieved for query: '{query}'."
