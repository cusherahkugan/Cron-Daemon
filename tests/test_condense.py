from condense import full_content
from scrape import extract_links

HTML = ("<h2>Intro</h2><p>One. Two. Three.</p><p><img src='a.png'></p><pre>"
        + "\n".join(f"line{i}" for i in range(30)) + "</pre>")

DSA_URL = "https://www.geeksforgeeks.org/dsa/dsa-tutorial-learn-data-structures-and-algorithms/"


def test_nothing_is_trimmed():
    out = full_content(HTML)
    assert "Three" in out and "line29" in out


def test_images_embedded_or_dropped():
    assert "data:image/png" in full_content(HTML, embed=lambda s: "data:image/png;base64,AAAA")
    assert "<img" not in full_content(HTML, embed=lambda s: None)


def test_junk_removed_real_text_kept():
    out = full_content("<p>Last updated : 12 Jan, 2025</p><p>Real text here.</p>")
    assert "Last updated" not in out and "Real text here." in out


PAGE_ML = """
<header><a href='/courses/x/'>menu</a></header>
<ul><li><a href='/machine-learning/python-for-machine-learning/'>nav</a></li></ul>
<h1>Machine Learning Tutorial</h1>
<h2>Module 1</h2>
<ul><li><a href='/machine-learning/introduction-machine-learning/'>Introduction</a></li>
<li><a href='/artificial-intelligence/ai-vs-ml/'>AI vs ML</a></li>
<li><a href='/machine-learning/introduction-machine-learning/#x'>dup</a></li></ul>
<h2>Module 2</h2>
<ul><li><a href='/python/introduction-to-python/'>Python</a></li>
<li><a href='/machine-learning/machine-learning-interview-questions/'>Interview</a></li>
<li><a href='/courses/ds/'>course</a></li>
<li><a href='/machine-learning/machine-learning-tutorial/'>self</a></li></ul>
<h3>Explore</h3>
<ul><li><a href='/machine-learning/types-of-machine-learning/'>Types</a></li></ul>
"""
ML_URL = "https://www.geeksforgeeks.org/machine-learning/machine-learning-tutorial/"


def test_links_follow_page_order_from_first_to_last():
    got = extract_links(PAGE_ML, ML_URL)
    assert got == [
        "https://www.geeksforgeeks.org/machine-learning/introduction-machine-learning/",
        "https://www.geeksforgeeks.org/artificial-intelligence/ai-vs-ml/",
        "https://www.geeksforgeeks.org/python/introduction-to-python/",
        "https://www.geeksforgeeks.org/machine-learning/machine-learning-interview-questions/",
    ]


def test_menu_before_title_and_sidebar_after_body_are_ignored():
    got = extract_links(PAGE_ML, ML_URL)
    assert not any("python-for-machine-learning" in u or "types-of-machine-learning" in u for u in got)