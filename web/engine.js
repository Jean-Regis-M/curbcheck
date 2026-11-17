// In-browser engine for the static demo: CLIP ViT-B/32 (int8 ONNX) via transformers.js + the shipped linear head + city rules.
// Mirrors src/curbcheck/decision.py. No image ever leaves the browser.
import { AutoProcessor, CLIPVisionModelWithProjection, RawImage, env }
  from "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/+esm";

env.allowLocalModels = false;
const MODEL = "Xenova/clip-vit-base-patch32";
let ready = null, head = null, cities = null;
const rulesCache = {}, featCache = new WeakMap();

async function json(url) { const r = await fetch(url); if (!r.ok) throw new Error(`${url}: ${r.status}`); return r.json(); }

export function load(onProgress) {
  if (!ready) {
    ready = (async () => {
      [head, cities] = await Promise.all([json("head.json"), json("cities.json")]);
      const cb = p => { if (p && p.status === "progress" && onProgress) onProgress(p); };
      const [processor, model] = await Promise.all([
        AutoProcessor.from_pretrained(MODEL),
        CLIPVisionModelWithProjection.from_pretrained(MODEL, { dtype: new URLSearchParams(location.search).get("dtype") || "q8", progress_callback: cb }),
      ]);
      return { processor, model };
    })();
  }
  return ready;
}

export async function listCities() { await load(); return cities; }

export async function embed(file) {
  if (featCache.has(file)) return featCache.get(file);
  const { processor, model } = await load();
  const img = await RawImage.fromBlob(file);
  const { image_embeds } = await model(await processor(img));
  const f = Array.from(image_embeds.data), n = Math.hypot(...f);
  const v = f.map(x => x / n);
  featCache.set(file, v);
  return v;
}

function softmax(z) { const m = Math.max(...z), e = z.map(x => Math.exp(x - m)), s = e.reduce((a, b) => a + b, 0); return e.map(x => x / s); }

export async function probs(file) {
  const f = await embed(file);
  const z = head.W.map((row, i) => (row.reduce((a, w, j) => a + w * f[j], 0) + head.b[i]) / head.T);
  return softmax(z);
}

export async function check(file, cityId) {
  const p = await probs(file);
  const rules = rulesCache[cityId] ||= await json(`rules/${cityId}.json`);
  const mass = { accept: 0, reject: 0, conditional: 0 };
  head.classes.forEach((c, i) => { mass[rules.rules[c].verdict] += p[i]; });
  const verdict = mass.accept >= head.threshold ? "accept" : mass.reject >= head.threshold ? "reject" : "not_sure";
  const top = head.classes.map((c, i) => [c, p[i]]).sort((a, b) => b[1] - a[1]).slice(0, 3);
  const r = x => Math.round(x * 10000) / 10000;
  return {
    city: rules.city, verdict, p_accept: r(mass.accept), p_reject: r(mass.reject), p_conditional: r(mass.conditional),
    threshold: r(head.threshold),
    top_items: top.map(([c, v]) => ({ item: c, label: head.labels[c], p: r(v), rule: rules.rules[c].verdict, note: rules.rules[c].note })),
    not_recognised: ["batteries", "greasy or food-soiled pizza boxes and paper", "food waste"],
    source_url: rules.sources[rules.rules[top[0][0]].source].url,
    disclaimer: "Runs entirely in your browser; the photo never leaves your device. Model trained on outdoor litter photos; abstains when unsure. Check your city's official page.",
  };
}
