import sys
from pathlib import Path

from curbcheck.rules import list_cities, load_city

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_rules import normalize


def test_normalize_handles_html_spacing_and_quotes():
    assert normalize("Paper : newspaper,  magazines") == normalize("paper: newspaper, magazines")
    assert normalize("* No Ceramics") == normalize("*No ceramics")
    assert normalize("it’s") == "it's"


def test_every_decisive_rule_has_a_real_quote_or_is_conditional():
    for cid in list_cities():
        city = load_city(cid)
        quoted = [r for r in city.rules.values() if r.quote]
        assert len(quoted) >= 8, f"{cid}: too few verbatim quotes"
        for item, rule in city.rules.items():
            if rule.quote:
                assert 15 <= len(rule.quote) <= 220, f"{cid}/{item}: quote length"
            if rule.verdict == "accept":
                assert rule.quote, f"{cid}/{item}: an accept rule must carry a verbatim quote"
