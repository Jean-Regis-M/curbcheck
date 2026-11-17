# CurbCheck

Can this item go in my curbside recycling bin, **in my city**? CurbCheck identifies an item from a photo, looks up the
city's published rules, and answers **accept**, **reject** or **not sure**. A wrong "accept" contaminates a whole load,
so it abstains instead of guessing. Research prototype for Arbiter Hacks V1 (Theme Track: Rethinking Waste).

## What is implemented
- Rules engine: per-city JSON tables where every rule cites an official page and retrieval date (Seattle, Washington DC).
- Image model: OpenCLIP ViT-B/32 (CPU) plus a linear head trained on crops of the TACO litter dataset, 13 item types.
- Abstention: temperature-scaled probabilities are summed per city verdict; the tool answers only above a threshold chosen on a validation split.
- FastAPI service (/api/check, /api/cities) and a single-page web UI.
- Tests (pytest), lint (uff), reproducible data and evaluation scripts.

## Measured results (TACO crops, split by source photo; test n = 306)
Threshold chosen on validation only (see eval/fixed_threshold.json):

| City | No abstention: false-accept rate | With abstention: false-accept rate | Coverage answered |
|---|---|---|---|
| Seattle | 13.8% | 3.3% | 69.6% |
| Washington DC | 12.2% | 3.2% | 68.6% |

False accept = predicted "accept" when the city's rule for the true item is not "accept" (includes conditional items).
Item accuracy on the test split: 64% (linear head), 44% (zero-shot CLIP). Curves: eval/far_vs_coverage.png, numbers: eval/results.json.

### What did not work
We hypothesised that abstaining on the probability of the *city verdict* would beat abstaining on *item confidence*.
It did not: the two perform about the same (zero-shot: worse). The benefit comes from abstention itself and from tying answers to city rules.

## Limitations (read before trusting it)
- Trained and tested only on TACO: outdoor litter, small test set (306 crops, 95% intervals in eval/results.json are wide). No test on household or other datasets yet.
- Food waste, batteries and greasy pizza boxes had too few examples (5, 2, 3) so the model cannot predict them, although the rules tables include them.
- 330 TACO annotations were dropped because photo orientation disagreed with the annotation.
- Two cities only. Where a city page is silent on an item the rule is marked conditional (never auto-answered); that is a gap in the page, not a statement of the city's actual rule.
- Not a substitute for your city's official guidance.

## Run it
`ash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]" open_clip_torch torch torchvision scikit-learn matplotlib requests --extra-index-url https://download.pytorch.org/whl/cpu
.venv/Scripts/python -m pytest
.venv/Scripts/python -m uvicorn curbcheck.api:app --port 8000   # open http://localhost:8000
`
(On macOS/Linux use .venv/bin/python.) The first request downloads the OpenAI CLIP weights.

Reproduce the evaluation (downloads TACO images from the dataset's own host; images are never committed):
`ash
python scripts/prepare_taco.py && python scripts/extract_features.py && python scripts/evaluate.py && python scripts/train_head.py
`

See docs/ARCHITECTURE.md and docs/DATA.md (data sources, licences, unresolved conflicts). Code is MIT licensed; datasets keep their own licences.
