import ipaddress
import os
import re
import socket
import sys
import tempfile
from datetime import date
from urllib.parse import urlparse

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bundle import build_chapters  # noqa: E402
from generate import (chapter, explain_text, html_to_text, make_outline, make_quiz,  # noqa: E402
                      make_section, quiz_chapters)
from llm import LLM, LLMError  # noqa: E402
from pdf_builder import build_pdf  # noqa: E402
from scrape import fetch_article  # noqa: E402
from slides_pdf import build_slides_pdf  # noqa: E402

st.set_page_config(page_title="StudyForge", page_icon="📚", layout="wide")


# ----------------------------------------------------------------------- helpers
def cfg(key: str, default: str = "") -> str:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "notes"


def safe_url(url: str) -> str | None:
    """Return an error message if the URL is not a public http(s) URL (blocks SSRF to localhost/LAN)."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return "Enter a full http(s) link."
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return "That address is not a public website."
    except socket.gaierror:
        return "Could not resolve that host."
    return None


def build_outputs(topic: str, chapters: list[dict], want_a4: bool, want_slides: bool,
                  label: str = "Study Guide") -> list[tuple[str, bytes, int, str]]:
    """Returns [(filename, bytes, pages, kind)]. Page numbers ("n / total") are drawn by the CSS footer."""
    out = []
    d = date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        stem = os.path.join(tmp, slug(topic))
        jobs = []
        if want_a4:
            jobs.append(("A4 notes", build_pdf(d, topic, label, chapters, f"{stem}_A4", 500)))
        if want_slides:
            jobs.append(("Slides", build_slides_pdf(d, topic, label, chapters, f"{stem}_slides", 500)))
        for kind, parts in jobs:
            for path, pages in parts:
                with open(path, "rb") as f:
                    out.append((os.path.basename(path), f.read(), pages, kind))
    return out


def show_downloads(outputs, key: str):
    if not outputs:
        return
    cols = st.columns(len(outputs))
    for i, (name, data, pages, kind) in enumerate(outputs):
        cols[i].download_button(f"⬇ {kind} ({pages} pages)", data, file_name=name,
                                mime="application/pdf", key=f"{key}-{i}", use_container_width=True)


# ------------------------------------------------------------------- password gate
APP_PASSWORD = cfg("APP_PASSWORD")
if APP_PASSWORD and not st.session_state.get("authed"):
    st.title("📚 StudyForge")
    pw = st.text_input("Password", type="password")
    if pw:
        if pw == APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

# ----------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("⚙️ Model")
    provider_label = st.radio(
        "Provider", ["Ollama", "OpenAI-compatible (Groq, OpenRouter, OpenAI...)"],
        index=0 if cfg("LLM_PROVIDER", "ollama") == "ollama" else 1)
    provider = "ollama" if provider_label == "Ollama" else "openai"
    if provider == "ollama":
        base_url = st.text_input("Ollama URL", cfg("OLLAMA_HOST", "http://localhost:11434"), key="ollama_url")
        api_key = st.text_input("API key (only for hosted Ollama)", cfg("OLLAMA_API_KEY"), type="password",
                                key="ollama_key")
        model = st.text_input("Model", cfg("LLM_MODEL", "llama3.1:8b"), key="ollama_model")
    else:
        base_url = st.text_input("Base URL", cfg("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"),
                                 key="oa_url")
        api_key = st.text_input("API key", cfg("OPENAI_API_KEY"), type="password", key="oa_key")
        model = st.text_input("Model", cfg("OPENAI_MODEL", "llama-3.3-70b-versatile"), key="oa_model")
    temperature = st.slider("Creativity", 0.0, 1.0, 0.4, 0.05)
    max_chars = st.number_input("Max characters of page text sent to the model", 2000, 60000, 12000, 1000)
    llm = LLM(provider, model, base_url, api_key, temperature)
    if st.button("Test connection"):
        try:
            names = llm.list_models()
            st.success(f"Connected. {len(names)} models: " + ", ".join(names[:8]))
        except LLMError as e:
            st.error(str(e))

st.title("📚 StudyForge")
st.caption("Topic or link → notes, A4 PDF, slide PDF (with page numbers) and quizzes.")

tab_topic, tab_link, tab_quiz = st.tabs(["📖 Topic → Notes", "🔗 Page link → Explain", "📝 Quiz"])

# ------------------------------------------------------------------ tab 1: topic
with tab_topic:
    c1, c2 = st.columns([3, 1])
    topic = c1.text_input("Topic", placeholder="e.g. Docker networking, Binary trees, Spring Boot security")
    level = c2.selectbox("Level", ["Beginner", "Intermediate", "Advanced"], key="lvl1")
    c3, c4, c5 = st.columns(3)
    n_sec = c3.slider("Sections (one page-group each)", 3, 15, 6)
    detail = c4.selectbox("Detail per section", ["Brief", "Standard", "Deep"], index=1)
    fmt = c5.multiselect("Outputs", ["A4 PDF", "Slides PDF"], default=["A4 PDF", "Slides PDF"])

    if st.button("Generate notes", type="primary", disabled=not topic.strip()):
        try:
            bar = st.progress(0.0, text="Planning outline...")
            outline = make_outline(llm, topic.strip(), n_sec, level)
            chapters = []
            for i, title in enumerate(outline):
                bar.progress(i / len(outline), text=f"Writing {i + 1}/{len(outline)}: {title}")
                md = make_section(llm, topic.strip(), title, level, detail, outline)
                chapters.append(chapter(title, md, f"Generated with {model}"))
            bar.progress(0.95, text="Building PDFs...")
            outs = build_outputs(topic.strip(), chapters, "A4 PDF" in fmt, "Slides PDF" in fmt)
            bar.progress(1.0, text="Done")
            st.session_state["notes"] = {"topic": topic.strip(), "outline": outline, "outs": outs,
                                         "text": "\n\n".join(f"{c['title']}\n{html_to_text(c['body'])}"
                                                             for c in chapters)}
        except LLMError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed: {e}")

    res = st.session_state.get("notes")
    if res:
        st.success(f"Notes ready: {res['topic']}")
        show_downloads(res["outs"], "dl-notes")
        with st.expander("Outline"):
            st.write("\n".join(f"{i}. {t}" for i, t in enumerate(res["outline"], 1)))

# ------------------------------------------------------------------- tab 2: link
with tab_link:
    url = st.text_input("Page link", placeholder="https://www.geeksforgeeks.org/...")
    c1, c2 = st.columns(2)
    mode = c1.selectbox("What to do", ["Explain simply", "Summarize", "Original article only"])
    level2 = c2.selectbox("Reader level", ["Beginner", "Intermediate", "Advanced"], key="lvl2")
    c3, c4 = st.columns(2)
    include_orig = c3.checkbox("Include the original article in the PDF", value=True)
    fmt2 = c4.multiselect("Outputs", ["A4 PDF", "Slides PDF"], default=["A4 PDF", "Slides PDF"], key="fmt2")

    if st.button("Fetch & generate", type="primary", disabled=not url.strip()):
        err = safe_url(url.strip())
        if err:
            st.error(err)
        else:
            try:
                with st.status("Working...", expanded=True) as status:
                    status.write("Fetching page...")
                    art = fetch_article(url.strip())
                    if not art:
                        raise RuntimeError("Could not fetch or extract content from that page.")
                    chapters = []
                    text = html_to_text(art["html"])
                    if mode != "Original article only":
                        status.write(f"Asking {model}...")
                        md = explain_text(llm, art["title"], text, mode, level2, int(max_chars))
                        chapters.append(chapter(f"{mode}: {art['title']}", md, f"Generated with {model}"))
                    if include_orig or mode == "Original article only":
                        status.write("Embedding original article...")
                        chapters += build_chapters([art])
                    status.write("Building PDFs...")
                    outs = build_outputs(art["title"], chapters, "A4 PDF" in fmt2, "Slides PDF" in fmt2)
                    status.update(label="Done", state="complete")
                st.session_state["link"] = {"title": art["title"], "outs": outs, "text": text,
                                            "preview": chapters[0]["body"] if chapters else ""}
            except LLMError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Failed: {e}")

    res = st.session_state.get("link")
    if res:
        st.success(res["title"])
        show_downloads(res["outs"], "dl-link")
        with st.expander("Preview"):
            st.html(res["preview"])

# ------------------------------------------------------------------- tab 3: quiz
with tab_quiz:
    src_choice = st.radio("Quiz source", ["Topic name", "Page link", "Pasted text", "Last generated notes"],
                          horizontal=True)
    q_topic = q_url = q_text = ""
    if src_choice == "Topic name":
        q_topic = st.text_input("Topic", key="qt")
    elif src_choice == "Page link":
        q_url = st.text_input("Page link", key="qu")
    elif src_choice == "Pasted text":
        q_text = st.text_area("Paste text", height=180, key="qx")
    c1, c2 = st.columns(2)
    n_q = c1.slider("Questions", 3, 30, 10)
    diff = c2.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)

    if st.button("Generate quiz", type="primary"):
        try:
            title, source = "", ""
            if src_choice == "Topic name":
                title, source = q_topic.strip(), f"Topic: {q_topic.strip()}"
            elif src_choice == "Page link":
                err = safe_url(q_url.strip())
                if err:
                    raise RuntimeError(err)
                art = fetch_article(q_url.strip())
                if not art:
                    raise RuntimeError("Could not fetch that page.")
                title, source = art["title"], html_to_text(art["html"])
            elif src_choice == "Pasted text":
                title, source = "Pasted text", q_text
            else:
                last = st.session_state.get("notes") or {}
                title, source = last.get("topic", ""), last.get("text", "")
            if not source.strip():
                raise RuntimeError("Nothing to build a quiz from yet.")
            with st.spinner("Writing questions..."):
                quiz = make_quiz(llm, source, n_q, diff, int(max_chars))
            for k in [k for k in st.session_state if k.startswith("qq-")]:
                del st.session_state[k]
            outs = build_outputs(f"Quiz {title}", quiz_chapters(title, quiz), True, False, "Quiz")
            st.session_state["quiz"] = {"title": title, "items": quiz, "checked": False, "outs": outs}
        except LLMError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Failed: {e}")

    quiz = st.session_state.get("quiz")
    if quiz:
        st.subheader(f"Quiz: {quiz['title']}")
        letters = "ABCDEFGH"
        for i, q in enumerate(quiz["items"]):
            st.radio(f"**{i + 1}. {q['question']}**", [f"{letters[j]}. {o}" for j, o in enumerate(q["options"])],
                     index=None, key=f"qq-{i}")
            if quiz["checked"]:
                pick = st.session_state.get(f"qq-{i}")
                right = f"{letters[q['answer_index']]}. {q['options'][q['answer_index']]}"
                if pick == right:
                    st.success(f"Correct. {q['explanation']}")
                else:
                    st.error(f"Answer: {right}. {q['explanation']}")
        b1, b2 = st.columns(2)
        if b1.button("Check answers"):
            quiz["checked"] = True
            st.rerun()
        if quiz["checked"]:
            score = sum(
                st.session_state.get(f"qq-{i}") == f"{letters[q['answer_index']]}. {q['options'][q['answer_index']]}"
                for i, q in enumerate(quiz["items"]))
            st.metric("Score", f"{score} / {len(quiz['items'])}")
        with b2:
            show_downloads(quiz["outs"], "dl-quiz")