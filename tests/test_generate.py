from generate import md_to_body, make_quiz, quiz_chapters
from llm import extract_json


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply

    def chat(self, system, user, json_mode=False):
        return self.reply


def test_extract_json_handles_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 2} hope that helps') == {"a": 2}


def test_quiz_validation_drops_bad_items():
    reply = ('{"questions": [{"question": "Q?", "options": ["a","b","c","d"], "answer_index": 2, "explanation": "e"},'
             '{"question": "Bad", "options": ["a","b"], "answer_index": 9}]}')
    quiz = make_quiz(FakeLLM(reply), "text", 2, "easy")
    assert len(quiz) == 1 and quiz[0]["answer_index"] == 2
    assert len(quiz_chapters("T", quiz)) == 2


def test_markdown_code_survives():
    body = md_to_body("## Hi\n\ntext here ok\n\n```python\nx = 1\nprint(x)\n```")
    assert "<pre>" in body and "print(x)" in body