import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from curbcheck import api
from curbcheck.taxonomy import ITEMS


class FakeClf:
    classes = list(ITEMS)
    threshold = 0.7

    def __init__(self, item="aluminum_can", p=0.97):
        self.item, self.p = item, p

    def predict(self, image):
        rest = (1 - self.p) / (len(ITEMS) - 1)
        return {i: (self.p if i == self.item else rest) for i in ITEMS}


def png(size=(32, 32)):
    b = io.BytesIO()
    Image.new("RGB", size, "red").save(b, "PNG")
    return b.getvalue()


@pytest.fixture
def client():
    api.app.dependency_overrides[api.get_classifier] = lambda: FakeClf()
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def post(client, data=None, ctype="image/png", city="seattle"):
    return client.post("/api/check", files={"image": ("x.png", data if data is not None else png(), ctype)}, data={"city": city})


def test_health_and_cities(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    ids = {c["id"] for c in client.get("/api/cities").json()}
    assert {"seattle", "washington_dc"} <= ids


def test_accept_with_cited_source(client):
    r = post(client)
    assert r.status_code == 200
    j = r.json()
    assert j["verdict"] == "accept" and j["source_url"].startswith("https://")
    assert len(j["top_items"]) == 3


def test_city_changes_answer():
    api.app.dependency_overrides[api.get_classifier] = lambda: FakeClf("milk_carton")
    c = TestClient(api.app)
    assert post(c, city="washington_dc").json()["verdict"] == "accept"
    assert post(c, city="seattle").json()["verdict"] == "not_sure"
    api.app.dependency_overrides.clear()


def test_uncertain_model_abstains():
    api.app.dependency_overrides[api.get_classifier] = lambda: FakeClf("aluminum_can", p=0.2)
    assert post(TestClient(api.app)).json()["verdict"] == "not_sure"
    api.app.dependency_overrides.clear()


def test_rejects_bad_input(client):
    assert post(client, city="atlantis").status_code == 404
    assert post(client, ctype="text/plain").status_code == 415
    assert post(client, data=b"not an image").status_code == 422
    assert post(client, data=b"0" * (5 * 1024 * 1024 + 10)).status_code == 413
    assert client.post("/api/check", data={"city": "seattle"}).status_code == 422


def test_oversized_declared_body_is_rejected_before_parsing(client):
    r = client.post("/api/check", content=b"x", headers={"content-length": str(50 * 1024 * 1024),
                                                         "content-type": "multipart/form-data; boundary=x"})
    assert r.status_code == 413


def test_pixel_bomb_is_rejected_from_the_header(client):
    big = io.BytesIO()
    Image.new("L", (6000, 5000)).save(big, "PNG")  # 30 megapixels, tiny when compressed
    assert len(big.getvalue()) < 1024 * 1024
    assert post(client, data=big.getvalue()).status_code == 413


def test_rate_limit_applies_per_client(client):
    api._hits.clear()
    codes = [post(client).status_code for _ in range(api.RATE_LIMIT + 2)]
    assert codes[:api.RATE_LIMIT] == [200] * api.RATE_LIMIT and codes[-1] == 429
    api._hits.clear()


def test_answer_lists_what_the_model_cannot_recognise(client):
    api._hits.clear()
    assert "batteries" in post(client).json()["not_recognised"]
