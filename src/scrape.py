import base64
import io
import json
import os
import random
import time
from functools import lru_cache
from urllib.parse import urldefrag, urljoin, urlparse

import markdown
import requests
import trafilatura
from lxml import html as lh
from PIL import Image

HEADERS = {
    "User-Agent": "Mozilla/5.0 (personal study-notes bot; contact: you@example.com)"
}
SKIP_SEGMENTS = {"courses", "videos", "user", "tag", "category", "batch", "explore",
                 "jobs", "contest", "puzzles", "interview-experiences", "community"}
SKIP_WORDS = ("interview", "quiz", "cheat-sheet", "mcq", "projects", "roadmap", "-books")


def _get(url: str) -> str | None:
    time.sleep(random.uniform(2, 4))  # be polite to the site
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch failed {url}: {e}")
        return None


def _norm(url: str) -> str:
    u = urldefrag(url)[0].split("?")[0]
    return u.rstrip("/") + "/"


def extract_links(page_html: str, tutorial_url: str) -> list[str]:
    """Ordered, de-duplicated article links that belong to the same tutorial section."""
    tree = lh.fromstring(page_html)
    tree.make_links_absolute(tutorial_url)
    for bad in tree.xpath("//footer"):
        bad.drop_tree()
    section = urlparse(tutorial_url).path.strip("/").split("/")[0]
    self_url = _norm(tutorial_url)
    links: list[str] = []
    for href in tree.xpath("//a/@href"):
        p = urlparse(href)
        if not p.netloc.endswith("geeksforgeeks.org"):
            continue
        segs = p.path.strip("/").split("/")
        if len(segs) < 2 or segs[0] in SKIP_SEGMENTS or segs[0] != section:
            continue
        if any(w in segs[-1].lower() for w in SKIP_WORDS):
            continue
        n = _norm(href)
        if n != self_url and n not in links:
            links.append(n)
    return links


def get_tutorial_links(tutorial_url: str, cache_path: str = "cache/links.json") -> list[str]:
    """Subtopic list for a tutorial. Cached so the day -> subtopic mapping stays stable."""
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    if tutorial_url in cache:
        return cache[tutorial_url]

    page = _get(tutorial_url)
    links = extract_links(page, tutorial_url) if page else []
    if len(links) < 5:
        print(f"  WARNING: only {len(links)} links found on {tutorial_url}; pin a better URL in topics.yaml")
    if links:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        cache[tutorial_url] = links
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1)
    return links


@lru_cache(maxsize=256)
def embed_image(src: str | None, base: str = "") -> str | None:
    """Download an image, shrink it, return a data: URI (so the PDF is self-contained)."""
    if not src:
        return None
    url = urljoin(base, src)
    low = url.lower()
    if low.startswith("data:") or any(w in low for w in (".svg", "logo", "icon", "sprite", "avatar", "/ads/")):
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
    except Exception:
        return None
    if im.width < 150 or im.height < 80:  # icons, bullets, badges
        return None
    im.thumbnail((700, 700))
    buf = io.BytesIO()
    if im.mode in ("RGBA", "LA", "P"):
        im.convert("RGBA").save(buf, "PNG", optimize=True)
        mime = "png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=70, optimize=True)
        mime = "jpeg"
    return f"data:image/{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def fetch_article(url: str) -> dict | None:
    page = _get(url)
    if not page:
        return None
    md = trafilatura.extract(
        page,
        output_format="markdown",
        include_formatting=True,
        include_tables=True,
        include_links=False,
        include_images=True,   # diagrams are embedded later by condense()
    )
    if not md:
        print(f"  no content extracted from {url}")
        return None
    meta = trafilatura.extract_metadata(page)
    title = (meta.title if meta and meta.title else url).replace(" - GeeksforGeeks", "")
    html = markdown.markdown(md, extensions=["fenced_code", "tables"])
    return {"title": title, "url": url, "html": html}