"""LLM fact extraction via OpenRouter. The only probabilistic component.

Confidentiality: amounts and currency figures are redacted before the text leaves the machine;
the calculator uses the structured amount locally.
"""
import json
import os
import re

import requests

from .checklist import SYSTEM_PROMPT, build_user_prompt

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")

# Run-1 bug: the old pattern r"(?:INR|USD|GBP|SGD|Rs\.?|₹|\$|£)\s?[\d,]+..." with re.I had no word
# boundary and accepted a bare comma as the "amount", so "engineers, including" became
# "enginee[AMOUNT] including" (case C07). The marker must now be a whole word or a currency symbol
# and must be followed by a digit.
_AMOUNT = re.compile(r"(?:\b(?:INR|USD|GBP|SGD|Rs\.?)|[₹$£])\s?\d[\d,]*(?:\.\d+)?", re.I)


def redact(text: str) -> str:
    return _AMOUNT.sub("[AMOUNT]", text)


def chat(system: str, user: str, model: str = MODEL) -> str:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Set OPENROUTER_API_KEY to run LLM stages")
    r = requests.post(URL, timeout=120, headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "temperature": 0,
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": user}]})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def parse_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else {}


def extract_facts(text: str, model: str = MODEL) -> tuple[dict, str]:
    """Return (facts, raw_response). On repeated failure returns {} -> verify() makes all UNCLEAR."""
    raw = ""
    for _ in range(2):
        raw = chat(SYSTEM_PROMPT, build_user_prompt(redact(text)), model)
        try:
            return parse_json(raw), raw
        except json.JSONDecodeError:
            continue
    return {}, raw
