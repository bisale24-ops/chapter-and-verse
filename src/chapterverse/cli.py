"""Ask from the terminal.

  python3 -m chapterverse.cli "Does a 15-minute break have to be paid?"
  python3 -m chapterverse.cli --jurisdiction us-ca --date 2027-01-15 "Missed rest period?"
  python3 -m chapterverse.cli --doc data/fixtures/timesheet_ca_week.csv "Is overtime owed?"
  python3 -m chapterverse.cli --lang ru --jurisdiction kg "Как оплачивается сверхурочная работа?"
"""
import argparse
import datetime
import json
import pathlib
import sys

from . import model, pipeline

GREEN, AMBER, GREY, OFF = "\033[32m", "\033[33m", "\033[90m", "\033[0m"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chapterverse")
    ap.add_argument("question")
    ap.add_argument("--jurisdiction", action="append", default=[],
                    help="us-federal, us-ca or kg; repeatable, defaults to the two US levels")
    ap.add_argument("--date", default=None, help="the date the work was done, YYYY-MM-DD")
    ap.add_argument("--doc", action="append", default=[], help="a contract or timesheet to attach")
    ap.add_argument("--lang", default="en", choices=("en", "ru"))
    ap.add_argument("--model", default=model.DEFAULT_MODEL)
    ap.add_argument("--json", action="store_true", help="print the whole answer object")
    args = ap.parse_args(argv)

    on_date = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
    documents = {pathlib.Path(p).name: pathlib.Path(p).read_text() for p in args.doc}
    answer = pipeline.ask(args.question,
                          jurisdictions=tuple(args.jurisdiction) or ("us-federal", "us-ca"),
                          on_date=on_date, documents=documents, language=args.lang,
                          model_name=args.model)
    if args.json:
        print(json.dumps(answer, ensure_ascii=False, indent=1, default=str))
        return 0

    trace = answer["trace"]
    if trace.get("substituted"):
        print(f"{AMBER}warning: asked {trace['asked_model']}, the gateway served "
              f"{trace['served_model']}{OFF}\n")
    if facts := answer.get("facts"):
        summary = facts["summary"]
        print(f"{GREY}timesheet: {summary['total_hours']} h in the week, "
              f"{summary['over_40']} beyond forty{OFF}")
        if pay := facts.get("pay"):
            print(f"{GREY}computed: federal ${pay['federal']['total']:,.2f}, "
                  f"California ${pay['california']['total']:,.2f} -> owed ${pay['owed']:,.2f} "
                  f"({pay['under']}){OFF}\n")

    for n, claim in enumerate(answer["claims"], 1):
        print(f"{GREEN}{n}.{OFF} {claim['text']}")
        print(f"   {GREY}{claim['citation']} — {claim['title']} [{claim['jurisdiction']}]{OFF}")
        if quote := claim.get("quote"):
            print(f"   {GREY}“{quote}”{OFF}")
        elif paraphrase := claim.get("paraphrase"):
            print(f"   {AMBER}not a verbatim quote, shown as the model wrote it:{OFF} "
                  f"{GREY}{paraphrase}{OFF}")
        for other in claim["superseded_versions"]:
            print(f"   {AMBER}another version of this provision exists: {other}{OFF}")

    if answer["gaps"]:
        print(f"\n{AMBER}Not verified{OFF}")
        for gap in answer["gaps"]:
            print(f" - {gap.get('missing', '')}")
            print(f"   {GREY}{gap.get('why', '')}{OFF}")
    elif not answer["claims"]:
        print(f"{AMBER}nothing could be established from the sources{OFF}")

    print(f"\n{GREY}{len(answer['sources'])} provisions read, "
          f"{trace['verifier_calls']} verification calls, model {trace['served_model']}{OFF}")
    print(f"{GREY}This shows provisions and arithmetic. It is not legal advice.{OFF}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
