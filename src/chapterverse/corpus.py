"""The corpus: citable units of law, filtered before anything is ranked.

A unit is the smallest thing an answer may cite - one CFR section, one statute section, one
article of the Kyrgyz code. Jurisdiction comes from the citation family, and the few units that
exist in two versions at once carry the window in which each is in force.
"""
import datetime
import json
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"

JURISDICTIONS = {
    "29USC": "us-federal",
    "29CFR": "us-federal",
    "CALAB": "us-ca",
    "TKKR": "kg",
}
LABELS = {
    "us-federal": "United States, federal",
    "us-ca": "California",
    "kg": "Kyrgyz Republic",
    "document": "supplied document",
}


def jurisdiction_of(unit_id):
    for prefix, name in JURISDICTIONS.items():
        if unit_id.startswith(prefix):
            return name
    raise ValueError(f"no jurisdiction for {unit_id}")


def in_force_window(unit):
    """(from, until) as dates, either side possibly None. Absent means always in force."""
    note = unit.get("in_force")
    if not note:
        return None, None
    if match := re.match(r"(\d{4})-(\d{2})-(\d{2}) onwards", note):
        return datetime.date(*(int(g) for g in match.groups())), None
    if match := re.match(r"until (\d{4})-(\d{2})-(\d{2})", note):
        return None, datetime.date(*(int(g) for g in match.groups()))
    return None, None


def load():
    units = {}
    for name in ("us", "kg"):
        corpus = json.loads((DATA / f"corpus_{name}.json").read_text())
        for unit in corpus["units"]:
            units[unit["id"]] = dict(unit,
                                     corpus=name,
                                     language=corpus["language"],
                                     jurisdiction=jurisdiction_of(unit["id"]))
    return units


def select(units, jurisdictions, on_date):
    """Everything a question may be answered from: the right places, the right date."""
    wanted = set(jurisdictions)
    out = []
    for unit in units.values():
        if unit["jurisdiction"] not in wanted:
            continue
        start, end = in_force_window(unit)
        if start and on_date < start:
            continue
        if end and on_date > end:
            continue
        out.append(unit)
    return out


def superseded(units, unit_id, on_date):
    """The other versions of the same provision, so the answer can name what it did not use."""
    base = unit_id.split("-")[0]
    others = []
    for other in units.values():
        if other["id"] != unit_id and other["id"].split("-")[0] == base:
            start, end = in_force_window(other)
            when = ("from " + start.isoformat()) if start else ("until " + end.isoformat()) if end else "undated"
            others.append(f"{other['citation']} ({when})")
    return others
