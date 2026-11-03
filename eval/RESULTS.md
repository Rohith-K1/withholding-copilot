# Evaluation results: run 1 vs run 2

- **Model (both runs):** `nvidia/nemotron-3-ultra-550b-a55b:free` via OpenRouter, temperature 0, prompt `checklist-v1`
- **Cases:** 16, all synthetic (`eval/cases.json`). Gold labels are unchanged between runs.
- **Run 1 outputs:** `eval/results_run1/` (kept unmodified). **Run 2 outputs:** `eval/results/`.
- **What changed between runs:** the two pipeline bug fixes and one scorer fix described under
  [Bugs found and fixed](#bugs-found-and-fixed). Model, prompts, rules, register and gold labels did not change.

## 1. Run 1 vs run 2, every metric in `summary.json`

| Metric | Run 1 | Run 2 | Change |
|---|---|---|---|
| A. Rules + calculator on gold facts | 16/16 | 16/16 | none (deterministic) |
| B. Keyword baseline (non-AI), category | 7/16 | 7/16 | none (deterministic) |
| 1. LLM fact extraction, decisive questions | 49/54 | 53/54 | +4 |
| 2. Pipeline, category | 15/16 | 16/16 | +1 (C07) |
| 3. Pipeline, category + rate + section | 15/16 | 16/16 | +1 (C07) |
| Abstain: correct / false abstain / missed abstain | 4/1/0 | 4/0/0 | C07 false abstain removed |
| C. Plain-LLM baseline, category | 8/16 | 8/16 | none |
| C. Plain-LLM baseline, category + rate + section | 5/16 | 7/16 | +2, **all due to the scorer fix** (see below) |

**About the plain-LLM +2.** The run-1 figure of 5/16 used the old scorer. When the run-1 raw answers
(`eval/results_run1/raw/*_plain.txt`) are rescored offline with the fixed scorer, run 1 also gets
**7/16** (C09 and C16 become correct). So the plain LLM did not get better between runs; the scorer did.
In run 2 the model gave an explicit `0` rate for every business-profits answer, so the scorer fix had no
effect on run 2's score.

**Fact extraction, 49 → 53.** C07 +3 (Q1, Q4, Q6; their quotes now verify), C08 +1 (Q8 now `NO` instead of
`NOT_MENTIONED`), C15 +1 (Q5 now `YES` instead of `UNCLEAR`), C16 −1 (Q1 now `SAAS` instead of `SERVICES`).
Only the C07 change comes from the fixes. The C08, C15 and C16 changes are run-to-run variation from the
free model, even at temperature 0. **The C16 Q1 fact got worse in run 2.**

**Run-to-run variation in the plain LLM.** The plain LLM scored the same in both runs, but several of its
answers changed (C11: `BUSINESS_PROFITS 40` → `FTS 10`; C12: `ROYALTY 20` → `ROYALTY 10`;
C15: `FTS 10` → `FTS 15`; C06: rate 10 → 15). Treat single-run numbers from this model as noisy.

## 2. Per-case failures, run 2

Failure reasons come from `eval/results/raw/*_extract.txt` and `*_plain.txt` (the plain LLM's own
`reasoning` field) and from the keyword rule that fired in `baselines/keyword.py`.

### Pipeline (LLM facts → verify → rules → calculator)

**No end-to-end failures (16/16).** One fact error did not change the outcome:

| Case | Gold | Pipeline | What went wrong |
|---|---|---|---|
| C16 (managed data-warehouse hosting) | BUSINESS_PROFITS 0 | BUSINESS_PROFITS 0 (correct) | Q1 extracted as `SAAS` (quote: "Provider will host and operate Customer's data warehouse on Provider's servers in Manchester"), gold `SERVICES`. The answer was right for a different reason: the SaaS path (P-SAAS) instead of the "make-available not met" path (P-CPP-2025). The worksheet cites a different precedent from the one the gold facts would produce. |

### Plain-LLM baseline (single call returns category, section and rate): 9 failures

| Case | Gold | Plain LLM | Cause (from the model's own reasoning) |
|---|---|---|---|
| C05 executive-pay consultancy (US) | BUSINESS_PROFITS 0 | FTS 10 | Called consultancy FTS without applying the make-available test (the text says the methodology "is not shared"). The rate is also wrong: the register's India-US FTS rate is 15. |
| C06 training + manuals, paid 2026-07-01 (US) | FTS 15, s.393 | ROYALTY 15 | Treated the handed-over manuals as "information concerning industrial experience" (royalty). Also cited s.195 / Form 15CA/15CB, which had been replaced by s.393 / Form 146 on that date. |
| C07 know-how transfer programme (SG) | FTS 10 | ROYALTY 10 | Treated "transfer of proprietary process know-how and written recipes" as royalty under s.9(1)(vi). |
| C08 engineering drawings, no training (UK) | ABSTAIN | FTS 10 | Answered confidently on the contested design-handover limb (Buro Happold), which the gold label routes to the CA. 10% is not the register's UK FTS rate either (15). |
| C10 thin invoice "Consulting services, Q3" (US) | ABSTAIN | FTS 10 | Classified an invoice with no facts at all as FTS at 10%, where it should have abstained. |
| C11 engineers seconded to Chennai (UK) | ABSTAIN | FTS 10 | Ignored the possible PE from nine months of on-site personnel. (In run 1 it did spot the PE but answered `BUSINESS_PROFITS 40` instead of abstaining.) |
| C12 SPC method handover, **no TRC** (SG) | FTS 20 | ROYALTY 10 | Wrong category (royalty), and it applied a 10% treaty rate even though no TRC was available, so the domestic 20% rate should apply. |
| C13 same facts as C06, paid 2025-11-01 (US) | FTS 15, s.195 | FTS 10 | Right category and section, wrong rate: 10 instead of the register's India-US Art.12 rate of 15. |
| C15 training + three-year managed service (US) | ABSTAIN | FTS 15 | Resolved a contract with conflicting facts (know-how transfer and continued reliance) as FTS instead of flagging it. |

### Keyword baseline (non-AI): 9 failures (identical in both runs)

| Case | Gold | Keyword | Rule that fired / cause |
|---|---|---|---|
| C01 SaaS CRM (SG) | BUSINESS_PROFITS | ROYALTY | "source code" plus "modify"/"distribute" in "no source code and no right to copy, modify or distribute". The negation check only looks for "not" before "source code", so it misses "no". |
| C02 off-the-shelf CAD licence (US) | BUSINESS_PROFITS | ROYALTY | Same rule. The negation comes *after* the phrase ("Source code is not provided"). |
| C04 recurring IT helpdesk (UK) | BUSINESS_PROFITS | FTS | "train", "know-how" and "transfer" inside "No training or transfer of know-how is included". |
| C05 executive-pay consultancy (US) | BUSINESS_PROFITS | FTS | "consult". Wording beat substance. |
| C08 drawings (UK) | ABSTAIN | FTS | "drawings" / "train" (inside "will not train"). It has no abstain path for contested facts. |
| C09 intra-group admin (SG) | BUSINESS_PROFITS | FTS | "train" inside "not trained". |
| C10 thin invoice (US) | ABSTAIN | FTS | "consult". No way to recognise missing facts. |
| C15 training + managed service (US) | ABSTAIN | FTS | "train". No way to detect conflicting facts. |
| C16 managed hosting (UK) | BUSINESS_PROFITS | FTS | "train", "know-how" and "design", all inside negations ("will not provide training ... know-how", "no design work"). |

## 3. Which law did the plain LLM cite?

15 cases have a payment date on or after 2026-04-01, when the Income-tax Act 2025 replaced the 1961 Act
for withholding (register: `DOM-TDS-2025`, s.393 + Form 145/146). I checked each plain-LLM `section`
and `reasoning` field for s.393 / Form 146 / "Income-tax Act 2025" versus s.195 / Form 15CA/15CB / "1961".

| | Run 1 | Run 2 |
|---|---|---|
| Cited the 2025 Act (s.393 / Form 146) | **0 / 15** | **0 / 15** |
| Cited only the old law (s.195 and/or Form 15CA/15CB) | 15 / 15 | 14 / 15 |
| Cited no domestic withholding section (treaty article only) | 0 / 15 | 1 / 15 (C01: "Article 7 of India-Singapore DTAA (no PE)") |

Across both runs the single-call baseline **never** cited the provision in force on the payment date.
In run 2 it also cited the 1961 Act's s.115A domestic rate (now s.207 per the register) in C07, C12 and C15.
Only C06 is actually scored on section (`gold_section_contains: "393"`), and there it would have failed on
section even with the right category. On every other post-April case the scorer does not check section,
so the plain-LLM scores in table 1 **understate** how far it is from a usable answer. The pipeline gets
the section from the effective-dated register, so it cited s.393 / Form 145/146 for every post-April case
and s.195 for C13.

## Bugs found and fixed

These were found after run 1 by reading the C07 raw output and the scorer. Run 1's numbers above are
reported as they were produced, bugs included.

1. **Redaction corrupted ordinary words (`src/extract.py`, `redact()`).** The amount pattern
   `(?:INR|USD|GBP|SGD|Rs\.?|₹|\$|£)\s?[\d,]+...` with `re.I` had no word boundary and accepted a bare comma
   as the amount. In C07, "process engineers, including" matched `rs,` and became
   "process enginee[AMOUNT] including". The LLM therefore saw corrupted text. **Fix:** the marker must be a
   whole word (`\bINR`, `\bRs.` ...) or a currency symbol, and it must be followed by a digit.
   Regression test: `test_redact_keeps_words_and_redacts_amounts`.
2. **Quotes were verified against different text from what the LLM saw (`src/pipeline.py`, `run_case()`).**
   The LLM received the redacted text, but `verify()` checked its quotes against the original. Any quote
   spanning a redaction could never match. In C07 the model copied the (corrupted) text faithfully, and
   Q1, Q4 and Q6 were rejected as "quote not found verbatim", so the pipeline **falsely abstained** on a case
   it had answered correctly. **Fix:** verify against `redact(case["text"])`.
   Regression test: `test_quote_from_redacted_text_verifies`. Bug 1 made bug 2 visible, but bug 2 would
   also have rejected any honest quote containing a real amount.
3. **Scorer unfair to the baseline (`eval/run_eval.py`).** A plain-LLM answer of `BUSINESS_PROFITS` with
   `rate_pct: null` ("no withholding required") was scored wrong against a gold rate of 0. That affected
   C09 and C16 in run 1. **Fix:** treat a null rate as 0.0 for business profits. This *raised* the baseline's
   score; it was not tuned in the pipeline's favour.

The fail-safe design worked as intended in run 1: the bad quotes made the pipeline abstain rather than
produce a wrong draft. The cost was a needless CA referral, not a wrong tax figure.

## Interpretation limits

- **16 synthetic cases.** Written by the author and inspired by public orders, not drawn from real contracts.
  One case is about 6 percentage points; differences of one or two cases are not meaningful.
- **One model, one run per configuration.** A free OpenRouter model. Answers changed between runs at
  temperature 0 (section 1), so the numbers carry run-to-run noise that has not been measured.
- **Gold labels and rules share an author.** "Rules on gold facts 16/16" is a consistency check that the
  code does what the author intended. It is **not** evidence of legal accuracy. The pipeline's 16/16 means
  the LLM's facts agreed with the author's facts closely enough to reach the author's answer.
- **Contested cases abstain by design** (C08, C11, C15, C10). That makes the pipeline look safer, but it also
  means it does not attempt the hardest judgements; those go to the CA.
- **Register sources** are partly secondary or unverified (see the `verification` column of
  `data/register.csv`), including the 2025 Act section numbers. Rates scored as "correct" are correct
  *against the register*, not against verified law.
- **Section is scored on only two cases** (C06, C13).
