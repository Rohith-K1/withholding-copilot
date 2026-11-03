# Withholding Copilot: drafting Form 15CB tax determinations for CA review

**Problem.** Before an Indian company pays a foreign vendor, a Chartered Accountant (CA) must certify how
much tax to withhold (Form 15CB, Form 146 from 1 April 2026). The hard step is deciding what the payment
*is* (royalty, fees for technical services (FTS), or business profits), because that is a reading-comprehension
problem over contracts and invoices. The rate and arithmetic are then mechanical.

**Jurisdiction.** India (payer) with payees resident in the US, UK and Singapore.

**Design in one line.** The LLM extracts facts with verbatim quotes, and never the tax answer. Code verifies
the quotes, rules map facts to a category, an effective-dated register supplies the law, a calculator computes
the TDS, and a CA approves.

```
contract text ─► [redact amounts] ─► LLM: 8-question fact checklist + quotes      (probabilistic)
              ─► verify.py: quote must exist verbatim, else UNCLEAR                (deterministic)
              ─► rules.py: facts → ROYALTY / FTS / BUSINESS_PROFITS / ABSTAIN      (deterministic)
              ─► calc.py + data/register.csv: rate & section valid on payment date (deterministic)
              ─► draft worksheet (worksheets/*.md) ─► CA approves / overrides       (human, accountable)
```

## Repository

| Path | What it is |
|---|---|
| `src/checklist.py` | The 8 fact questions and the LLM prompt (`PROMPT_VERSION`) |
| `src/extract.py` | OpenRouter call; redacts amounts before sending |
| `src/verify.py` | Rejects unsupported or invented evidence (fail-safe to UNCLEAR) |
| `src/rules.py` | Facts → category, or ABSTAIN with a reason |
| `src/calc.py` | Loads the register, picks rules valid on the payment date, computes TDS |
| `src/pipeline.py` | End-to-end run, audit record, worksheet, stale-draft check |
| `data/register.csv` | Law: rates, sections, precedents, effective dates, source URL, verification status |
| `eval/cases.json` | 16 test cases, **all synthetic**, with gold labels |
| `eval/run_eval.py` | Per-stage evaluation plus two baselines |
| `baselines/` | Keyword rules (non-AI) and a single-LLM-call baseline |
| `tests/test_core.py` | Unit tests for the deterministic layer |

## How to run

```bash
pip install requests pytest
python -m pytest -q tests                  # deterministic layer
python -m eval.run_eval --mode offline     # rules on gold facts + keyword baseline (no key needed)

export OPENROUTER_API_KEY=...              # free key from openrouter.ai
export OPENROUTER_MODEL=<free model id>    # record the exact model used here: ____________
python -m eval.run_eval --mode llm         # LLM pipeline + single-LLM baseline
```

Outputs: `eval/results/summary.json`, raw LLM responses in `eval/results/raw/` (keep these for the
LLM-log submission), and one draft worksheet per case in `worksheets/`.

## Test cases

All 16 cases are **synthetic**. Parties, texts and amounts are invented. Fact patterns are inspired by public
orders (Engineering Analysis (SC 2021), Salesforce.com Singapore, CPPGroup Services (ITAT Delhi 2025),
Korn Ferry, Buro Happold (ITAT Mumbai 2023)). They cover SaaS, licensed software, a source-code licence,
recurring support, consultancy, know-how transfer (US/SG), design handover, a thin invoice, staff in India,
a missing TRC, a law-change pair (C06 and C13: same facts, paid either side of 1 April 2026), managerial
services, a mixed contract, and a negation trap.

## Results so far (actually run)

LLM rows: run 2, model `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter, temperature 0, prompt
`checklist-v1`), one run. Run 1 vs run 2, per-case failure reasons and the bugs fixed between the two runs:
[eval/RESULTS.md](eval/RESULTS.md).

| Stage | Result | What it shows |
|---|---|---|
| Unit tests (deterministic layer) | 10/10 pass | Quote check, fail-safe parsing, PE gate, date-based section, TRC fallback, stale-draft detection, traceability, redaction regressions |
| A. Rules + calculator on gold facts | 16/16 | Consistency check only. Rules and gold labels share an author, so this is **not** evidence of legal correctness. |
| B. Keyword baseline (non-AI), category | 7/16 | Fails on negations ("no source code", "will not provide training") and on substance over wording |
| 1. LLM fact extraction, decisive questions | 53/54 | One miss (C16 Q1 `SAAS` vs `SERVICES`); the category was still right, but via a different rule |
| 2–3. Pipeline: category / category + rate + section | 16/16 / 16/16 | 4 correct abstentions, 0 false, 0 missed. Run 1 was 15/16 because of a redaction bug, since fixed (see RESULTS.md) |
| C. Single-LLM baseline: category / category + rate + section | 8/16 / 7/16 | Calls know-how transfers royalty, answers cases that should abstain, and cited the 2025 Act (s.393 / Form 146) in 0 of 15 post-April-2026 cases |

## Known limitations

- The register mixes official, primary and secondary sources (see its `verification` column). The 2025 Act
  section numbers come from secondary sources and must be checked against the official Act.
- PE determination, surcharge and cess, MFN clauses, transfer pricing and GST are out of scope (flagged to the CA).
- Gold labels are one reader's view under these rules. Contested areas (design handover, mixed contracts) abstain by design.
- Business-profits rows assume no PE. The CA is always flagged to confirm.

**Output is a draft for a qualified CA. It is not tax advice.**
