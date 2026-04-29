---
tags: [phase-2, grpc, langchain, report]
file: services/report-service/app/services/report.py
---

# Report Service

> Receives all research summaries collected across iterations, asks an LLM to synthesize them into a single comprehensive markdown report, and returns the result.

Related: [[gRPC]] · [[Protocol Buffers]] · [[gRPC aio Servers]] · [[Critic Agent]] · [[gRPC Clients]] · [[LangGraph Phase 2]] · [[Home]]

---

## The Code

**Proto contract** (`proto/report.proto`):
```proto
service ReportService {
  rpc GenerateReport (ReportRequest) returns (ReportResponse);
}

message ReportRequest {
  string task_id = 1;
  string user_query = 2;
  repeated string summaries = 3;   // one string per research iteration
}

message ReportResponse {
  string report_markdown = 1;
}
```

**Servicer** (`app/services/report.py`):
```python
class ReportServicer(report_pb2_grpc.ReportServiceServicer):
    async def GenerateReport(self, request, context):
        combined = "\n\n---\n\n".join(request.summaries)

        prompt = f"""Generate a comprehensive research report for: {request.user_query}

Research findings:
{combined}

Format in markdown with clear sections, key findings, and a conclusion."""

        try:
            response = await _llm.ainvoke([HumanMessage(content=prompt)])
        except Exception as exc:
            await context.abort(grpc.StatusCode.INTERNAL, str(exc))

        return report_pb2.ReportResponse(report_markdown=response.content)
```

---

## Walkthrough

### Why `repeated string summaries`?

The report service is called once, at the very end of the workflow. By that point `state["summaries"]` might contain multiple strings — one from each research iteration:
- Iteration 1 summary: "Quantum computing uses qubits..."
- Iteration 2 summary (if critic requested more): "Quantum error correction..."

The report service receives all of them and synthesizes a single final report. The planner's `report_sections` (section headings) are currently **not** passed to the report service — the LLM decides its own section structure based on the summaries. This is a known simplification; a future improvement would pass the section headings from the planner so the report follows the planned structure.

### The `---` Separator

```python
combined = "\n\n---\n\n".join(request.summaries)
```

Summaries are joined with a markdown horizontal rule (`---`). This makes the combined text visually clear in the prompt:

```
Summary from iteration 1:
Quantum computers leverage qubits...

---

Summary from iteration 2:
Error correction is critical because...
```

The LLM sees this as distinct research passes and can synthesize them coherently.

### Output Format

The prompt asks for markdown output. The `report_markdown` field comes back as a string like:

```markdown
# Quantum Computing: A Comprehensive Overview

## Introduction
Quantum computers leverage the principles of superposition...

## How Quantum Computers Work
...

## Current Applications
...

## Conclusion
...
```

This string is stored in `state["final_report"]` and then saved to the `ResearchTask.final_report` column in PostgreSQL. The API gateway returns it verbatim when a client polls for the completed task.

---

## Workflow

```
Orchestrator (generate_report node)     Report Service (port 50055)
───────────────────────────────────     ──────────────────────────
generate_final_report(
  task_id, user_query,
  summaries=state["summaries"])
  → open channel to report-service:50055
  → stub.GenerateReport(ReportRequest(
      task_id=...,
      user_query=...,
      summaries=["summary1", "summary2"],
    ))                        ──────────►  ReportServicer.GenerateReport()
                                            → join summaries with "---"
                                            → build markdown prompt
                                            → await _llm.ainvoke(prompt)
                                            → return ReportResponse(
                                                report_markdown="# Title\n..."
                                              )
  ◄────────── ReportResponse ─────────────
  → state["final_report"] = response.report_markdown
  → state["status"] = "completed"

Back in run_workflow():
  → task.final_report = final_state["final_report"]
  → task.status = "completed"
  → db.commit()
```

> [!tip]
> This is the only agent that receives a `repeated string` (list of strings) rather than a `repeated MessageType` (list of structured objects). Summaries are treated as opaque text blobs — the report service doesn't need to know their internal structure.

> [!note]
> The report LLM call is the most expensive in the workflow. With multiple summaries each potentially 500+ words, the combined prompt can be very long. In Phase 5, Qdrant could retrieve only the most relevant passages from each summary rather than sending everything, reducing token cost.
