"""Capture the screens the demo video is made of, from the running app.

Nothing here is a mock-up: the page is driven the way a person would drive it, and whatever it
answers is what the video shows. Run the server first:

    ./run.sh 8123 &
    /tmp/ttsenv/bin/python video/capture.py
"""
import asyncio
import pathlib
import sys

from playwright.async_api import async_playwright

HERE = pathlib.Path(__file__).parent
SHOTS = HERE / "shots"
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8123"

SCENES = [
    {"name": "01-question", "question": None, "docs": ["timesheet_ca_week.csv"],
     "where": "us-federal,us-ca", "shoot": "form"},
    {"name": "02-answer", "question": None, "docs": ["timesheet_ca_week.csv"],
     "where": "us-federal,us-ca", "shoot": "answer"},
    {"name": "03-source-open", "question": None, "docs": ["timesheet_ca_week.csv"],
     "where": "us-federal,us-ca", "shoot": "source"},
    {"name": "04-gaps", "question": "Does New York require daily overtime after eight hours, the way California does?",
     "docs": [], "where": "us-federal,us-ca", "shoot": "gaps"},
    {"name": "05-russian", "question": "Работник отработал сверхурочно 5 часов за смену. Как это оплачивается?",
     "docs": ["timesheet_kg_week.csv"], "where": "kg", "shoot": "answer"},
]


async def run_scene(page, scene):
    await page.goto(BASE, wait_until="networkidle")
    if scene["question"]:
        await page.fill("#q", scene["question"])
    await page.select_option("#j", scene["where"])
    for box in await page.query_selector_all(".docs input"):
        value = await box.get_attribute("value")
        checked = await box.is_checked()
        if (value in scene["docs"]) != checked:
            await box.click()
    if scene["shoot"] == "form":
        return await page.screenshot(path=str(SHOTS / f"{scene['name']}.png"))

    for attempt in range(3):
        await page.click("#go")
        await page.wait_for_selector("#out .claim, #out .gap", timeout=180_000)
        await page.wait_for_timeout(700)
        claims = await page.query_selector_all("#out .claim")
        if claims or scene["shoot"] == "gaps":      # a gap-only answer is the point of that scene
            break
        print(f"  no claims, asking again ({attempt + 1})", flush=True)
    if scene["shoot"] == "source":
        chip = await page.query_selector("#out .claim .cite")
        if chip:
            await chip.click()
            await page.wait_for_timeout(400)
    target = "#out"
    if scene["shoot"] == "gaps":
        headings = await page.query_selector_all("#out h2")
        if headings:
            await headings[-1].scroll_into_view_if_needed()
    element = await page.query_selector(target)
    box = await element.bounding_box()
    # a whole answer is taller than a video frame; a tall screenshot scaled down is unreadable,
    # so the shot is cut to the top of the block and the rest is left out of the film
    clip = {"x": box["x"], "y": box["y"], "width": box["width"],
            "height": min(box["height"], 760)}
    await page.screenshot(path=str(SHOTS / f"{scene['name']}.png"), clip=clip)


async def main():
    SHOTS.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1100, "height": 900}, device_scale_factor=2)
        for scene in SCENES:
            print(scene["name"], flush=True)
            try:
                await run_scene(page, scene)
            except Exception as e:                               # noqa: BLE001 - keep the rest
                print(f"  failed: {e}", flush=True)
        await browser.close()
    print("shots in", SHOTS)


if __name__ == "__main__":
    asyncio.run(main())
