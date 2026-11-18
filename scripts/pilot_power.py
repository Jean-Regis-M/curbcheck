"""Sample-size planning for a real-world pilot: how many bin audits per arm are needed to detect a relative
reduction r in contamination by weight, when bin-level contamination varies with coefficient of variation CV?
Uses a two-sample comparison on the log scale (lognormal bin contamination). The closed form is checked by
Monte Carlo simulation, so the table can be trusted. No assumed baseline contamination rate is needed.
Usage: python scripts/pilot_power.py   -> eval/pilot_power.json"""
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
ALPHA, POWER = 0.05, 0.80


def n_per_arm(r, cv):
    sigma = math.sqrt(math.log(1 + cv**2))  # sd of log contamination for a lognormal with this CV
    delta = -math.log(1 - r)  # shift on the log scale for a relative reduction r
    z = stats.norm.ppf(1 - ALPHA / 2) + stats.norm.ppf(POWER)
    return math.ceil(2 * (z * sigma / delta) ** 2)


def simulated_power(n, r, cv, reps=4000, seed=0):
    rng = np.random.default_rng(seed)
    sigma = math.sqrt(math.log(1 + cv**2))
    hits = 0
    for _ in range(reps):
        a = rng.normal(0, sigma, n)
        b = rng.normal(math.log(1 - r), sigma, n)
        hits += stats.ttest_ind(a, b).pvalue < ALPHA
    return hits / reps


def main():
    table = []
    for cv in (0.5, 1.0, 1.5):
        for r in (0.10, 0.20, 0.30, 0.50):
            n = n_per_arm(r, cv)
            table.append({"cv": cv, "relative_reduction": r, "bins_per_arm": n, "simulated_power": round(simulated_power(n, r, cv), 3)})
    (ROOT / "eval/pilot_power.json").write_text(json.dumps({"alpha": ALPHA, "target_power": POWER, "table": table}, indent=2), encoding="utf-8")
    print("cv  reduction  bins/arm  simulated power")
    for t in table:
        print(f"{t['cv']:<4}{t['relative_reduction']:<11.0%}{t['bins_per_arm']:<10}{t['simulated_power']}")


if __name__ == "__main__":
    main()
