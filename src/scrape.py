import base64
import io
import json
import os
import random
import re
import time
from functools import lru_cache
from html import escape as _esc
from urllib.parse import urldefrag, urljoin, urlparse

import markdown
import requests
import trafilatura
from lxml import html as lh
from PIL import Image

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0 Safari/537.36 personal-study-notes-bot"),
    "Accept-Language": "en-US,en;q=0.9",
}
CACHE_PATH = "cache/links.json"
CACHE_VERSION = 6   # bumped: links are now every article link of the tutorial body, in page order
MIN_LINKS = 8

SKIP_SEGMENTS = {"courses", "videos", "user", "tag", "category", "batch", "explore",
                 "jobs", "contest", "puzzles", "interview-experiences", "community"}

def _get(url: str, tries: int = 2) -> str | None:
    for attempt in range(tries):
        time.sleep(random.uniform(2, 4))  # be polite to the site
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 404:
                print(f"  404 {url}")
                return None
            r.raise_for_status()
            return r.content.decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  fetch failed ({attempt + 1}/{tries}) {url}: {e}")
    return None


def _norm(url: str) -> str:
    u = urldefrag(url)[0].split("?")[0]
    return u.rstrip("/") + "/"


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --------------------------------------------------------------------------- links
def extract_links(page_html: str, tutorial_url: str, topic: str | None = None) -> list[str]:
    """Every article link in the tutorial page's own body, in page order (first -> last).

    Only the region between the page <h1> and the "Explore" sidebar is read, so the site
    menu (before the title) and the sidebar/footer (after the body) never leak in. Links to
    other GFG sections are kept - a tutorial like ML links to Python, Maths, etc. and every
    one of them is a day. Only duplicates, the page itself and non-article URLs
    (courses, videos, tags ...) are dropped. `topic` is unused, kept for compatibility."""
    tree = lh.fromstring(page_html)
    tree.make_links_absolute(tutorial_url)
    for bad in tree.xpath("//footer | //header | //nav | //script | //style"):
        bad.drop_tree()
    self_url = _norm(tutorial_url)

    started = not tree.xpath("//h1")          # no <h1> -> read the whole page
    links: list[str] = []
    for el in tree.iter():
        if not isinstance(el.tag, str):
            continue
        if el.tag == "h1":
            started = True
            continue
        if not started:
            continue
        if el.tag in ("h2", "h3", "h4") and el.text_content().strip().lower() == "explore":
            break
        if el.tag != "a" or not el.get("href"):
            continue
        p = urlparse(el.get("href"))
        if p.netloc not in ("www.geeksforgeeks.org", "geeksforgeeks.org"):
            continue
        segs = [x for x in p.path.split("/") if x]
        if len(segs) < 2 or segs[0] in SKIP_SEGMENTS:
            continue
        n = _norm(el.get("href"))
        if n != self_url and n not in links:
            links.append(n)
    return links


def _load_cache(path: str = CACHE_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
        if (isinstance(c, dict) and c.get("v") == CACHE_VERSION
                and "links" in c and "resolved" in c):
            return c
    except Exception:
        pass
    return {"v": CACHE_VERSION, "resolved": {}, "links": {}}


def _save_cache(cache: dict, path: str = CACHE_PATH) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1)


def resolve_topic(topic: str, pinned: list[str], search_fn, cache_path: str = CACHE_PATH):
    """Return (tutorial_url, ordered_article_links) for a topic, cached so that
    'Day N -> same subtopic' stays stable. Pinned URLs are tried first, then search.
    A cached entry is only reused if it still matches the pinned URLs in topics.yaml."""
    cache = _load_cache(cache_path)
    url = cache["resolved"].get(topic)
    pinned_norm = {p.rstrip("/") + "/" for p in pinned}
    if url and cache["links"].get(url) and (not pinned_norm or url in pinned_norm):
        return url, cache["links"][url]

    def candidates():
        yield from pinned
        yield from search_fn(topic)

    best = None
    seen: set[str] = set()
    for u in candidates():
        n = u.rstrip("/") + "/"
        if n in seen:
            continue
        seen.add(n)
        page = _get(n)
        links = extract_links(page, n, topic) if page else []
        print(f"  [{topic}] candidate {n} -> {len(links)} links")
        if len(links) >= MIN_LINKS:
            best = (n, links)
            break
        if links and (best is None or len(links) > len(best[1])):
            best = (n, links)

    if not best:
        return None
    if len(best[1]) < MIN_LINKS:
        print(f"  WARNING [{topic}]: only {len(best[1])} links; pin a better URL in topics.yaml")
    cache["resolved"][topic] = best[0]
    cache["links"][best[0]] = best[1]
    _save_cache(cache, cache_path)
    return best


# ------------------------------------------------------------------------- images
@lru_cache(maxsize=1024)
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


# ------------------------------------------------------------------------ article
_CODE_CLS = re.compile(
    r"(?:^|[\s_-])(?:highlight|highlighter-rouge|hljs|codeblock|code-block|code-container|"
    r"gfg-code|syntaxhighlighter|wp-block-code)(?:$|[\s_-])", re.I)
_LINE_XP = ".//*[contains(concat(' ', normalize-space(@class), ' '), ' line ')]"
_TOKEN = "CODEBLOCKXQ{}X"
_TOKEN_RE = re.compile(r"CODEBLOCKXQ(\d+)X")


def _code_text(el) -> str:
    """Text of a code container with one source line per line."""
    for br in el.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    rows = el.xpath(".//li")
    if len(rows) > 1:
        return "\n".join("".join(li.itertext()).rstrip() for li in rows)
    leafs = [n for n in el.xpath(_LINE_XP) if not n.xpath(_LINE_XP)]
    if len(leafs) > 1:
        return "\n".join("".join(n.itertext()).rstrip() for n in leafs)
    return "".join(el.itertext()).strip("\n")


def _prepare(page: str) -> tuple[str, list[str]]:
    """Repair GFG markup before trafilatura.

    * lazy-loaded images get a real src
    * every code block is swapped for a placeholder paragraph and its text (with real
      line breaks) is returned separately, so extraction can't flatten it.
    Returns (html, code_blocks)."""
    try:
        tree = lh.fromstring(page)
    except Exception:
        return page, []

    for img in tree.xpath("//img"):
        for attr in ("data-src", "data-lazy-src", "data-original"):
            v = img.get(attr)
            if v and not v.startswith("data:"):
                img.set("src", v)
                break

    blocks: list[str] = []
    done: set = set()
    for el in list(tree.iter("div", "pre", "figure", "section")):
        if el.getparent() is None:
            continue
        if el.tag != "pre" and not _CODE_CLS.search(el.get("class") or ""):
            continue
        if any(a in done for a in el.iterancestors()):
            continue
        if el.xpath(".//p | .//h2 | .//h3 | .//img"):  # a content wrapper, not code
            continue
        text = _code_text(el)
        if not text.strip():
            continue
        new = lh.Element("p")
        new.text = _TOKEN.format(len(blocks))
        new.tail = el.tail
        blocks.append(text)
        el.getparent().replace(el, new)
        done.add(el)
    return lh.tostring(tree, encoding="unicode"), blocks


def _restore_code(article_html: str, blocks: list[str]) -> str:
    def sub(m):
        i = int(m.group(1))
        return f"<pre>{_esc(blocks[i])}</pre>" if i < len(blocks) else ""

    article_html = re.sub(r"<p>\s*CODEBLOCKXQ(\d+)X\s*</p>", sub, article_html)
    return _TOKEN_RE.sub(sub, article_html)


def _clean_title(page: str, url: str) -> str:
    """Page title, ignoring template placeholders such as '%%title%%'."""
    meta = trafilatura.extract_metadata(page)
    title = (meta.title or "").strip() if meta and meta.title else ""
    if not title or "%%" in title:
        try:
            title = " ".join(lh.fromstring(page).xpath("string(//h1)").split())
        except Exception:
            title = ""
    if not title or "%%" in title:
        title = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
    return re.sub(r"\s*[-|–]\s*GeeksforGeeks\s*$", "", title).strip()


def fetch_article(url: str) -> dict | None:
    page = _get(url)
    if not page:
        return None
    kwargs = dict(
        output_format="markdown",
        include_formatting=True,
        include_tables=True,
        include_links=False,
        include_images=True,   # diagrams are embedded later by full_content()
    )
    prepared, blocks = _prepare(page)
    md = trafilatura.extract(prepared, favor_recall=True, **kwargs)
    if not md:
        blocks = []
        md = trafilatura.extract(page, **kwargs)
    if not md:
        print(f"  no content extracted from {url}")
        return None
    title = _clean_title(page, url)
    body = markdown.markdown(md, extensions=["fenced_code", "tables"])
    return {"title": title, "url": url, "html": _restore_code(body, blocks)}