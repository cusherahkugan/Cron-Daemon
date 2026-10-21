from urllib.parse import urlparse

from ddgs import DDGS


def find_tutorial_url(topic: str) -> str | None:
    """Find the GFG tutorial landing page for a topic (e.g. 'Docker' -> Docker Tutorial)."""
    query = f"site:geeksforgeeks.org {topic} tutorial"
    try:
        results = DDGS().text(query, max_results=10)
    except Exception as e:
        print(f"  search failed: {e}")
        return None
    urls = [r.get("href", "") for r in results if "geeksforgeeks.org" in r.get("href", "")]
    for u in urls:  # prefer a page whose slug says "tutorial"
        if "tutorial" in urlparse(u).path.lower():
            return u
    return urls[0] if urls else None