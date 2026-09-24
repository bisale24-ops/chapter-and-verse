"""Build the demo video: synthesised narration over real screens.

    /tmp/ttsenv/bin/python video/build.py

Narration is edge-tts (`en-US-AndrewNeural`) — no presenter voice, and the last card says so.
The app screens come from `capture.py`, which drives the running page; the cards are rendered
here from the project's own numbers. Nothing is re-typed for the camera.
"""
import asyncio
import pathlib
import subprocess
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
SHOTS = HERE / "shots"
BUILD = HERE / "build"
VOICE = "en-US-AndrewNeural"
W, H, FPS = 1280, 720, 30

SCENES = [
    ("title", None,
     "A language model was asked what twenty-nine C F R section five thirty-one point seven "
     "requires. It described a recordkeeping rule, and quoted it. That section is marked "
     "Reserved. It has no text at all."),
    ("measured", None,
     "We measured that before building anything. Sixteen of twenty-six answers quoted words "
     "that are not in any source. This is the problem the project is built against."),
    ("shot:01-question", None,
     "Chapter and Verse answers a pay question from three things: the law, the contract and the "
     "timesheet. The date matters, because provisions change."),
    ("shot:03-source-open", None,
     "Every claim names the provision it rests on. The citation opens the provision underneath. "
     "The quotation was matched against that text in code before it was shown in quotation marks."),
    ("computed", None,
     "Both levels of law apply here. Federal law counts the week, California counts the day. "
     "The tool computes both in Python and takes the larger: this week the federal figure wins "
     "by fifteen dollars, and the assumption that state law always pays more is wrong."),
    ("shot:04-gaps", None,
     "The other half of the answer is what could not be established, and why. A provision that "
     "does not cover the question. A check that failed. It sits in the same column as the answer, "
     "not in small print at the bottom."),
    ("verifier", None,
     "A contract paying overtime at one and a quarter times the rate. The first pass wrote that "
     "this was allowed. The verification pass reads the claim against the provision alone, "
     "without the question and without the reasoning that produced it, and rejects it."),
    ("results", None,
     "Same questions, same checks, before and after. The bare model with the same sources showed "
     "three altered quotations and cited four things it had been told to ignore. This shows none, "
     "and reports the gap in every question that has no answer in the corpus."),
    ("shot:05-russian", None,
     "The second corpus is the Labour Code of Kyrgyzstan, in Russian. Same behaviour, and no "
     "Californian rule smuggled into a country that does not have one."),
    ("end", None,
     "Chapter and Verse. Sourced, or silent. M I T licensed, and the narration in this video is "
     "synthesised."),
]

CARD = """<!doctype html><meta charset="utf-8"><style>
 body {{ margin:0; width:1280px; height:720px; background:#fbfaf7; color:#1a1a18;
   font:20px/1.5 system-ui,-apple-system,sans-serif; display:flex; flex-direction:column;
   justify-content:center; padding:0 72px; box-sizing:border-box; }}
 h1 {{ font-size:40px; margin:0 0 6px; letter-spacing:-.02em; }}
 .sub {{ color:#6b6a64; margin:0 0 28px; font-size:22px; }}
 pre {{ font:16px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; background:#fff;
   border:1px solid #e2e0d8; border-left:3px solid #8a5a12; border-radius:10px; padding:18px 20px;
   margin:0; white-space:pre-wrap; }}
 table {{ border-collapse:collapse; font-size:19px; width:100%; }}
 th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid #e2e0d8; }}
 th {{ color:#6b6a64; font-weight:600; font-size:15px; text-transform:uppercase;
   letter-spacing:.06em; }}
 td.n {{ text-align:right; font-variant-numeric:tabular-nums; }}
 .ok {{ color:#2f6f45; font-weight:700; }}
 .bad {{ color:#8a5a12; font-weight:700; }}
 .big {{ font-size:30px; line-height:1.35; }}
 .foot {{ color:#6b6a64; font-size:16px; margin-top:26px; }}
</style>{body}"""

CARDS = {
    "title": """<h1>&ldquo;29 CFR&nbsp;531.7 requires employers to keep accurate and complete
    records&hellip;&rdquo;</h1><p class="sub">Apertus 70B, asked without sources, 24 September 2026</p>
    <pre>$ grep -A2 '531.7' data/corpus_us.json
  "id": "29CFR531.7",
  "title": "[Reserved]",
  "text": ""</pre>""",
    "measured": """<h1>Measured before anything was built</h1>
    <p class="sub">26 questions, the bare model, three conditions</p>
    <table><tr><th>&nbsp;</th><th>no sources</th><th>sources</th><th>sources + may decline</th></tr>
    <tr><td>Answers quoting words that are in no source</td><td class="n bad">16</td><td class="n">3</td><td class="n">1</td></tr>
    <tr><td>Cited something ruled out</td><td class="n">1</td><td class="n bad">4</td><td class="n">1</td></tr>
    <tr><td>Reported the gap where that is the only honest answer</td><td class="n bad">0 / 4</td><td class="n">2 / 4</td><td class="n">4 / 4</td></tr>
    </table><p class="foot">Raw logs: 364 calls, $0.49, in the repository.</p>""",
    "computed": """<h1>Two rules, both computed</h1>
    <p class="sub">69 hours at $20, one week, California</p>
    <table><tr><td class="big">Federal weekly rule</td><td class="n big ok">$1,670.00</td></tr>
    <tr><td class="big">California daily and seventh-day rule</td><td class="n big">$1,655.00</td></tr>
    <tr><td class="big">Owed</td><td class="n big ok">$1,670.00</td></tr></table>
    <p class="foot">California entitles the employee to the larger result and never pays the same
    hour twice. Assuming the state figure is higher would be wrong by $15.00 — the arithmetic is
    done in Python, never by the model.</p>""",
    "verifier": """<h1>The verifier sees the claim and the provision. Nothing else.</h1>
    <pre>claim   Overtime at 1.25 times the base rate is allowed under federal law.
source  29 CFR 778.308 &mdash; The overtime rate must not be less than one and
        one-half times the regular rate.

verdict unsupported
        &rarr; moved out of the answer and into &ldquo;Not verified&rdquo;</pre>
    <p class="foot">It never sees the question, the other claims, or the reasoning that produced
    the claim &mdash; a verifier shown the reasoning agrees with it.</p>""",
    "results": """<h1>The same 26 questions, through the tool</h1>
    <table><tr><th>&nbsp;</th><th>bare model, same sources</th><th>Chapter and Verse</th></tr>
    <tr><td>Passed</td><td class="n">13 / 26</td><td class="n">11 / 26</td></tr>
    <tr><td>Altered quotation shown as a quotation</td><td class="n bad">3</td><td class="n ok">0</td></tr>
    <tr><td>Cited something ruled out</td><td class="n bad">4</td><td class="n ok">0</td></tr>
    <tr><td>Gap reported where it must be</td><td class="n">2 / 4</td><td class="n ok">4 / 4</td></tr>
    </table><p class="foot">Right less often, wrong less dangerously. What it loses, it loses to
    retrieval — and says so.</p>""",
    "end": """<h1>Chapter and Verse</h1><p class="sub">Sourced, or silent.</p>
    <p class="big">github.com/bisale24-ops/chapter-and-verse</p>
    <p class="foot">MIT licensed &middot; built with the Devpost Learn skill pack &middot;
    corpora: FLSA, 29 CFR 531/541/778/785, California Labor Code, Labour Code of the Kyrgyz
    Republic &middot; the narration in this video is synthesised, there is no presenter.</p>""",
}


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def render_cards():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for name, body in CARDS.items():
            await page.set_content(CARD.format(body=body))
            await page.screenshot(path=str(BUILD / f"card-{name}.png"))
        await browser.close()


def narrate():
    for index, (name, _, line) in enumerate(SCENES):
        out = BUILD / f"line-{index:02d}.mp3"
        if out.exists():
            continue
        subprocess.run([sys.executable.replace("python", "edge-tts"), "--voice", VOICE,
                        "--text", line, "--write-media", str(out)], check=True)


def main():
    BUILD.mkdir(exist_ok=True)
    asyncio.run(render_cards())
    narrate()

    segments = []
    for index, (name, _, _) in enumerate(SCENES):
        audio = BUILD / f"line-{index:02d}.mp3"
        image = SHOTS / f"{name.split(':', 1)[1]}.png" if name.startswith("shot:") \
            else BUILD / f"card-{name}.png"
        segment = BUILD / f"seg-{index:02d}.mp4"
        seconds = duration(audio) + 0.9
        run("-loop", "1", "-i", str(image), "-i", str(audio),
            "-filter_complex",
            f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
            f"pad={W}:{H}:(ow-iw)/2:0:color=0xfbfaf7,format=yuv420p[v];"
            f"[1:a]apad=pad_dur=0.9,aresample=48000[a]",
            "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-t", f"{seconds:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", str(segment))
        segments.append(segment)

    listing = BUILD / "segments.txt"
    listing.write_text("".join(f"file '{s.name}'\n" for s in segments))
    final = HERE / "chapter-and-verse-demo.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(listing),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        str(final))
    print(f"{final.name}  {duration(final):.1f}s")


if __name__ == "__main__":
    main()
