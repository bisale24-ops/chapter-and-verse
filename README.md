# Chapter and Verse

A labour-pay assistant that answers only what it can trace to a source, and shows you the rest.

Ask whether overtime is owed and most assistants will answer fluently, with a citation that
looks right. Put the twenty-six questions in  to the bare model with no sources and it
quotes words that exist in no provision in sixteen of its answers; one answer out of twenty-six
survives grading. The worst of them describes a recordkeeping rule under 29 CFR 531.7 and
quotes it - that section is marked [Reserved] and has no text at all. Someone who is owed money
cannot tell a real citation from a well-formed one.

So this tool does something narrower and more useful: every claim carries the provision it rests
on, every quotation is matched against that provision before it is shown in quotation marks, and
everything that could not be established appears under **Not verified** — in the same column, in
the same type, as part of the answer rather than a disclaimer at the bottom.

```bash
./run.sh                 # http://localhost:8000
```

No dependencies. Python 3.11 and the standard library. Set `PUBLICAI_KEY`, or put a key in
`~/.config/publicai.key`, for the free [Public AI](https://publicai.co) gateway.

```bash
PYTHONPATH=src python3 -m chapterverse.cli "Does a 15-minute coffee break have to be paid?"
PYTHONPATH=src python3 -m chapterverse.cli --doc data/fixtures/timesheet_ca_week.csv \
    "A California employee works four 10-hour days at $20 an hour. Is overtime owed?"
PYTHONPATH=src python3 -m chapterverse.cli --lang ru --jurisdiction kg \
    "Работник отработал сверхурочно 5 часов. Как это оплачивается?"
```

## How an answer is built

1. **Plan.** The model proposes the phrases it would look up, in the register of the law. People
   ask about a "coffee break"; the regulation is headed "Rest".
2. **Filter, then rank.** Units outside the chosen jurisdictions, or not in force on the date of
   the work, are removed *before* ranking, so a version that takes effect in 2027 cannot win on
   wording for a shift worked in 2026. BM25 over what remains, balanced across the parts of the
   law, plus any provision the question names outright — including one with no text at all.
3. **Draft.** The model writes claims, each naming one source id. A claim that cites something
   outside the shortlist never becomes an answer; it becomes a gap.
4. **Verify.** Each claim goes back to the model on its own, with the text of the provision and
   nothing else — not the question, not the other claims, not the reasoning that produced it. A
   verifier that sees the reasoning agrees with it.
5. **Check the quotes in code.** A quoted span must appear in the cited provision after
   normalisation, elisions allowed. If it does not, the quotation marks come off and the text is
   labelled as the model's own words.
6. **Compute in Python.** Hours and pay are worked out in `hours.py` and handed to the model as
   facts. During the pre-build baseline the model, asked to do this arithmetic itself, went from
   the correct $637.00 to $757.36 inside one answer and presented the second figure as a
   correction.

## What it knows

| Corpus | Contents | Frozen at |
|---|---|---|
| United States | FLSA §§ 206, 207, 213; 29 CFR parts 531, 541, 778, 785; California Labor Code §§ 204, 226.7, 510, 511, 512, 558.1, 1194 | eCFR 2026-09-01, U.S. Code 2024 edition |
| Kyrgyz Republic | Labour Code, all 265 articles | edition of 28.07.2026 |

530 citable units in two languages. Cal. Labor Code § 226.7 is present in both of its versions,
the one in force through 2026 and the one operative from 1 January 2027, because which one
applies depends on the date of the shift.

Everything outside these two corpora is out of scope, and the tool says so instead of guessing.

## Measurement

`evals/` holds 26 questions with expected answers, required and forbidden citations, and the
figures that must appear. Twelve are ordinary questions; the rest are traps — a provision that
changed, a section marked `[Reserved]` with no text, a jurisdiction the corpus does not contain,
a contract that was never supplied, a contract clause that is perfectly lawful among five that
are not.

```bash
python3 evals/retrieval_check.py      # retrieval alone, no model calls, no cost
python3 evals/run_evals.py            # the whole pipeline, graded
```

The same questions were run against the bare model before this project existed, which is what
the numbers are compared against. See `evals/RESULTS.md`.

## Honest limits

- A proof of concept. Two corpora, frozen, and no way to add a jurisdiction without editing a file.
- Retrieval is BM25 with a planning step. On the eval questions it brings back about seven of
  every ten required provisions; when it misses, the tool reports a gap rather than inventing.
- Not legal advice. It shows provisions and arithmetic, and it is wrong often enough that you
  should read the provision it shows you.
- The gateway does not always serve the model that was requested: in 364 logged calls, 11 came
  back from another vendor's model. Every answer carries the model that actually served it, and
  the page says so when they differ.

## Layout

```
src/chapterverse/   corpus, retrieve, plan, hours, model, answer pipeline, verify, cli, server
data/               the two corpora, the eval set, sample contracts and timesheets
evals/              graded runs and the retrieval check
devpost/            scope, PRD and spec, written before the code
```

MIT licensed. Built with the Devpost Learn skill pack; the planning documents in `devpost/` are
the ones that drove the build.
