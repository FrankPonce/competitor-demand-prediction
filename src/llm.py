"""Tiny provider-agnostic chat client for free OpenAI-compatible LLM APIs (used only to *write* prose).

Providers are tried in order; any that has no API key is skipped:
    1. Groq        GROQ_API_KEY         openai/gpt-oss-120b      (free tier: 1,000 requests/day, 8k tokens/min)
    2. OpenRouter  OPENROUTER_API_KEY   openai/gpt-oss-120b:free (free tier: 50 requests/day)
Override the model of the first provider with LLM_MODEL. Set LLM_DISABLE=1 to force template text.

The caller always has a non-LLM fallback: `chat_json` returns None when every provider fails.
"""

from __future__ import annotations

import json
import os
import re
import time

import requests

PROVIDERS = [
    ("groq", "https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    ("openrouter", "https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY", "openai/gpt-oss-120b:free"),
]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        from pathlib import Path

        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    except ImportError:
        pass


def available() -> list[str]:
    _load_env()
    if os.environ.get("LLM_DISABLE") == "1":
        return []
    return [name for name, _, env, _ in PROVIDERS if os.environ.get(env)]


def _parse_json(text: str) -> dict | None:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _wait(resp: requests.Response, default: float = 20.0) -> float:
    """Seconds to wait from Retry-After / x-ratelimit-reset-* headers (e.g. '2.31s', '1m26.4s')."""
    for h in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        v = resp.headers.get(h)
        if not v:
            continue
        m = re.fullmatch(r"(?:(\d+)m)?([\d.]+)s?", v.strip())
        if m:
            return min(90.0, float(m.group(1) or 0) * 60 + float(m.group(2)) + 1)
    return default


def chat_json(system: str, user: str, max_tokens: int = 2500, temperature: float = 0.4) -> tuple[dict, str] | None:
    """Ask for a JSON object. Returns (object, 'provider/model') or None if no provider produced valid JSON."""
    _load_env()
    if os.environ.get("LLM_DISABLE") == "1":
        return None
    for i, (name, url, env, model) in enumerate(PROVIDERS):
        key = os.environ.get(env)
        if not key:
            continue
        if i == 0 and os.environ.get("LLM_MODEL"):
            model = os.environ["LLM_MODEL"]
        body = {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if "gpt-oss" in model:
            body["reasoning_effort"] = "low"  # reasoning tokens count against the per-minute budget
        for attempt in range(3):
            try:
                r = requests.post(url, json=body, timeout=120, headers={"Authorization": f"Bearer {key}"})
            except requests.RequestException as e:
                print(f"  llm {name}: {e}")
                break
            if r.status_code == 429 or r.status_code >= 500:
                w = _wait(r)
                print(f"  llm {name}: HTTP {r.status_code}, waiting {w:.0f}s")
                time.sleep(w)
                continue
            if not r.ok:
                print(f"  llm {name}: HTTP {r.status_code} {r.text[:160]}")
                break
            content = r.json()["choices"][0]["message"].get("content") or ""
            obj = _parse_json(content)
            if obj is not None:
                return obj, f"{name}/{model}"
            print(f"  llm {name}: response was not JSON")
            break
    return None
