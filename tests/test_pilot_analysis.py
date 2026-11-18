import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_pilot import analyse


def simulate(n_per_arm, true_reduction, cv=0.8, seed=0):
    rng = np.random.default_rng(seed)
    sigma = math.sqrt(math.log(1 + cv**2))
    rows = []
    for arm, eff in (("control", 0.0), ("tool", true_reduction)):
        for i in range(n_per_arm):
            unit = rng.normal(0, sigma)  # a unit's persistent contamination level
            for period, shift in (("baseline", 0.0), ("followup", math.log(1 - eff))):
                share = 0.2 * math.exp(unit + shift + rng.normal(0, 0.3))
                rows.append({"unit_id": f"{arm}{i}", "arm": arm, "period": period,
                             "contaminant_kg": str(share * 100), "total_kg": "100"})
    return rows


def test_recovers_a_known_effect():
    est = analyse(simulate(150, 0.30))
    lo, hi = est["relative_reduction_95ci"]
    assert lo < 0.30 < hi and abs(est["relative_reduction"] - 0.30) < 0.08


def test_no_effect_is_not_called_significant_most_of_the_time():
    false_positives = sum(analyse(simulate(60, 0.0, seed=s))["p_value"] < 0.05 for s in range(100))
    assert false_positives <= 10  # nominal 5%, allow sampling noise


def test_interval_covers_the_truth_about_95_percent_of_the_time():
    covered = 0
    for s in range(200):
        lo, hi = analyse(simulate(40, 0.25, seed=100 + s))["relative_reduction_95ci"]
        covered += lo < 0.25 < hi
    assert 0.90 <= covered / 200 <= 0.99


def test_rejects_unusable_data():
    with pytest.raises(ValueError):
        analyse(simulate(2, 0.2))
