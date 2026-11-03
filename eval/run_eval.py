"""Evaluation harness.

  python -m eval.run_eval --mode offline   # rules+calc on gold facts, keyword baseline (no API key)
  python -m eval.run_eval --mode llm       # + LLM extraction pipeline and plain-LLM baseline

Scores are reported per stage so extraction errors are separated from rule/calculation errors.
Raw LLM responses are saved to eval/results/raw/ for audit and for the LLM-log submission.
"""
import argparse
import json
from pathlib import Path

from baselines import keyword
from src.calc import Register
from src.checklist import QUESTIONS
from src.pipeline import run_case, save, worksheet_md

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "eval" / "results"


def load_cases():
    return json.loads((ROOT / "eval" / "cases.json").read_text())["cases"]


def gold_facts(case):
    f = {q: {"answer": "NOT_MENTIONED", "quote": ""} for q in QUESTIONS}
    for q, (a, quote) in case["gold_facts"].items():
        f[q] = {"answer": a, "quote": quote}
    return f


def outcome(record):
    r = record["result"]
    return ("ABSTAIN", None, r.get("section", "")) if r["status"] == "ABSTAIN" else \
        (r["category"], r["rate_pct"], r.get("section", ""))


def score_end(case, cat, rate, section):
    ok_cat = cat == case["gold_category"]
    ok_rate = ok_cat and (case["gold_rate_pct"] is None or rate == case["gold_rate_pct"])
    ok_sec = "gold_section_contains" not in case or case["gold_section_contains"] in (section or "")
    return ok_cat, ok_rate and ok_sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["offline", "llm"], default="offline")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    reg, cases = Register(), load_cases()
    (RES / "raw").mkdir(parents=True, exist_ok=True)
    rows, summary = [], {}

    # Stage A: rules + calculator on gold facts (tests the deterministic layer alone)
    a_ok = 0
    for c in cases:
        rec = run_case(c, gold_facts(c), reg)
        cat, rate, sec = outcome(rec)
        ok_cat, ok_all = score_end(c, cat, rate, sec)
        a_ok += ok_all
        (ROOT / "worksheets" / f"{c['id']}_gold.md").write_text(worksheet_md(rec, c, reg))
        rows.append({"id": c["id"], "gold": c["gold_category"], "gold_rate": c["gold_rate_pct"],
                     "rules_on_gold": f"{cat} {rate if rate is not None else ''}".strip(),
                     "rules_ok": ok_all, "gold_quote_issues": rec["verification_issues"]})
    summary["A_rules_on_gold_facts"] = f"{a_ok}/{len(cases)}"

    # Baseline 1: keyword rules (non-AI)
    k_ok = 0
    for c, row in zip(cases, rows):
        k = keyword.classify(c["text"])
        row["keyword"], row["keyword_ok"] = k, k == c["gold_category"]
        k_ok += row["keyword_ok"]
    summary["B_keyword_baseline_category"] = f"{k_ok}/{len(cases)}"

    if args.mode == "llm":
        from baselines import plain_llm
        from src.extract import MODEL, extract_facts
        model = args.model or MODEL
        summary["model"] = model
        f_hits = f_total = p_cat = p_all = abst_tp = abst_fp = abst_fn = 0
        pl_cat = pl_all = 0
        for c, row in zip(cases, rows):
            facts, raw = extract_facts(c["text"], model)
            (RES / "raw" / f"{c['id']}_extract.txt").write_text(raw)
            rec = run_case(c, facts, reg, model)
            save(rec, RES / f"{c['id']}_pipeline.json")
            (ROOT / "worksheets" / f"{c['id']}_llm.md").write_text(worksheet_md(rec, c, reg))
            # Stage 1: fact extraction accuracy on decisive questions
            misses = []
            for q, (a, _) in c["gold_facts"].items():
                f_total += 1
                got = rec["facts"][q]["answer"]
                if got == a:
                    f_hits += 1
                else:
                    misses.append(f"{q}:{got}!={a}")
            cat, rate, sec = outcome(rec)
            ok_cat, ok_all = score_end(c, cat, rate, sec)
            p_cat += ok_cat
            p_all += ok_all
            g_abs, p_abs = c["gold_category"] == "ABSTAIN", cat == "ABSTAIN"
            abst_tp += g_abs and p_abs
            abst_fp += p_abs and not g_abs
            abst_fn += g_abs and not p_abs
            row.update({"pipeline": f"{cat} {rate if rate is not None else ''}".strip(),
                        "pipeline_ok": ok_all, "fact_misses": misses,
                        "verify_issues": rec["verification_issues"]})
            # Baseline 2: single LLM call
            out, raw2 = plain_llm.classify(c, model)
            (RES / "raw" / f"{c['id']}_plain.txt").write_text(raw2)
            pcat = str(out.get("category", "")).upper()
            try:
                prate = float(out.get("rate_pct")) if out.get("rate_pct") is not None else None
            except (TypeError, ValueError):
                prate = None
            # "Business profits, no withholding required" with a null rate means a 0% rate.
            # Run 1 scored that as wrong (C09, C16); fixed for run 2.
            if pcat == "BUSINESS_PROFITS" and prate is None:
                prate = 0.0
            ok_c, ok_a = score_end(c, pcat, prate, str(out.get("section", "")))
            pl_cat += ok_c
            pl_all += ok_a
            row.update({"plain_llm": f"{pcat} {prate if prate is not None else ''}".strip(),
                        "plain_section": out.get("section", ""), "plain_ok": ok_a})
        n = len(cases)
        summary.update({
            "1_fact_extraction_decisive_Qs": f"{f_hits}/{f_total}",
            "2_pipeline_category": f"{p_cat}/{n}", "3_pipeline_category+rate+section": f"{p_all}/{n}",
            "abstain_correct/false_abstain/missed_abstain": f"{abst_tp}/{abst_fp}/{abst_fn}",
            "C_plain_llm_category": f"{pl_cat}/{n}", "C_plain_llm_category+rate+section": f"{pl_all}/{n}",
        })

    (RES / "summary.json").write_text(json.dumps({"summary": summary, "cases": rows}, indent=2))
    print(json.dumps(summary, indent=2))
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
