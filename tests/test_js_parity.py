"""The browser's decision code (web/decision.js) must give the same answers as the Python implementation."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

from curbcheck.decision import decide
from curbcheck.rules import list_cities, load_city

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_site import head_dict

NODE = shutil.which("node")

SCRIPT = """
import { decide, headProbs } from %(decision)r;
import fs from 'node:fs';
const cases = JSON.parse(fs.readFileSync(%(cases)r, 'utf8'));
const head = JSON.parse(fs.readFileSync(%(head)r, 'utf8'));
const out = [];
for (const c of cases) {
  const rules = JSON.parse(fs.readFileSync(%(rules)r + c.city + '.json', 'utf8'));
  const p = c.probs ?? headProbs(head, c.feature);
  const d = decide(p, head.classes, rules, head.threshold);
  out.push({ verdict: d.verdict, mass: d.mass, probs: p });
}
fs.writeFileSync(%(out)r, JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_javascript_and_python_decisions_agree():
    with tempfile.TemporaryDirectory() as d:
        run_parity(Path(d))


def run_parity(tmp_path):
    head = head_dict()
    head_path = tmp_path / "head.json"
    head_path.write_text(json.dumps(head), encoding="utf-8")
    rng = np.random.default_rng(7)
    k = len(head["classes"])
    cities = list_cities()
    cases = []
    for i in range(300):
        p = rng.dirichlet(np.ones(k) * rng.choice([0.1, 0.5, 2.0]))
        cases.append({"city": cities[i % len(cities)], "probs": p.tolist()})
    feats = rng.normal(size=(60, 512))
    feats /= np.linalg.norm(feats, axis=1, keepdims=True)
    cases += [{"city": cities[i % len(cities)], "feature": feats[i].tolist()} for i in range(60)]
    cases_path, out_path, js_path = tmp_path / "cases.json", tmp_path / "out.json", tmp_path / "run.mjs"
    js_path.write_text(SCRIPT % {"decision": (ROOT / "web/decision.js").as_uri(), "cases": str(cases_path), "head": str(head_path),
                                 "rules": str(ROOT / "data/rules") + "/", "out": str(out_path)}, encoding="utf-8")
    cases_path.write_text(json.dumps(cases), encoding="utf-8")
    subprocess.run([NODE, str(js_path)], check=True)
    results = json.loads(out_path.read_text("utf-8"))
    classes = head["classes"]
    for case, js in zip(cases, results):
        py = decide(dict(zip(classes, js["probs"])), load_city(case["city"]), threshold=head["threshold"])
        assert js["verdict"] == py.verdict, (case["city"], js["mass"], py)
        assert abs(js["mass"]["accept"] - py.p_accept) < 1e-9
        assert abs(js["mass"]["reject"] - py.p_reject) < 1e-9
