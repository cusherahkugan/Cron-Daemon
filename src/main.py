import argparse
import os

from dotenv import load_dotenv

from config import get_day_index, load_config, pick_subtopics, today_in_tz
from pdf_builder import build_pdf
from scrape import fetch_article
from search import find_gfg_urls


def parse_args():
    p = argparse.ArgumentParser(description="cronDaemon: nightly GFG notes -> PDF -> email")
    p.add_argument("--day", type=int, help="force a day number (1 = first day) instead of using the date")
    p.add_argument("--only", help="only process this topic, e.g. --only Docker")
    p.add_argument("--limit", type=int, help="articles per subtopic (overrides config)")
    p.add_argument("--no-mail", action="store_true", help="build the PDF but do not send email")
    return p.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    cfg = load_config()
    today = today_in_tz(cfg.get("timezone", "Asia/Colombo"))
    day_index = args.day - 1 if args.day else get_day_index(cfg["start_date"], today)
    limit = args.limit or cfg.get("articles_per_subtopic", 3)

    picks = pick_subtopics(cfg["topics"], day_index, args.only)
    if not picks:
        print(f"Nothing to do for day {day_index + 1} (before start_date, or all subtopics finished).")
        return

    sections = []
    for topic, sub in picks:
        print(f"[{topic}] -> {sub}")
        articles = []
        for url in find_gfg_urls(topic, sub, limit):
            print(f"  fetching {url}")
            art = fetch_article(url)
            if art:
                articles.append(art)
        sections.append({"topic": topic, "subtopic": sub, "articles": articles})

    os.makedirs("output", exist_ok=True)
    pdf_path = f"output/notes_{today.isoformat()}.pdf"
    build_pdf(today.isoformat(), sections, pdf_path)
    print("PDF saved:", pdf_path)

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