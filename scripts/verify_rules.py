"""Audit the rule tables against their sources: fetch every cited page and check that each rule's verbatim quote
still appears in the page text. Catches misquotes, dead links and pages that changed.
Usage: python scripts/verify_rules.py [city_id ...]   (network required; exit code 1 on any failure)"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from curbcheck.rules import list_cities, load_city

UA = {"User-Agent": "Mozilla/5.0 (compatible; curbcheck-rule-audit; +https://github.com/Jean-Regis-M/curbcheck)"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style") and self.skip > 0

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def normalize(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace(" ", " ").replace("–", "-").replace("—", "-")
    t = re.sub(r"\s+", " ", t).strip().lower()
    t = re.sub(r" ([:;,.!?)])", r"\1", t)  # HTML often splits "Label" and ": text" into separate elements
    return re.sub(r"\*\s+", "*", t)


def _browser_text(url: str) -> str:
    """Fallback for sites that block plain HTTP clients (HTTP 403): render with headless Chromium (needs playwright)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto(url, wait_until="networkidle", timeout=60000)
        text = pg.inner_text("body")
        b.close()
    return normalize(text)


def page_text(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=40)
    if r.status_code == 403:
        return _browser_text(url)
    r.raise_for_status()
    if "pdf" in r.headers.get("content-type", "").lower():
        raise RuntimeError("PDF sources are not supported by this auditor")
    p = _Text()
    p.feed(r.text)
    return normalize(" ".join(p.parts))


ALLOW_BLOCKED = "--allow-blocked" in sys.argv


def main(ids):
    bad = 0
    for cid in ids or list_cities():
        city = load_city(cid)
        texts = {}
        for i, src in enumerate(city.sources):
            try:
                texts[i] = page_text(src.url)
            except Exception as e:
                texts[i] = None
                print(f"[{cid}] source {i} unreadable: {src.url} ({e})")
        checked = missing = silent = 0
        for item, rule in city.rules.items():
            if not rule.quote:
                silent += 1
                continue
            checked += 1
            t = texts.get(rule.source)
            if t is None or normalize(rule.quote) not in t:
                missing += 1
                print(f"[{cid}] NOT FOUND {item}: {rule.quote[:90]!r}")
        print(f"[{cid}] quotes checked {checked}, not found {missing}, rules without a quote {silent}")
        bad += missing + (0 if ALLOW_BLOCKED else sum(t is None for t in texts.values()))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")])
