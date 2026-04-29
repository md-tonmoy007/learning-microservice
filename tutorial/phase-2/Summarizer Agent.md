---
tags: [phase-2, grpc, langchain, summarizer]
file: services/summarizer-agent/app/services/summarizer.py
---

# Summarizer Agent

> Receives search results, asks an LLM to produce a structured summary and key points, and returns them alongside the source URLs as citations.

Related: [[gRPC]] · [[Protocol Buffers]] · [[gRPC aio Servers]] · [[Search Agent]] · [[Critic Agent]] · [[gRPC Clients]] · [[Home]]

---

## The Code

**Proto contract** (`proto/summarizer.proto`):
```proto
service SummarizerService {
  rpc Summarize (SummarizeRequest) returns (SummarizeResponse);
}

message SummarizeRequest {
  string task_id = 1;
  string user_query = 2;
  repeated SearchResult results = 3;  // reuses SearchResult from search.proto
}

message SummarizeResponse {
  string summary = 1;
  repeated string key_points = 2;
  repeated string citations = 3;
}
```

> [!note]
> `SummarizeRequest` embeds `SearchResult` — the same message type defined in `search.proto`. Both services share this structure via the generated stubs. The orchestrator builds `summarizer_pb2.SearchResult` objects when sending results to the summarizer.

**Servicer** (`app/services/summarizer.py`):
```python
class SummarizerServicer(summarizer_pb2_grpc.SummarizerServiceServicer):
    async def Summarize(self, request, context):
        results_text = "\n\n".join(
            f"Source: {result.url or 'unknown'}\n{result.content[:500]}"
            for result in request.results
        )

        prompt = f"""Summarize the following research results for: {request.user_query}

Results:
{results_text}

Return a JSON object with:
- "summary": a structured paragraph with key facts, preserving source URLs
- "key_points": list of 3-5 concise strings highlighting the most important findings

Return only valid JSON. No markdown fences."""

        try:
            response = await _llm.ainvoke([HumanMessage(content=prompt)])
            parsed = json.loads(response.content)
        except Exception as exc:
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))
            return

        citations = [result.url for result in request.results if result.url]
        return summarizer_pb2.SummarizeResponse(
            summary=parsed.get("summary", ""),
            key_points=parsed.get("key_points") or [],
            citations=citations,
        )
```

---

## Walkthrough

### Building the Results Text

The prompt includes the raw search results, but not the full content — only the first 500 characters:
```python
f"Source: {result.url or 'unknown'}\n{result.content[:500]}"
```

With up to 10 results (the orchestrator sends the last 10), that's at most 5,000 characters of source content. The `[:500]` prevents the prompt from blowing up LLM context limits when a result has a very long page.

### Why Citations Come from URLs, Not from the LLM

```python
citations = [result.url for result in request.results if result.url]
```

Citations are extracted directly from the `SearchResult.url` fields — we do **not** ask the LLM to produce them. This is intentional:

- LLMs hallucinate URLs. They might change a URL slightly, combine two URLs, or invent one that looks plausible.
- The actual URLs from Tavily are already available in the request — no need to generate what we already have.
- This is a general principle: when data is deterministic, don't delegate it to a probabilistic model.

### The JSON Prompt Pattern

The prompt asks for JSON with two keys: `summary` and `key_points`. This is the same pattern used by the planner and critic agents. Asking for JSON instead of free text means:
- The response is machine-parseable
- The `key_points` field is always a list with a defined structure
- The LLM can't decide to use a different format

---

## Why This Was Buggy (And How We Fixed It)

**Original code** had a freeform prompt:
```python
prompt = "Write a structured summary with key facts. Preserve source URLs."
```

The LLM returned a paragraph of text. The code then did:
```python
return summarizer_pb2.SummarizeResponse(
    summary=response.content,
    citations=citations,
    # key_points field was never populated
)
```

The proto defined `repeated string key_points` but the code never set it, so `response.key_points` was always `[]`. The orchestrator client (`grpc_clients/summarizer.py`) returned `list(response.key_points)` which was always an empty list.

**The fix**: change the prompt to request JSON, `json.loads()` the response, and explicitly set `key_points` from the parsed result. This makes `key_points` useful — it feeds into the critique and final report in future phases.

---

## Workflow

```
Orchestrator (summarize_results node)     Summarizer Agent (port 50053)
─────────────────────────────────────     ─────────────────────────────
summarize_search_results(
  task_id, user_query,
  results=state["search_results"][-10:])
  → build summarizer_pb2.SearchResult list
  → open channel to summarizer-agent:50053
  → stub.Summarize(SummarizeRequest)  ──►  SummarizerServicer.Summarize()
                                             → build results_text (500 chars each)
                                             → build JSON prompt
                                             → await _llm.ainvoke(prompt)
                                             → json.loads(response.content)
                                             → extract citations from result.url
                                             → return SummarizeResponse(
                                                 summary=...,
                                                 key_points=[...],
                                                 citations=[...]
                                               )
  ◄───────── SummarizeResponse ────────────
  → {"summary": ..., "key_points": [...], "citations": [...]}
  → state["summaries"].append(summary)
```

> [!tip]
> The `[-10:]` slice in the orchestrator means: if the workflow loops (critic says more research needed), only the most recent 10 results are summarized on each pass. Earlier results are implicitly "forgotten" by the summarizer — though all summaries are kept in `state["summaries"]` and sent to the report service at the end.
