#!/usr/bin/env python
"""Zero-dependency baseline metrics for a RAG / agent eval set.

Heuristic (string-overlap) metrics by default: no API key, no network, no vendor SDK.
That makes this the right Day-2 baseline; swap in RAGAS / DeepEval for semantic metrics
once the harness and thresholds are agreed (see README.md).

Usage:
  python eval_runner.py --samples samples.jsonl --out results.json --print-md
  python eval_runner.py --samples samples.jsonl --thresholds thresholds.json --out results.json
Exit code: 0 = all gates met, 1 = at least one gate failed (CI-friendly).
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import content_tokens, dump_json, load_jsonl, overlap, percentile, sentences

DEFAULT_THRESHOLDS = {
    "faithfulness": 0.85,
    "context_precision": 0.5,
    "context_recall": 0.8,
    "answer_correctness": 0.8,
    "citation_validity": 1.0,
    "tool_arg_validity": 0.98,
    "p95_latency_ms": 8000,
}

def metric_faithfulness(s):
    ctx = " ".join(c.get("text", "") for c in s.get("contexts") or [])
    ctx_tok = set(content_tokens(ctx))
    sents = sentences(s.get("answer", ""))
    if not sents:
        return None, {"sentences": 0, "unsupported": []}
    unsupported = [t for t in sents if overlap(content_tokens(t), ctx_tok) < 0.5]
    return (len(sents) - len(unsupported)) / len(sents), {"sentences": len(sents), "unsupported": unsupported[:5]}

def metric_context_precision(s):
    ctxs = s.get("contexts") or []
    if not ctxs:
        return None, {"retrieved": 0}
    q_tok = set(content_tokens(s.get("question", "")))
    rel = [c for c in ctxs if overlap(content_tokens(c.get("text", "")), q_tok) >= 0.3]
    return len(rel) / len(ctxs), {"retrieved": len(ctxs), "relevant": len(rel)}

def metric_recall_and_correctness(s):
    facts = s.get("expected_facts") or []
    if not facts:
        return None
    ctx_tok = set(content_tokens(" ".join(c.get("text", "") for c in s.get("contexts") or [])))
    ans_tok = set(content_tokens(s.get("answer", "")))
    rec = sum(1 for f in facts if overlap(content_tokens(f), ctx_tok) >= 0.6) / len(facts)
    cor = sum(1 for f in facts if overlap(content_tokens(f), ans_tok) >= 0.6) / len(facts)
    return rec, cor

def metric_citations(s):
    cites = s.get("citations") or []
    ids = {c.get("id") for c in s.get("contexts") or []}
    if not cites:
        return None, {"citations": 0}
    bad = [c for c in cites if c not in ids]
    return (len(cites) - len(bad)) / len(cites), {"citations": len(cites), "dangling": bad}

def metric_tools(s):
    calls = s.get("tool_calls") or []
    if not calls:
        return None, {"calls": 0}
    missing, dup, seen = 0, 0, set()
    for c in calls:
        req = c.get("required_args") or []
        args = c.get("args") or {}
        if any(r not in args for r in req):
            missing += 1
        key = (c.get("name"), json.dumps(args, sort_keys=True, ensure_ascii=False))
        if key in seen:
            dup += 1
        seen.add(key)
    n = len(calls)
    return (n - missing) / n, {"calls": n, "missing_required_args": missing, "duplicate_calls": dup}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True)
    ap.add_argument("--out", default="results.json")
    ap.add_argument("--thresholds", default=None)
    ap.add_argument("--print-md", action="store_true")
    a = ap.parse_args()

    th = dict(DEFAULT_THRESHOLDS)
    if a.thresholds:
        th.update(json.load(open(a.thresholds, encoding="utf-8")))
    samples = load_jsonl(a.samples)

    per, agg = [], {}
    keys = ["faithfulness", "context_precision", "context_recall", "answer_correctness",
            "citation_validity", "tool_arg_validity"]
    buckets = {k: [] for k in keys}
    latencies, costs = [], []
    tools = {"calls": 0, "missing": 0, "dup": 0}

    for s in samples:
        rec = {"id": s.get("id"), "intent": s.get("intent", "unknown"), "detail": {}}
        f, d = metric_faithfulness(s); rec["faithfulness"] = f; rec["detail"]["faithfulness"] = d
        if f is not None: buckets["faithfulness"].append(f)
        c, d = metric_context_precision(s); rec["context_precision"] = c; rec["detail"]["context_precision"] = d
        if c is not None: buckets["context_precision"].append(c)
        rc = metric_recall_and_correctness(s)
        if rc:
            rec["context_recall"], rec["answer_correctness"] = rc
            buckets["context_recall"].append(rc[0]); buckets["answer_correctness"].append(rc[1])
        cv, d = metric_citations(s); rec["citation_validity"] = cv; rec["detail"]["citation_validity"] = d
        if cv is not None: buckets["citation_validity"].append(cv)
        tv, d = metric_tools(s); rec["tool_arg_validity"] = tv; rec["detail"]["tool_arg_validity"] = d
        if tv is not None:
            buckets["tool_arg_validity"].append(tv)
            tools["calls"] += d["calls"]; tools["missing"] += d["missing_required_args"]; tools["dup"] += d["duplicate_calls"]
        if s.get("latency_ms") is not None: latencies.append(float(s["latency_ms"]))
        if s.get("prompt_tokens") is not None or s.get("completion_tokens") is not None:
            costs.append(int(s.get("prompt_tokens") or 0) + int(s.get("completion_tokens") or 0))
        per.append(rec)

    for k in keys:
        v = buckets[k]
        agg[k] = round(sum(v) / len(v), 4) if v else None
        agg[k + "_n"] = len(v)
    agg["p50_latency_ms"] = percentile(latencies, 50)
    agg["p95_latency_ms"] = percentile(latencies, 95)
    agg["mean_tokens_per_sample"] = round(sum(costs) / len(costs), 1) if costs else None
    agg["tool_calls_total"] = tools["calls"]
    agg["tool_calls_missing_args"] = tools["missing"]
    agg["tool_calls_duplicate"] = tools["dup"]
    agg["samples"] = len(samples)

    gates = []
    for k, limit in th.items():
        val = agg.get(k)
        if val is None:
            gates.append({"metric": k, "value": None, "limit": limit, "status": "not_applicable"})
        else:
            ok = (val <= limit) if k == "p95_latency_ms" else (val >= limit)
            gates.append({"metric": k, "value": val, "limit": limit, "status": "pass" if ok else "FAIL"})

    dump_json({"generated_by": "eval_runner.py (heuristic baseline, no LLM calls)",
               "samples_file": os.path.basename(a.samples),
               "aggregate": agg, "gates": gates, "per_sample": per}, a.out)

    if a.print_md:
        print("| 指标 | 值 | 阈值 | 判定 | 样本数 |")
        print("|---|---|---|---|---|")
        for g in gates:
            print(f"| {g['metric']} | {g['value']} | {g['limit']} | {g['status']} | {agg.get(g['metric'] + '_n', '')} |")
        print(f"\nP50/P95 latency: {agg['p50_latency_ms']}/{agg['p95_latency_ms']} ms; mean tokens/sample: {agg['mean_tokens_per_sample']}")
        print(f"tool calls: {agg['tool_calls_total']} (missing args {agg['tool_calls_missing_args']}, duplicates {agg['tool_calls_duplicate']})")

    failed = [g for g in gates if g["status"] == "FAIL"]
    print(f"results -> {a.out} | gates failed: {len(failed)}/{len(gates)}", file=sys.stderr)
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
