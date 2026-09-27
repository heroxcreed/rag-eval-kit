"""Shared helpers for the RAG/Agent reliability kit (stdlib only, no dependencies).

Sample schema (one JSON object per line in samples.jsonl):
{
  "id": "s001",                       # required, unique
  "intent": "refund",                 # optional, used for stratified sampling
  "question": "text",                 # required
  "answer": "text",                   # required
  "contexts": [{"id":"c1","text":"..."}],           # retrieved contexts (optional)
  "citations": ["c1"],                             # ids cited by the answer
  "expected_facts": ["fact a","fact b"],           # optional golden facts
  "tool_calls": [{"name":"lookup","args":{"id":1},"ok":true,
                  "required_args":["id"],"duplicate":false}],  # optional
  "latency_ms": 1200, "prompt_tokens": 800, "completion_tokens": 200
}
"""
import json, re, unicodedata

STOP = set("""a an the and or but if then than that this those these is are was were be been being do does did
of to in on at for with without from by as it its their there here what which who whom whose when where why how
i you he she they we me my your our us not no yes can could should would will shall may might must about into
over under again more most some such only own same so too very just don now 的 了 是 在 和 与 就 都 而 及 或
一个 我们 你们 他们 这个 那个 什么 怎么 如何 为了 吗 呢 吧 请 有 没有""".split())

def content_tokens(text):
    """Lowercased alphanumeric tokens, stopwords removed. Works for EN and CJK text."""
    if not text:
        return []
    text = unicodedata.normalize("NFKC", str(text)).lower()
    toks = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text)
    return [t for t in toks if (t not in STOP and len(t) > 1) or ("\u4e00" <= t <= "\u9fff")]

def sentences(text):
    """Deterministic sentence splitter (EN + CJK punctuation)."""
    if not text:
        return []
    parts = re.split(r"(?<=[.!?;:\n])\s*|(?<=[。！？；：])", str(text))
    return [p.strip() for p in parts if len(p.strip()) >= 8]

def overlap(a_tokens, b_token_set):
    if not a_tokens:
        return 0.0
    return sum(1 for t in a_tokens if t in b_token_set) / len(a_tokens)

def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise SystemExit(f"{path}:{i}: invalid JSON ({e})")
    return rows

def dump_json(obj, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)

def percentile(values, p):
    if not values:
        return None
    vs = sorted(values)
    k = max(0, min(len(vs) - 1, int(round((p / 100.0) * (len(vs) - 1)))))
    return vs[k]

def norm_text(t):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(t or "")).lower()).strip()
