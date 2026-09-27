#!/usr/bin/env python
"""Extract a 50-100 sample eval set from raw logs and de-identify it.

Usage:
  python sample_extractor.py --in raw.jsonl --out samples.jsonl --n 60 --stratify intent
  python sample_extractor.py --in raw.csv --out samples.jsonl --n 60 --csv-map question=query,answer=response
Writes samples.jsonl plus composition.json (intent / length / tool-call distribution).
"""
import argparse, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import content_tokens, dump_json, load_jsonl, norm_text

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)|(?<!\d)\+?\d[\d ()\-]{7,}\d(?!\d)")
CN_ID = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
IP = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")

def mask(text):
    if not isinstance(text, str):
        return text
    text = EMAIL.sub("[EMAIL]", text)
    text = CN_ID.sub("[CN_ID]", text)
    text = CARD.sub("[CARD]", text)
    text = PHONE.sub("[PHONE]", text)
    return IP.sub("[IP]", text)

def deep_mask(obj):
    if isinstance(obj, str):
        return mask(obj)
    if isinstance(obj, list):
        return [deep_mask(x) for x in obj]
    if isinstance(obj, dict):
        return {k: deep_mask(v) for k, v in obj.items()}
    return obj

def read_csv(path, mapping):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append({dst: r.get(src, "") for dst, src in mapping.items()})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", default="samples.jsonl")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--stratify", default=None, help="field to stratify on (e.g. intent)")
    ap.add_argument("--csv-map", default=None, help="comma list dst=src for CSV input")
    ap.add_argument("--question-field", default="question")
    ap.add_argument("--answer-field", default="answer")
    ap.add_argument("--context-field", default="contexts")
    ap.add_argument("--seed", type=int, default=20260927)
    a = ap.parse_args()

    if a.inp.lower().endswith((".jsonl", ".ndjson")):
        rows = load_jsonl(a.inp)
    else:
        rows = read_csv(a.inp, dict(x.split("=", 1) for x in (a.csv_map or "").split(",") if x))

    out, seen = [], set()
    for r in rows:
        q = r.get(a.question_field) or r.get("q") or ""
        ans = r.get(a.answer_field) or r.get("a") or ""
        if not str(q).strip():
            continue
        key = norm_text(q)
        if key in seen:
            continue
        seen.add(key)
        ctx = r.get(a.context_field)
        if isinstance(ctx, str):
            ctx = [{"id": f"c{i+1}", "text": c} for i, c in enumerate(ctx.split("\n---\n"))]
        out.append({
            "id": f"s{len(out)+1:04d}",
            "intent": (r.get(a.stratify, "unknown") if a.stratify else r.get("intent", "unknown")),
            "question": mask(str(q)),
            "answer": mask(str(ans)),
            "contexts": deep_mask(ctx or []),
            "citations": r.get("citations", []),
            "expected_facts": deep_mask(r.get("expected_facts", [])),
            "tool_calls": deep_mask(r.get("tool_calls", [])),
            "latency_ms": r.get("latency_ms"),
            "prompt_tokens": r.get("prompt_tokens"),
            "completion_tokens": r.get("completion_tokens"),
        })

    buckets = {}
    for r in out:
        buckets.setdefault(r["intent"], []).append(r)
    picked, order = [], sorted(buckets)
    while len(picked) < min(a.n, len(out)):
        progressed = False
        for k in order:
            if buckets[k]:
                picked.append(buckets[k].pop(0)); progressed = True
                if len(picked) >= a.n:
                    break
        if not progressed:
            break

    with open(a.out, "w", encoding="utf-8") as fh:
        for r in picked:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    comp = {
        "source_rows": len(rows), "kept_after_dedupe": len(out), "sampled": len(picked),
        "intent_distribution": {k: sum(1 for r in picked if r["intent"] == k) for k in order},
        "with_contexts": sum(1 for r in picked if r["contexts"]),
        "with_tool_calls": sum(1 for r in picked if r["tool_calls"]),
        "mean_question_tokens": round(sum(len(content_tokens(r["question"])) for r in picked) / max(1, len(picked)), 1),
        "pii_masked_patterns": ["EMAIL", "PHONE", "CN_ID", "CARD", "IP"],
        "seed": a.seed,
    }
    dump_json(comp, os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "composition.json"))
    print(json.dumps(comp, ensure_ascii=False, indent=2))
    print(f"\nwrote {len(picked)} samples -> {a.out}")

if __name__ == "__main__":
    main()
