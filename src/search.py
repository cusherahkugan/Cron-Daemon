import re
from urllib.parse import urlparse

from ddgs import DDGS

BAD = ("interview", "exercise", "quiz", "practice", "cheat", "mcq", "project",
       "roadmap", "pdf", "question", "video", "course")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_tutorial_urls(topic: str, limit: int = 3) -> list[str]:
    """Fallback when no pinned URL works: ranked GFG tutorial-landing candidates."""
    want = _slug(topic)
    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for q in (f"site:geeksforgeeks.org {topic} tutorial",
              f"geeksforgeeks {topic} tutorial learn"):
        try:
            results = DDGS().text(q, max_results=10)
        except Exception as e:
            print(f"  search failed: {e}")
            continue
        for r in results:
            p = urlparse(r.get("href", ""))
            if not p.netloc.endswith("geeksforgeeks.org"):
                continue
            path = p.path.lower()
            if path.rstrip("/").endswith("/amp") or any(b in path for b in BAD):
                continue
            segs = [s for s in path.split("/") if s]
            if len(segs) < 2 or want not in _slug(path):
                continue
            url = f"https://{p.netloc}{p.path.rstrip('/')}/"
            if url in seen:
                continue
            seen.add(url)
            score = -len(segs)  # shallower = more likely a hub page
            if "tutorial" in path:
                score += 3
            if want in _slug(segs[-1]):
                score += 2
            scored.append((score, url))
    scored.sort(reverse=True)
    return [u for _, u in scored[:limit]]