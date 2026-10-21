import argparse
import os

from dotenv import load_dotenv

from config import get_day_index, load_config, pick_subtopics, today_in_tz
from pdf_builder import build_pdf
from scrape import fetch_article, get_tutorial_links
from search import find_tutorial_url


def parse_args():
    p = argparse.ArgumentParser(description="cronDaemon: nightly GFG notes -> PDF -> email")
    p.add_argument("--day", type=int, help="force a day number (1 = first day) instead of using the date")
    p.add_argument("--only", help="only process this topic, e.g. --only Docker")
    p.add_argument("--no-mail", action="store_true", help="build the PDF but do not send email")
    return p.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    cfg = load_config()
    today = today_in_tz(cfg.get("timezone", "Asia/Colombo"))
    day_index = args.day - 1 if args.day else get_day_index(cfg["start_date"], today)

    # topic -> ordered list of article URLs from its GFG tutorial page (each link = one subtopic)
    tutorial_links: dict[str, list[str]] = {}
    for topic, pinned_url in cfg["topics"].items():
        if args.only and args.only.lower() != topic.lower():
            continue
        if day_index < 0:
            break
        url = pinned_url or find_tutorial_url(topic)
        if not url:
            print(f"[{topic}] no tutorial page found, skipping")
            continue
        print(f"[{topic}] tutorial page: {url}")
        tutorial_links[topic] = get_tutorial_links(url)

    picks = pick_subtopics(tutorial_links, day_index, args.only)
    if not picks:
        print(f"Nothing to do for day {day_index + 1} (before start_date, or all subtopics finished).")
        return

    sections = []
    for topic, article_url in picks:
        print(f"[{topic}] -> {article_url}")
        art = fetch_article(article_url)
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

    summary = "\n".join(f"- {s['topic']}: {s['subtopic']}" for s in sections)
    send_mail(
        subject=f"Study Notes {today.isoformat()} (Day {day_index + 1})",
        body=f"Good morning! Today's notes:\n\n{summary}",
        attachment_path=pdf_path,
    )


if __name__ == "__main__":
    main()