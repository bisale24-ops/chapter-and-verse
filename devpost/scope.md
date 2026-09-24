---
name: scope
status: approved
---

# Scope — Chapter and Verse

## The idea in one line

A labour-pay assistant that answers only what it can trace to a source, and shows the rest as a
list of things it could not verify.

## The problem it is built against

Ask any assistant whether overtime is owed and it will answer, fluently, with a citation that
looks right. Measured on the questions in  before this project existed: with no
sources, sixteen of twenty-six answers quoted words that are in no provision, and one answer in
twenty-six survived grading. A person who is owed money cannot tell the difference between a real
citation and a well-formed one, and neither can their employer.

The kernel is not retrieval. Retrieval is a solved-enough building block. The kernel is
**refusing to present an unverified claim as an answer**: every claim carries the provision it
rests on, every quoted span is matched against the source before it is shown in quotation marks,
and anything left over is reported instead of being smoothed into prose.

## Who it is for

Someone with a pay dispute and three documents: the law, their contract and their timesheet.
In the demo that is a warehouse worker in California and a fitter in Bishkek.

## The core loop

1. Ask a question, optionally attaching a contract and a timesheet.
2. The tool retrieves provisions, filtered by date and jurisdiction before ranking.
3. It drafts an answer in which every claim names the unit it relies on.
4. A second pass re-reads each claim against the source text alone and marks it supported,
   unsupported or not in the source.
5. The answer shows supported claims with their citations, and a gap section listing everything
   else, including what document was missing.

## What "done" means for the proof of concept

- The 26 questions in `data/evals.json` run end to end and are graded automatically.
- On the questions where the honest answer is "this is not in the sources", the tool says so.
- The Californian week in the fixtures is computed both ways — federal weekly and Californian
  daily — and the larger figure is chosen with a citation, not by assumption.
- No quoted span appears in the output unless it was matched in the source.

## Deliberately out of scope

- Any jurisdiction outside the two corpora. The corpus carries the boundary; the tool reports it.
- Legal advice. The tool shows provisions and arithmetic; it does not advise, and says so.
- Accounts, storage of a user's documents, anything multi-user.
- A polished interface. One page, readable, no framework.

## Why this is a proof of concept and not a product

It ships with two corpora frozen at a date, a handful of question types, and no way to add a
jurisdiction without editing a file. What it demonstrates is the behaviour — sourced or silent —
not coverage.
