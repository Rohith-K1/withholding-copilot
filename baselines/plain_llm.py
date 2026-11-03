"""Single-LLM-call baseline: ask the model for the whole answer (category, section, rate)."""
from src.extract import chat, parse_json, redact

SYSTEM = """You are an Indian international tax expert preparing a withholding-tax determination
for a payment by an Indian company to a non-resident. Return ONLY JSON:
{"category": "ROYALTY|FTS|BUSINESS_PROFITS|ABSTAIN", "section": "<Indian withholding section and form>",
 "rate_pct": <number or null>, "reasoning": "<one sentence>"}"""


def classify(case: dict, model: str) -> tuple[dict, str]:
    user = (f"Payee country: {case['payee_country']}\nPayment date: {case['payment_date']}\n"
            f"Tax Residency Certificate available: {case['trc']}\nForm 10F filed: {case['form_10f']}\n"
            f"Contract/invoice text:\n{redact(case['text'])}")
    raw = chat(SYSTEM, user, model)
    try:
        return parse_json(raw), raw
    except Exception:
        return {}, raw
