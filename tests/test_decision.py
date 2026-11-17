import pytest

from curbcheck.decision import decide
from curbcheck.rules import CityRules, Rule, Source
from curbcheck.taxonomy import ITEMS


def make_city(overrides=None):
    rules = {i: Rule(verdict="reject", source=0) for i in ITEMS}
    for i in ("aluminum_can", "steel_can", "glass_bottle_jar", "plastic_bottle"):
        rules[i] = Rule(verdict="accept", source=0)
    rules["plastic_bag_film"] = Rule(verdict="conditional", note="store drop-off", source=0)
    for k, v in (overrides or {}).items():
        rules[k] = Rule(verdict=v, source=0)
    return CityRules(city="T", program="t", sources=[Source(url="http://x", retrieved="2026-01-01")], rules=rules)


def onehot(item, p=0.97):
    rest = (1 - p) / (len(ITEMS) - 1)
    return {i: (p if i == item else rest) for i in ITEMS}


def test_confident_accept():
    assert decide(onehot("aluminum_can"), make_city()).verdict == "accept"


def test_confident_reject():
    assert decide(onehot("foam"), make_city()).verdict == "reject"


def test_split_between_accept_and_reject_abstains():
    probs = {i: 0.0 for i in ITEMS}
    probs["aluminum_can"], probs["foam"] = 0.5, 0.5
    assert decide(probs, make_city()).verdict == "not_sure"


def test_items_sharing_a_verdict_do_not_cause_abstention():
    probs = {i: 0.0 for i in ITEMS}
    probs["aluminum_can"], probs["steel_can"], probs["glass_bottle_jar"] = 0.4, 0.3, 0.3
    assert decide(probs, make_city()).verdict == "accept"


def test_conditional_item_never_auto_accepts():
    assert decide(onehot("plastic_bag_film"), make_city()).verdict == "not_sure"


def test_city_rules_change_the_verdict():
    assert decide(onehot("foam"), make_city({"foam": "accept"})).verdict == "accept"


def test_unnormalised_probs_are_normalised():
    probs = {i: 0.0 for i in ITEMS}
    probs["aluminum_can"] = 5.0
    assert decide(probs, make_city()).verdict == "accept"


def test_invalid_probs_rejected():
    with pytest.raises(ValueError):
        decide({"aluminum_can": 0.0}, make_city())
    with pytest.raises(ValueError):
        decide({"nonsense": 1.0}, make_city())


def test_city_must_cover_taxonomy_and_cite_sources():
    with pytest.raises(ValueError):
        CityRules(city="T", program="t", sources=[Source(url="u", retrieved="d")],
                  rules={"foam": Rule(verdict="reject", source=0)})
    rules = {i: Rule(verdict="reject", source=3) for i in ITEMS}
    with pytest.raises(ValueError):
        CityRules(city="T", program="t", sources=[Source(url="u", retrieved="d")], rules=rules)
