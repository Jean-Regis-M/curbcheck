# CurbCheck

Status: early development. Nothing below is implemented yet unless marked.

CurbCheck answers one question: *can this item go in my curbside recycling bin, in my city?*
It identifies the item from a photo, looks it up in a city-specific rules table, and answers
**accept**, **reject** or **not sure**. It abstains when its confidence is too low, because a wrong
"accept" contaminates a whole load.

Planned headline metric: false-accept rate at a fixed coverage, compared with a material-only baseline,
evaluated across datasets (studio photos vs real-world photos).

See docs/ARCHITECTURE.md for the design and docs/DATA.md for data sources and licences.
