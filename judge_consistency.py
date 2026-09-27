#!/usr/bin/env python
"""Measure how far your LLM judge can be trusted, before you trust its numbers.

Two label files (jsonl: {"id": "s1", "label": "pass"}): judge-vs-human, or judge-vs-judge.
Position-bias mode: --pairs with {"id","winner_ab","winner_ba"} (same pair, swapped order).

Usage:
  python judge_consistency.py --a judge.jsonl --b human.jsonl
  python judge_consistency.py --pairs position_bias.jsonl
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_jsonl

def kappa(pairs):
    labels = sorted({l for p in pairs for l in p})
    if len(labels) < 2 or not pairs:
        return None, None
    n = len(pairs); idx = {l: i for i, l in enumerate(labels)}
    m = [[0] * len(labels) for _ in labels]
    for x, y in pairs:
        m[idx[x]][idx[y]] += 1
    agree = sum(m[i][i] for i in range(len(labels))) / n
    pe = sum((sum(m[i]) / n) * (sum(m[r][i] for r in range(len(labels))) / n) for i in range(len(labels)))
    return agree, (None if pe == 1 else (agree - pe) / (1 - pe))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a"); ap.add_argument("--b")
    ap.add_argument("--pairs", help="jsonl with winner_ab / winner_ba")
    a = ap.parse_args()

    if a.pairs:
        rows = load_jsonl(a.pairs)
        flips = [r for r in rows if r.get("winner_ab") != r.get("winner_ba")]
        rate = len(flips) / len(rows) if rows else 0
        verdict = ("位置偏差可忽略(<10%)" if rate < 0.10
                   else "需交换位置取平均(10-30%)" if rate < 0.30
                   else "判官不可用于成对比较(>=30%)")
        print(json.dumps({"pairs": len(rows), "position_flips": len(flips),
                          "flip_rate": round(rate, 4), "verdict": verdict}, ensure_ascii=False, indent=2))
        return 0

    la = {r["id"]: r["label"] for r in load_jsonl(a.a)}
    lb = {r["id"]: r["label"] for r in load_jsonl(a.b)}
    ids = sorted(set(la) & set(lb))
    if not ids:
        raise SystemExit("no overlapping ids between the two label files")
    pairs = [(la[i], lb[i]) for i in ids]
    agree, k = kappa(pairs)
    out = {
        "compared": len(ids), "agreement": round(agree, 4),
        "cohen_kappa": None if k is None else round(k, 4),
        "interpretation": ("几乎一致(>=0.8)" if (k or 0) >= 0.8 else
                           "基本一致(0.6-0.8)" if (k or 0) >= 0.6 else
                           "脆弱(<0.6)：不得单独用作发布门禁"),
        "disagreement_ids": [i for i in ids if la[i] != lb[i]][:20],
        "note": "k<0.6 时先修 rubric 或换判官模型；确定性规则（如引用 ID 不存在）可直接设硬门禁。",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
