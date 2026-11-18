"""Analyse a CurbCheck pilot (see docs/PILOT.md) from bin-audit data. Turns the audit sheet into an effect estimate.

Input CSV columns: unit_id, arm (tool or control), period (baseline or followup), contaminant_kg, total_kg
(one row per unit and period; see docs/pilot_audit_template.csv).

Method: one observation per unit, so the unit (route or building) is the analysis cluster. The outcome is the log of the
follow-up contamination share, adjusted for the log of the same unit's baseline share (ANCOVA by ordinary least squares),
with a t interval. The effect is reported as a relative reduction in contamination by weight, 1 - exp(arm coefficient).

Usage: python scripts/analyze_pilot.py audits.csv
"""
import csv
import math
import sys

import numpy as np
from scipy import stats


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def analyse(rows):
    units = {}
    for r in rows:
        u = units.setdefault(r["unit_id"], {"arm": r["arm"]})
        share = float(r["contaminant_kg"]) / float(r["total_kg"])
        if share <= 0:
            raise ValueError(f"unit {r['unit_id']} has zero contamination in {r['period']}; the log scale needs a positive share")
        u[r["period"]] = share
    keep = [(k, v) for k, v in units.items() if "baseline" in v and "followup" in v]
    if len(keep) < 6:
        raise ValueError("need at least 6 units with both a baseline and a follow-up audit")
    y = np.array([math.log(v["followup"]) for _, v in keep])
    base = np.array([math.log(v["baseline"]) for _, v in keep])
    arm = np.array([1.0 if v["arm"] == "tool" else 0.0 for _, v in keep])
    if arm.sum() == 0 or arm.sum() == len(arm):
        raise ValueError("both arms (tool and control) are required")
    X = np.column_stack([np.ones_like(y), arm, base])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    sigma2 = resid @ resid / dof
    se = math.sqrt(sigma2 * np.linalg.inv(X.T @ X)[1, 1])
    t = stats.t.ppf(0.975, dof)
    lo, hi = beta[1] - t * se, beta[1] + t * se
    p = 2 * (1 - stats.t.cdf(abs(beta[1] / se), dof))
    return {"units": len(y), "tool_units": int(arm.sum()), "control_units": int(len(y) - arm.sum()),
            "relative_reduction": 1 - math.exp(beta[1]),
            "relative_reduction_95ci": [1 - math.exp(hi), 1 - math.exp(lo)], "p_value": float(p)}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    r = analyse(read_rows(sys.argv[1]))
    lo, hi = r["relative_reduction_95ci"]
    print(f"{r['units']} units ({r['tool_units']} tool, {r['control_units']} control)")
    print(f"relative reduction in contamination by weight: {r['relative_reduction']:.1%} (95% CI {lo:.1%} to {hi:.1%}), p = {r['p_value']:.3f}")


if __name__ == "__main__":
    main()
