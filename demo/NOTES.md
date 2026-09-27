# demo/: what a real run looks like (and the honesty warnings)

`bash demo/run_demo.sh` runs the full 6-step pipeline on synthetic demo data.
Zero third-party dependencies, no network, no API key.

## What the demo run produces (real output, 2026-09-27, Python 3.12)

| Step | Result |
|---|---|
| 1 sample extraction | 15 raw rows → 14 after dedup → 8 stratified samples; emails/phones/ID/card numbers replaced with `[EMAIL]` / `[PHONE]` / `[CN_ID]` / `[CARD]` |
| 2 baseline metrics + gates | faithfulness 0.625, context_precision 0.167, context_recall 0.722, answer_correctness 0.681, citation_validity 0.958, tool_arg_validity 0.667, P95 3200ms → **6/7 gates FAIL, exit code 1** (the demo data is deliberately defective: fabricated refund terms, dangling citations, missing tool args, duplicate calls) |
| 3 judge vs human | 12 labeled samples: agreement 0.833, Cohen's kappa 0.625 ("substantial") |
| 4 position bias | 10 A/B pairs swapped → flip rate 0.4 → verdict: "judge must not be used for pairwise comparison" |
| 5 report | EN + ZH reports generated, with metric table, worst samples, gates, runbook |
| 6 OTel check | `otel_genai_snippet.py --check`: verifies the 18 attribute names against a local clone of `open-telemetry/semantic-conventions-genai` (pass `--repo <path>`); skips gracefully when no clone is present |

## Honesty warnings (read before quoting any number)

- The heuristic metrics are **string overlap, not semantic judgment**.
  `context_precision 0.167` is a typical underestimate of this naive algorithm (a
  short context sentence has almost no literal overlap with the question). It does
  **not** mean retrieval is bad in a real project. Use it to watch trends and spot
  obvious breakage — never to report absolute values to a client.
- The recommended practice: settle the harness and thresholds with this kit,
  then re-run with semantic metrics (RAGAS / DeepEval) for the semantic layer.
- Gate exit-code semantics: 0 = all gates pass, 1 = at least one gate failed (CI-friendly).
- Determinism check (two consecutive runs are byte-identical):

```bash
python3 eval_runner.py --samples demo/samples.jsonl --out /tmp/a.json >/dev/null
python3 eval_runner.py --samples demo/samples.jsonl --out /tmp/b.json >/dev/null
diff /tmp/a.json /tmp/b.json && echo DETERMINISTIC_OK
```
