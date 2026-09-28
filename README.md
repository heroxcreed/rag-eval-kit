# rag-eval-kit

> **Need a reliability checkup for your RAG / AI-agent system?** I do fixed-scope,
> email-based reliability audits — no calls, no meetings.
> Contact: **heroxcreed861@gmail.com**

A zero-dependency evaluation pipeline for RAG and tool-using agent systems:
sample → baseline metrics → quality gates → client-readable report.
Python standard library only. No API key, no network, no vendor SDK.

## Why this exists

Before you pay for a semantic eval stack (RAGAS / DeepEval / TruLens), you need
three things settled: **what "correct" means for your system, which metrics gate
a release, and whether your judge agrees with your humans.** This kit gives you
that baseline in one afternoon, and the harness stays useful afterwards as a CI
regression gate.

## 60-second start

```bash
git clone https://github.com/heroxcreed/rag-eval-kit.git
cd rag-eval-kit
bash demo/run_demo.sh        # full 6-step pipeline on synthetic demo data
```

## The pipeline

```bash
# 1) Sample + de-identify (from logs/CSV: 50-100 rows, deduped, stratified by intent)
python3 sample_extractor.py --in raw.jsonl --out samples.jsonl --n 60 --stratify intent

# 2) Baseline metrics + gates (exit 1 = a gate failed → block the release)
python3 eval_runner.py --samples samples.jsonl --thresholds thresholds.json \
    --out results.json --print-md

# 3) Judge trustworthiness (judge vs human; report Cohen's kappa)
python3 judge_consistency.py --a judge.jsonl --b human.jsonl
python3 judge_consistency.py --pairs position_bias.jsonl   # A/B flip rate

# 4) Client-readable report
python3 report_gen.py --results results.json --samples samples.jsonl \
    --client "Acme" --lang en --out report.md

# 5) OTel GenAI instrumentation snippet (+ attribute-name freshness check)
python3 otel_genai_snippet.py --check
```

## Scripts

| Script | What it does |
|---|---|
| `sample_extractor.py` | Stratified sampling + PII de-identification (emails/phones/IDs/cards → placeholders) |
| `eval_runner.py` | Heuristic baseline metrics (faithfulness, context precision/recall, answer correctness, citation validity, tool-arg validity, latency) + threshold gates; exit code 1 on failure |
| `judge_consistency.py` | Judge-vs-human agreement (Cohen's kappa) and position-bias flip rate |
| `report_gen.py` | Markdown report from results: metric table, worst samples, gates, runbook |
| `otel_genai_snippet.py` | Print/check OpenTelemetry GenAI semantic-convention attributes for tracing |
| `common.py` | Shared helpers (tokenization, JSONL I/O, overlap) |
| `thresholds.json` | Default gate thresholds (tune to your traffic before enforcing) |

## Docs

- `docs/failure-taxonomy.md` — failure-mode catalog for RAG + agents (symptom → detection → fix)
- `docs/metric-spec.md` — how to pick 4–6 metrics and what each one gates
- `demo/NOTES.md` — what the demo run actually produced, and the honesty warnings
  (heuristic metrics are string-overlap, not semantic judgment — read this before
  quoting any number)

## Sample format (`samples.jsonl`, one JSON per line)

```json
{"id":"s001","intent":"refund","question":"...","answer":"...",
 "contexts":[{"id":"c1","text":"..."}],"citations":["c1"],
 "expected_facts":["..."],"tool_calls":[{"name":"lookup","args":{"id":1},"required_args":["id"]}],
 "latency_ms":1200,"prompt_tokens":800,"completion_tokens":200}
```

## Honesty notes

- The default metrics are **heuristics** (string overlap). They catch obvious
  breakage and trends; they do not replace semantic judges. Settle the harness
  and thresholds first, then swap in RAGAS / DeepEval for the semantic layer.
- Two consecutive runs are deterministic (`eval_runner.py` has no randomness);
  verify with the diff check in `demo/NOTES.md`.
- The demo data is synthetic and deliberately defective — see `demo/NOTES.md`.

## License

MIT — see `LICENSE`. Maintained by
[heroxcreed](https://github.com/heroxcreed).
