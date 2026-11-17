"""Generate data/rules/*.json from curated entries. Run: python scripts/build_rules.py
Each verdict was read from the cited official page on the retrieval date; 'conditional' means the
page is silent or ambiguous for that item, so the system must not auto-accept or auto-reject it."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "rules"
D = "2026-11-17"

SEATTLE = {
    "city": "Seattle, WA", "program": "Seattle Public Utilities curbside",
    "sources": [{"url": "https://www.seattle.gov/utilities/your-services/collection-and-disposal/how-to-sort-at-home", "retrieved": D}],
    "rules": {
        "aluminum_can": ("accept", "Metal cans: aluminum cans"),
        "steel_can": ("accept", "Metal cans: steel cans"),
        "glass_bottle_jar": ("accept", "Glass bottles and jars; no drink glasses or window glass"),
        "plastic_bottle": ("accept", "Plastic containers, bottles, jugs and tubs"),
        "plastic_tub": ("accept", "Yogurt and sauce tubs; dirty food containers go in garbage"),
        "plastic_bag_film": ("reject", "Plastic bags, wraps and wrappers go in garbage"),
        "cardboard_box": ("accept", "Flatten cardboard; labels and tape are okay"),
        "pizza_box_greasy": ("reject", "Food-soiled pizza boxes go in compost, not recycling"),
        "paper_clean": ("accept", "Newspaper, magazines, paperboard, office paper"),
        "paper_cup": ("conditional", "Page does not list coated paper cups; check the Where Does It Go tool"),
        "milk_carton": ("conditional", "Cartons not named on this page; check the Where Does It Go tool"),
        "foam": ("reject", "Foam trays, instant food containers and blocks go in garbage"),
        "aluminum_foil": ("accept", "Clean foil trays are accepted; clean foil only"),
        "food_waste": ("reject", "Food scraps go in compost"),
        "battery": ("reject", "Batteries need special collection"),
        "other_trash": ("reject", "Garbage"),
    },
}
DC = {
    "city": "Washington, DC", "program": "DPW single-stream curbside",
    "sources": [{"url": "https://zerowaste.dc.gov/page/recycle-residents", "retrieved": D}],
    "rules": {
        "aluminum_can": ("accept", "Steel and aluminum bottles, cans, containers; clean and empty"),
        "steel_can": ("accept", "Steel and aluminum bottles, cans, containers; no paint cans"),
        "glass_bottle_jar": ("accept", "Glass bottles and jars; no ceramics"),
        "plastic_bottle": ("accept", "Plastic bottles and lids; clean and empty"),
        "plastic_tub": ("accept", "Plastic cups and containers; clean and empty"),
        "plastic_bag_film": ("reject", "Plastic bags, wraps and film of any kind are not accepted"),
        "cardboard_box": ("accept", "Flattened cardboard; empty and flatten boxes"),
        "pizza_box_greasy": ("conditional", "Page does not state a rule for greasy pizza boxes"),
        "paper_clean": ("accept", "Newspaper, magazines, junk mail, office paper; no tissues"),
        "paper_cup": ("conditional", "Page lists paper 'cups and containers' without describing coatings"),
        "milk_carton": ("accept", "Milk, juice and soup cartons are accepted"),
        "foam": ("reject", "No foam polystyrene"),
        "aluminum_foil": ("conditional", "Page lists aluminum containers but not foil specifically"),
        "food_waste": ("reject", "Not a recyclable; keep out of the recycling bin"),
        "battery": ("reject", "Batteries and electronics are kept out of recycling"),
        "other_trash": ("reject", "Not accepted"),
    },
}

def emit(cid, d):
    d = dict(d)
    d["rules"] = {k: {"verdict": v[0], "note": v[1], "source": 0} for k, v in d["rules"].items()}
    (OUT / f"{cid}.json").write_text(json.dumps(d, indent=2), encoding="utf-8")

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    emit("seattle", SEATTLE)
    emit("washington_dc", DC)
