from pathlib import Path

from src.calc import Register, compute
from src.checklist import QUESTIONS
from src.pipeline import is_stale, run_case
from src.rules import characterise
from src.verify import verify

TEXT = "Vendor will train staff. Customer's team will apply the method on their own."


def facts(**kw):
    f = {q: {"answer": "NOT_MENTIONED", "quote": ""} for q in QUESTIONS}
    for q, (a, quote) in kw.items():
        f[q] = {"answer": a, "quote": quote}
    return f


def test_invented_quote_becomes_unclear():
    f = facts(Q5=("YES", "Vendor hands over all source code"))
    v, issues = verify(f, TEXT)
    assert v["Q5"]["answer"] == "UNCLEAR" and any("not found" in i for i in issues)


def test_answer_without_quote_becomes_unclear():
    v, _ = verify(facts(Q5=("YES", "")), TEXT)
    assert v["Q5"]["answer"] == "UNCLEAR"


def test_malformed_llm_output_fails_safe():
    v, issues = verify({"garbage": 1}, TEXT)
    assert all(x["answer"] == "UNCLEAR" for x in v.values()) and len(issues) == 8


def test_possible_pe_abstains():
    c = characterise(facts(Q8=("YES", "x")), "UK")
    assert c["category"] == "ABSTAIN" and "permanent establishment" in c["reason"]


def test_section_follows_payment_date():
    reg = Register()
    char = {"category": "BUSINESS_PROFITS", "reason": "", "basis": [], "flags": []}
    base = {"payee_country": "US", "amount_inr": 100, "trc": True, "form_10f": True}
    old = compute(char, {**base, "payment_date": "2026-03-31"}, reg)
    new = compute(char, {**base, "payment_date": "2026-04-01"}, reg)
    assert "195" in old["section"] and "393" in new["section"]


def test_missing_trc_uses_domestic_rate():
    reg = Register()
    char = {"category": "FTS", "reason": "", "basis": [], "flags": []}
    r = compute(char, {"payee_country": "SG", "amount_inr": 1000, "trc": False, "form_10f": True,
                       "payment_date": "2026-08-01"}, reg)
    assert r["rate_pct"] == 20 and r["tds_inr"] == 200


def test_register_change_marks_old_drafts_stale(tmp_path):
    reg = Register()
    case = {"id": "T", "text": TEXT, "payee_country": "SG", "payment_date": "2026-08-01",
            "amount_inr": 1000, "trc": True, "form_10f": True}
    rec = run_case(case, facts(Q1=("SERVICES", "Vendor will train staff"), Q4=("YES", "Vendor will train staff"),
                               Q5=("YES", "apply the method on their own"), Q8=("NO", "Vendor will train staff")), reg)
    assert rec["result"]["rate_pct"] == 10
    p = tmp_path / "register.csv"  # HYPOTHETICAL amendment, for the test only
    p.write_text(Path(reg.path).read_text().replace("SG-FTS,treaty_rate,SG,FTS,India-Singapore DTAA Art.12(4)(b) make-available,10",
                                                    "SG-FTS,treaty_rate,SG,FTS,India-Singapore DTAA Art.12(4)(b) make-available,8"))
    new_reg = Register(p)
    assert is_stale(rec, new_reg)
    assert run_case(case, rec["facts"], new_reg)["result"]["rate_pct"] == 8


def test_redact_keeps_words_and_redacts_amounts():
    """Run-1 regression: 'engineers, including' was corrupted to 'enginee[AMOUNT] including'."""
    from src.extract import redact
    assert redact("Customer's process engineers, including written recipes.") == \
        "Customer's process engineers, including written recipes."
    out = redact("Fee INR 2,200,000; travel Rs. 500; licence $1,000.")
    assert out == "Fee [AMOUNT]; travel [AMOUNT]; licence [AMOUNT]."


def test_quote_from_redacted_text_verifies():
    """Run-1 regression: the LLM quotes the redacted text, so verification must use it too."""
    from src.extract import redact
    text = "Vendor will train staff for a fee of INR 2,200,000. Customer's team will apply the method."
    quote = "train staff for a fee of [AMOUNT]"
    assert quote in redact(text)
    v, issues = verify(facts(Q4=("YES", quote)), redact(text))
    assert v["Q4"]["answer"] == "YES"
    assert not any(i.startswith("Q4") for i in issues)
    case = {"id": "T", "text": text, "payee_country": "SG", "payment_date": "2026-08-01",
            "amount_inr": 1000, "trc": True, "form_10f": True}
    rec = run_case(case, facts(Q4=("YES", quote)), Register())
    assert rec["facts"]["Q4"]["answer"] == "YES"
    assert not any(i.startswith("Q4") for i in rec["verification_issues"])


def test_every_cited_rule_exists_in_register():
    """Traceability: no output may cite a rule the auditor cannot look up."""
    import json
    from eval.run_eval import gold_facts
    reg = Register()
    cases = json.loads((Path(__file__).resolve().parent.parent / "eval" / "cases.json").read_text())["cases"]
    for c in cases:
        rec = run_case(c, gold_facts(c), reg)
        missing = [r for r in rec["result"]["rules_used"] if r not in reg.by_id]
        assert not missing, (c["id"], missing)
