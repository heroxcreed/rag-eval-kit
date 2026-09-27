# Metric spec (pick 4–6, start small)

Rule: **every metric must answer "who reads this number, and at what value do we
stop the line."** A metric with no decision attached doesn't go in the report.

Suggested sets:
- RAG single-turn QA: M1 faithfulness + M2 context precision + M3 context recall + M6 cost/latency (4)
- Agent / tool use: add M4 answer correctness + M5 tool-call validity (6)
- Finer ones (noise sensitivity, answer relevancy, format compliance) only when a
  client explicitly disputes acceptance.

## M1 Faithfulness / groundedness (highest priority)
- Definition: is every checkable claim in the answer supported by the retrieved context?
- Input: question, answer, retrieved_contexts (or tool return values).
- Computation: split the answer into atomic claims → judge each supported / partially / unsupported → faithfulness = supported / total.
- Threshold: measure a baseline first, then gate at "baseline minus 5 points" (an absolute like 0.85 only fits businesses with zero tolerance for fabrication).
- Common misuse: eyeballing "looks right"; blaming the model when retrieval failed (that's M3's job).
- Open-source implementations: RAGAS `faithfulness`, DeepEval `Faithfulness`, TruLens groundedness feedback.

## M2 Context precision
- Definition: share of retrieved chunks truly relevant to the question (rank-weighted is better).
- Input: question, retrieved_contexts (+ optional ground truth).
- Computation: judge each chunk relevant/irrelevant without golden; context precision@k with golden.
- Threshold: record a baseline; flag "relevant-chunk share < 50%" as a retrieval-layer fix (prompt tuning at that point is wasted effort).
- Common misuse: substituting "doc contains the answer" for "chunk is relevant"; raising top-k boosts recall but crushes precision — report both.

## M3 Context recall
- Definition: how much of the information needed to answer was retrieved.
- Input: question, ground truth (or a human-labeled list of required facts).
- Computation: split the golden into claims → check each against retrieved_contexts → coverage.
- Threshold: support/KB scenarios usually demand > 0.8, otherwise fix retrieval (hybrid search, rerank, chunking) before touching prompts.
- Common misuse: claiming recall without a golden; the honest substitute is "human-label the required facts for 20 samples."

## M4 Answer correctness
- Input: question, answer, ground truth.
- Computation: fact overlap (e.g. F1) + semantic agreement (embedding or judge score), weighted; exact match for short answers (classification, extraction).
- Threshold: defined by the business (e.g. "≥ 90% to ship"), confirmed in writing by the client.
- Common misuse: having the same model family judge its own output (same-source bias) — switch model or family and report agreement.

## M5 Tool-call validity (required for agents)
- Definition: are tool choice, parameters, order, and termination correct?
- Input: each tool_call (name + args), tool returns, final answer.
- Computation: ① parameter-validity rate ② redundant-call rate ③ missing-required-call rate ④ abnormal-return-handled rate.
- Threshold: parameter-invalid rate > 2%, or any privilege-escalation call, is P0.
- Common misuse: checking only the final answer while ignoring "took 6 detours to get it right" (cost and stability risk hide there).

## M6 Cost & latency per resolved query
- Definition: token cost and P50/P95 latency **per resolved query**, not per request.
- Input: token counts, model pricing, elapsed time, resolved-or-not (unresolved queries stay in the denominator).
- Computation: total cost / resolutions; latency percentiles over the resolved subset.
- Threshold: measure a baseline; gate at "+30% cost per resolution".
- Common misuse: reporting mean latency without P95; dropping failed requests from the denominator to make the number look good.

## LLM-as-judge discipline

1. The judge must be from a different source than the system under test (different model family is best); name the model and version in the report.
2. Use a rubric (1–5 with anchored descriptions), not "score 0–10".
3. Spot-check 20–30 samples against humans; report agreement / Cohen's kappa (`judge_consistency.py`).
4. Test order/length bias: swap A/B positions, re-run, report the flip rate.
