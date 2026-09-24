"""Hours and pay, computed in Python and never by the model.

During the pre-build baseline the model was asked to work out a week's pay and drifted from the
correct $637.00 to $757.36 inside a single answer, presenting the second figure as a correction.
So the arithmetic lives here, the model is handed the result, and the answer shows the working.
"""
import csv
import re

DAY_STRAIGHT = 8          # California: straight time up to eight hours in a workday
DAY_DOUBLE = 12           # and double time beyond twelve
WEEK_STRAIGHT = 40        # federal: straight time up to forty hours in a workweek


def _minutes(value):
    value = (value or "").strip()
    if not re.match(r"^\d{1,2}:\d{2}$", value):
        return None
    return int(value[:2]) * 60 + int(value[3:5])


def parse(text):
    """A timesheet as exported by a clock: comment lines, then columns in a fixed order."""
    header = [line[1:].strip() for line in text.splitlines() if line.startswith("#")]
    rate = next((float(m.group(1)) for line in header
                 if (m := re.search(r"([\d.]+) (?:USD|сом\w*)/(?:hour|час)", line))), None)
    bonus = next((float(m.group(1)) for line in header
                  if (m := re.search(r"bonus[^:]*:\s*([\d.]+)", line, re.I))), 0.0)
    # a bonus promised in advance is not discretionary, so it belongs in the regular rate
    promised = any(re.search(r"promis|guarantee|handbook|announced", line, re.I)
                   for line in header if re.search(r"bonus", line, re.I))
    rows = list(csv.reader(line for line in text.splitlines() if not line.startswith("#")))
    days = []
    for row in rows[1:]:
        if len(row) < 6:
            continue
        date, weekday, start, end, meal_start, meal_end = (row + [""] * 7)[:6]
        note = row[6] if len(row) > 6 else ""
        first, last = _minutes(start), _minutes(end)
        if first is None or last is None:
            days.append({"date": date, "weekday": weekday, "hours": 0.0, "worked": False,
                         "meal": None, "note": note, "incomplete": bool(start or end)})
            continue
        worked = last - first
        meal = None
        if (ms := _minutes(meal_start)) is not None and (me := _minutes(meal_end)) is not None:
            meal = (me - ms) / 60
            worked -= me - ms
        days.append({"date": date, "weekday": weekday, "hours": round(worked / 60, 2),
                     "worked": True, "meal": meal, "note": note, "incomplete": False})
    return {"rate": rate, "bonus": bonus, "bonus_promised": promised,
            "days": days, "header": header}


def week(sheet):
    days = sheet["days"]
    worked = [d for d in days if d["worked"]]
    total = round(sum(d["hours"] for d in worked), 2)
    no_meal = [d["date"] for d in worked if d["hours"] > 5 and d["meal"] is None]
    return {
        "days": days,
        "total_hours": total,
        "over_40": round(max(total - WEEK_STRAIGHT, 0), 2),
        "days_worked": len(worked),
        "seventh_consecutive_day": worked[-1]["date"] if len(worked) == 7 else None,
        "shifts_without_recorded_meal": no_meal,
        "incomplete_days": [d["date"] for d in days if d.get("incomplete")],
    }


def federal_pay(summary, rate, bonus=0.0, bonus_in_rate=False):
    """29 U.S.C. 207(a)(1) and 29 CFR 778.110: time and a half beyond forty hours.

    A bonus that was promised in advance goes into the regular rate before the premium is
    computed (778.110(b)); a truly discretionary one does not (778.211).
    """
    hours_worked = summary["total_hours"]
    overtime = summary["over_40"]
    earnings = hours_worked * rate
    regular = (earnings + bonus) / hours_worked if bonus_in_rate and hours_worked else rate
    premium = 0.5 * regular * overtime
    lines = [f"{hours_worked:g} h at ${rate:.2f} = ${earnings:,.2f}"]
    if bonus:
        lines.append(f"bonus ${bonus:,.2f}"
                     + (" is promised in advance, so it enters the regular rate"
                        if bonus_in_rate else " is discretionary, so it stays out of the rate"))
    if bonus_in_rate:
        lines.append(f"regular rate = (${earnings:,.2f} + ${bonus:,.2f}) / {hours_worked:g} h "
                     f"= ${regular:,.2f}")
    lines.append(f"overtime premium: {overtime:g} h at half of ${regular:,.2f} = ${premium:,.2f}")
    return {
        "rule": "federal weekly",
        "regular_rate": round(regular, 2),
        "lines": lines,
        "total": round(earnings + bonus + premium, 2),
    }


def california_pay(summary, rate):
    """Cal. Lab. Code 510: daily overtime, double time past twelve, and the seventh day."""
    lines, total = [], 0.0
    seventh = summary["seventh_consecutive_day"]
    for day in summary["days"]:
        if not day["worked"]:
            continue
        hours = day["hours"]
        if day["date"] == seventh:
            first, rest = min(hours, DAY_STRAIGHT), max(hours - DAY_STRAIGHT, 0)
            pay = first * rate * 1.5 + rest * rate * 2
            lines.append(f"{day['date']} seventh day: {first:g} h at 1.5x, {rest:g} h at 2x = ${pay:,.2f}")
        else:
            straight = min(hours, DAY_STRAIGHT)
            half = min(max(hours - DAY_STRAIGHT, 0), DAY_DOUBLE - DAY_STRAIGHT)
            double = max(hours - DAY_DOUBLE, 0)
            pay = straight * rate + half * rate * 1.5 + double * rate * 2
            detail = f"{straight:g} h straight"
            if half:
                detail += f", {half:g} h at 1.5x"
            if double:
                detail += f", {double:g} h at 2x"
            lines.append(f"{day['date']}: {detail} = ${pay:,.2f}")
        total += pay
    return {"rule": "California daily and seventh-day", "lines": lines, "total": round(total, 2)}


def compare(summary, rate, bonus=0.0, bonus_in_rate=False):
    """California pays the more favourable of the two computations, without paying an hour twice."""
    federal = federal_pay(summary, rate, bonus, bonus_in_rate)
    state = california_pay(summary, rate)
    winner = federal if federal["total"] >= state["total"] else state
    return {
        "federal": federal,
        "california": state,
        "owed": winner["total"],
        "under": winner["rule"],
        "note": ("The two rules are computed separately and the employee is entitled to the "
                 "larger result; the same hour is never paid twice."),
    }
