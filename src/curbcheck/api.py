"""HTTP API and static UI. Run: uvicorn curbcheck.api:app"""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .decision import decide
from .model import Classifier, ClipHeadClassifier
from .rules import list_cities, load_city
from .taxonomy import ITEMS

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 25_000_000
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
WEB = Path(__file__).resolve().parents[2] / "web"

Image.MAX_IMAGE_PIXELS = MAX_PIXELS
app = FastAPI(title="CurbCheck", version="0.1.0")
_clf: Classifier | None = None


def get_classifier() -> Classifier:
    global _clf
    if _clf is None:
        _clf = ClipHeadClassifier()
    return _clf


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/cities")
def cities():
    out = []
    for cid in list_cities():
        c = load_city(cid)
        out.append({"id": cid, "city": c.city, "program": c.program, "sources": [s.model_dump() for s in c.sources]})
    return out


@app.post("/api/check")
async def check(image: UploadFile = File(...), city: str = Form(...), clf: Classifier = Depends(get_classifier)):
    if city not in list_cities():
        raise HTTPException(404, f"unknown city '{city}'")
    if image.content_type not in ALLOWED:
        raise HTTPException(415, "upload a JPEG, PNG or WebP image")
    data = await image.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "image larger than 5 MB")
    try:
        pic = Image.open(io.BytesIO(data))
        pic.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, "could not read the image") from None
    rules = load_city(city)
    probs = clf.predict(pic)
    d = decide(probs, rules, threshold=clf.threshold)
    # decide() thresholds each verdict's mass; report only what the rules table can support.
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
    return {
        "city": rules.city,
        "verdict": d.verdict,
        "p_accept": round(d.p_accept, 4),
        "p_reject": round(d.p_reject, 4),
        "p_conditional": round(d.p_conditional, 4),
        "threshold": round(clf.threshold, 4),
        "top_items": [{"item": k, "label": ITEMS[k], "p": round(v, 4), "rule": rules.rules[k].verdict,
                       "note": rules.rules[k].note} for k, v in top],
        "source_url": d.source_url,
        "disclaimer": "Model trained on outdoor litter photos; abstains when unsure. Check your city's official page.",
    }


if WEB.exists():
    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    app.mount("/static", StaticFiles(directory=WEB), name="static")
