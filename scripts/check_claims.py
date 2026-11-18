"""Fail if a headline number in README.md no longer matches the evaluation JSON it came from.
Offline, stdlib only; runs in CI. Usage: python scripts/check_claims.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"seattle": "Seattle", "washington_dc": "Washington DC", "new_york": "New York City", "austin": "Austin",
         "minneapolis": "Minneapolis", "boston": "Boston", "san_francisco": "San Francisco"}


def crossval_rows():
    cv = json.loads((ROOT / "eval/crossval.json").read_text("utf-8"))
    pm = lambda d: f"{d['mean']*100:.1f} ± {d['sd']*100:.1f}%"
    rows = [f"| {name} | {pm(cv['cities'][cid]['forced'])} | {pm(cv['cities'][cid]['far'])} | {pm(cv['cities'][cid]['cov'])} | {pm(cv['cities'][cid]['prec'])} |"
            for cid, name in NAMES.items()]
    rc = cv["risk_control"]
    risk = [f"| {float(a)*100:.0f}% | {d['threshold_found_share']*100:.0f}% | {pm(d['coverage'])} | {pm(d['test_far'])} | {d['share_of_runs_with_test_far_above_alpha']*100:.1f}% |"
            for a, d in rc.items()]
    return rows, risk, cv


def main():
    readme = (ROOT / "README.md").read_text("utf-8")
    bad, checked = [], 0

    def need(row, what):
        nonlocal checked
        checked += 1
        if row not in readme:
            bad.append(f"{what}: README is missing {row!r}")

    fx = json.loads((ROOT / "eval/fixed_threshold.json").read_text("utf-8"))["test"]
    for cid, name in NAMES.items():
        r, k = fx[cid], fx[cid]["counts"]
        need(f"| {name} | {r['no_abstention']['false_accept_rate']*100:.1f}% | **{r['false_accept_rate']*100:.1f}%** | "
             f"{r['coverage']*100:.1f}% | {k['accept_precision']*100:.1f}% | {k['false_accepts']} of {k['non_accept_items']} |", f"TACO test {cid}")
    tn = json.loads((ROOT / "eval/trashnet.json").read_text("utf-8"))["heads"]["v1"]
    for cid, name in NAMES.items():
        r, k = tn[cid], tn[cid]["counts"]
        lo, hi = r["far_ci95"]
        need(f"| {name} | {r['false_accept_rate']*100:.1f}% ({k['false_accepts']} of {k['non_accept_items']}) | {lo*100:.1f} to {hi*100:.1f} | "
             f"{r['forced_false_accept_rate']*100:.1f}% | {r['missed_recyclable_rate']*100:.1f}% | {r['coverage']*100:.0f}% |", f"TrashNet {cid}")
    rows, risk, cv = crossval_rows()
    for r in rows + risk:
        need(r, "cross-validation")
    need(f"{cv['ece_before_temperature']['mean']*100:.1f}%", "ECE before")
    need(f"{cv['ece_after_temperature']['mean']*100:.1f}%", "ECE after")
    if bad:
        print("\n".join(bad))
        sys.exit(1)
    print(f"README matches the evaluation files: {checked} table rows checked")


if __name__ == "__main__":
    main()
