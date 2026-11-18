// The decision rule, kept free of any network or model code so it can be tested against the Python implementation
// (tests/test_js_parity.py). Mirrors src/curbcheck/decision.py: probabilities are summed per city verdict, and the
// tool answers only if one verdict reaches the threshold.

export function softmax(z) {
  const m = Math.max(...z), e = z.map(x => Math.exp(x - m)), s = e.reduce((a, b) => a + b, 0);
  return e.map(x => x / s);
}

const dot = (a, b) => a.reduce((s, x, j) => s + x * b[j], 0);

export function headProbs(head, f) {
  // linear head, plus an optional zero-shot blend (CLIP text embeddings of the item prompts, weighted by zs_scale)
  const z = head.W.map((row, i) => (dot(row, f) + head.b[i] + (head.zs_text ? head.zs_scale * dot(head.zs_text[i], f) : 0)) / head.T);
  return softmax(z);
}

export function decide(p, classes, rules, threshold) {
  const total = p.reduce((a, b) => a + b, 0);
  const mass = { accept: 0, reject: 0, conditional: 0 };
  classes.forEach((c, i) => { mass[rules.rules[c].verdict] += p[i] / total; });
  const verdict = mass.accept >= threshold ? "accept" : mass.reject >= threshold ? "reject" : "not_sure";
  return { verdict, mass };
}
