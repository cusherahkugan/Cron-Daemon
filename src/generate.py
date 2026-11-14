"""Prompts + helpers that turn LLM output into the `chapters` format used by pdf_builder / slides_pdf."""
import html as h
import re

import markdown
from lxml import html as lh

from condense import full_content
from llm import LLM, LLMError, extract_json

SYS_TEACHER = (
    "You are an expert technical teacher. Write accurate, concise study notes in Markdown. "
    "Use '##' for main headings and '###' for sub-headings (never '#'). Use short paragraphs, "
    "bullet lists, comparison tables where useful, and fenced code blocks with a language tag. "
    "Do not add greetings or closing remarks. Do not invent facts or URLs."
)
DETAIL = {"Brief": "about 250 words", "Standard": "about 500 words", "Deep": "about 900 words with several code examples"}


def md_to_body(md: str) -> str:
    md = re.sub(r"^\s*```(?:markdown|md)\s*\n(.*?)\n```\s*$", r"\1", md.strip(), flags=re.S)
    raw = markdown.markdown(md, extensions=["fenced_code", "tables"])
    return full_content(raw, keep_links=True)


def chapter(title: str, md: str, note: str) -> dict:
    return {"title": title, "url": note, "body": md_to_body(md)}


def html_to_text(article_html: str) -> str:
    root = lh.fragment_fromstring(article_html, create_parent="div")
    return "\n".join(t.strip() for t in root.itertext() if t.strip())


# ------------------------------------------------------------------ topic -> notes
def make_outline(llm: LLM, topic: str, n: int, level: str) -> list[str]:
    raw = llm.chat(
        SYS_TEACHER,
        f"Create a logical learning path for the topic '{topic}' at {level} level as exactly {n} sections, "
        f'ordered from first to last. Reply as JSON: {{"sections": ["Section title", ...]}}',
        json_mode=True,
    )
    data = extract_json(raw)
    secs = data.get("sections") if isinstance(data, dict) else data
    secs = [str(s).strip() for s in (secs or []) if str(s).strip()]
    if not secs:
        raise LLMError("Could not build an outline.")
    return secs[:n]


def make_section(llm: LLM, topic: str, title: str, level: str, detail: str, outline: list[str]) -> str:
    return llm.chat(
        SYS_TEACHER,
        f"Topic: {topic}\nLevel: {level}\nFull outline: {'; '.join(outline)}\n\n"
        f"Write the study notes for the section '{title}' ({DETAIL.get(detail, DETAIL['Standard'])}). "
        "Cover only this section; do not repeat other sections. End with a '### Key takeaways' list.",
    )


# ------------------------------------------------------------ page text -> explanation
def explain_text(llm: LLM, title: str, text: str, mode: str, level: str, max_chars: int) -> str:
    text = text[:max_chars]
    task = {
        "Explain simply": "Explain this article step by step as if teaching a student. Define jargon, "
                          "add small examples, and finish with a '### Key takeaways' list.",
        "Summarize": "Summarize this article as structured notes: overview, main points, important code "
                     "or formulas, and a '### Key takeaways' list.",
    }[mode]
    return llm.chat(SYS_TEACHER, f"Reader level: {level}\nArticle title: {title}\n\n{task}\n\n--- ARTICLE ---\n{text}")


# ------------------------------------------------------------------------- quiz
def make_quiz(llm: LLM, source: str, n: int, difficulty: str, max_chars: int = 12000) -> list[dict]:
    raw = llm.chat(
        "You write fair, unambiguous multiple-choice quizzes for learners. Output JSON only.",
        f"Write {n} {difficulty}-difficulty multiple-choice questions based ONLY on the material below. "
        "Each question has exactly 4 options and exactly one correct answer. Vary which option is correct. "
        'Reply as JSON: {"questions": [{"question": "...", "options": ["...","...","...","..."], '
        '"answer_index": 0, "explanation": "one or two sentences"}]}\n\n'
        f"--- MATERIAL ---\n{source[:max_chars]}",
        json_mode=True,
    )
    data = extract_json(raw)
    items = data.get("questions") if isinstance(data, dict) else data
    quiz = []
    for q in items or []:
        try:
            opts = [str(o).strip() for o in q["options"]]
            idx = int(q["answer_index"])
            if len(opts) >= 2 and 0 <= idx < len(opts) and str(q["question"]).strip():
                quiz.append({"question": str(q["question"]).strip(), "options": opts,
                             "answer_index": idx, "explanation": str(q.get("explanation", "")).strip()})
        except (KeyError, ValueError, TypeError):
            continue
    if not quiz:
        raise LLMError("No valid questions were returned. Try again or use a larger model.")
    return quiz


def quiz_chapters(title: str, quiz: list[dict]) -> list[dict]:
    letters = "ABCDEFGH"
    qs, ans = [], []
    for i, q in enumerate(quiz, 1):
        opts = "".join(f"<p>{letters[j]}. {h.escape(o)}</p>" for j, o in enumerate(q["options"]))
        qs.append(f"<h5>Q{i}. {h.escape(q['question'])}</h5>{opts}")
        ans.append(f"<p><b>Q{i}: {letters[q['answer_index']]}.</b> {h.escape(q['options'][q['answer_index']])}"
                   f"<br>{h.escape(q['explanation'])}</p>")
    return [
        {"title": f"Quiz: {title}", "url": "Generated quiz", "body": "".join(qs)},
        {"title": "Answer key", "url": "Generated quiz", "body": "".join(ans)},
    ]