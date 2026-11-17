# Data sources and licences (verified 2026-11-17)

## City rules
- The Recycling Partnership National Recycling Database (recyclingpartnership.org/data): the page describes the database
  but offers no download link or reuse licence. NOT used. Revisit only if terms are found.
- Chosen approach: hand-curated rules for a small set of cities, each entry citing the city's official
  recycling page URL and retrieval date. Row-level source and date are stored with every rule.
- Washington DC open data is listed under CC BY (verify on the dataset page before reuse).

## Image datasets (licences still to confirm before redistribution)
- TACO: code MIT; Roboflow mirror says CC BY 4.0; images are Flickr with per-image free licences. Do not redistribute images; download via script.
- ZeroWaste: CC BY 4.0 on Zenodo, CC BY-NC 4.0 on Papers With Code. Treat as non-commercial until resolved.
- RealWaste: CC BY 4.0 per UCI (archive.ics.uci.edu/dataset/908), but IEEE DataPort says CC BY-NC-SA 4.0. Conflict, so treat as non-commercial research use until resolved.`n- TrashNet: licence not verified (check the GitHub LICENSE file).
Policy: the repo ships download scripts and checksums, never the images.


## Used for evaluation only
- RealWaste via HuggingFace mirror shahzaibvohra/realwaste (card says CC BY 4.0; UCI says CC BY 4.0; IEEE DataPort says CC BY-NC-SA 4.0). The UCI zip download repeatedly stalled, hence the mirror. Used only to measure, never redistributed.
