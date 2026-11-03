"""Non-AI baseline: the kind of keyword rules a team would write without an LLM.
Deliberately reasonable, not a strawman: it checks the strongest signals first."""


def classify(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["india", "chennai", "mumbai", "bengaluru", "delhi", "second"]) \
            and "engineer" in t:
        return "ABSTAIN"
    if "source code" in t and ("modify" in t or "distribute" in t) and "not" not in t.split("source code")[0][-20:]:
        return "ROYALTY"
    if any(k in t for k in ["subscription", "hosted", "saas", "cloud"]):
        return "BUSINESS_PROFITS"
    if any(k in t for k in ["licence", "license", "software"]):
        return "BUSINESS_PROFITS"
    if any(k in t for k in ["train", "know-how", "know how", "drawings", "design", "transfer"]):
        return "FTS"
    if any(k in t for k in ["consult", "technical", "engineering"]):
        return "FTS"
    return "BUSINESS_PROFITS"
