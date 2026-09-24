"""One page, served by the standard library.

  python3 -m chapterverse.server          then open http://localhost:8000

The layout carries the argument: claims and the "not verified" list sit in the same column, in
the same type, under headings of the same weight. The gap list is not a disclaimer in small
print at the bottom - it is half the answer.
"""
import datetime
import http.server
import json
import pathlib
import urllib.parse

from . import corpus, model, pipeline

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"
SAMPLES = sorted(p.name for p in (DATA / "fixtures").glob("*") if p.is_file())

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chapter and Verse</title>
<style>
  :root {
    --bg: #fbfaf7; --fg: #1a1a18; --muted: #6b6a64; --line: #e2e0d8;
    --ok: #2f6f45; --ok-bg: #edf5ef; --gap: #8a5a12; --gap-bg: #fbf3e4; --card: #fff;
  }
  @media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
    --bg: #14140f; --fg: #eceae2; --muted: #9a988e; --line: #2c2b24;
    --ok: #7fc79a; --ok-bg: #16241b; --gap: #e0b063; --gap-bg: #2a2012; --card: #1b1a15;
  } }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg);
         font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
  .wrap { max-width: 860px; margin: 0 auto; padding: 32px 16px 80px; }
  h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -.01em; }
  .sub { color: var(--muted); margin: 0 0 28px; }
  form { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }
  label { display: block; font-size: 13px; color: var(--muted); margin: 12px 0 4px; }
  label:first-child { margin-top: 0; }
  textarea, select, input { width: 100%; font: inherit; color: inherit; background: transparent;
    border: 1px solid var(--line); border-radius: 8px; padding: 9px 10px; }
  textarea { min-height: 76px; resize: vertical; }
  .row { display: flex; gap: 12px; flex-wrap: wrap; }
  .row > div { flex: 1 1 200px; }
  .docs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
  .docs label { display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 13px;
    color: var(--fg); border: 1px solid var(--line); border-radius: 999px; padding: 5px 11px; }
  .docs input { width: auto; }
  button { margin-top: 16px; font: inherit; font-weight: 600; background: var(--fg); color: var(--bg);
    border: 0; border-radius: 8px; padding: 10px 18px; cursor: pointer; }
  button[disabled] { opacity: .5; cursor: default; }
  h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .08em; margin: 34px 0 12px; }
  .claim, .gap { border: 1px solid var(--line); border-left-width: 3px; border-radius: 10px;
    background: var(--card); padding: 14px 16px; margin-bottom: 10px; }
  .claim { border-left-color: var(--ok); }
  .gap { border-left-color: var(--gap); }
  .cite { display: inline-block; font-size: 13px; margin-top: 8px; padding: 3px 9px; border-radius: 999px;
    background: var(--ok-bg); color: var(--ok); cursor: pointer; border: 0; font-family: inherit; }
  .gap .cite { background: var(--gap-bg); color: var(--gap); cursor: default; }
  blockquote { font-family: Georgia, "Iowan Old Style", serif; margin: 10px 0 0; padding-left: 12px;
    border-left: 2px solid var(--line); color: var(--fg); }
  .para { font-family: Georgia, serif; color: var(--gap); margin-top: 10px; }
  .src { display: none; margin-top: 10px; padding: 10px; border-radius: 8px; background: var(--bg);
    border: 1px solid var(--line); font-family: Georgia, serif; font-size: 14px; white-space: pre-wrap;
    max-height: 260px; overflow: auto; }
  .src.open { display: block; }
  .why { color: var(--muted); font-size: 14px; margin-top: 6px; }
  .note { color: var(--muted); font-size: 13px; margin-top: 24px; border-top: 1px solid var(--line);
    padding-top: 12px; }
  .warn { background: var(--gap-bg); color: var(--gap); border-radius: 8px; padding: 10px 12px;
    margin-bottom: 14px; font-size: 14px; }
  .sums { font-size: 14px; color: var(--muted); }
  .sums b { color: var(--fg); }
</style></head>
<body><div class="wrap">
<h1>Chapter and Verse</h1>
<p class="sub">Answers only what it can trace to a source, and shows the rest.</p>
<form id="f">
  <label for="q">Question</label>
  <textarea id="q" name="q">A California employee works four 10-hour days, 40 hours in the week, at $20 an hour. Is any overtime owed?</textarea>
  <div class="row">
    <div><label for="j">Where</label><select id="j" name="j">
      <option value="us-federal,us-ca">United States: federal and California</option>
      <option value="us-federal">United States: federal only</option>
      <option value="kg">Kyrgyz Republic</option>
    </select></div>
    <div><label for="d">Date of the work</label><input type="date" id="d" name="d" value="__TODAY__"></div>
  </div>
  <label>Documents</label>
  <div class="docs">__DOCS__</div>
  <button id="go">Ask</button>
</form>
<div id="out"></div>
<p class="note">Provisions are quoted from official sources, frozen at the dates named in the
repository. This shows provisions and arithmetic; it is not legal advice.</p>
</div>
<script>
const out = document.getElementById('out');
const esc = s => (s ?? '').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
document.getElementById('f').addEventListener('submit', async e => {
  e.preventDefault();
  const go = document.getElementById('go');
  go.disabled = true; go.textContent = 'Reading the law…';
  out.innerHTML = '';
  const docs = [...document.querySelectorAll('.docs input:checked')].map(i => i.value);
  const body = { question: document.getElementById('q').value,
                 jurisdictions: document.getElementById('j').value.split(','),
                 date: document.getElementById('d').value, documents: docs,
                 language: document.getElementById('j').value === 'kg' ? 'ru' : 'en' };
  try {
    const r = await fetch('/ask', {method: 'POST', body: JSON.stringify(body)});
    render(await r.json());
  } catch (err) { out.innerHTML = '<div class="gap">' + esc(String(err)) + '</div>'; }
  go.disabled = false; go.textContent = 'Ask';
});
function render(a) {
  let html = '';
  if (a.trace && a.trace.substituted) html += `<div class="warn">The gateway answered with
    <b>${esc(a.trace.served_model)}</b> although <b>${esc(a.trace.asked_model)}</b> was requested,
    so the provenance of this answer is not what it should be.</div>`;
  if (a.facts && a.facts.pay) { const p = a.facts.pay;
    html += `<h2>Computed from the timesheet</h2><div class="claim"><div class="sums">
      ${a.facts.summary.total_hours} hours in the week, ${a.facts.summary.over_40} beyond forty.<br>
      Federal weekly rule <b>$${p.federal.total.toFixed(2)}</b> · California daily rule
      <b>$${p.california.total.toFixed(2)}</b> → owed <b>$${p.owed.toFixed(2)}</b> under the ${esc(p.under)} rule.<br>
      <span>${esc(p.note)}</span></div></div>`; }
  html += '<h2>Answer</h2>';
  html += a.claims.length ? a.claims.map(claimHtml).join('')
        : '<div class="gap">Nothing in the sources supports an answer to this question.</div>';
  html += '<h2>Not verified</h2>';
  html += a.gaps.length ? a.gaps.map(g => `<div class="gap">${esc(g.missing)}
      <div class="why">${esc(g.why)}</div></div>`).join('')
        : '<div class="claim">Every claim above was checked against its source.</div>';
  const t = a.trace || {};
  html += `<p class="note">${a.sources.length} provisions read · ${t.verifier_calls} verification
    calls · model ${esc(t.served_model)} · searched for ${esc((t.search_phrases||[]).join('; '))}</p>`;
  out.innerHTML = html;
  out.querySelectorAll('.cite').forEach(b => b.onclick = () => {
    const src = document.getElementById(b.dataset.src); if (src) src.classList.toggle('open'); });
}
function claimHtml(c, i) {
  const id = 'src' + i;
  const quote = c.quote ? `<blockquote>“${esc(c.quote)}”</blockquote>`
    : c.paraphrase ? `<div class="para">Not found in the source as written, so it is shown as the
        model's own words: ${esc(c.paraphrase)}</div>` : '';
  const other = (c.superseded_versions || []).map(v =>
    `<div class="why">Another version of this provision exists: ${esc(v)}</div>`).join('');
  return `<div class="claim">${esc(c.text)}${quote}
    <button class="cite" data-src="${id}">${esc(c.citation)} — ${esc(c.jurisdiction)}</button>
    ${other}<div class="src" id="${id}">${esc(c.source_text || '')}</div></div>`;
}
</script></body></html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, content_type):
        payload = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if urllib.parse.urlparse(self.path).path != "/":
            return self._send(404, "not found", "text/plain")
        docs = "".join(
            f'<label><input type="checkbox" value="{name}"'
            f'{" checked" if name == "timesheet_ca_week.csv" else ""}> {name}</label>'
            for name in SAMPLES)
        page = PAGE.replace("__DOCS__", docs).replace("__TODAY__", datetime.date.today().isoformat())
        self._send(200, page, "text/html; charset=utf-8")

    def do_POST(self):
        if urllib.parse.urlparse(self.path).path != "/ask":
            return self._send(404, "not found", "text/plain")
        length = int(self.headers.get("Content-Length") or 0)
        request = json.loads(self.rfile.read(length) or b"{}")
        try:
            answer = pipeline.ask(
                request.get("question", ""),
                jurisdictions=tuple(request.get("jurisdictions") or ("us-federal", "us-ca")),
                on_date=datetime.date.fromisoformat(request["date"]) if request.get("date") else None,
                documents=pipeline.sample_documents(*(request.get("documents") or [])),
                language=request.get("language", "en"),
                model_name=request.get("model") or model.DEFAULT_MODEL)
        except Exception as e:                                   # noqa: BLE001 - surface it in the page
            return self._send(200, json.dumps({"claims": [], "gaps": [
                {"missing": "an answer", "why": repr(e)}], "sources": [], "trace": {}}),
                "application/json")
        by_id = {u["id"]: u for u in answer["sources"]}
        for claim in answer["claims"]:
            unit = by_id.get(claim["unit"])
            claim["source_text"] = (unit["text"][:4000] if unit else "")
        answer["sources"] = [{"id": u["id"], "citation": u["citation"]} for u in answer["sources"]]
        self._send(200, json.dumps(answer, ensure_ascii=False, default=str), "application/json")


def main(port=8000):
    # threaded: one answer takes the better part of a minute, and a second visitor should not wait
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    with http.server.ThreadingHTTPServer(("", port), Handler) as httpd:
        print(f"Chapter and Verse on http://localhost:{port}  ({len(corpus.load())} units loaded)")
        httpd.serve_forever()


if __name__ == "__main__":
    import sys
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
