---
name: submission
status: draft
---

# Devpost submission — Build With AI: Basics

Fields as the form asks for them. Aleksandr reads them before anything is sent, and presses
Submit himself.

## Project name

Chapter and Verse

## Tagline

Answers only what it can trace to a source, and shows you the rest.

## What it does

It answers a question about pay and working time from three things: the law, the employment
contract and the timesheet. Every claim in the answer names the provision it rests on, every
quotation is matched against that provision in code before it is shown in quotation marks, and
everything that could not be established appears under **Not verified** — in the same column, in
the same type, as part of the answer rather than a disclaimer at the bottom.

It holds 530 provisions: the Fair Labor Standards Act, four parts of 29 CFR, seven sections of
the California Labor Code, and all 265 articles of the Labour Code of the Kyrgyz Republic, in
Russian. Two versions of California Labor Code § 226.7 are in there at once — the one in force
through 2026 and the one operative from January 2027 — because which applies depends on the date
of the shift.

## The problem

Ask any assistant whether overtime is owed and it answers fluently, with a citation that looks
right. Before writing a line of this project I measured that on the 26 questions in the
repository: with no sources, the model quoted words that exist in no source in 16 of its answers,
and one answer in twenty-six survived grading. The worst of them described a recordkeeping rule under 29 CFR § 531.7 and
quoted it — that section is marked [Reserved] and has no text at all.

Someone who is owed money cannot tell a real citation from a well-formed one.

## How it works

1. **Plan.** The model proposes the phrases it would look up, in the register of the law: people
   ask about a "coffee break", the regulation is headed "Rest".
2. **Filter, then rank.** Provisions outside the chosen jurisdictions or not in force on the date
   of the work are removed before ranking, so a version that takes effect in 2027 cannot win on
   wording for a shift worked in 2026.
3. **Draft.** Claims are written, each naming one source id. A claim citing anything outside the
   shortlist never becomes an answer; it becomes a gap.
4. **Look again.** Whatever the first pass could not settle becomes a query of its own — the
   words the model used to describe what is missing sit closer to the provision than the original
   question did. This second round is what took the graded run from 9 passes to 11.
5. **Verify.** Each claim goes back to the model alone, with the text of the provision and nothing
   else: not the question, not the other claims, not the reasoning that produced it. A verifier
   shown the reasoning agrees with it.
6. **Check quotations in code, compute in Python.** Hours and pay are worked out in `hours.py`.
   The baseline model, asked to do that arithmetic itself, went from the correct $637.00 to
   $757.36 inside one answer and called the second figure a correction.

## What I learned

That grounding and honesty are different problems. Giving the model the sources cut invented
quotations from 16 to 3 — and *raised* the number of times it cited something it had been told to
ignore, from 1 to 4. More text in front of it meant more to reach for.

And that the instruction which fixes fabrication has a price. Told it may answer "not in the
corpus", the model reported the gap in all four questions where that is the only honest answer —
and also declined 12 of the 22 questions it could have answered. Both halves of that trade-off
are only visible if you run both conditions, which is why the eval set has controls in it.

Two things I tried and threw away, both measured: a model reranking the shortlist by title (it
dropped § 785.18, "Rest", from second place for a question about a coffee break) and handing the
model the whole table of contents, 6,800 tokens a question, which did no better than the lexical
search it was meant to replace.

## Built with

Python 3.11 and the standard library — no framework, no vector database, no dependencies to
install. Apertus 70B through the Public AI gateway. Playwright for the screenshots, edge-tts for
the narration. Planned with the Devpost Learn skill pack; `devpost/scope.md`, `prd.md` and
`spec.md` are the documents that drove the build.

## Try it out

- Repository: https://github.com/bisale24-ops/chapter-and-verse
- `./run.sh` and open http://localhost:8000 — no install step
- Results against the pre-build baseline: `evals/RESULTS.md`

## What is honestly not there

Retrieval finds about seven in ten of the provisions a question needs; when it misses, the tool
reports a gap instead of inventing, but the answer is incomplete. A contract review with six
unlawful clauses gets one or two verified thoroughly rather than all six enumerated. It is a
proof of concept: two corpora, frozen at a date, and no way to add a jurisdiction without editing
a file. It shows provisions and arithmetic; it is not legal advice.

## Disclosure

The corpora, the eval set and the sample documents were assembled on 24 September 2026, inside
the submission period, and are in the repository with the scripts that built them. The pipeline,
the interface, the graders and the video were written after them, the same day.
