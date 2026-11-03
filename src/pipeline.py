"""End-to-end: text -> facts (LLM) -> verify -> rules -> calculator -> draft worksheet for CA."""
import json
from datetime import datetime, timezone

from .calc import Register, compute
from .checklist import PROMPT_VERSION, QUESTIONS
from .extract import redact
from .rules import characterise
from .verify import verify


def run_case(case: dict, facts: dict, reg: Register, model: str = "gold-facts") -> dict:
    # The LLM only sees the redacted text, so its quotes must be checked against that same text
    # (run-1 bug: verifying against the original text rejected quotes spanning a redaction).
    vfacts, issues = verify(facts, redact(case["text"]))
    char = characterise(vfacts, case["payee_country"])
    result = compute(char, case, reg)
    return {
        "case_id": case["id"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model, "prompt_version": PROMPT_VERSION,
        "facts": vfacts, "verification_issues": issues, "result": result,
        "ca_decision": None,  # filled by the reviewing Chartered Accountant
        "label": "DRAFT FOR CA REVIEW - NOT TAX ADVICE",
    }


def is_stale(record: dict, reg: Register) -> bool:
    """A draft made under an older register version must be re-reviewed."""
    return record["result"]["register_version"] != reg.version


def worksheet_md(record: dict, case: dict, reg: Register) -> str:
    r = record["result"]
    lines = [f"# Draft withholding worksheet: {case['id']} ({record['label']})", "",
             f"Payee country: {case['payee_country']} | Payment date: {case['payment_date']} | "
             f"Amount (INR): {case['amount_inr']:,} | TRC: {case['trc']} | Form 10F: {case['form_10f']}",
             "", f"**Status:** {r['status']}"]
    if r["status"] == "DRAFT":
        lines += [f"**Category:** {r['category']}  |  **Rate:** {r['rate_pct']}%  |  "
                  f"**TDS:** INR {r['tds_inr']:,}", f"**Basis:** {r['reason']}"]
    else:
        lines += [f"**Routed to CA:** {r['reason']}"]
    lines += [f"**Section:** {r.get('section', 'n/a')}", "", "## Evidence",
              "| Q | Question | Answer | Quote |", "|---|---|---|---|"]
    for q, v in record["facts"].items():
        lines.append(f"| {q} | {QUESTIONS[q][:60]}... | {v['answer']} | {v['quote'] or '-'} |")
    lines += ["", "## Rules and sources used"]
    for rid in r.get("rules_used", []):
        row = reg.by_id.get(rid, {})
        lines.append(f"- `{rid}`: {row.get('article_or_section', '?')} "
                     f"({row.get('verification', '?')}) {row.get('source', '')}")
    if r.get("flags") or record["verification_issues"]:
        lines += ["", "## Flags for CA"] + [f"- {x}" for x in r.get("flags", []) +
                                             record["verification_issues"]]
    lines += ["", f"Register version: `{r['register_version']}` | Model: {record['model']} | "
                  f"Prompt: {record['prompt_version']}", "",
              "CA decision: [ ] Approve  [ ] Override (reason: ________)  Signature/UDIN: ________"]
    return "\n".join(lines)


def save(record: dict, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
