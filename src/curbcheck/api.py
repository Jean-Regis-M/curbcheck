"""HTTP API and static UI. Run: uvicorn curbcheck.api:app"""
from __future__ import annotations

import io
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .decision import decide
from .model import Classifier, ClipHeadClassifier
from .rules import list_cities, load_city
from .taxonomy import ITEMS

MAX_BYTES = 5 * 1024 * 1024
MAX_BODY = MAX_BYTES + 64 * 1024  # multipart framing overhead
MAX_PIXELS = 25_000_000
RATE_LIMIT = 30  # requests per client per minute on /api/check
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
WEB = Path(__file__).resolve().parents[2] / "web"

# The classifier was never trained on these items; the UI and API say so on every answer.
UNRECOGNISED = ["batteries", "greasy or food-soiled pizza boxes and paper", "food waste"]

Image.MAX_IMAGE_PIXELS = MAX_PIXELS
app = FastAPI(title="CurbCheck", version="0.2.0")
_clf: Classifier | None = None
_hits: dict[str, deque] = defaultdict(deque)


def get_classifier() -> Classifier:
    global _clf
    if _clf is None:
        _clf = ClipHeadClassifier()
    return _clf


@app.middleware("http")
async def guard_uploads(request: Request, call_next):
    """Reject oversized or unframed uploads before the multipart body is parsed, and rate-limit the check endpoint."""
    if request.url.path == "/api/check" and request.method == "POST":
        length = request.headers.get("content-length")
        if length is None:
            return JSONResponse({"detail": "Content-Length required"}, status_code=411)
        if not length.isdigit() or int(length) > MAX_BODY:
            return JSONResponse({"detail": "image larger than 5 MB"}, status_code=413)
        now = time.monotonic()
        q = _hits[request.client.host if request.client else "?"]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return JSONResponse({"detail": "rate limit: 30 checks per minute"}, status_code=429)
        q.append(now)
    return await call_next(request)


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
def check(image: UploadFile = File(...), city: str = Form(...), clf: Classifier = Depends(get_classifier)):
    # Plain `def`: FastAPI runs it in a worker thread, so CPU-bound inference does not block the event loop.
    if city not in list_cities():
        raise HTTPException(404, f"unknown city '{city}'")
    if image.content_type not in ALLOWED:
        raise HTTPException(415, "upload a JPEG, PNG or WebP image")
    data = image.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "image larger than 5 MB")
    try:
        pic = Image.open(io.BytesIO(data))
        if pic.width * pic.height > MAX_PIXELS:  # check the header before decoding any pixels
            raise HTTPException(413, "image has more than 25 megapixels")
        pic.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, "could not read the image") from None
    rules = load_city(city)
    probs = clf.predict(pic)
    d = decide(probs, rules, threshold=clf.threshold)
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
        "not_recognised": UNRECOGNISED,
        "disclaimer": "Model trained on outdoor litter photos; abstains when unsure. Check your city's official page.",
    }


if WEB.exists():
    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    app.mount("/static", StaticFiles(directory=WEB), name="static")
