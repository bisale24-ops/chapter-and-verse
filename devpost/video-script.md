# Demo video — under three minutes

Narration synthesised with edge-tts (`en-US-AndrewNeural`), screen capture only, no presenter.
An end card states that the narration is synthetic. Every screen is a real run.

| # | Time | On screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:18 | Terminal: the closed-book answer from the baseline run, the invented quotation highlighted | "This is a language model answering a question about 29 CFR section 531.7. It states a recordkeeping rule and quotes it. The section is marked Reserved. It has no text at all. Nothing in that quotation exists." |
| 2 | 0:18–0:32 | `FAILURE-MODES.md` table, the row for invented quotations | "We measured this before building anything. Sixteen of twenty-six answers quoted words that were not in any source. That is the problem this project is built against." |
| 3 | 0:32–0:50 | The page: question about a Californian week, timesheet attached, Ask pressed | "Chapter and Verse answers a pay question from three things: the law, the contract and the timesheet. It answers only what it can trace." |
| 4 | 0:50–1:15 | Answer appears: two claims, each with a citation chip; one chip clicked, source text expands with the quoted words visible | "Every claim names the provision it rests on. Click the citation and the provision opens underneath. The quotation was matched against that text in code before it was shown in quotation marks — if the model paraphrases, the quotation marks come off." |
| 5 | 1:15–1:35 | The computed block: federal $1,670.00 against California $1,655.00 | "Here both levels of law apply. Federal law counts the week, California counts the day. The tool computes both in Python, not in the model, and shows that this week the federal figure is the larger one — so that is what is owed. The assumption that state law always pays more is wrong by fifteen dollars." |
| 6 | 1:35–1:55 | The **Not verified** block, same column, same type | "And this is the other half of the answer. What could not be established, and why: a provision that does not cover the question, a document that was never supplied. It is not a disclaimer at the bottom; it is part of the answer." |
| 7 | 1:55–2:15 | Terminal: the contract clause paying overtime at 1.25×; the claim is rejected by the verifier and lands in the gap list | "The draft pass wrote that 1.25 times was allowed. The verification pass reads the claim against the provision alone — it never sees the question or the reasoning that produced the claim — and rejects it. The claim does not reach the answer." |
| 8 | 2:15–2:35 | `run_evals.py` output beside the baseline table | "**[fill: passes, invented quotations, gaps reported — from the final run]** The same questions, the same checks, before and after." |
| 9 | 2:35–2:50 | The Russian question against the Kyrgyz code | "The second corpus is the Labour Code of Kyrgyzstan, in Russian. Same behaviour, and the same refusal to import a Californian rule into a country that does not have it." |
| 10 | 2:50–3:00 | End card: name, repository URL, MIT, "narration is synthesised" | "Chapter and Verse. Sourced or silent. MIT licensed, and the narration in this video is synthetic." |

## Capture plan

1. Page at 1280×720, light theme, browser chrome hidden.
2. Terminal at the same size, 16 pt, the repo's own output — no retyping for the camera.
3. TTS per line, durations measured, screens held for the line plus 0.8 s.
4. Concatenate with ffmpeg, loudness normalised to −16 LUFS, single pass, watch end to end before upload.
