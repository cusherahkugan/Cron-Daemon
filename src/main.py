import argparse
import os
import re

from dotenv import load_dotenv

from bundle import build_chapters
from config import get_day_index, load_config, today_in_tz
from pdf_builder import build_pdf
from scrape import CACHE_PATH, fetch_article, resolve_topic
from search import find_tutorial_urls
from slides_pdf import build_slides_pdf

MAX_MAIL_MB = 23   # Gmail's limit is 25 MB including encoding overhead


def parse_args():
    p = argparse.ArgumentParser(description="cronDaemon: one tech stack per day -> full-notes PDFs -> email")
    p.add_argument("--day", type=int, help="force a day number (1 = first topic)")
    p.add_argument("--only", help="build this topic regardless of the day, e.g. --only Docker")
    p.add_argument("--no-mail", action="store_true", help="build PDFs but do not send email")
    p.add_argument("--no-slides", action="store_true", help="skip the landscape slide-style PDF")
    p.add_argument("--no-a4", action="store_true", help="skip the A4 PDF")
    p.add_argument("--list", action="store_true", help="print the day -> topic plan, then exit")
    p.add_argument("--refresh", action="store_true", help="delete cache/links.json and re-resolve")
    return p.parse_args()


def _as_list(v) -> list[str]:
    if not v:
        return []
    return [v] if isinstance(v, str) else list(v)


def _flag_finished() -> None:
    """Tell the GitHub workflow that every topic is done, so it can disable itself."""
    print("ALL TOPICS DONE - workflow will be disabled.")
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("finished=true\n")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    load_dotenv()
    args = parse_args()

    if args.refresh and os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
        print("cache cleared")

    cfg = load_config()
    topics: dict = cfg["topics"]
    names = list(topics)
    today = today_in_tz(cfg.get("timezone", "Asia/Colombo"))

    if args.list:
        for i, n in enumerate(names, 1):
            print(f"Day {i:>2}: {n}")
        return

    if args.only:
        match = [n for n in names if n.lower() == args.only.lower()]
        if not match:
            print(f"Unknown topic {args.only!r}. Known: {', '.join(names)}")
            return
        topic = match[0]
        day_index = names.index(topic)
    else:
        day_index = args.day - 1 if args.day else get_day_index(cfg["start_date"], today)
        if day_index < 0:
            print(f"Nothing to do: today is before start_date {cfg['start_date']}.")
            return
        if day_index >= len(names):
            _flag_finished()
            return
        topic = names[day_index]

    is_last_day = day_index == len(names) - 1
    day_label = f"Day {day_index + 1} of {len(names)}"
    print(f"== {day_label}: {topic} ==")

    res = resolve_topic(topic, _as_list(topics[topic]), find_tutorial_urls)
    if not res:
        raise SystemExit(f"[{topic}] no tutorial page found")
    tutorial_url, links = res
    print(f"[{topic}] {tutorial_url} -> {len(links)} articles")

    articles, failed = [], []
    for i, url in enumerate(links, 1):
        print(f"  ({i}/{len(links)}) {url}")
        art = fetch_article(url) or fetch_article(url)   # one retry
        if art:
            articles.append(art)
        else:
            failed.append(url)

    chapters = build_chapters(articles)
    if not chapters:
        raise SystemExit(f"[{topic}] no content could be fetched")
    if failed:
        print(f"WARNING: {len(failed)} articles failed:\n  " + "\n  ".join(failed))

    os.makedirs("output", exist_ok=True)
    stem = f"output/{day_index + 1:02d}_{_slug(topic)}_{today.isoformat()}"
    d = today.isoformat()
    attachments: list[str] = []

    if not args.no_a4:
        p = f"{stem}_notes_A4.pdf"
        n = build_pdf(d, topic, day_label, chapters, p)
        print(f"A4 PDF: {p} ({n} pages)")
        attachments.append(p)
    if not args.no_slides:
        p = f"{stem}_slides.pdf"
        n = build_slides_pdf(d, topic, day_label, chapters, p)
        print(f"Slides PDF: {p} ({n} pages)")
        attachments.append(p)

    if args.no_mail:
        print("--no-mail set, skipping email.")
    else:
        from mailer import send_mail

        send, skipped, total = [], [], 0
        for p in attachments:
            size = os.path.getsize(p) / 1_048_576
            if total + size <= MAX_MAIL_MB:
                send.append(p)
                total += size
            else:
                skipped.append(f"{os.path.basename(p)} ({size:.0f} MB)")
        note = ""
        if skipped:
            note += "\nToo big for email, download from the GitHub Actions artifact: " + ", ".join(skipped)
        if failed:
            note += f"\n{len(failed)} article(s) could not be fetched."
        if send:
            send_mail(
                subject=f"Study Notes - {topic} ({day_label})",
                body=(f"Good morning! Today's full notes: {topic}\n"
                      f"{len(chapters)} articles from {tutorial_url}{note}"),
                attachments=send,
            )
        else:
            print("All PDFs exceed the email limit; not sending (see workflow artifact).")

    if is_last_day and not args.only:
        _flag_finished()


if __name__ == "__main__":
    main()