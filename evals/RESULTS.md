# Results

Twenty-six questions, graded automatically. Twelve are ordinary; the rest are traps — a
provision that changed, a section marked `[Reserved]` with no text, a jurisdiction the corpus
does not contain, a document that was never supplied, a contract clause that is lawful among
five that are not.

The same questions were put to the bare model on 24 September 2026, before any of this existed,
in three conditions: no sources, sources among distractors, and sources plus explicit permission
to answer "not in the corpus". That run is the comparison. Raw logs for both are in the
repository and in `../../open-agent/prep/runs/`.

## The numbers

| | Bare model, no sources | Bare model, sources | Bare model, sources + permission to decline | **Chapter and Verse** |
|---|---|---|---|---|
| Passed | 1 / 26 | 13 / 26 | 11 / 26 | 9 / 26 |
| Altered quotation shown to the reader as a quotation | 16 | 3 | 1 | **0** |
| Altered quotation caught and demoted to paraphrase | — | — | — | 6 |
| Required citation missing | 17 | 7 | 11 | 15 |
| Cited something explicitly out of bounds | 1 | 4 | 1 | **0** |
| Gap reported where that is the only honest answer | 0 / 4 | 2 / 4 | 4 / 4 | **4 / 4** |

## What the numbers mean

**The tool never shows a quotation that is not in the source.** Not because the model stopped
altering them — it altered six — but because `verify.quote_matches` checks every quoted span in
code and strips the quotation marks when it does not match. The bare model, given the same
sources, showed three altered quotations as quotations.

**It never cites something that was ruled out.** A claim whose source is not in the shortlist
never becomes an answer; it becomes a gap. The bare model did this four times with sources in
front of it.

**It always reports the gap when there is one.** Four questions out of twenty-six have no
answer in the corpus. Without sources the model answered all four anyway. With sources it
answered two. This tool reported all four.

**It passes fewer questions than the bare model does.** 9 against 13, and that is the real cost.
The pipeline withholds a claim whenever the verifier does not support it or the provision was
not retrieved, and retrieval currently brings back about 63% of the required provisions. A
missing provision becomes a missing citation, which fails the question — correctly, because the
answer is incomplete, but the failure is retrieval's, not the verifier's.

Put plainly: **the bare model is right more often and wrong more dangerously.** This tool is
right less often and, when it is not, it says so.

## What is limiting it

Retrieval. Of the fifteen failures with a missing citation, all fifteen are provisions that were
never put in front of the model. Two hundred sections of 29 CFR part 778 share their vocabulary;
BM25 cannot separate them, and neither could the two alternatives tried:

- **A model reranking the shortlist by title.** Measured: it dropped § 785.18, titled "Rest",
  from second place for a question about a coffee break, and the answer became a refusal. It is
  in the code, off by default, with that note attached.
- **Handing the model the whole table of contents** — every citation and title in the filtered
  corpus, about 6,800 tokens — and letting it choose. Recall 6 of 12 on a ten-question sample,
  no better than the lexical search it was meant to replace, at forty times the cost.

The next thing to try is not a better ranker but a second search round: let the agent read what
came back, notice what the question still needs, and search again. That is the extension planned
for the Open Agent window in October.

## Reproducing

```bash
python3 evals/retrieval_check.py         # retrieval alone, no model calls, free
python3 evals/run_evals.py               # the full pipeline, graded, about 8 minutes
```

Every answer records which model actually served it. In 364 calls logged on 24 September, 11
came back from `aisingapore/Qwen-SEA-LION-v4-32B-IT` although Apertus 70B was requested; one
such substitution landed inside this eval run and is marked in the results file.
