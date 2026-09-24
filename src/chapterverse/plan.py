"""Turn a question into search phrases, because questions and statutes use different words.

A person asks about a "coffee break" and the regulation is headed "Rest"; a person asks about a
"year-end bonus" and the exclusion lives under "Discretionary bonuses". Lexical search cannot
cross that gap on its own: measured over the eval questions, one search with the raw question
found 39% of the required provisions in the top six.

So the model first proposes the phrases it would look up, in the register of the law, and each
phrase is searched separately. The model never sees the corpus here - it is planning a search,
not answering - and the union of the hits is what the answering pass gets.
"""
import re

from . import model, retrieve

PLANNER_SYSTEM = (
    "You turn a question about pay or working time into search phrases for a database of statutes "
    "and regulations. Reply with JSON only: {\"phrases\": [\"...\", \"...\"]}. Three to six phrases, "
    "two to five words each, in the vocabulary a statute would use rather than the vocabulary of "
    "the question. Cover every distinct matter the question raises, including anything that has to "
    "be looked up to decide which rule wins. Same language as the question."
)


def phrases(question, model_name=model.DEFAULT_MODEL):
    reply = model.call(PLANNER_SYSTEM, question, model=model_name, max_tokens=250)
    parsed = model.as_json(reply["text"]) or {}
    found = [p.strip() for p in (parsed.get("phrases") or []) if isinstance(p, str) and p.strip()]
    return found[:6], reply


CITATION_PATTERNS = [
    (r"29\s*C\.?F\.?R\.?\s*§?\s*(\d+\.\d+[a-z]?)", "29CFR{}"),
    (r"29\s*U\.?S\.?C\.?\s*§?\s*(\d+)", "29USC{}"),
    (r"(?:Labor|Lab\.)\s*Code\s*§?\s*(\d+(?:\.\d+)?)", "CALAB{}"),
    (r"(?:стать[а-я]+|ст\.)\s*(\d+)", "TKKR{}"),
]


def named_units(question, units):
    """A provision the question names by number is fetched directly.

    Lexical search cannot find § 531.7 at all - it is marked [Reserved] and has no text - yet
    "what does 29 CFR 531.7 require" is exactly the question where inventing an answer is worst.
    """
    named = []
    for pattern, template in CITATION_PATTERNS:
        for number in re.findall(pattern, question, re.I):
            unit = units.get(template.format(number))
            if unit is not None and unit not in named:
                named.append(unit)
    return named


def gather(idx, question, planned, units=None, pool=40, per_container=2, per_phrase=5):
    """The shortlist: provisions named outright, then a spread across the parts of the law,
    then the planned searches, then whatever the plain search ranks next."""
    chosen, seen = [], set()

    def take(unit):
        if unit["id"] not in seen:
            chosen.append(unit)
            seen.add(unit["id"])

    available = {u["id"] for u in idx["units"]}
    for unit in named_units(question, units or {}):
        if unit["id"] in available:
            take(unit)

    ranked = retrieve.search(idx, question, limit=len(idx["units"]))
    per = {}
    for unit in ranked:                                   # a spread across parts, so that one
        container = unit.get("container", "")             # regulation cannot fill the shortlist
        if per.get(container, 0) < per_container:
            per[container] = per.get(container, 0) + 1
            take(unit)
    for phrase in planned:
        for unit in retrieve.search(idx, phrase, limit=per_phrase):
            take(unit)
    for unit in ranked:
        if len(chosen) >= pool:
            break
        take(unit)
    return chosen[:pool]


RERANKER_SYSTEM = (
    "You are given a question and a numbered list of provisions, each as its citation and title. "
    "Choose the ones whose text is most likely to decide the question, most likely first. "
    "Reply with JSON only: {\"pick\": [<numbers>]}. Pick at most eight. Include a provision from "
    "every level of law that could apply, and include anything needed to decide which rule wins. "
    "Judge by what the provision is about, not by wording overlap with the question."
)


def rerank(candidates, question, keep=8, model_name=model.DEFAULT_MODEL):
    """A second look at the shortlist, by title only.

    BM25 cannot separate two hundred sections of one regulation that share their vocabulary;
    a reader can, from the titles alone, and titles are cheap to send.
    """
    if len(candidates) <= keep:
        return candidates, None
    listing = "\n".join(f"{n}. {u['citation']} — {u['title']}"
                        for n, u in enumerate(candidates, 1))
    reply = model.call(RERANKER_SYSTEM, f"QUESTION:\n{question}\n\nPROVISIONS:\n{listing}",
                       model=model_name, max_tokens=200)
    parsed = model.as_json(reply["text"]) or {}
    picked = [candidates[n - 1] for n in (parsed.get("pick") or [])
              if isinstance(n, int) and 1 <= n <= len(candidates)]
    if not picked:
        return candidates[:keep], reply
    for unit in candidates:                       # top up from the lexical order if the pick is short
        if len(picked) >= keep:
            break
        if unit not in picked:
            picked.append(unit)
    return picked[:keep], reply
