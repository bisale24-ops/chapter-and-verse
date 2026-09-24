"""Run the 26 questions through the pipeline and grade the answers.

The same checks the model was measured with before this project existed, so the two numbers can
be put side by side: required citations present, forbidden ones absent, expected figures there,
no quotation that is not in its source, and a stated gap wherever the honest answer is "not in
the sources".

Usage:
  run_evals.py                      all items
  run_evals.py --items us-ca-10,us-reserved-15
  run_evals.py --model swiss-ai/apertus-v1.5-8b
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from chapterverse import corpus, model, pipeline                 # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "evals" / "results"
JURISDICTIONS = {"us": ("us-federal", "us-ca"), "kg": ("kg",)}
ON_DATE = datetime.date(2026, 9, 24)
LATER = {"us-version-14": datetime.date(2027, 1, 15)}
FIXTURES = {"us-fixture-23": ["timesheet_us_hourly_week.csv"],
            "us-ca-10": ["timesheet_ca_week.csv"],
            "us-ca-11": ["timesheet_ca_week.csv"],
            "us-ca-13": ["timesheet_ca_week.csv"],
            "kg-ot-21": ["timesheet_kg_week.csv"],
            "us-audit-24": ["contract_ca_hourly.md", "timesheet_ca_week.csv"],
            "us-exempt-25": ["contract_us_salaried.md"],
            "kg-audit-26": ["contract_kg.md", "timesheet_kg_week.csv"]}


def rendered(answer):
    """Everything the user is shown, as one string, for the phrase and figure checks."""
    parts = [c["text"] + " " + (c.get("quote") or c.get("paraphrase") or "") for c in answer["claims"]]
    parts += [f"{g.get('missing', '')} {g.get('why', '')}" for g in answer["gaps"]]
    if facts := answer.get("facts"):
        if pay := facts.get("pay"):
            parts.append(f"{pay['owed']:.2f} {pay['federal']['total']:.2f} {pay['california']['total']:.2f}")
            parts += pay["federal"]["lines"] + pay["california"]["lines"]
        parts.append(f"{facts['summary']['total_hours']} {facts['summary']['over_40']}")
    return " ".join(parts)


def grade(item, answer):
    expected = item["expected"]
    cited = {c["unit"] for c in answer["claims"]}
    text = rendered(answer)
    flat = re.sub(r"\s+", " ", text).lower().replace(",", "")
    # a quotation the model altered is caught by verify.quote_matches and shown as paraphrase,
    # so it never reaches the reader as a quotation; both numbers are reported, separately
    caught = [c["unit"] for c in answer["claims"] if c.get("paraphrase")]
    shown_wrong = []
    needs_gap = item["kind"] in ("absent", "reserved", "contract-missing")
    result = {
        "item": item["id"], "kind": item["kind"], "lang": item["lang"],
        "missing_cites": sorted(set(expected["must_cite"]) - cited),
        "bad_cites": sorted(set(expected["must_not_cite"]) & cited),
        "missing_numbers": [n for n in expected.get("numbers", [])
                            if re.search(r"\d", n) and n.replace(",", "").lower() not in flat],
        "forbidden": [f for f in expected["forbidden"] if f.lower().replace(",", "") in flat],
        "quotes_caught": caught,
        "quotes_shown_wrong": shown_wrong,
        "gap_needed": needs_gap,
        "gap_said": bool(answer["gaps"]),
        "claims": len(answer["claims"]),
        "gaps": len(answer["gaps"]),
        "served_model": answer["trace"].get("served_model"),
        "substituted": answer["trace"].get("substituted", False),
    }
    result["passed"] = not (result["missing_cites"] or result["bad_cites"] or result["forbidden"]
                            or result["missing_numbers"] or shown_wrong
                            or (needs_gap and not result["gap_said"]))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="")
    ap.add_argument("--model", default=model.DEFAULT_MODEL)
    args = ap.parse_args()

    items = json.loads((DATA / "evals.json").read_text())["items"]
    if args.items:
        keep = set(args.items.split(","))
        items = [i for i in items if i["id"] in keep]

    units = corpus.load()
    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = RESULTS / f"evals-{args.model.split('-')[-1]}-{stamp}.jsonl"
    rows = []
    with out.open("w") as log:
        for item in items:
            answer = pipeline.ask(
                item["question"],
                jurisdictions=JURISDICTIONS[item["corpus"]],
                on_date=LATER.get(item["id"], ON_DATE),
                documents=pipeline.sample_documents(*FIXTURES.get(item["id"], [])),
                language=item["lang"], model_name=args.model, units=units)
            row = grade(item, answer)
            rows.append(row)
            log.write(json.dumps({"grade": row, "answer": answer}, ensure_ascii=False, default=str) + "\n")
            log.flush()
            print(f"  {row['item']:<16} {'pass' if row['passed'] else 'fail':<5} "
                  f"claims {row['claims']} gaps {row['gaps']}"
                  + (f"  missing {','.join(row['missing_cites'])}" if row["missing_cites"] else "")
                  + (f"  forbidden {row['forbidden']}" if row["forbidden"] else ""), flush=True)

    passed = sum(r["passed"] for r in rows)
    print(f"\n{passed}/{len(rows)} passed")
    print(f"  altered quotations shown as quotations: "
          f"{sum(bool(r['quotes_shown_wrong']) for r in rows)}")
    print(f"  altered quotations caught and demoted:  "
          f"{sum(bool(r['quotes_caught']) for r in rows)}")
    print(f"  required citation missing:          {sum(bool(r['missing_cites']) for r in rows)}")
    print(f"  cited something forbidden:          {sum(bool(r['bad_cites']) for r in rows)}")
    print(f"  wrong or missing figure:            {sum(bool(r['missing_numbers']) for r in rows)}")
    gap_items = [r for r in rows if r["gap_needed"]]
    print(f"  gap reported where it must be:      "
          f"{sum(r['gap_said'] for r in gap_items)}/{len(gap_items)}")
    if subs := [r["item"] for r in rows if r["substituted"]]:
        print(f"  answered by another model entirely:  {len(subs)} ({', '.join(subs)})")
    print(f"\n-> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
