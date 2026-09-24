"""One way in and out of the model, with the served model recorded on every call.

The gateway does not always answer with the model that was asked for. On 364 calls made on
24 September 2026, 11 came back from another vendor's model with HTTP 200 and no other signal,
so every response here carries `served` and the pipeline passes it through to the user.
"""
import json
import os
import pathlib
import random
import re
import time
import urllib.error
import urllib.request

API = os.environ.get("CHAPTERVERSE_API", "https://api.publicai.co/v1/chat/completions")
UA = "ChapterAndVerse/0.1 (+https://github.com/bisale24-ops/chapter-and-verse)"
KEY_FILE = pathlib.Path.home() / ".config" / "publicai.key"
DEFAULT_MODEL = "swiss-ai/apertus-v1.5-70b"


def key():
    return (os.environ.get("PUBLICAI_KEY")
            or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")).strip()


def call(system, user, model=DEFAULT_MODEL, max_tokens=1200, tries=4):
    body = {"model": model, "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    request = urllib.request.Request(API, method="POST", data=json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key()}",
                                              "User-Agent": UA,
                                              "Content-Type": "application/json"})
    for attempt in range(tries):
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = json.loads(response.read())
                choice = (payload.get("choices") or [{}])[0]
                return {"text": (choice.get("message") or {}).get("content") or "",
                        "served": payload.get("model"),
                        "asked": model,
                        "substituted": bool(payload.get("model")) and payload["model"] != model,
                        "usage": payload.get("usage") or {},
                        "seconds": round(time.time() - started, 2)}
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                time.sleep(min(30, 2 ** attempt + random.random()))
                continue
            return {"text": "", "served": None, "asked": model, "substituted": False,
                    "error": f"HTTP {e.code}", "usage": {}, "seconds": round(time.time() - started, 2)}
        except Exception as e:                                  # noqa: BLE001 - network flakiness
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"text": "", "served": None, "asked": model, "substituted": False,
                    "error": repr(e), "usage": {}, "seconds": round(time.time() - started, 2)}


def as_json(text):
    """The model is asked for JSON; this survives it wrapping the JSON in prose or a fence."""
    if not text:
        return None
    for candidate in (text, *re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)):
        try:
            return json.loads(candidate.strip())
        except (json.JSONDecodeError, AttributeError):
            pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None
