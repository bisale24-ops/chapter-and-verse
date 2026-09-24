"""Question in, sourced claims and honest gaps out.

The shape of the answer is the argument of the project: claims that survived verification, and
a gap list that is part of the answer rather than a disclaimer. Nothing reaches `claims` without
a unit that was actually retrieved and a verifier that supported it.
"""
import concurrent.futures as futures
import datetime
import pathlib
import re

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
        '{"claims": [{"text": "<one sentence>", "units": ["<source id>"], '
        '"quote": "<words copied exactly from one of those sources, or empty>"}],\n'
        ' "gaps": [{"missing": "<what could not be established>", "why": "<one line>"}]}\n'
        "Rules: a claim names one source id, or two when it sets a document against a provision. "
        "Use the ids exactly as they appear after \'id:\'. Copy a quote character for "
        "character or leave it empty; never adjust it. If the sources do not settle part of the "
        "question, put that part in gaps instead of answering it. If a document is mentioned in "
        "the question but not supplied, that is a gap. Where two jurisdictions both apply, make a "
        "claim for each and a claim for the rule that decides between them. If the question "
        "covers several clauses, matters or days, produce a claim or a gap for every one of them, "
        "not only the clearest."
    ),
    "ru": (
        "Вы отвечаете на вопросы об оплате и рабочем времени, используя только выданные источники.\n"
        "Отвечайте только JSON в таком виде:\n"
        '{"claims": [{"text": "<одно предложение>", "units": ["<id источника>"], '
        '"quote": "<слова, скопированные из источника дословно, либо пусто>"}],\n'
        ' "gaps": [{"missing": "<что не удалось установить>", "why": "<одна строка>"}]}\n'
        "Правила: утверждение ссылается на один id, либо на два, если оно сопоставляет документ "
        "с нормой. Идентификаторы писать ровно так, как они стоят после \'id:\'. Цитату копируйте "
        "буквально или оставляйте пустой. Если источники не решают часть вопроса, эта часть "
        "идёт в gaps, а не в ответ. Если в вопросе упомянут документ, которого нет среди "
        "выданных, это тоже gap. Если вопрос охватывает несколько пунктов, вопросов или дней, "
        "по каждому должно быть либо утверждение, либо gap, а не только по самому очевидному."
    ),
}


def resolve(raw, by_id):
    """Find the unit a claim points at, forgiving how the model wrote the id.

    It returns "id:CALAB226.7", "`CALAB226.7`" or "Cal. Labor Code § 226.7" often enough that
    treating those as unknown sources - and throwing away a correct claim - was the single
    largest source of lost answers in the first graded run.
    """
    key = (raw or "").strip().strip("`\"' ")
    for prefix in ("id:", "id ", "unit:", "source:"):
        if key.lower().startswith(prefix):
            key = key[len(prefix):].strip()
    if key in by_id:
        return by_id[key]
    squashed = re.sub(r"[^a-z0-9.]", "", key.lower())
    for uid, unit in by_id.items():
        if re.sub(r"[^a-z0-9.]", "", uid.lower()) == squashed:
            return unit
    for unit in by_id.values():
        citation = re.sub(r"[^a-z0-9.]", "", unit["citation"].lower())
        if squashed and (squashed == citation or squashed.endswith(citation)):
            return unit
    return None


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
        language="en", model_name=model.DEFAULT_MODEL, units=None, rerank=False, rounds=2):
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
    preamble = "\n".join(parts)

    draft = model.call(DRAFT_SYSTEM[language], preamble, model=model_name)
    parsed = model.as_json(draft["text"])
    trace = {"asked_model": model_name, "served_model": draft.get("served"),
             "search_phrases": planned,
             "substituted": draft.get("substituted", False), "retrieved": [u["id"] for u in found],
             "date": on_date.isoformat(), "jurisdictions": list(jurisdictions),
             "error": draft.get("error"), "verifier_calls": 0, "rounds": 1}

    if not parsed:
        return {"claims": [], "gaps": [{"missing": "an answer", "why": trace["error"] or
                                        "the model did not return usable JSON"}],
                "sources": found, "facts": facts, "trace": trace}

    # A second round, driven by what the first round could not settle. Every remaining gap is
    # itself a search: the words the model used to describe what is missing are usually closer
    # to the provision than the original question was. This is what a reader does - look again,
    # knowing what you are looking for - and it is what one search round cannot do.
    if rounds > 1 and (parsed.get("gaps") or []):
        wanted = [str(gap.get("missing") or "") for gap in parsed["gaps"]][:4]
        shown = {u["id"] for u in found}
        extra = []
        for query in wanted:
            for unit in retrieve.search(idx, query, limit=4):
                if unit["id"] not in shown and len(extra) < CONTEXT_UNITS // 2:
                    extra.append(unit)
                    shown.add(unit["id"])
        if extra:
            trace["rounds"] = 2
            trace["second_round_queries"] = wanted
            more = "\n\n".join(
                f"--- id: {u['id']} | {u['citation']} — {u['title']}"
                f" | {corpus.LABELS[u['jurisdiction']]}"
                f" | in force: {u.get('in_force', 'current')}\n{u['text'][:FULL_TEXT]}" for u in extra)
            again = model.call(
                DRAFT_SYSTEM[language],
                f"{preamble}\n\nYour first answer left these unresolved:\n"
                + "\n".join(f"- {w}" for w in wanted)
                + f"\n\nFurther sources (cite by id):\n{more}\n\n"
                  "Answer the whole question again, keeping the claims that already held and "
                  "adding any the further sources now support. What is still unsettled stays a gap.",
                model=model_name)
            second = model.as_json(again["text"])
            if second and (second.get("claims") or second.get("gaps")):
                parsed = second
                found = found + extra
                trace["retrieved"] = [u["id"] for u in found]
                trace["substituted"] = trace["substituted"] or again.get("substituted", False)

    by_id = {u["id"]: u for u in found + supplied}
    claims, gaps = [], list(parsed.get("gaps") or [])
    checkable = []
    for claim in parsed.get("claims") or []:
        named = claim.get("units") or claim.get("unit") or []
        if isinstance(named, str):
            named = re.split(r"\s+and\s+|\s*,\s*", named)
        resolved = [u for u in (resolve(name, by_id) for name in named) if u]
        if not resolved:
            gaps.append({"missing": claim.get("text", ""),
                         "why": f"cites {', '.join(named) or 'nothing'}, which was not among the sources"})
            continue
        checkable.append((claim, resolved))

    # every claim is checked against each source it names, and the checks are independent
    jobs = [(claim, unit) for claim, resolved in checkable for unit in resolved]
    with futures.ThreadPoolExecutor(max_workers=6) as workers:
        verdicts = list(workers.map(lambda job: verify.check(job[0], job[1], model_name=model_name),
                                    jobs))
    trace["verifier_calls"] = len(jobs)
    checked = {}
    for (claim, unit), result in zip(jobs, verdicts):
        checked.setdefault(id(claim), []).append((unit, result))

    for claim, resolved in checkable:
        outcomes = checked[id(claim)]
        supporting = [(unit, result) for unit, result in outcomes if result["verdict"] == "supported"]
        if not supporting:
            unit, result = outcomes[0]
            gaps.append({"missing": claim.get("text", ""),
                         "why": f"{unit['citation']} does not support it: {result['reason']}"})
            continue
        unit, result = supporting[0]
        entry = {"text": claim.get("text", ""), "unit": unit["id"], "citation": unit["citation"],
                 "title": unit["title"], "url": unit.get("url"),
                 "jurisdiction": corpus.LABELS[unit["jurisdiction"]],
                 "quote": claim.get("quote") or "", "quote_verified": result["quote_ok"],
                 "verdict": result["verdict"], "reason": result["reason"],
                 "also_cites": [u["citation"] for u, _ in outcomes if u is not unit],
                 "unsupported_sources": [f"{u['citation']}: {r['reason']}"
                                         for u, r in outcomes if r["verdict"] != "supported"],
                 "superseded_versions": corpus.superseded(units, unit["id"], on_date)}
        if not result["quote_ok"] and entry["quote"]:
            entry["paraphrase"] = entry.pop("quote")
        claims.append(entry)

    if facts:
        trace["computed"] = facts["summary"]
    return {"claims": claims, "gaps": gaps, "sources": found, "facts": facts, "trace": trace}


def load_document(path):
    return pathlib.Path(path).read_text()


def sample_documents(*names):
    return {name: (DATA / "fixtures" / name).read_text() for name in names}
