"""Retrieval on its own, before any model call: does the right provision come back at all?

Gold comes from `data/evals.json`: the units each question must cite. Nothing here spends money,
so the ranking can be tuned honestly instead of by feel — and if retrieval misses, no amount of
prompting downstream will save the answer.

Usage:
  retrieval_check.py            report recall at 6 per question
  retrieval_check.py --grid     search the few parameters that matter
"""
import datetime
import itertools
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from chapterverse import corpus, retrieve                        # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
JURISDICTIONS = {"us": ("us-federal", "us-ca"), "kg": ("kg",)}
ON_DATE = datetime.date(2026, 9, 24)


def gold_items():
    items = json.loads((DATA / "evals.json").read_text())["items"]
    return [i for i in items if i["expected"]["must_cite"]]


def recall(units, items, limit=6, verbose=False):
    hits = total = 0
    misses = []
    for item in items:
        on_date = ON_DATE
        if item["id"] == "us-version-14":
            on_date = datetime.date(2027, 1, 15)                  # the question is about that date
        available = corpus.select(units, JURISDICTIONS[item["corpus"]], on_date)
        found = {u["id"] for u in retrieve.search_balanced(retrieve.index(available),
                                                           item["question"], limit=limit)}
        wanted = set(item["expected"]["must_cite"])
        got = wanted & found
        hits += len(got)
        total += len(wanted)
        if verbose and got != wanted:
            misses.append((item["id"], sorted(wanted - got)))
    return hits, total, misses


def main():
    units = corpus.load()
    items = gold_items()
    if "--grid" not in sys.argv:
        hits, total, misses = recall(units, items, verbose=True)
        print(f"recall@6: {hits}/{total} required citations retrieved over {len(items)} questions")
        for item_id, missing in misses:
            print(f"  {item_id:<16} missing {', '.join(missing)}")
        return

    best = []
    for title_weight, common, stem, per in itertools.product(
            (1.0, 2.5, 4.0, 6.0), (0.25, 0.4, 0.7, 1.0), (5, 6, 8, 99), (1, 2, 3)):
        retrieve.TITLE_WEIGHT, retrieve.COMMON, retrieve.STEM_AT = title_weight, common, stem
        hits, total, _ = recall(units, items, limit=6)
        best.append((hits / total, title_weight, common, stem, per))
    best.sort(reverse=True)
    print(f"{'recall':>7}  title  common  stem  per-jurisdiction")
    for score, title_weight, common, stem, per in best[:10]:
        print(f"{score:7.3f}  {title_weight:5.1f}  {common:6.2f}  {stem:4}  {per}")


if __name__ == "__main__":
    main()
