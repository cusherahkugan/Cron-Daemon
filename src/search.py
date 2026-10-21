from ddgs import DDGS


def find_gfg_urls(topic: str, subtopic: str, limit: int = 3) -> list[str]:
    query = f"site:geeksforgeeks.org {subtopic} {topic}"
    urls: list[str] = []
    try:
        results = DDGS().text(query, max_results=15)
    except Exception as e:
        print(f"  search failed: {e}")
        return urls
    for r in results:
        url = r.get("href", "")
        if "geeksforgeeks.org" in url and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls