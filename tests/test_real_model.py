"""End-to-end checks with the real encoder and the shipped head (skipped when torch or open_clip are not installed, as in CI)."""
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("open_clip")

from PIL import Image

from curbcheck.decision import decide
from curbcheck.model import ClipHeadClassifier
from curbcheck.rules import load_city

SAMPLES = Path(__file__).resolve().parents[1] / "web" / "samples"


@pytest.fixture(scope="module")
def clf():
    return ClipHeadClassifier()


def verdict(clf, name, city="seattle"):
    probs = clf.predict(Image.open(SAMPLES / f"{name}.jpg"))
    return decide(probs, load_city(city), threshold=clf.threshold).verdict


def test_probabilities_are_a_distribution(clf):
    p = clf.predict(Image.open(SAMPLES / "glass20.jpg"))
    assert abs(sum(p.values()) - 1) < 1e-6 and len(p) == len(clf.classes)


def test_a_clear_recyclable_is_accepted(clf):
    assert verdict(clf, "glass20") == "accept"


def test_non_recyclable_trash_is_never_accepted(clf):
    assert verdict(clf, "trash7") != "accept"  # it may abstain; it must not tell anyone to recycle it


def test_every_sample_gets_a_valid_verdict_in_every_city(clf):
    for sample in SAMPLES.glob("*.jpg"):
        for city in ("seattle", "washington_dc", "new_york", "austin", "minneapolis", "boston", "san_francisco"):
            assert verdict(clf, sample.stem, city) in {"accept", "reject", "not_sure"}
