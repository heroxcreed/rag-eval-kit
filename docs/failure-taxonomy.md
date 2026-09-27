# Failure-mode catalog (RAG + agents): symptom → detection → fix

How to use: assign every failing sample to one mode (a sample may touch several,
but pick exactly one primary cause — otherwise the fix list can't be prioritized).
A top-10 table should carry: sample ID / mode / root-cause layer / share of
failures / fix recommendation. Impact must be expressed as a share of failing
samples, never as vague words like "sometimes".

Root-cause layers: retrieval / prompt / tooling / data / infrastructure.

## RAG side

| # | Mode | Typical symptom | Detection | Common fix |
|---|---|---|---|---|
| R1 | Empty retrieval | Context empty or all irrelevant, yet the answer is made up | Relevant-chunk share = 0 | Check index/embeddings, filters, query rewriting |
| R2 | Chunk-boundary split | The answer spans two chunks and gets cut | Coverage low but top-k has the right doc | Tune chunk size/overlap, semantic chunking |
| R3 | Out-of-domain embeddings | Jargon / internal terms never retrieved | Term-sampling hit rate | Domain fine-tuning, hybrid keyword retrieval, synonym lists |
| R4 | top-k too small | Long-tail questions under-recalled | Coverage jumps when k increases | Adaptive k + rerank instead of blindly raising k |
| R5 | Lost in the middle | Key passage buried mid-context and ignored | Rank of relevant chunk vs whether it was cited | Rerank, context compression, staged answering |
| R6 | Misaligned / fabricated citations | The cited doc doesn't contain the claim | Verify every citation against its source text | Citations must carry spans; add a citation-check gate |
| R7 | Contradicts context | Context says A, answer says not-A | Low faithfulness score | Grounded prompting, refusal policy |
| R8 | Multi-hop failure | Needs 2+ docs combined to answer | Correctness fine on single-hop, collapses on multi-hop | Iterative retrieval / query decomposition |
| R9 | Staleness drift | Outdated answers, expired data | Time-sensitive subset tracked separately | Freshness monitoring + cache invalidation |
| R10 | Bad refusal | Refuses when it should answer, or fabricates when it should refuse | Refusal rate vs human judgment | Jointly tune refusal threshold and coverage |
| R11 | Format violation | JSON/table/fields break downstream contract | Schema validation pass rate | Structured-output constraints + parse fallback |
| R12 | Instruction drift | Forgets initial constraints in long sessions | Re-test the same constraint across multi-turn samples | Restate constraints, externalize state |

## Agent side

| # | Mode | Typical symptom | Detection | Common fix |
|---|---|---|---|---|
| A1 | Wrong tool | Called an API it shouldn't have | Trace vs expected tool set | Rewrite tool descriptions, add a routing layer |
| A2 | Hallucinated parameters | Invented order_id / dates | Parameter schema validation | Strong typing + required-field checks + examples |
| A3 | Unhandled errors | Keeps guessing after a tool 500 | Behavior following abnormal returns | Explicit error branches and retry policy |
| A4 | Loop / step explosion | Same call repeated N times | Step-count distribution + duplicate-call detection | Step cap + dedup + plan reuse |
| A5 | Lost state | Forgets confirmed info across turns | Multi-turn sample consistency | Externalize session state, compress summaries |
| A6 | Premature termination | Concludes with insufficient information | Completion judgment | Make stop conditions explicit (ask when params are missing) |
| A7 | Privilege escalation | Called resources it shouldn't access | Permission-matrix check | Authorize at the tool layer, not in the prompt |
| A8 | Cost blowup | Token usage explodes on one task | Per-task token percentiles | Context trimming, caching, model tiering |
| A9 | Concurrency race | Parallel tool results overwrite each other | Replay concurrent samples | Idempotency + ordering constraints |
| A10 | Unfounded confidence | Certain tone with no source | Low faithfulness + assertive wording | Force citations/refusal; surface uncertainty in the UI |

## Three classification rules

1. One sample may match several modes, but the primary cause is exactly one.
2. Root-cause layer must be one of: retrieval / prompt / tooling / data / infrastructure.
3. Impact = share of all failing samples, not "occasionally".
