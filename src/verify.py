"""Deterministic checks on the LLM's facts. Anything unsupported becomes UNCLEAR (fail safe)."""
import re

from .checklist import ALLOWED

NEEDS_QUOTE = {"YES", "NO", "SOFTWARE", "SAAS", "SERVICES", "OTHER"}


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().lower()


def verify(facts: dict, text: str) -> tuple[dict, list[str]]:
    """Return (verified_facts, issues). Never raises on bad LLM output."""
    src = _norm(text)
    out, issues = {}, []
    for q, allowed in ALLOWED.items():
        item = facts.get(q) if isinstance(facts, dict) else None
        if not isinstance(item, dict):
            out[q] = {"answer": "UNCLEAR", "quote": ""}
            issues.append(f"{q}: missing or malformed -> UNCLEAR")
            continue
        ans = str(item.get("answer", "")).strip().upper()
        quote = str(item.get("quote", "") or "")
        if ans not in allowed:
            out[q] = {"answer": "UNCLEAR", "quote": quote}
            issues.append(f"{q}: invalid answer '{ans}' -> UNCLEAR")
            continue
        if ans in NEEDS_QUOTE:
            if not quote.strip():
                out[q] = {"answer": "UNCLEAR", "quote": ""}
                issues.append(f"{q}: '{ans}' given without evidence -> UNCLEAR")
                continue
            if _norm(quote) not in src:
                out[q] = {"answer": "UNCLEAR", "quote": quote}
                issues.append(f"{q}: quote not found verbatim in source -> UNCLEAR")
                continue
        out[q] = {"answer": ans, "quote": quote}

    # Consistency: hosted SaaS cannot also be an installed copy.
    if out["Q1"]["answer"] == "SAAS" and out["Q2"]["answer"] == "YES":
        out["Q1"] = {"answer": "UNCLEAR", "quote": out["Q1"]["quote"]}
        issues.append("Q1/Q2: SAAS but installed copy -> Q1 UNCLEAR")
    return out, issues
