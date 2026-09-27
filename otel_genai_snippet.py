#!/usr/bin/env python
"""OpenTelemetry GenAI instrumentation snippet generator + attribute-name checker.

The authoritative GenAI semantic conventions moved OUT of open-telemetry/semantic-conventions
into open-telemetry/semantic-conventions-genai (the old docs/gen-ai path is a deprecation stub).
This script prints a minimal snippet using current attribute names, and can verify those names
against a local clone of that repo.

Run:  python otel_genai_snippet.py                  -> print the snippet
      python otel_genai_snippet.py --check           -> verify attribute names against a local clone
      python otel_genai_snippet.py --check --repo /path/to/semantic-conventions-genai
"""
import argparse, os, sys

ATTRS = [
    "gen_ai.operation.name", "gen_ai.provider.name", "gen_ai.request.model",
    "gen_ai.response.model", "gen_ai.response.finish_reasons", "gen_ai.response.id",
    "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
    "gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.cache_write.input_tokens",
    "gen_ai.input.messages", "gen_ai.output.messages", "gen_ai.system_instructions",
    "gen_ai.agent.name", "gen_ai.conversation.id", "gen_ai.tool.definitions",
    "gen_ai.prompt.variable", "gen_ai.output.type",
]

SNIPPET_LINES = [
    "# pip install opentelemetry-sdk opentelemetry-exporter-otlp",
    "from opentelemetry import trace",
    "from opentelemetry.sdk.trace import TracerProvider",
    "from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter",
    "",
    "provider = TracerProvider()",
    "provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))",
    "trace.set_tracer_provider(provider)",
    "tracer = trace.get_tracer(\"rag-audit\")",
    "",
    "def answer_with_trace(question, retrieve, call_model, model=\"your-model\"):",
    "    with tracer.start_as_current_span(\"rag.answer\") as span:",
    "        span.set_attribute(\"gen_ai.operation.name\", \"chat\")",
    "        span.set_attribute(\"gen_ai.provider.name\", \"openai\")   # NOT gen_ai.system (deprecated)",
    "        span.set_attribute(\"gen_ai.request.model\", model)",
    "        span.set_attribute(\"gen_ai.input.messages\", json.dumps([{\"role\": \"user\", \"content\": question}]))",
    "",
    "        contexts = retrieve(question)                          # your retriever",
    "        with tracer.start_as_current_span(\"rag.retrieve\") as s2:",
    "            s2.set_attribute(\"retrieval.k\", len(contexts))",
    "",
    "        answer, usage = call_model(question, contexts)",
    "        span.set_attribute(\"gen_ai.output.messages\", json.dumps([{\"role\": \"assistant\", \"content\": answer}]))",
    "        span.set_attribute(\"gen_ai.usage.input_tokens\", usage.prompt_tokens)",
    "        span.set_attribute(\"gen_ai.usage.output_tokens\", usage.completion_tokens)",
    "        span.set_attribute(\"gen_ai.response.model\", usage.model)",
    "        span.set_attribute(\"gen_ai.response.finish_reasons\", [usage.finish_reason])",
    "        return answer",
    "",
    "# Self-hosted Langfuse ingests OTLP: point OTEL_EXPORTER_OTLP_ENDPOINT at it,",
    "# then the same spans feed both your metrics and the Langfuse UI.",
    "# See 03-OBSERVABILITY/langfuse-selfhost/docker-compose.yml + .env.prod.example"
]

SNIPPET = "\n".join(SNIPPET_LINES)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--repo", default=None,
                    help="path to a local clone of open-telemetry/semantic-conventions-genai")
    a = ap.parse_args()
    if not a.check:
        print(SNIPPET); return 0
    root = a.repo
    if root is None:
        root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "semconv-genai")
    if not os.path.isdir(root):
        print("no local semconv-genai clone found at " + root)
        print("skipped: clone https://github.com/open-telemetry/semantic-conventions-genai")
        print("and re-run with --repo <path> to verify attribute names.")
        return 0
    blob = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith((".md", ".yaml", ".yml", ".json")):
                try:
                    blob.append(open(os.path.join(dirpath, f), encoding="utf-8", errors="replace").read())
                except OSError:
                    pass
    blob = "\n".join(blob)
    missing = [x for x in ATTRS if x not in blob]
    print("checked %d attribute names against %s" % (len(ATTRS), root))
    print("all present" if not missing else "MISSING (renamed/removed upstream): %s" % missing)
    print("note: 'gen_ai.system' still appears (prefer gen_ai.provider.name)")
    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
