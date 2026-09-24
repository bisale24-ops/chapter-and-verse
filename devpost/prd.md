---
name: prd
status: approved
---

# PRD — Chapter and Verse

## Screens

One page, three regions stacked on a phone and side by side on a wide screen.

**Ask.** A question field, a date field defaulting to today (because which version of a
provision applies depends on it), a jurisdiction selector with three entries — US federal,
California, Kyrgyz Republic — and a file area holding the sample contract and timesheet, with
the option to drop in another.

**Answer.** Claims as a numbered list. Each claim shows its citation as a chip; clicking the
chip expands the source text underneath with the matched words highlighted. A claim that
involves arithmetic shows the arithmetic, not only the result.

**Not verified.** Always present, never collapsed by default, never empty without saying so.
Each entry says what could not be established and why: no provision found, the provision exists
but does not cover the question, or a document was referred to that was never supplied.

## Behaviour that matters

- A quoted span appears in quotation marks only when it was found verbatim in the cited source.
  If the model paraphrased, the text is shown as paraphrase, without quotation marks, and marked.
- When two levels of law both apply, both are shown with their own computation, and the rule
  that decides between them is stated with its own citation.
- When the question is outside the corpus, the answer is the gap section and nothing else.
- Nothing is ever attributed to a document that was not supplied.

## Visual style

Documentary, not chatbot. A serif face for the legal text so it reads as quoted material, a
plain sans for the interface. Two states have colour: verified is a quiet green, unverified is
amber. No other decoration. Dark and light both follow the system.

The point of the design is that the gap section looks like part of the answer rather than a
disclaimer. It sits in the same column, in the same type size, under the same heading weight.

## Edge cases

| Case | Behaviour |
|---|---|
| Question in Russian | Answer in Russian, Kyrgyz corpus, same structure |
| Date falls after a provision changes | The version in force on that date is used and the other is named |
| Timesheet has a missing clock-out | The day is reported as incomplete rather than guessed |
| Model returns a claim with no citation | The claim is moved to the gap section, not shown as an answer |
| The API returns a different model than requested | The run is logged with the served model and the answer is marked as unverifiable provenance |

## Now and later

**Now:** the two corpora, the five sample documents, question answering with verification, the
arithmetic for a week of hours, the eval harness, one page.

**Later, and not in this submission:** adding a jurisdiction without editing code, storing a
user's documents, exporting a claim letter, anything to do with accounts.
