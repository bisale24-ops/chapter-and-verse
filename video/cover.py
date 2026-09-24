"""Render the submission cover image (1280x720)."""
import asyncio
import pathlib

from playwright.async_api import async_playwright

from build import CARD                                          # noqa: E402

OUT = pathlib.Path(__file__).parent / "cover.png"
BODY = """
<div style="display:flex;flex-direction:column;gap:22px">
  <div>
    <h1 style="font-size:54px;margin:0">Chapter and Verse</h1>
    <p class="sub" style="font-size:26px;margin:6px 0 0">A labour-pay assistant that answers only
    what it can trace to a source &mdash; and shows you the rest.</p>
  </div>
  <table>
    <tr><th>&nbsp;</th><th>bare model, same sources</th><th>Chapter and Verse</th></tr>
    <tr><td>Altered quotation shown as a quotation</td><td class="n bad">3</td><td class="n ok">0</td></tr>
    <tr><td>Cited something ruled out</td><td class="n bad">4</td><td class="n ok">0</td></tr>
    <tr><td>Gap reported where it must be</td><td class="n">2 / 4</td><td class="n ok">4 / 4</td></tr>
  </table>
  <p class="foot" style="margin:0">530 provisions &middot; FLSA, 29 CFR, California Labor Code,
  Labour Code of the Kyrgyz Republic &middot; Python, no dependencies &middot; MIT</p>
</div>"""


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=2)
        await page.set_content(CARD.format(body=BODY))
        await page.screenshot(path=str(OUT))
        await browser.close()
    print(OUT)


if __name__ == "__main__":
    asyncio.run(main())
