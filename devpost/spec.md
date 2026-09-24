---
name: spec
status: approved
---

# Spec — Chapter and Verse

## Shape

Python 3.11, standard library only, no framework and no vector database. A proof of concept that
needs `pip install` of nothing is one that a judge can actually run.

```
src/chapterverse/
  corpus.py     load units, filter by jurisdiction and by date in force
  retrieve.py   BM25 over the filtered units
  hours.py      parse a timesheet, compute hours, federal and Californian pay
  model.py      one call to the Public AI gateway, logs the served model
  answer.py     draft pass: claims, each with a unit id
  verify.py     second pass per claim, source only, plus verbatim quote matching
  pipeline.py   ask() -> {claims, gaps, sources, trace}
  server.py     http.server, one page, two endpoints
  cli.py        ask from the terminal
evals/run_evals.py   the 26 questions through the pipeline, graded
```

## The two passes

The draft pass gets the question, any attached documents and the retrieved units, and must
return JSON: a list of claims, each with `text`, `unit` and an optional `quote`.

The verification pass gets, for each claim, only the claim text and the text of the unit it
names. It never sees the question, the other claims or the reasoning that produced them, because
a verifier that sees the reasoning agrees with it. It returns `supported`, `unsupported` or
`not_in_source` with a one-line reason.

Quotes are checked deterministically, not by the model: whitespace, quotation marks, non-breaking
hyphens and markdown emphasis are normalised, elisions are split on `...` and `* * *`, and each
fragment of 25 characters or more must appear in the unit.

## Model choice

`swiss-ai/apertus-v1.5-70b` for both passes, temperature 0. Measured on 208 calls on 24 September
2026: with permission to decline, the 8B model invented quotations in 29 of 104 answers against 2
of 98 for 70B, Fisher p < 0.0001, paired permutation p < 0.0001. 8B stays available behind a flag
for the draft pass only.

Every response's `model` field is recorded. In the same 364 calls, 11 came back from
`aisingapore/Qwen-SEA-LION-v4-32B-IT` although Apertus 70B was requested, so provenance is part
of the output, not a footnote.

## Retrieval

Filter first, rank second. Jurisdiction comes from the request; date defaults to today and
excludes units whose `in_force` window does not contain it. Ranking is BM25 over the unit text
with the citation and title weighted, k1 = 1.5, b = 0.75, top 6 units passed to the draft pass.

Filtering before ranking is the whole reason the 2027 version of a provision cannot win on
wording for a shift worked in 2026.

## Arithmetic stays out of the model

`hours.py` computes hours from the timesheet and both pay figures in Python. The model is told
the numbers; it is never asked to produce them. A model that was allowed to compute this drifted
from $637 to $757.36 inside one answer during the baseline run.

## Failure handling

| Failure | Response |
|---|---|
| API error or timeout | retry with backoff, then return the gap section with the error |
| Draft pass returns unparseable JSON | one repair attempt, then every claim becomes a gap |
| Claim names a unit that was not retrieved | claim moves to gaps, marked as an invented citation |
| Quote not matched | quotation marks removed, claim marked paraphrase, kept only if the verifier supports it |
| Served model differs from the requested one | answer is returned with a provenance warning |

## Testing

`evals/run_evals.py` runs all 26 questions and grades them with the same checks as the
pre-build baseline: invented quotation, required and forbidden citations, expected figures,
required gap statements. The baseline numbers to beat, on the same questions and the same model:
12 of 26 passed with sources, 3 answers with an invented quotation, 2 of 4 gaps reported.
