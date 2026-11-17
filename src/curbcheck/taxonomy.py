"""Item taxonomy shared by the classifier and the city rule tables."""

ITEMS: dict[str, str] = {
    "aluminum_can": "Aluminum beverage can",
    "steel_can": "Steel or tin food can",
    "glass_bottle_jar": "Glass bottle or jar",
    "plastic_bottle": "Plastic bottle (PET/HDPE, with neck)",
    "plastic_tub": "Plastic tub or tray (yogurt, takeout)",
    "plastic_bag_film": "Plastic bag or film wrap",
    "cardboard_box": "Clean cardboard box",
    "pizza_box_greasy": "Greasy pizza box",
    "paper_clean": "Clean paper or newspaper",
    "paper_cup": "Paper coffee cup (plastic-lined)",
    "milk_carton": "Milk or juice carton",
    "foam": "Polystyrene foam",
    "aluminum_foil": "Aluminum foil or tray",
    "food_waste": "Food waste",
    "battery": "Battery",
    "other_trash": "Other non-recyclable trash",
}

VERDICTS = ("accept", "reject", "conditional")
