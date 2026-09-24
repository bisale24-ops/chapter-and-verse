"""Question in, sourced claims and honest gaps out.

The shape of the answer is the argument of the project: claims that survived verification, and
a gap list that is part of the answer rather than a disclaimer. Nothing reaches `claims` without
a unit that was actually retrieved and a verifier that supported it.
"""
import concurrent.futures as futures
import datetime
import pathlib

from . import corpus, hours, model, plan, retrieve, verify

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"
CONTEXT_UNITS = 14        # what the answering pass sees; recall beats precision at this size
RERANK_KEEP = 8           # how many of those the reranker put first, and get their full text
POOL = 60                 # how wide the lexical shortlist is before the reranker sees it
FULL_TEXT = 6000
SHORT_TEXT = 1200

DRAFT_SYSTEM = {
    "en": (
        "You answer questions about pay and working time using only the sources given to you.\n"
        "Reply with JSON only, in this shape:\n"
        '{"claims": [{"text": "<one sentence>", "unit": "<source id>", '
        '"quote": "<words copied exactly from that source, or empty>"}],\n'
        ' "gaps": [{"missing": "<what could not be established>", "why": "<one line>"}]}\n'
        "Rules: every claim names exactly one source id from the list. Copy a quote character for "
        "character or leave it empty; never adjust it. If the sources do not settle part of the "
        "question, put that part in gaps instead of answering it. If a document is mentioned in "
        "the question but not supplied, that is a gap. Where two jurisdictions both apply, make a "
        "claim for each and a claim for the rule that decides between them."
    ),
    "ru": (
        "Вы отвечаете на вопросы об оплате и рабочем времени, используя только выданные источники.\n"
        "Отвечайте только JSON в таком виде:\n"
        '{"claims": [{"text": "<одно предложение>", "unit": "<id источника>", '
        '"quote": "<слова, скопированные из источника дословно, либо пусто>"}],\n'
        ' "gaps": [{"missing": "<что не удалось установить>", "why": "<одна строка>"}]}\n'
        "Правила: каждое утверждение ссылается ровно на один id из списка. Цитату копируйте "
        "буквально или оставляйте пустой. Если источники не решают часть вопроса, эта часть "
        "идёт в gaps, а не в ответ. Если в вопросе упомянут документ, которого нет среди "
        "выданных, это тоже gap."
    ),
}


def timesheet_facts(text):
    """Hours and pay are computed here and handed to the model as facts, never asked of it."""
    sheet = hours.parse(text)
    summary = hours.week(sheet)
    facts = {"summary": summary}
    if sheet["rate"]:
        facts["pay"] = hours.compare(summary, sheet["rate"], sheet.get("bonus", 0.0),
                                     sheet.get("bonus_promised", False))
        facts["rate"] = sheet["rate"]
        facts["bonus"] = sheet.get("bonus", 0.0)
    return facts


def render_facts(facts):
    summary, lines = facts["summary"], []
    lines.append(f"Hours computed from the timesheet: {summary['total_hours']} in the week, "
                 f"{summary['over_40']} beyond forty, {summary['days_worked']} days worked.")
    for day in summary["days"]:
        if day["worked"]:
            meal = f", meal {day['meal']:g} h" if day["meal"] else ", no meal recorded"
            lines.append(f"  {day['date']} {day['weekday']}: {day['hours']:g} h{meal}")
    if summary["seventh_consecutive_day"]:
        lines.append(f"  {summary['seventh_consecutive_day']} is a seventh consecutive day worked.")
    if pay := facts.get("pay"):
        lines.append(f"Pay at ${facts['rate']:.2f}/h, computed arithmetically, not by you:")
        for name in ("federal", "california"):
            lines.append(f"  {pay[name]['rule']}: ${pay[name]['total']:,.2f}")
            lines += [f"    {line}" for line in pay[name]["lines"]]
        lines.append(f"  owed: ${pay['owed']:,.2f} under the {pay['under']} rule. {pay['note']}")
    return "\n".join(lines)


def ask(question, jurisdictions=("us-federal", "us-ca"), on_date=None, documents=None,
        language="en", model_name=model.DEFAULT_MODEL, units=None, rerank=False):
    on_date = on_date or datetime.date.today()
    units = units if units is not None else corpus.load()
    available = corpus.select(units, jurisdictions, on_date)
    idx = retrieve.index(available)
    planned, plan_reply = plan.phrases(question, model_name=model_name)
    pool = plan.gather(idx, question, planned, units=units, pool=POOL,
                       per_container=3, per_phrase=6)
    # The reranker is off by default and the measurement is why: asked to choose from sixty
    # titles it dropped § 785.18 - "Rest" - from second place for a question about a coffee
    # break, and the answer became a refusal. The lexical order, phrase hits first, does better.
    if rerank:
        found, _ = plan.rerank(pool, question, keep=RERANK_KEEP, model_name=model_name)
        for unit in pool:
            if len(found) >= CONTEXT_UNITS:
                break
            if unit not in found:
                found.append(unit)
    else:
        found = pool[:CONTEXT_UNITS]

    parts = [question]
    facts = None
    supplied = []
    for name, text in (documents or {}).items():
        # a document that was handed over is citable like a provision, and quotes from it are
        # checked the same way; a document that was not handed over can never be cited at all
        supplied.append({"id": name, "citation": name, "title": "supplied document",
                         "text": text, "jurisdiction": "document", "url": None})
        parts.append(f"\nDocument (citable as id {name}):\n{text}")
        if name.endswith(".csv"):
            facts = timesheet_facts(text)
            parts.append("\n" + render_facts(facts))
    blocks = []
    for position, unit in enumerate(found):
        cap = FULL_TEXT if position < RERANK_KEEP else SHORT_TEXT
        text = unit["text"][:cap] + ("\n[... truncated]" if len(unit["text"]) > cap else "")
        blocks.append(f"--- id: {unit['id']} | {unit['citation']} — {unit['title']}"
                      f" | {corpus.LABELS[unit['jurisdiction']]}"
                      f" | in force: {unit.get('in_force', 'current')}\n{text}")
    parts.append("\nSources (cite by id):\n" + "\n\n".join(blocks))

    draft = model.call(DRAFT_SYSTEM[language], "\n".join(parts), model=model_name)
    parsed = model.as_json(draft["text"])
    trace = {"asked_model": model_name, "served_model": draft.get("served"),
             "search_phrases": planned,
             "substituted": draft.get("substituted", False), "retrieved": [u["id"] for u in found],
             "date": on_date.isoformat(), "jurisdictions": list(jurisdictions),
             "error": draft.get("error"), "verifier_calls": 0}

    if not parsed:
        return {"claims": [], "gaps": [{"missing": "an answer", "why": trace["error"] or
                                        "the model did not return usable JSON"}],
                "sources": found, "facts": facts, "trace": trace}

    by_id = {u["id"]: u for u in found + supplied}
    claims, gaps = [], list(parsed.get("gaps") or [])
    checkable = []
    for claim in parsed.get("claims") or []:
        unit = by_id.get(claim.get("unit"))
        if not unit:
            gaps.append({"missing": claim.get("text", ""),
                         "why": f"cites {claim.get('unit') or 'nothing'}, which was not among the sources"})
            continue
        checkable.append((claim, unit))

    # each claim is checked against its own source, so the checks are independent and run together
    with futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda pair: verify.check(pair[0], pair[1], model_name=model_name),
                                checkable))
    for (claim, unit), result in zip(checkable, results):
        trace["verifier_calls"] += 1
        entry = {"text": claim.get("text", ""), "unit": unit["id"], "citation": unit["citation"],
                 "title": unit["title"], "url": unit.get("url"),
                 "jurisdiction": corpus.LABELS[unit["jurisdiction"]],
                 "quote": claim.get("quote") or "", "quote_verified": result["quote_ok"],
                 "verdict": result["verdict"], "reason": result["reason"],
                 "superseded_versions": corpus.superseded(units, unit["id"], on_date)}
        if not result["quote_ok"] and entry["quote"]:
            entry["paraphrase"] = entry.pop("quote")
        if result["verdict"] == "supported":
            claims.append(entry)
        else:
            gaps.append({"missing": entry["text"],
                         "why": f"{entry['citation']} does not support it: {result['reason']}"})
    if facts:
        trace["computed"] = facts["summary"]
    return {"claims": claims, "gaps": gaps, "sources": found, "facts": facts, "trace": trace}


def load_document(path):
    return pathlib.Path(path).read_text()


def sample_documents(*names):
    return {name: (DATA / "fixtures" / name).read_text() for name in names}
