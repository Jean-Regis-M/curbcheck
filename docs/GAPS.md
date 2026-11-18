# Known gaps, with their status

Last reviewed 2026-11-18. "Open" means not fixed. Nothing here is hidden from the README.

| # | Gap | Why it matters for the rubric | Status | Evidence or next step |
|---|---|---|---|---|
| 1 | The model is trained on litter, studio and landfill photos, not household items | Impact, feasibility | **Open** | Needs item-level labelled household photos; no such data was available |
| 2 | Batteries, greasy or food-soiled paper and food waste are not recognised | Impact | **Open** (disclosed on every answer) | Too few labelled examples (2, 3 and 5 in TACO) |
| 3 | Recyclables were wrongly rejected 8% to 33% by the first model | Feasibility | **Mitigated, with a cost** | The shipped three-dataset model rejects about 0% on unseen datasets, but by answering only ~25% to 70% of photos ([`eval/v3.json`](../eval/v3.json)); the operating point was tuned after seeing those tests |
| 4 | Small single test set | Technical execution | **Mitigated** | 20 random photo-grouped splits ([`eval/crossval.json`](../eval/crossval.json)); still one source dataset for the headline |
| 5 | No real-world contamination measurement | Impact | **Open** | Pilot protocol with power analysis written ([PILOT.md](PILOT.md)); not run |
| 6 | The hosted browser model was not re-evaluated on unseen datasets | Technical execution | **Closed** | Own head trained and tested on browser features ([`eval/v3_web.json`](../eval/v3_web.json)); slightly worse than PyTorch (Austin TrashNet false accepts 10.9%) |
| 7 | New York's rule quotes cannot be audited by script (its site blocks scripts) | Technical execution | **Partly** | Checked by hand once; the other six cities are audited automatically |
| 8 | Only seven US cities; no non-US rules | Impact | **Open** | Adding a city is one audited JSON file; Los Angeles and Chicago were excluded for unreadable or unauditable sources |
| 9 | The API has no authentication, and its rate limit is per process | Feasibility | **Open** | Documented in the README security section |
| 10 | The hosted page loads its script from a CDN without integrity pinning | Feasibility | **Open** | Vendoring the script would remove the dependency |
| 11 | Accessibility checked by an automated audit only | Presentation | **Partly** | axe-core reports no violations in light and dark; no manual screen-reader test |
| 12 | The demo video may predate the latest page design and model; the voice is synthetic | Presentation | **Open** | Re-record after the final build |
| 13 | Image-dataset licence conflicts (RealWaste, ZeroWaste) | Feasibility | **Open** | [`docs/DATA.md`](DATA.md); datasets are never redistributed |
| 14 | The latest model has not had a third AI-agent review | Technical execution | **Open** | Review 1 scored ~62/100, review 2 ~71/100; both sets of defects were fixed and re-measured |
| 16 | Labels for TrashNet and RealWaste are material-level (weak), and the answer-rate target was tuned after seeing the unseen tests | Technical execution | **Open** (disclosed) | README caveats; [`docs/DATA.md`](DATA.md) |
| 17 | Greasy pizza boxes can pass as clean cardboard (7 of 21 city answers wrongly "recycle" in a tiny smoke test) | Impact | **Open** (warned on every cardboard/paper accept) | [`eval/hazard_check.json`](../eval/hazard_check.json) |
| 15 | Feedback reports are collected but not used to retrain | Feasibility | **Open** | Reports go to GitHub issues; a labelling and retraining loop is future work |
