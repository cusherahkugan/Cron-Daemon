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
CACHE_VERSION = 4   # bumped: hub-page filtering changed, old cached link lists are invalid
MIN_LINKS = 8

SKIP_SEGMENTS = {"courses", "videos", "user", "tag", "category", "batch", "explore",
                 "jobs", "contest", "puzzles", "interview-experiences", "community"}

SKIP_WORDS = ("interview", "quiz", "cheat-sheet", "mcq", "projects", "roadmap", "-books",
              "exercise", "practice", "-pdf", "complete-reference", "programming-examples",
              "examples", "-programs", "programs", "-reference", "references",
              "must-do", "questions", "for-companies", "companies", "asked-in", "-sheet")
SKIP_TEXT = ("interview", "cheat sheet", "cheatsheet", "quiz", "projects", "roadmap",
             "companies using", "career", "complete reference", "exercises",
             "practice questions", "mcq", "comparison of", "examples", "programs",
             "must do", "companies", "coding questions", "maang")

# Parent / landing / category-index pages that are never a real "subtopic".
# These pages are just lists of links to other articles (e.g. "Advanced Data Structures"
# lists AVL, Splay, Trie...), so using one as "Day 1" gives a useless PDF section.
HUB_SLUGS = {"devops-tutorial", "advanced-java", "nodejs", "angularjs", "java", "dbms",
             "react", "reactjs", "php", "python",
             # DSA category index pages
             "advanced-data-structures", "data-structures", "basic-data-structures",
             "algorithms", "advanced-algorithms", "dsa", "dsa-tutorial",
             "analysis-of-algorithms", "searching-algorithms", "sorting-algorithms",
             "graph-data-structure-and-algorithms", "tree-data-structure"}
# Slugs ending in "-tutorial(s)" are only treated as hub/landing pages when short
# (e.g. "docker-tutorial"). Longer slugs such as
# "introduction-to-arrays-data-structure-and-algorithm-tutorials" are real articles.
HUB_MAX_WORDS = 3
# Extra words that count as a match for a topic keyword.
KEYWORD_ALIASES = {"kubernetes": ("kubernetes", "k8s")}


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


def _keyword(topic: str) -> str:
    """'Docker' -> 'docker', 'Express.js' -> 'express', 'Node.js' -> 'node'."""
    k = _slug(topic)
    return k[:-2] if k.endswith("js") and len(k) > 4 else k


def _is_hub(slug: str) -> bool:
    slug = slug.lower()
    if slug in HUB_SLUGS:
        return True
    return (slug.endswith(("-tutorial", "-tutorials"))
            and len(slug.split("-")) <= HUB_MAX_WORDS)


# --------------------------------------------------------------------------- links
def extract_links(page_html: str, tutorial_url: str, topic: str | None = None) -> list[str]:
    """Ordered, de-duplicated article links that belong to the same tutorial section.

    When several topics share one GFG section (Docker/Kubernetes in /devops/, Express in
    /node-js/, Spring in /advance-java/) the link slug must contain the topic keyword, so
    the parent hub page is never picked as 'Day 1'."""
    tree = lh.fromstring(page_html)
    tree.make_links_absolute(tutorial_url)
    for bad in tree.xpath("//footer | //header | //nav | //aside"):
        bad.drop_tree()
    section = urlparse(tutorial_url).path.strip("/").split("/")[0]
    self_url = _norm(tutorial_url)

    kw = _keyword(topic) if topic else ""
    kws = KEYWORD_ALIASES.get(kw, (kw,)) if kw else ()
    need_kw = bool(kws) and not _slug(section).startswith(kw)

    links: list[str] = []
    for a in tree.xpath("//a[@href]"):
        href = a.get("href")
        p = urlparse(href)
        if not p.netloc.endswith("geeksforgeeks.org"):
            continue
        segs = p.path.strip("/").split("/")
        if len(segs) < 2 or segs[0] in SKIP_SEGMENTS or segs[0] != section:
            continue
        last = segs[-1].lower()
        if any(w in last for w in SKIP_WORDS) or _is_hub(last):
            continue
        if need_kw and not any(k in _slug(last) for k in kws):
            continue
        text = " ".join(a.text_content().split()).lower()
        if any(w in text for w in SKIP_TEXT):
            continue
        n = _norm(href)
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
    meta = trafilatura.extract_metadata(page)
    title = meta.title if meta and meta.title else url
    title = re.sub(r"\s*[-|–]\s*GeeksforGeeks\s*$", "", title).strip()
    body = markdown.markdown(md, extensions=["fenced_code", "tables"])
    return {"title": title, "url": url, "html": _restore_code(body, blocks)}