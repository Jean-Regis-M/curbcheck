# Data sources and licences

Verified 2026-11-17. Policy: the repository ships download scripts, never the images.

## City rules

Each rule table in `data/rules/` cites the official city page(s) it was read from and the retrieval date, and every
non-silent rule carries a verbatim quote. `scripts/verify_rules.py` re-fetches each page and checks the quotes
(a monthly workflow runs it). Sites that block scripted clients (NYC) cannot be audited automatically; those quotes
were checked by hand against the page text on the retrieval date.

| Source | Status |
|---|---|
| Official city and city-contracted hauler pages | Used. Facts read from public pages, each cited with a URL and date. |
| The Recycling Partnership National Recycling Database (recyclingpartnership.org/data) | Not used. The page offers no download link or reuse terms. |
| Los Angeles | Not included. City pages returned 403 to every client; the only reachable source was a commercial-service PDF. |
| Chicago | Not included. The only readable source was a 2018 JavaScript-rendered 311 article that could not be audited. |
| Washington DC open data (Pathway to Zero Waste) | Listed as CC BY, narrative only, not used for rules. |

## Image datasets

| Dataset | Used for | Licence status |
|---|---|---|
| TACO (Proença and Simões, 2020) | Training and main test split | Code MIT; images are Flickr photos with per-image free licences; a Roboflow mirror says CC BY 4.0. Not redistributed. |
| TrashNet (Thung and Yang) | Training (shipped model), unseen test, sample photos in `web/samples` | Repository licence MIT. |
| RealWaste (Single, Iranmanesh and Raad, 2023) | Training (shipped model) and unseen test | **Conflict:** CC BY 4.0 on UCI and on the HuggingFace mirror card, CC BY-NC-SA 4.0 on IEEE DataPort. Treated as non-commercial research use. The UCI zip download stalled twice, so evaluation used the HuggingFace mirror `shahzaibvohra/realwaste`. |
| ZeroWaste | Considered, not used | CC BY 4.0 on Zenodo, CC BY-NC 4.0 on Papers With Code. |

## Known data problems

- Batteries, greasy pizza boxes and food waste have too few TACO crops (2, 3 and 5) to train or test; the model cannot recognise them and the interface says so on every answer.
- 330 TACO annotations were dropped because the photo orientation disagreed with the annotation.
- TrashNet has only 137 non-recyclable images, and its photos include near-duplicates, so resampled confidence intervals are optimistic.
- The v1 versus v2 choice and the shipped model's answer-rate target were made after seeing TrashNet and RealWaste results, so neither is a pristine holdout.
- On TrashNet about 93% of photos are recyclable, so "accept precision" is inflated there; use the false-accept rate.

## Weak labels used by the shipped model

TrashNet and RealWaste only have material-level labels (for example "cardboard", "Food Organics"). The shipped model maps them to items
(cardboard to cardboard box, glass to glass bottle or jar, paper to clean paper, trash/vegetation/textile/miscellaneous to other trash,
RealWaste "Food Organics" to food waste); metal is split into can, tin or foil by the earlier model's best guess; plastic is left out because
a plastic photo does not determine the verdict (bottles are accepted, bags are not). These labels are noisy by construction. All
evaluation on these datasets uses the same material-level truth, stated in the README.
