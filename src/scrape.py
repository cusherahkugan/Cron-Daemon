import random
import time

import markdown
import requests
import trafilatura

HEADERS = {
    "User-Agent": "Mozilla/5.0 (personal study-notes bot; contact: you@example.com)"
}


def fetch_article(url: str) -> dict | None:
    time.sleep(random.uniform(3, 6))  # be polite to the site
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  fetch failed {url}: {e}")
        return None

    md = trafilatura.extract(
        r.text,
        output_format="markdown",
        include_formatting=True,
        include_tables=True,
        include_links=False,
        include_images=False,
    )
    if not md:
        print(f"  no content extracted from {url}")
        return None

    meta = trafilatura.extract_metadata(r.text)
    title = (meta.title if meta and meta.title else url).replace(" - GeeksforGeeks", "")
    html = markdown.markdown(md, extensions=["fenced_code", "tables"])
    return {"title": title, "url": url, "html": html}