"""Effective-dated law register + deterministic rate/TDS calculator. No LLM involved."""
import csv
import hashlib
from datetime import date
from pathlib import Path

DEFAULT_REGISTER = Path(__file__).resolve().parent.parent / "data" / "register.csv"


class Register:
    def __init__(self, path=DEFAULT_REGISTER):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.version = hashlib.sha256(raw).hexdigest()[:10]
        self.rows = list(csv.DictReader(self.path.read_text(encoding="utf-8").splitlines()))
        self.by_id = {r["rule_id"]: r for r in self.rows}

    @staticmethod
    def _valid(row, on: date) -> bool:
        f, t = row["effective_from"], row["effective_to"]
        return (not f or date.fromisoformat(f) <= on) and (not t or on <= date.fromisoformat(t))

    def find(self, kind: str, on: date, payee_country="ANY", category=None):
        hits = [r for r in self.rows if r["kind"] == kind and self._valid(r, on)
                and r["payee_country"] in (payee_country, "ANY")
                and (category is None or r["category"] in (category, "ROYALTY_OR_FTS", "ALL"))]
        if len(hits) != 1:
            raise LookupError(f"Expected 1 '{kind}' row for {payee_country}/{category} on {on}, "
                              f"found {len(hits)}")
        return hits[0]


def compute(char: dict, case: dict, reg: Register) -> dict:
    on = date.fromisoformat(case["payment_date"])
    out = {"register_version": reg.version, "rules_used": list(char.get("basis", [])),
           "flags": list(char.get("flags", []))}
    try:
        sec = reg.find("withholding_section", on)
        out["section"] = sec["article_or_section"]
        out["rules_used"].append(sec["rule_id"])
    except LookupError as e:
        return {**out, "status": "ABSTAIN", "reason": str(e)}

    cat = char["category"]
    if cat == "ABSTAIN":
        return {**out, "status": "ABSTAIN", "reason": char["reason"]}

    if cat == "BUSINESS_PROFITS":
        rate = 0.0
        out["flags"].append("Not taxable in India only if vendor has no PE (assumed, CA to confirm)")
    else:
        dom = reg.find("domestic_rate", on, "ANY", cat)
        out["rules_used"].append(dom["rule_id"])
        out["flags"].append("Surcharge and cess not computed: CA to add if domestic rate applies")
        if case.get("trc") and case.get("form_10f"):
            treaty = reg.find("treaty_rate", on, case["payee_country"], cat)
            out["rules_used"].append(treaty["rule_id"])
            rate = min(float(treaty["rate_pct"]), float(dom["rate_pct"]))
        else:
            rate = float(dom["rate_pct"])
            out["flags"].append("TRC or Form 10F missing: treaty rate not available")
    out["rules_used"] = list(dict.fromkeys(out["rules_used"]))  # de-duplicate, keep order
    amount = float(case["amount_inr"])
    return {**out, "status": "DRAFT", "category": cat, "reason": char["reason"],
            "rate_pct": rate, "tds_inr": round(amount * rate / 100, 2)}
