---
name: checklist
status: draft
mode: fast
---

# Build checklist

Fast mode: verification after every slice, explanation only where it changes a decision.

## Slices

- [x] **S1 corpus and filtering** — 530 units load; jurisdiction from the citation family; the
  date of the work selects between the two versions of Cal. Labor Code § 226.7. Verified: a
  query on 2027-01-15 returns the 2027 version and only that one.
- [x] **S2 retrieval** — BM25 over body and title as separate fields, a crude six-character stem
  that covers English and Russian inflection, a spread across the parts of the law so one
  regulation cannot fill the shortlist, and direct lookup of any provision the question names.
  Verified with `evals/retrieval_check.py`, which costs nothing: recall of the required
  provisions rose from 0.39 to 0.73 across the tuning.
- [x] **S3 arithmetic in Python** — `hours.py` parses a timesheet, computes the week, and works
  out both the federal and the Californian figure. Verified against the regulation's own worked
  example: $12/h for 46 hours with a $46 promised bonus gives a regular rate of $13.00 and
  $637.00 owed, exactly as 29 CFR 778.110(b) states.
- [x] **S4 draft and verification passes** — claims carry a source id; the verifier sees the
  claim and the provision alone; quotes are matched in code. Verified by hand on the contract
  that pays overtime at 1.25×: the model's claim that this is lawful was rejected by the
  verifier and moved to the gap list.
- [x] **S5 the page** — one page, claims and gaps in the same column, citations expand to the
  source text, a warning when the gateway serves a different model. Verified in the browser.
- [x] **S6 evals through the pipeline** — `evals/run_evals.py` grades all 26 questions with the
  checks used on the bare model before the build, so the two are comparable.
- [ ] **S7 packaging** — README, licence, video, submission.

## What was cut

- Uploading your own documents through the page. The samples are selectable; a file picker adds
  nothing to the argument.
- Storing anything. No accounts, no history, no database.
- A third jurisdiction. Two is enough to show a conflict and a language boundary.

## What changed during the build

The reranking step was added after retrieval on its own turned out to miss three of every five
required provisions: two hundred sections of one regulation share their vocabulary, and BM25
cannot separate them. Choosing from titles can.

The bonus handling in `hours.py` was added after the first eval run, when the computed figure
came out as $588 — the answer without the bonus in the regular rate, and the exact number the
baseline model produced by mistake. The regulation's own example is $637, and the code now gets
there.
