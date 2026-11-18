"""Markdown blocks for the README, generated from the evaluation files so the numbers cannot drift.

`python scripts/readme_blocks.py` rewrites every <!-- block:NAME:start --> ... <!-- block:NAME:end --> region in README.md.
scripts/check_claims.py verifies the README still matches these blocks (CI).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"seattle": "Seattle", "washington_dc": "Washington DC", "new_york": "New York City", "austin": "Austin",
         "minneapolis": "Minneapolis", "boston": "Boston", "san_francisco": "San Francisco"}
KEY = "zs2.0|None|cov0.55"  # the shipped operating point


def jl(name):
    return json.loads((ROOT / "eval" / name).read_text("utf-8"))


def pc(x, d=1):
    return f"{x * 100:.{d}f}%"


def rng(vals, d=1):
    lo, hi = min(vals), max(vals)
    return f"{lo * 100:.{d}f}% to {hi * 100:.{d}f}%"


def unseen_table(v3, which, v1_name):
    key = {"TrashNet": "A_train_TACO_RealWaste_test_TrashNet", "RealWaste": "B_train_TACO_TrashNet_test_RealWaste"}[which]
    rows = ["| City | False accepts, forced yes/no | False accepts, shipped model | Recyclables wrongly rejected, shipped | Share answered, shipped | False accepts, earlier model | Recyclables wrongly rejected, earlier | Share answered, earlier |",
            "|---|---|---|---|---|---|---|---|"]
    for cid, name in NAMES.items():
        r, b = v3[key][KEY]["cities"][cid], v3["v1_baseline_same_sets"][v1_name][cid]
        rows.append(f"| {name} | {pc(r['forced_false_accept_rate'])} | **{pc(r['false_accept_rate'])}** | {pc(r['missed_recyclable_rate'], 2)} | {pc(r['coverage'])} | "
                    f"{pc(b['false_accept_rate'])} | {pc(b['missed_recyclable_rate'])} | {pc(b['coverage'])} |")
    return "\n".join(rows)


def in_domain_table(v3):
    F = v3["F_all_three_in_domain"][KEY]
    rows = ["| Held-out part (Seattle) | False accepts, forced yes/no | False accepts, shipped | Recyclables wrongly rejected | Share answered |", "|---|---|---|---|---|"]
    for ds, label in (("TACO_test", "TACO litter photos (306 crops)"), ("TrashNet_test", "TrashNet studio photos"), ("RealWaste_test", "RealWaste landfill photos")):
        r = F[ds]["seattle"]
        rows.append(f"| {label} | {pc(r['forced_false_accept_rate'])} | **{pc(r['false_accept_rate'])}** | {pc(r['missed_recyclable_rate'], 2)} | {pc(r['coverage'])} |")
    return "\n".join(rows)


def summary_sentence(v3):
    t, r = v3["A_train_TACO_RealWaste_test_TrashNet"][KEY]["cities"], v3["B_train_TACO_TrashNet_test_RealWaste"][KEY]["cities"]
    tb, rb = v3["v1_baseline_same_sets"]["TrashNet"], v3["v1_baseline_same_sets"]["RealWaste"]
    g = lambda d, k: [d[c][k] for c in NAMES]
    return (f"On photos from a dataset it never saw, the shipped model wrongly accepts {rng(g(t, 'false_accept_rate'))} (TrashNet) and "
            f"{rng(g(r, 'false_accept_rate'))} (RealWaste) of non-recyclable items, and wrongly rejects {rng(g(t, 'missed_recyclable_rate'), 2)} and "
            f"{rng(g(r, 'missed_recyclable_rate'), 2)} of recyclable ones. The earlier TACO-only model wrongly rejected {rng(g(tb, 'missed_recyclable_rate'))} and "
            f"{rng(g(rb, 'missed_recyclable_rate'))}. The price: it answers {rng(g(t, 'coverage'), 0)} of TrashNet photos and {rng(g(r, 'coverage'), 0)} of RealWaste photos, "
            f"against {rng(g(tb, 'coverage'), 0)} and {rng(g(rb, 'coverage'), 0)} for the earlier model.")


def web_table():
    p = ROOT / "eval/v3_web.json"
    if not p.exists():
        return "_The in-browser model's multi-domain evaluation has not been run yet._"
    w = json.loads(p.read_text("utf-8"))
    rows = ["| City | TrashNet (unseen): false accepts / recyclables wrongly rejected / answered | RealWaste (unseen): false accepts / recyclables wrongly rejected / answered |", "|---|---|---|"]
    for cid, name in NAMES.items():
        t = w["A_train_TACO_RealWaste_test_TrashNet"][KEY]["cities"][cid]
        r = w["B_train_TACO_TrashNet_test_RealWaste"][KEY]["cities"][cid]
        rows.append(f"| {name} | {pc(t['false_accept_rate'])} / {pc(t['missed_recyclable_rate'], 2)} / {pc(t['coverage'], 0)} | {pc(r['false_accept_rate'])} / {pc(r['missed_recyclable_rate'], 2)} / {pc(r['coverage'], 0)} |")
    return "\n".join(rows)


def extras():
    cd, hz = jl("city_disagreement.json"), jl("hazard_check.json")
    lat = jl("latency.json") if (ROOT / "eval/latency.json").exists() else None
    lines = [(f"- **Same photo, different answers.** Across the seven cities, the answer is not the same for {pc(cd['TrashNet']['cities_not_all_agree'], 0)} of TrashNet photos, "
             f"{pc(cd['RealWaste']['cities_not_all_agree'], 0)} of RealWaste photos and {pc(cd['TACO_test']['cities_not_all_agree'], 0)} of held-out TACO crops. "
             f"Most of these are \"recycle it\" in one city and \"not sure\" in another (the page is silent); one city saying \"recycle it\" while another says \"not recyclable\" happens for "
             f"{pc(cd['TACO_test']['accept_in_one_reject_in_another'])} of TACO crops, {pc(cd['TrashNet']['accept_in_one_reject_in_another'])} of TrashNet and {pc(cd['RealWaste']['accept_in_one_reject_in_another'])} of RealWaste.")]
    h = hz["items"]
    lines.append(f"- **The three item types without enough training data** (tiny smoke test, not evidence): of the answers over all seven cities, "
                 f"{h['battery']['verdicts_over_all_city_answers'].get('accept', 0)} of {sum(h['battery']['verdicts_over_all_city_answers'].values())} for the {h['battery']['crops']} battery crops and "
                 f"{h['food_waste']['verdicts_over_all_city_answers'].get('accept', 0)} of {sum(h['food_waste']['verdicts_over_all_city_answers'].values())} for the {h['food_waste']['crops']} food-waste crops were wrongly \"recycle it\"; "
                 f"for the {h['pizza_box_greasy']['crops']} greasy pizza boxes it was {h['pizza_box_greasy']['verdicts_over_all_city_answers'].get('accept', 0)} of {sum(h['pizza_box_greasy']['verdicts_over_all_city_answers'].values())} "
                 f"({pc(h['pizza_box_greasy']['share_wrongly_accepted'], 0)}), because a greasy box can look like clean cardboard.")
    if lat:
        tp = lat["pytorch_cpu_per_photo"]
        s = f"- **Speed.** On this laptop CPU (no GPU) the PyTorch model takes a median of {tp['median_ms']:.0f} ms per photo (95th percentile {tp['p95_ms']:.0f} ms, {tp['images']} photos)"
        if "browser_per_photo_model_loaded" in lat:
            b = lat["browser_per_photo_model_loaded"]
            s += f"; in the browser, with the model loaded, a median of {b['median_ms'] / 1000:.1f} s from choosing a photo to the verdict ({b['photos']} photos)"
        lines.append(s + ".")
    return "\n".join(lines)


def blocks():
    v3 = jl("v3.json")
    return {"summary": summary_sentence(v3), "unseen-trashnet": unseen_table(v3, "TrashNet", "TrashNet"),
            "unseen-realwaste": unseen_table(v3, "RealWaste", "RealWaste"), "in-domain": in_domain_table(v3),
            "web": web_table(), "extras": extras()}


def render(text):
    for name, body in blocks().items():
        pat = re.compile(rf"(<!-- block:{name}:start -->\n).*?(\n<!-- block:{name}:end -->)", re.DOTALL)
        if not pat.search(text):
            raise SystemExit(f"README has no block named {name}")
        text = pat.sub(lambda m: m.group(1) + body + m.group(2), text)
    return text


if __name__ == "__main__":
    p = ROOT / "README.md"
    p.write_text(render(p.read_text("utf-8")), encoding="utf-8")
    print("README blocks rendered:", ", ".join(blocks()))
    sys.exit(0)
