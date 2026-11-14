"""Tiny LLM client: Ollama (local/remote) or any OpenAI-compatible API (Groq, OpenRouter, OpenAI, LM Studio...)."""
import json
import re

import requests


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, provider: str = "ollama", model: str = "llama3.1:8b", base_url: str = "",
                 api_key: str = "", temperature: float = 0.4, timeout: int = 600, num_ctx: int = 8192):
        self.provider = provider
        self.model = model
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.temperature = temperature
        self.timeout = timeout
        self.num_ctx = num_ctx

    # ------------------------------------------------------------------ helpers
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def list_models(self) -> list[str]:
        try:
            if self.provider == "ollama":
                r = requests.get(f"{self.base_url}/api/tags", headers=self._headers(), timeout=15)
                r.raise_for_status()
                return sorted(m["name"] for m in r.json().get("models", []))
            r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=15)
            r.raise_for_status()
            return sorted(m["id"] for m in r.json().get("data", []))
        except Exception as e:
            raise LLMError(f"Cannot reach {self.base_url}: {e}") from e

    # --------------------------------------------------------------------- chat
    def chat(self, system: str, user: str, json_mode: bool = False) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        try:
            if self.provider == "ollama":
                payload = {"model": self.model, "messages": messages, "stream": False,
                           "options": {"temperature": self.temperature, "num_ctx": self.num_ctx}}
                if json_mode:
                    payload["format"] = "json"
                r = requests.post(f"{self.base_url}/api/chat", json=payload,
                                  headers=self._headers(), timeout=self.timeout)
                r.raise_for_status()
                return r.json()["message"]["content"]

            payload = {"model": self.model, "messages": messages, "temperature": self.temperature}
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                              headers=self._headers(), timeout=self.timeout)
            if r.status_code == 400 and json_mode:      # some providers reject response_format
                payload.pop("response_format")
                r = requests.post(f"{self.base_url}/chat/completions", json=payload,
                                  headers=self._headers(), timeout=self.timeout)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except requests.HTTPError as e:
            body = e.response.text[:300] if e.response is not None else ""
            raise LLMError(f"LLM error {e.response.status_code if e.response is not None else ''}: {body}") from e
        except Exception as e:
            raise LLMError(f"LLM request failed: {e}") from e


def extract_json(text: str):
    """Parse JSON from a model reply, tolerating ```json fences and chatter around it."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise LLMError("Model did not return valid JSON. Try again or use a larger model.")