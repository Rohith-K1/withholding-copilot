"""Deterministic characterisation: verified facts -> category, or ABSTAIN with a reason.

Every outcome carries the register rule_ids that justify it.
NOT_MENTIONED handling (a design decision, see README):
  - decisive questions (Q1, Q3 for software, Q4/Q5 for services): NOT_MENTIONED counts as UNCLEAR
  - Q6, Q7: NOT_MENTIONED counts as NO
  - Q8: NOT_MENTIONED counts as NO, but the CA is flagged to confirm there is no PE
"""

COVERED = {"US", "UK", "SG"}


def _a(f, q):
    return f[q]["answer"]


def _abstain(reason, basis=()):
    return {"category": "ABSTAIN", "reason": reason, "basis": list(basis), "flags": []}


def characterise(f: dict, payee_country: str) -> dict:
    flags = []
    # Step 1: out-of-scope gates
    if payee_country not in COVERED:
        return _abstain(f"Payee country {payee_country} not in register")
    q8 = _a(f, "Q8")
    if q8 in ("YES", "UNCLEAR"):
        return _abstain("Possible permanent establishment in India (out of scope)")
    if q8 == "NOT_MENTIONED":
        flags.append("No evidence either way on Indian presence: CA to confirm no PE")
    q1 = _a(f, "Q1")
    if q1 in ("OTHER", "UNCLEAR"):
        return _abstain("Payment type not covered or unclear")

    def done(cat, reason, basis):
        return {"category": cat, "reason": reason, "basis": list(basis), "flags": flags}

    # Step 2a: software / SaaS
    if q1 in ("SOFTWARE", "SAAS"):
        q3 = _a(f, "Q3")
        if q3 in ("UNCLEAR", "NOT_MENTIONED"):
            return _abstain("Software rights granted are unclear")
        if q1 == "SOFTWARE":
            if q3 == "YES":
                return done("ROYALTY", "Rights to copy/modify/distribute or source code granted",
                            [f"{payee_country}-ROY"])
            return done("BUSINESS_PROFITS", "Licence to use without copyright rights is not royalty",
                        ["P-EAC-2021", f"{payee_country}-BP"])
        if q3 == "YES":
            return _abstain("SaaS with rights to copy/modify is an atypical, contested structure")
        return done("BUSINESS_PROFITS", "Remote SaaS access without IP rights is not royalty",
                    ["P-SAAS", f"{payee_country}-BP"])

    # Step 2b: services
    q4, q5 = _a(f, "Q4"), _a(f, "Q5")
    q6 = "NO" if _a(f, "Q6") == "NOT_MENTIONED" else _a(f, "Q6")
    q7 = "NO" if _a(f, "Q7") == "NOT_MENTIONED" else _a(f, "Q7")
    if q4 in ("UNCLEAR", "NOT_MENTIONED"):
        return _abstain("Nature of services unclear")
    if q4 == "NO" and payee_country in ("US", "UK"):
        return done("BUSINESS_PROFITS", "Treaty FTS covers only technical/consultancy services",
                    [f"{payee_country}-BP"])
    if q5 in ("UNCLEAR", "NOT_MENTIONED"):
        return _abstain("Insufficient facts on whether know-how is made available")
    if q6 == "UNCLEAR" or q7 == "UNCLEAR":
        return _abstain("Supporting facts (Q6/Q7) unclear")
    if q5 == "YES" and q6 == "YES":
        return _abstain("Conflicting: know-how transfer and continued reliance on vendor",
                        ["P-CPP-2025"])
    if q5 == "YES":
        return done("FTS", "Make-available test met", [f"{payee_country}-FTS"])
    if q7 == "YES":
        return _abstain("Design handed over without make-available: contested limb",
                        ["P-BURO-2023"])
    return done("BUSINESS_PROFITS", "Make-available test not met",
                ["P-CPP-2025", f"{payee_country}-BP"])
