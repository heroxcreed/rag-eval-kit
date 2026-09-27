#!/usr/bin/env python
"""Turn results.json + samples.jsonl into a client-ready audit report (markdown).

Usage:
  python report_gen.py --results results.json --samples samples.jsonl --client "Acme" --out report.md --lang zh
"""
import argparse, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_jsonl

def worst(samples, per, key, n=3):
    rows = [(r["id"], r.get(key)) for r in per if r.get(key) is not None]
    rows.sort(key=lambda t: t[1])
    by_id = {s.get("id"): s for s in samples}
    out = []
    for sid, val in rows[:n]:
        s = by_id.get(sid, {})
        out.append((sid, val, s.get("intent", "unknown"),
                    (s.get("question") or "")[:60], (s.get("answer") or "")[:80]))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True); ap.add_argument("--samples", required=True)
    ap.add_argument("--client", default="Client"); ap.add_argument("--out", default="report.md")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"])
    a = ap.parse_args()
    res = json.load(open(a.results, encoding="utf-8"))
    samples = load_jsonl(a.samples)
    agg, gates, per = res["aggregate"], res["gates"], res["per_sample"]
    failed = [g for g in gates if g["status"] == "FAIL"]
    zh = a.lang == "zh"
    L = []
    L.append(f"# {'RAG / Agent 可靠性体检报告' if zh else 'RAG / Agent Reliability Audit Report'}：{a.client}")
    L.append(f"\n> {'样本量' if zh else 'samples'}: {agg['samples']} · {'样本文件' if zh else 'file'}: {res['samples_file']} · "
             f"{'计算方式' if zh else 'computed by'}: {res.get('generated_by')}\n")
    L.append(f"## 1. {'执行摘要' if zh else 'Executive summary'}")
    if failed:
        L.append(("1. 当前有 " + str(len(failed)) + " 项指标未达阈值：" if zh else
                  "1. " + str(len(failed)) + " metric(s) below threshold: ")
                 + ", ".join(f"{g['metric']}={g['value']} (<{g['limit']})" for g in failed))
    else:
        L.append("1. " + ("全部指标达到阈值；建议把当前值冻结为回归基线。" if zh else
                          "All metrics meet thresholds; freeze current values as the regression baseline."))
    wf = worst(samples, per, "faithfulness", 3)
    if wf:
        L.append(("2. 忠实度最差样本：" if zh else "2. Lowest faithfulness: ")
                 + ", ".join(f"{sid}({val:.2f},{it})" for sid, val, it, _, _ in wf))
    if agg.get("p95_latency_ms"):
        L.append(f"3. P95 {'延迟' if zh else 'latency'} {agg['p95_latency_ms']} ms · "
                 f"{'平均' if zh else 'mean'} tokens/{'样本' if zh else 'sample'} {agg['mean_tokens_per_sample']}")
    L.append(f"\n## 2. {'范围与方法' if zh else 'Scope and method'}")
    L.append(f"- {'样本构成' if zh else 'Sample composition'}: " +
             ", ".join(f"{k}={v}" for k, v in Counter(s.get('intent', 'unknown') for s in samples).most_common(8)))
    L.append(f"- {'门禁口径' if zh else 'Gate policy'}: " + "; ".join(
        f"{g['metric']} {'>=' if g['metric'] != 'p95_latency_ms' else '<='} {g['limit']}" for g in gates))
    L.append(f"\n## 3. {'基线指标表' if zh else 'Baseline metrics'}")
    L.append(f"| {'指标' if zh else 'Metric'} | {'值' if zh else 'Value'} | {'阈值' if zh else 'Threshold'} | "
             f"{'判定' if zh else 'Verdict'} | {'样本数' if zh else 'n'} |")
    L.append("|---|---|---|---|---|")
    for g in gates:
        L.append(f"| {g['metric']} | {g['value']} | {g['limit']} | {g['status']} | {agg.get(g['metric'] + '_n', agg['samples'])} |")
    L.append(f"\n## 4. {'最差样本（Top 失败模式的输入）' if zh else 'Worst samples (input to the failure taxonomy)'}")
    L.append(f"| {'样本' if zh else 'Sample'} | {'指标' if zh else 'Metric'} | {'值' if zh else 'Value'} | "
             f"{'意图' if zh else 'Intent'} | {'问题' if zh else 'Question'} | {'回答摘录' if zh else 'Answer'} |")
    L.append("|---|---|---|---|---|---|")
    for key in ["faithfulness", "answer_correctness", "context_recall", "tool_arg_validity", "citation_validity"]:
        for sid, val, it, q, ans in worst(samples, per, key, 3):
            L.append(f"| {sid} | {key} | {val} | {it} | {q} | {ans} |")
    L.append(f"\n## 5. {'回归门禁与运行手册' if zh else 'Regression gate and runbook'}")
    L.append("```bash\npython eval_runner.py --samples samples.jsonl --thresholds thresholds.json --out results.json\n```")
    L.append(("- 阈值文件 `thresholds.json`；退出码 1 表示有指标跌破阈值（可直接接 CI）。\n"
              "- 复跑要求：固定样本文件与抽样种子；更换判官模型后必须重跑一致性检查。") if zh else
             ("- Thresholds live in `thresholds.json`; exit code 1 means a gate failed (CI-ready).\n"
              "- Re-run with the same sample file and seed; re-check judge agreement after swapping judges."))
    L.append(f"\n## 6. {'下一步' if zh else 'Next steps'}")
    L.append("- P0：修复上表中忠实度/引用为 0 的样本簇；P1：补 golden facts 收紧覆盖度判定；P2：把 P95 延迟纳入 SLO。"
             if zh else
             "- P0: fix sample clusters with zero faithfulness / citation validity; P1: add golden facts; P2: put P95 latency under an SLO.")
    L.append(f"\n## 7. {'附录' if zh else 'Appendix'}")
    L.append(("- 复现命令、判官 prompt、抽样种子见 `06-SCRIPTS/`；本报告由 `report_gen.py` 从 `results.json` 自动生成。") if zh
             else "- Reproduction commands, judge prompt and sampling seed: see `06-SCRIPTS/`; generated by `report_gen.py`.")
    open(a.out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"report -> {a.out} ({len(L)} lines)")

if __name__ == "__main__":
    main()
