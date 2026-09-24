"""The second pass, and the only part of the answer the model cannot talk its way past.

Two checks, deliberately different in kind:

  the quote check is deterministic - a span in quotation marks must appear in the unit it is
  attributed to, or it stops being a quotation;

  the support check is another model call that sees the claim and the source text and nothing
  else. It never sees the question, the other claims or the reasoning that produced them,
  because a verifier shown the reasoning agrees with it.
"""
import re

from . import model

VERIFIER_SYSTEM = (
    "You check one statement against one legal text. You do not know the question that produced "
    "the statement and you must not guess it. Reply with JSON only: "
    '{"verdict": "supported" | "unsupported" | "not_in_source", "reason": "<one line>"}. '
    "supported: the text states or directly entails the statement. "
    "unsupported: the text addresses the matter and the statement is wrong or overstated. "
    "not_in_source: the text does not address the matter at all."
)


def normalise(text):
    text = (text or "").replace("’", "'").replace("‘", "'").replace("‑", "-")
    text = text.replace("“", '"').replace("”", '"').replace("\xa0", " ")
    text = re.sub(r"\*{1,2}|_{2}", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_matches(quote, unit_text):
    """An elided quotation still has to be a quotation: every fragment must be in the source."""
    if not quote:
        return True
    fragments = [normalise(f) for f in re.split(r"\.\.\.|…|\*\s*\*\s*\*", quote)]
    fragments = [f for f in fragments if len(f) >= 25] or [normalise(quote)]
    haystack = normalise(unit_text)
    return all(f in haystack for f in fragments)


def check(claim, unit, model_name=model.DEFAULT_MODEL):
    result = {"quote_ok": quote_matches(claim.get("quote"), unit["text"])}
    user = (f"TEXT ({unit['citation']} — {unit['title']}):\n{unit['text'][:6000]}\n\n"
            f"STATEMENT:\n{claim['text']}")
    reply = model.call(VERIFIER_SYSTEM, user, model=model_name, max_tokens=200)
    parsed = model.as_json(reply["text"]) or {}
    verdict = parsed.get("verdict")
    if verdict not in ("supported", "unsupported", "not_in_source"):
        # a check that failed is not a claim that failed; ask once more before holding it against
        # the claim, and if the second attempt is no better, say plainly that the check is what broke
        reply = model.call(VERIFIER_SYSTEM, user, model=model_name, max_tokens=200)
        parsed = model.as_json(reply["text"]) or {}
        verdict = parsed.get("verdict")
    result["verdict"] = verdict if verdict in ("supported", "unsupported", "not_in_source") else "check_failed"
    result["reason"] = (parsed.get("reason") or reply.get("error")
                        or "the check itself failed, so the claim is neither confirmed nor refuted")
    result["served"] = reply.get("served")
    result["substituted"] = reply.get("substituted", False)
    return result
