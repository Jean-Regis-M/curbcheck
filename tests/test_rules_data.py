from curbcheck.rules import list_cities, load_city


def test_shipped_cities_validate_and_cite_https_sources():
    cities = list_cities()
    assert {"seattle", "washington_dc", "new_york", "austin", "minneapolis"} <= set(cities)
    for c in cities:
        city = load_city(c)
        assert all(s.url.startswith("https://") and s.retrieved for s in city.sources)


def test_cities_genuinely_disagree():
    sea, dc = load_city("seattle"), load_city("washington_dc")
    diff = [i for i in sea.rules if sea.rules[i].verdict != dc.rules[i].verdict]
    assert len(diff) >= 3
