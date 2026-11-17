"""Mapping from TACO categories to the CurbCheck item taxonomy. Unmapped categories are dropped."""

TACO_TO_ITEM: dict[str, str] = {
    "Drink can": "aluminum_can",
    "Food Can": "steel_can",
    "Glass bottle": "glass_bottle_jar", "Glass jar": "glass_bottle_jar",
    "Clear plastic bottle": "plastic_bottle", "Other plastic bottle": "plastic_bottle",
    "Disposable food container": "plastic_tub", "Spread tub": "plastic_tub",
    "Tupperware": "plastic_tub", "Other plastic container": "plastic_tub",
    "Plastic film": "plastic_bag_film", "Single-use carrier bag": "plastic_bag_film",
    "Garbage bag": "plastic_bag_film", "Polypropylene bag": "plastic_bag_film",
    "Crisp packet": "plastic_bag_film", "Other plastic wrapper": "plastic_bag_film",
    "Corrugated carton": "cardboard_box",
    "Pizza box": "pizza_box_greasy",
    "Normal paper": "paper_clean", "Magazine paper": "paper_clean",
    "Paper cup": "paper_cup",
    "Drink carton": "milk_carton",
    "Styrofoam piece": "foam", "Foam food container": "foam", "Foam cup": "foam",
    "Aluminium foil": "aluminum_foil",
    "Food waste": "food_waste",
    "Battery": "battery",
    "Cigarette": "other_trash", "Plastic straw": "other_trash", "Plastic utensils": "other_trash",
    "Broken glass": "other_trash", "Tissues": "other_trash", "Rope & strings": "other_trash",
}
