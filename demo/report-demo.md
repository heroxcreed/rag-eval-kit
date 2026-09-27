# RAG / Agent 可靠性体检报告：Demo Client

> 样本量: 12 · 样本文件: samples.jsonl · 计算方式: eval_runner.py (heuristic baseline, no LLM calls)

## 1. 执行摘要
1. 当前有 6 项指标未达阈值：faithfulness=0.625 (<0.85), context_precision=0.1667 (<0.5), context_recall=0.7222 (<0.8), answer_correctness=0.6806 (<0.8), citation_validity=0.9583 (<1.0), tool_arg_validity=0.6667 (<0.98)
2. 忠实度最差样本：d003(0.00,refund), d007(0.00,agent_tool), d008(0.00,agent_tool)
3. P95 延迟 3200.0 ms · 平均 tokens/样本 1145.0

## 2. 范围与方法
- 样本构成: agent_tool=3, billing=2, refund=2, account=2, policy=2, troubleshooting=1
- 门禁口径: faithfulness >= 0.85; context_precision >= 0.5; context_recall >= 0.8; answer_correctness >= 0.8; citation_validity >= 1.0; tool_arg_validity >= 0.98; p95_latency_ms <= 8000

## 3. 基线指标表
| 指标 | 值 | 阈值 | 判定 | 样本数 |
|---|---|---|---|---|
| faithfulness | 0.625 | 0.85 | FAIL | 12 |
| context_precision | 0.1667 | 0.5 | FAIL | 12 |
| context_recall | 0.7222 | 0.8 | FAIL | 12 |
| answer_correctness | 0.6806 | 0.8 | FAIL | 12 |
| citation_validity | 0.9583 | 1.0 | FAIL | 12 |
| tool_arg_validity | 0.6667 | 0.98 | FAIL | 3 |
| p95_latency_ms | 3200.0 | 8000 | pass | 12 |

## 4. 最差样本（Top 失败模式的输入）
| 样本 | 指标 | 值 | 意图 | 问题 | 回答摘录 |
|---|---|---|---|---|---|
| d003 | faithfulness | 0.0 | refund | Can I get a refund after 45 days? | Yes, you can get a full refund within 60 days of purchase. |
| d007 | faithfulness | 0.0 | agent_tool | Where is order 12345? | Order 12345 shipped yesterday and will arrive in 2 days. |
| d008 | faithfulness | 0.0 | agent_tool | Where is order 99999? | Order 99999 is delayed by the carrier. |
| d003 | answer_correctness | 0.0 | refund | Can I get a refund after 45 days? | Yes, you can get a full refund within 60 days of purchase. |
| d006 | answer_correctness | 0.0 | account | How do I enable two-factor authentication? | Go to Security, then Two-factor, choose an authenticator app and scan the QR cod |
| d008 | answer_correctness | 0.0 | agent_tool | Where is order 99999? | Order 99999 is delayed by the carrier. |
| d008 | context_recall | 0.0 | agent_tool | Where is order 99999? | Order 99999 is delayed by the carrier. |
| d009 | context_recall | 0.0 | agent_tool | Cancel order 55555 and refund it. | Order 55555 has been cancelled and the refund was issued. |
| d007 | context_recall | 0.5 | agent_tool | Where is order 12345? | Order 12345 shipped yesterday and will arrive in 2 days. |
| d008 | tool_arg_validity | 0.0 | agent_tool | Where is order 99999? | Order 99999 is delayed by the carrier. |
| d007 | tool_arg_validity | 1.0 | agent_tool | Where is order 12345? | Order 12345 shipped yesterday and will arrive in 2 days. |
| d009 | tool_arg_validity | 1.0 | agent_tool | Cancel order 55555 and refund it. | Order 55555 has been cancelled and the refund was issued. |
| d004 | citation_validity | 0.5 | refund | How long does a refund take to arrive? | Refunds are processed within 5 business days and appear on your statement shortl |
| d001 | citation_validity | 1.0 | billing | How do I change my billing address? | Open Settings, choose Billing, then press Update address and save your new billi |
| d002 | citation_validity | 1.0 | billing | What is the invoice settlement period? | Invoices are issued on the first day of each month and are due within 30 days. |

## 5. 回归门禁与运行手册
```bash
python eval_runner.py --samples samples.jsonl --thresholds thresholds.json --out results.json
```
- 阈值文件 `thresholds.json`；退出码 1 表示有指标跌破阈值（可直接接 CI）。
- 复跑要求：固定样本文件与抽样种子；更换判官模型后必须重跑一致性检查。

## 6. 下一步
- P0：修复上表中忠实度/引用为 0 的样本簇；P1：补 golden facts 收紧覆盖度判定；P2：把 P95 延迟纳入 SLO。

## 7. 附录
- 复现命令、判官 prompt、抽样种子见 `06-SCRIPTS/`；本报告由 `report_gen.py` 从 `results.json` 自动生成。
