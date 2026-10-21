import argparse
import os

from dotenv import load_dotenv

from config import get_day_index, load_config, pick_subtopics, today_in_tz
from pdf_builder import build_pdf
from scrape import CACHE_PATH, fetch_article, resolve_topic
from search import find_tutorial_urls


def parse_args():
    p = argparse.ArgumentParser(description="cronDaemon: nightly GFG notes -> PDF -> email")
    p.add_argument("--day", type=int, help="force a day number (1 = first day) instead of using the date")
    p.add_argument("--only", help="only process this topic, e.g. --only Docker")
    p.add_argument("--no-mail", action="store_true", help="build the PDF but do not send email")
    p.add_argument("--list", action="store_true", help="print resolved tutorial pages + first subtopics, then exit")
    p.add_argument("--refresh", action="store_true", help="delete cache/links.json and re-resolve everything")
    return p.parse_args()


def _as_list(v) -> list[str]:
    if not v:
        return []
    return [v] if isinstance(v, str) else list(v)


def main():
    load_dotenv()
    args = parse_args()

    if args.refresh and os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
        print("cache cleared")

    cfg = load_config()
    today = today_in_tz(cfg.get("timezone", "Asia/Colombo"))
    day_index = args.day - 1 if args.day else get_day_index(cfg["start_date"], today)

    if day_index < 0 and not args.list:
        print(f"Nothing to do: today is before start_date {cfg['start_date']}.")
        return

    # topic -> ordered list of article URLs from its GFG tutorial page (each link = one subtopic)
    tutorial_links: dict[str, list[str]] = {}
    for topic, pinned in cfg["topics"].items():
        if args.only and args.only.lower() != topic.lower():
            continue
        res = resolve_topic(topic, _as_list(pinned), find_tutorial_urls)
        if not res:
            print(f"[{topic}] no tutorial page found, skipping")
            continue
        url, links = res
        print(f"[{topic}] tutorial page: {url} ({len(links)} subtopics)")
        tutorial_links[topic] = links

    if args.list:
        for topic, links in tutorial_links.items():
            print(f"\n== {topic} ==")
            for i, u in enumerate(links[:12], 1):
                print(f"  Day {i:>2}: {u}")
        return

    picks = pick_subtopics(tutorial_links, day_index, args.only)
    if not picks:
        print(f"Nothing to do for day {day_index + 1} (all subtopics finished).")
        return

    sections = []
    for topic, article_url in picks:
        print(f"[{topic}] -> {article_url}")
        art = fetch_article(article_url) or fetch_article(article_url)  # one retry
        sections.append({
            "topic": topic,
            "subtopic": art["title"] if art else article_url,
            "url": article_url,
            "html": art["html"] if art else "",
        })

    os.makedirs("output", exist_ok=True)
    pdf_path = f"output/notes_{today.isoformat()}.pdf"
    pages = build_pdf(today.isoformat(), sections, pdf_path, cfg.get("max_pages", 6))
    print(f"PDF saved: {pdf_path} ({pages} pages)")

    if args.no_mail:
        print("--no-mail set, skipping email.")
        return

    from mailer import send_mail

    summary = "\n".join(f"- {s['topic']}: {s['subtopic']}\n  {s['url']}" for s in sections)
    send_mail(
        subject=f"Study Notes {today.isoformat()} (Day {day_index + 1})",
        body=f"Good morning Cusherahhh! Today's notes just 10 pagessss:\n\n{summary}",
        attachment_path=pdf_path,
    )


if __name__ == "__main__":
    main()