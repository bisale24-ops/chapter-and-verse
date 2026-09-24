"""BM25 over the units that survived filtering. No index service, no embeddings.

530 units of a few hundred words each are cheap enough to score exhaustively, and a lexical
score suits legal text: a question carries the vocabulary of the provision that answers it, and
an exact term match is what should win.

Two crudenesses, deliberate and visible rather than buried. A word longer than six characters is
cut to its first six, which stands in for a stemmer in English and Russian alike. A query word
found in more than 40% of the units is dropped, because a long question is mostly filler and
otherwise the filler decides the ranking.
"""
import math
import re
from collections import Counter

K1 = 1.5
B = 0.75
TITLE_WEIGHT = 2.5        # the citation and title are short and dense; body length drowns them
COMMON = 0.4
STEM_AT = 6
TOKEN = re.compile(r"[\w’']+", re.UNICODE)


def tokens(text):
    out = []
    for raw in TOKEN.findall(text):
        word = raw.lower().strip("’'")
        out.append(word[:STEM_AT] if len(word) > STEM_AT else word)
    return out


def _field(texts):
    docs = [Counter(tokens(t)) for t in texts]
    lengths = [sum(c.values()) or 1 for c in docs]
    frequency = Counter()
    for counts in docs:
        frequency.update(counts.keys())
    return {"docs": docs, "lengths": lengths, "frequency": frequency, "n": len(docs),
            "average": (sum(lengths) / len(lengths)) if lengths else 1}


def index(units):
    units = list(units)
    return {
        "units": units,
        "body": _field([u["text"] for u in units]),
        "title": _field([f"{u['citation']} {u['title']} {u.get('container', '')}" for u in units]),
    }


def _score(field, terms, position):
    counts, length = field["docs"][position], field["lengths"][position]
    score = 0.0
    for term in terms:
        tf = counts.get(term, 0)
        if not tf:
            continue
        df = field["frequency"][term]
        idf = math.log(1 + (field["n"] - df + 0.5) / (df + 0.5))
        score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / field["average"]))
    return score


def search(idx, query, limit=6):
    body, title = idx["body"], idx["title"]
    all_terms = list(dict.fromkeys(tokens(query)))
    # "overtime" is filler inside the body of an overtime regulation and the whole point inside
    # its title, so the frequency filter applies to the body score only
    body_terms = [t for t in all_terms if body["frequency"].get(t, 0) <= COMMON * body["n"]]
    scored = []
    for position, unit in enumerate(idx["units"]):
        score = _score(body, body_terms, position) + TITLE_WEIGHT * _score(title, all_terms, position)
        if score:
            scored.append((score, unit))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [unit for _, unit in scored[:limit]]


def search_balanced(idx, query, per_jurisdiction=2, limit=6):
    """Top hits overall, but never all from one level of law.

    A question about a Californian week is answered wrongly when only federal sections come
    back: the conflict cannot be reported if only one side of it is in front of the model.
    """
    ranked = search(idx, query, limit=len(idx["units"]))
    chosen, seen = [], set()
    for jurisdiction in dict.fromkeys(u["jurisdiction"] for u in ranked):
        for unit in [u for u in ranked if u["jurisdiction"] == jurisdiction][:per_jurisdiction]:
            chosen.append(unit)
            seen.add(unit["id"])
    for unit in ranked:
        if len(chosen) >= limit:
            break
        if unit["id"] not in seen:
            chosen.append(unit)
            seen.add(unit["id"])
    return chosen[:limit]
