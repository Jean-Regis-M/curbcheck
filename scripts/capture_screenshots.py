"""Capture real screenshots of the running app (needs: pip install playwright && playwright install chromium,
and the server running on :8000). Images are TrashNet (MIT) and one TACO crop; they are used for illustration only.
Usage: python scripts/capture_screenshots.py"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "docs/img"
CASES = [
    ("02-accept-seattle", RAW / "trashnet/dataset-resized/glass/glass20.jpg", "seattle"),
    ("03-not-sure-seattle", RAW / "trashnet/dataset-resized/cardboard/cardboard30.jpg", "seattle"),
    ("04-reject-seattle", RAW / "trashnet/dataset-resized/trash/trash7.jpg", "seattle"),
    ("05-glass-seattle", RAW / "trashnet/dataset-resized/glass/glass122.jpg", "seattle"),
    ("06-glass-austin", RAW / "trashnet/dataset-resized/glass/glass122.jpg", "austin"),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
        page.goto("http://localhost:8000/")
        page.wait_for_selector("#city option", state="attached")
        page.screenshot(path=OUT / "01-home.png")  # hero, as a first-time visitor sees it
        page.add_style_tag(content="nav{display:none!important}")
        for name, img, city in CASES:
            page.select_option("#city", city)
            page.set_input_files("#file", str(img))
            page.click("#go")
            page.wait_for_function("document.querySelector('#result .verdict')", timeout=60000)
            page.wait_for_timeout(300)
            page.locator("#app").screenshot(path=OUT / f"{name}.png")
            print(name, page.inner_text("#result .verdict"))
        # hero image for the landing page: the answer panel for the same glass photo in Austin
        from PIL import Image
        page.select_option("#city", "austin")
        page.set_input_files("#file", str(RAW / "trashnet/dataset-resized/glass/glass122.jpg"))
        page.wait_for_function("document.querySelector('#result .verdict')", timeout=60000)
        page.wait_for_timeout(400)
        page.add_style_tag(content="#result p.small[style*='0 0 6px']{display:none}")  # keep the hero compact
        page.locator("#result").screenshot(path=OUT / "_hero_raw.png")
        im = Image.open(OUT / "_hero_raw.png").convert("RGB")
        im = im.resize((1100, int(im.height * 1100 / im.width)), Image.LANCZOS).crop((0, 0, 1100, 1180))
        im.save(ROOT / "web/img/hero.jpg", quality=88, optimize=True)
        (OUT / "_hero_raw.png").unlink()
        b.close()


if __name__ == "__main__":
    main()
