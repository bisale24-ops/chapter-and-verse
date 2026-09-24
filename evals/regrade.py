"""Re-grade a saved eval run without spending anything.

The answers are in the results file; grading is pure function of those answers and the eval set,
so a change to the rules can be applied to a run that already happened.

Usage: regrade.py evals/results/evals-70b-*.jsonl
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from run_evals import DATA, grade                                # noqa: E402


def main():
    path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(
        (pathlib.Path(__file__).parent / "results").glob("evals-*.jsonl"))[-1]
    items = {i["id"]: i for i in json.loads((DATA / "evals.json").read_text())["items"]}
    rows = []
    for line in path.read_text().splitlines():
        record = json.loads(line)
        rows.append(grade(items[record["grade"]["item"]], record["answer"]))
    for row in rows:
        print(f"  {row['item']:<16} {'pass' if row['passed'] else 'fail':<5} "
              + (f"missing {','.join(row['missing_cites'])}" if row["missing_cites"] else "")
              + (f"  forbidden {row['forbidden']}" if row["forbidden"] else ""))
    print(f"\n{sum(r['passed'] for r in rows)}/{len(rows)} passed  ({path.name})")
    print(f"  altered quotation shown as a quotation: {sum(bool(r['quotes_shown_wrong']) for r in rows)}")
    print(f"  altered quotation caught and demoted:   {sum(bool(r['quotes_caught']) for r in rows)}")
    print(f"  required citation missing:              {sum(bool(r['missing_cites']) for r in rows)}")
    print(f"  cited something forbidden:              {sum(bool(r['bad_cites']) for r in rows)}")
    print(f"  wrong or missing figure:                {sum(bool(r['missing_numbers']) for r in rows)}")
    gaps = [r for r in rows if r["gap_needed"]]
    print(f"  gap reported where it must be:          {sum(r['gap_said'] for r in gaps)}/{len(gaps)}")


if __name__ == "__main__":
    main()
