#!/usr/bin/env bash
# Demo run of the zero-dependency eval pipeline (stdlib only, no network, no API key).
set -e
cd "$(dirname "$0")/.."
PY=${PY:-python3}

echo "=== 1) sample_extractor (raw -> de-identified, stratified samples) ==="
$PY sample_extractor.py --in demo/raw.jsonl --out demo/samples_extracted.jsonl --n 8 --stratify intent

echo "=== 2) eval_runner (baseline metrics + gates) ==="
$PY eval_runner.py --samples demo/samples.jsonl --thresholds thresholds.json --out demo/results.json --print-md || echo "(exit=$? : gates failed, which is expected on the demo data)"

echo "=== 3) judge_consistency (judge vs human) ==="
$PY judge_consistency.py --a demo/judge.jsonl --b demo/human.jsonl

echo "=== 4) judge_consistency (position bias) ==="
$PY judge_consistency.py --pairs demo/position_pairs.jsonl

echo "=== 5) report_gen (client-ready markdown) ==="
$PY report_gen.py --results demo/results.json --samples demo/samples.jsonl --client "Demo Client" --lang zh --out demo/report-demo.md
$PY report_gen.py --results demo/results.json --samples demo/samples.jsonl --client "Demo Client" --lang en --out demo/report-demo-en.md

echo "=== 6) otel_genai_snippet --check (attribute names still valid?) ==="
$PY otel_genai_snippet.py --check

echo "=== done: see demo/ ==="
