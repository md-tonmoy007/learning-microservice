---
tags: [phase-2, grpc, tavily, search]
file: services/search-agent/app/services/search.py
---

# Search Agent

> Receives a list of search queries, calls the Tavily web search API for each, and returns all results as a list of `SearchResult` messages.

Related: [[gRPC]] · [[Protocol Buffers]] · [[gRPC aio Servers]] · [[gRPC Clients]] · [[Planner Agent]] · [[Summarizer Agent]] · [[Home]]

---

## The Code

**Proto contract** (`proto/search.proto`):
```proto
service SearchService {
  rpc Search (SearchRequest) returns (SearchResponse);
}

message SearchRequest {
  string task_id = 1;
  repeated string queries = 2;   // list of queries to search
}

message SearchResult {
  string title = 1;
  string url = 2;
  string content = 3;
  string source_type = 4;
}

message SearchResponse {
  repeated SearchResult results = 1;   // all results from all queries combined
}
```

**Servicer** (`app/services/search.py`):
```python
_search = TavilySearchResults(max_results=5)

class SearchServicer(search_pb2_grpc.SearchServiceServicer):
    async def Search(self, request, context):
        response_results = []

        for query in list(request.queries)[:3]:
            try:
                results = await _search.ainvoke(query)
            except Exception as exc:
                await context.abort(grpc.StatusCode.INTERNAL, str(exc))

            if not isinstance(results, list):
                continue

            for result in results:
                response_results.append(
                    search_pb2.SearchResult(
                        title=str(result.get("title", "")),
                        url=str(result.get("url", "")),
                        content=str(result.get("content", "")),
                        source_type=str(result.get("source_type", "web")),
                    )
                )

        return search_pb2.SearchResponse(results=response_results)
```

---

## Walkthrough

### The `SearchResult` Message

This is the only proto in the project that defines a **nested message** — a message used inside another message. `SearchResult` is defined once and appears:
- Inside `SearchResponse.results` (what the search agent returns)
- Inside `SummarizeRequest.results` (what the orchestrator sends to the summarizer)

This reuse is the point: the same strongly-typed structure flows from search → orchestrator → summarizer without any conversion or guessing at field names.

### `TavilySearchResults` Tool

`TavilySearchResults` is a LangChain tool that wraps the Tavily API. `max_results=5` caps how many results Tavily returns per query. Tavily is specialized for AI applications — it returns clean, scraped page content rather than raw HTML.

The `await _search.ainvoke(query)` call:
- Sends the query string to the Tavily API
- Gets back a list of result dicts: `[{"title": ..., "url": ..., "content": ...}, ...]`
- Returns `None` or raises if the API key is missing or the API is down

### Query Capping

```python
for query in list(request.queries)[:3]:
```

The planner returns 3-5 queries. The search agent caps at 3 regardless. With `max_results=5` per query, that's up to 15 results total per search node execution. This keeps costs predictable.

### Building `SearchResult` Messages

Each Tavily result dict is mapped to a `search_pb2.SearchResult` proto message:
```python
search_pb2.SearchResult(
    title=str(result.get("title", "")),
    url=str(result.get("url", "")),
    content=str(result.get("content", "")),
    source_type=str(result.get("source_type", "web")),
)
```

The `str(...)` wrapping handles cases where Tavily returns `None` for a field — protobuf `string` fields cannot be `None`.

---

## Workflow

```
Orchestrator (search_web node)     Search Agent (port 50052)
──────────────────────────────     ─────────────────────────
search_queries(task_id, queries)
  → open channel to search-agent:50052
  → stub.Search(SearchRequest(
      task_id=...,
      queries=["query1", "query2", "query3"],
    ))                   ──────────►  SearchServicer.Search()
                                        for query in queries[:3]:
                                          results = await _search.ainvoke(query)
                                          for r in results:
                                            append SearchResult(...)
                                        return SearchResponse(results=[...])
  ◄──────── SearchResponse ───────────
  → list of dicts extracted:
    [{"title", "url", "content", "source_type"}, ...]
  → appended to state["search_results"]
```

> [!tip]
> The search agent is the only agent that doesn't use an LLM. It calls an external API (Tavily) directly. This is why it needs a `TAVILY_API_KEY` environment variable instead of the OpenRouter variables used by the LLM agents.

> [!warning]
> If `_search.ainvoke(query)` raises an exception (API key missing, rate limit, network error), the current code aborts the entire gRPC call. In Phase 3+ we might want to catch per-query errors and continue with other queries rather than failing the whole search.

> [!note]
> `source_type` comes from Tavily's metadata. It's often `"web"` for standard pages, but Tavily can also return `"news"`, `"arxiv"`, etc. The field is passed through unchanged — the summarizer sees it and could use it for citation formatting in a future iteration.
