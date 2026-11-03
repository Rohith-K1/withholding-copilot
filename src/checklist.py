"""The fact checklist: the ONLY thing the LLM is asked to produce.

The LLM reports facts with verbatim evidence. It never decides the tax category,
the rate, or the section. Those come from rules.py and the register.
"""

PROMPT_VERSION = "checklist-v1"

ALLOWED = {
    "Q1": ["SOFTWARE", "SAAS", "SERVICES", "OTHER", "UNCLEAR"],
    **{q: ["YES", "NO", "NOT_MENTIONED", "UNCLEAR"] for q in
       ["Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]},
}

QUESTIONS = {
    "Q1": "What is the payment mainly for? SOFTWARE = a licence or copy of software the payer "
          "receives or installs; SAAS = online access to software hosted by the vendor; "
          "SERVICES = work performed by the vendor's people; OTHER = anything else.",
    "Q2": "Is a copy of the software delivered to or installed on the payer's systems?",
    "Q3": "Does the payer receive rights to copy (beyond its own use), modify, sublicense or "
          "distribute the software, or receive its source code?",
    "Q4": "Are the services technical or consultancy in nature (engineering, IT, technical or "
          "expert advice), as opposed to purely managerial, administrative, marketing or sales support?",
    "Q5": "After the service, will the payer's own staff be able to apply the technical knowledge, "
          "skill or process independently, without the vendor (for example training plus handover "
          "of know-how)?",
    "Q6": "Is the service ongoing or recurring, so that the payer continues to rely on the vendor "
          "to perform it?",
    "Q7": "Does the vendor develop and hand over technical plans or technical designs (drawings, "
          "specifications) to the payer?",
    "Q8": "Does the vendor have employees, an office or a fixed place of business in India, or send "
          "its personnel to India for this work?",
}

SYSTEM_PROMPT = """You extract facts from a contract or invoice excerpt for a tax reviewer.
You do NOT decide tax treatment, rates or legal sections.

For each question, give exactly one allowed answer and copy a supporting quote that appears
VERBATIM (exact substring) in the text.
- If the text says nothing relevant, answer NOT_MENTIONED with an empty quote.
- If the text is ambiguous or contradictory on the point, answer UNCLEAR.
- Never infer facts that are not written in the text.

Return ONLY a JSON object of this form, with keys Q1..Q8:
{"Q1": {"answer": "...", "quote": "..."}, "Q2": {"answer": "...", "quote": "..."}, ...}"""


def build_user_prompt(text: str) -> str:
    lines = [f"{q} ({'/'.join(ALLOWED[q])}): {QUESTIONS[q]}" for q in QUESTIONS]
    return "QUESTIONS:\n" + "\n".join(lines) + "\n\nTEXT:\n<<<\n" + text + "\n>>>"
