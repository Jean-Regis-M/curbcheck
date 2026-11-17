"""Download TACO 640px images and cut item crops. Usage: python scripts/prepare_taco.py
Images come from the dataset's own host and are NOT redistributed by this repo (data/raw is git-ignored)."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from curbcheck.taco_map import TACO_TO_ITEM

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "taco"
IMG = ROOT / "img640"
CROPS = ROOT / "crops"
MIN_SIDE = 24  # px on the 640 thumbnail


def fetch(im):
    dst = IMG / f"{im['id']}.jpg"
    if dst.exists() and dst.stat().st_size > 0:
        return True
    try:
        r = requests.get(im["flickr_640_url"] or im["flickr_url"], timeout=60)
        r.raise_for_status()
        dst.write_bytes(r.content)
        with Image.open(dst) as pic:  # full-size fallbacks are shrunk to 640 on the long side
            if max(pic.size) > 640:
                pic.convert("RGB").resize(tuple(int(v * 640 / max(pic.size)) for v in pic.size)).save(dst, quality=92)
        return True
    except Exception as e:  # network errors are reported, not hidden
        print("FAILED", im["id"], e)
        return False


def main():
    d = json.loads((ROOT / "annotations.json").read_text("utf-8"))
    IMG.mkdir(parents=True, exist_ok=True)
    CROPS.mkdir(exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(fetch, d["images"]))
    print(f"downloaded {sum(ok)}/{len(ok)} images")
    names = {c["id"]: c["name"] for c in d["categories"]}
    imgs = {i["id"]: i for i in d["images"]}
    rows = []
    skipped = [0]
    for a in d["annotations"]:
        item = TACO_TO_ITEM.get(names[a["category_id"]])
        im = imgs[a["image_id"]]
        src = IMG / f"{im['id']}.jpg"
        if item is None or not src.exists():
            continue
        with Image.open(src) as pic:
            pic = ImageOps.exif_transpose(pic).convert("RGB")
            if abs(pic.width / pic.height - im["width"] / im["height"]) > 0.02:
                skipped[0] += 1  # orientation/size disagrees with annotation: drop rather than guess
                continue
            s = pic.width / im["width"]
            x, y, w, h = [v * s for v in a["bbox"]]
            if min(w, h) < MIN_SIDE:
                continue
            pad = 0.1
            box = (max(0, x - pad * w), max(0, y - pad * h),
                   min(pic.width, x + w * (1 + pad)), min(pic.height, y + h * (1 + pad)))
            out = CROPS / f"{a['id']}.jpg"
            pic.crop(tuple(int(v) for v in box)).save(out, quality=92)
        rows.append({"crop": out.name, "image_id": im["id"], "item": item, "taco": names[a["category_id"]]})
    (ROOT / "crops.json").write_text(json.dumps(rows), encoding="utf-8")
    from collections import Counter
    print("skipped (orientation mismatch):", skipped[0])
    print(len(rows), "crops", dict(Counter(r["item"] for r in rows)))


if __name__ == "__main__":
    main()
