# Known gaps, with their status

Last reviewed 2026-11-18. "Open" means not fixed. Nothing here is hidden from the README.

| # | Gap | Why it matters for the rubric | Status | Evidence or next step |
|---|---|---|---|---|
| 1 | The model is trained on litter and landfill photos, not household items | Impact, feasibility | **Open** | Needs item-level labelled household photos; no such data was available |
| 2 | Batteries, greasy or food-soiled paper and food waste are not recognised | Impact | **Open** (disclosed on every answer) | Too few labelled examples (2, 3 and 5 in TACO) |
| 3 | Genuinely recyclable items are wrongly rejected 8% to 35% of the time | Feasibility | **Open** | Documented in the README; the safer error was chosen on purpose |
| 4 | Small single test set | Technical execution | **Mitigated** | 20 random photo-grouped splits ([`eval/crossval.json`](../eval/crossval.json)); still one source dataset for the headline |
| 5 | No real-world contamination measurement | Impact | **Open** | Pilot protocol with power analysis written ([PILOT.md](PILOT.md)); not run |
| 6 | The hosted browser model was not re-evaluated on TrashNet or RealWaste | Technical execution | **Open** | `extract_browser_features.py` can do it; not run |
| 7 | New York's rule quotes cannot be audited by script (its site blocks scripts) | Technical execution | **Partly** | Checked by hand once; the other six cities are audited automatically |
| 8 | Only seven US cities; no non-US rules | Impact | **Open** | Adding a city is one audited JSON file; Los Angeles and Chicago were excluded for unreadable or unauditable sources |
| 9 | The API has no authentication, and its rate limit is per process | Feasibility | **Open** | Documented in the README security section |
| 10 | The hosted page loads its script from a CDN without integrity pinning | Feasibility | **Open** | Vendoring the script would remove the dependency |
| 11 | Accessibility checked by an automated audit only | Presentation | **Partly** | axe-core reports no violations in light and dark; no manual screen-reader test |
| 12 | The demo video predates the new page design and logo; the voice is synthetic | Presentation | **Open** (minor) | The video shows the earlier interface; its numbers are still correct |
| 13 | Image-dataset licence conflicts (RealWaste, ZeroWaste) | Feasibility | **Open** | [`docs/DATA.md`](DATA.md); datasets are never redistributed |
| 14 | The fixed version has not had a second independent review | Technical execution | **Open** | The first review (about 62/100) found defects that were fixed and re-measured |
| 15 | Feedback reports are collected but not used to retrain | Feasibility | **Open** | Reports go to GitHub issues; a labelling and retraining loop is future work |
