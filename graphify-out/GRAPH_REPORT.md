# Graph Report - .  (2026-04-27)

## Corpus Check
- Corpus is ~13,085 words - fits in a single context window. You may not need a graph.

## Summary
- 170 nodes · 230 edges · 12 communities detected
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 26 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Tutorial & Learning Concepts|Tutorial & Learning Concepts]]
- [[_COMMUNITY_Architecture & Design Decisions|Architecture & Design Decisions]]
- [[_COMMUNITY_Observability & Infrastructure|Observability & Infrastructure]]
- [[_COMMUNITY_Event-Driven Messaging|Event-Driven Messaging]]
- [[_COMMUNITY_Database Layer|Database Layer]]
- [[_COMMUNITY_API Schemas & Routes|API Schemas & Routes]]
- [[_COMMUNITY_Service Entrypoints|Service Entrypoints]]
- [[_COMMUNITY_Configuration & Settings|Configuration & Settings]]
- [[_COMMUNITY_Structured Logging|Structured Logging]]
- [[_COMMUNITY_Architecture Diagrams|Architecture Diagrams]]
- [[_COMMUNITY_Request Flow Concept|Request Flow Concept]]
- [[_COMMUNITY_Project Structure|Project Structure]]

## God Nodes (most connected - your core abstractions)
1. `Multi-Agent Research Assistant` - 16 edges
2. `gRPC Service Contracts` - 13 edges
3. `Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` - 11 edges
4. `Tutorial: LangGraph Orchestrator (Phase 1)` - 11 edges
5. `Kafka Event Design` - 10 edges
6. `Phase 2 — gRPC Agent Decomposition` - 10 edges
7. `Research Orchestrator Service` - 9 edges
8. `MVP Build Order (16 Steps)` - 9 edges
9. `Phase 1 — Foundation: API Gateway + In-Process LangGraph` - 9 edges
10. `SQLAlchemy Async (Concept Note)` - 9 edges

## Surprising Connections (you probably didn't know these)
- `MVP Build Order (CLAUDE.md)` --semantically_similar_to--> `MVP Build Order (16 Steps)`  [INFERRED] [semantically similar]
  CLAUDE.md → project.md
- `Tech Stack` --references--> `Kafka Event Design`  [INFERRED]
  CLAUDE.md → project.md
- `Comparison: BackgroundTasks vs Celery vs Kafka` --references--> `Kafka Event Design`  [EXTRACTED]
  tutorial/concepts/FastAPI Background Tasks.md → project.md
- `System Architecture Overview` --references--> `Multi-Agent Research Assistant`  [EXTRACTED]
  docs/architecture.md → project.md
- `Phase 1 — Foundation: API Gateway + In-Process LangGraph` --references--> `API Gateway Service`  [EXTRACTED]
  docs/phase-1.md → project.md

## Hyperedges (group relationships)
- **LangGraph Core Triad: State + Nodes + Edges** — concept_langgraph_stategraph, concept_langgraph_nodes, concept_langgraph_edges, concept_langgraph_state_merging [EXTRACTED 0.95]
- **Agent gRPC Services Pattern: Proto + Server + Client** — phase2_proto_files, phase2_grpc_server_pattern, phase2_grpc_client_pattern, project_grpc_contracts [EXTRACTED 0.95]
- **Observability Stack: Metrics + Logs + Traces** — phase4_prometheus_metrics, phase4_loki_logging, phase4_opentelemetry_tracing, phase4_grafana_dashboards [EXTRACTED 0.90]

## Communities

### Community 0 - "Tutorial & Learning Concepts"
Cohesion: 0.09
Nodes (34): Tutorial Obsidian Vault, FastAPI Background Tasks (Concept Note), BackgroundTasks DB Session Lifecycle Gotcha, Comparison: BackgroundTasks vs Celery vs Kafka, LangGraph Concepts (Concept Note), LangGraph Conditional Edges, LangGraph Edges, LangGraph Nodes (+26 more)

### Community 1 - "Architecture & Design Decisions"
Cohesion: 0.12
Nodes (30): Data Storage Strategy, Rationale: Why gRPC Between Services, Rationale: Why LangGraph in Orchestrator Only, System Architecture Overview, gRPC Conventions, LangGraph Conventions, MVP Build Order (CLAUDE.md), Tech Stack (+22 more)

### Community 2 - "Observability & Infrastructure"
Cohesion: 0.14
Nodes (18): Observability Conventions, Phase 1 — Foundation: API Gateway + In-Process LangGraph, Grafana Dashboards, Loki Structured Logging, Phase 4 — Observability: Prometheus, Grafana, Loki, OpenTelemetry, OpenTelemetry Distributed Tracing, Prometheus Metrics Setup, Rationale: Why Observability Matters (+10 more)

### Community 3 - "Event-Driven Messaging"
Cohesion: 0.12
Nodes (17): Rationale: Why Kafka/Redpanda for Events, Rationale: Why Redpanda for Local Dev, Kafka/Redpanda Conventions, Rationale: HTTP Between Gateway and Orchestrator in Phase 1, Rationale: Polling Instead of Streaming in Phase 1, aiokafka Consumer Pattern, aiokafka Producer Pattern, Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis (+9 more)

### Community 4 - "Database Layer"
Cohesion: 0.15
Nodes (10): Base, Base, DeclarativeBase, create_task(), get_task(), Run the full LangGraph research workflow.      Creates its own DB session — the, ResearchTask, run_workflow() (+2 more)

### Community 5 - "API Schemas & Routes"
Cohesion: 0.21
Nodes (9): BaseModel, create_research(), CreateResearchRequest, get_research(), get_status(), ResearchRequest, ResearchResponse, TaskDetailResponse (+1 more)

### Community 8 - "Service Entrypoints"
Cohesion: 0.5
Nodes (1): health()

### Community 9 - "Configuration & Settings"
Cohesion: 0.5
Nodes (2): BaseSettings, Settings

### Community 10 - "Structured Logging"
Cohesion: 0.67
Nodes (2): get_logger(), _JSONFormatter

### Community 12 - "Architecture Diagrams"
Cohesion: 1.0
Nodes (2): Architecture Request Flow, Service Map

### Community 25 - "Request Flow Concept"
Cohesion: 1.0
Nodes (1): Request Flow

### Community 26 - "Project Structure"
Cohesion: 1.0
Nodes (1): Project Directory Structure

## Knowledge Gaps
- **39 isolated node(s):** `Request Flow`, `gRPC Conventions`, `Kafka/Redpanda Conventions`, `LangGraph Conventions`, `Observability Conventions` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Service Entrypoints`** (4 nodes): `health()`, `lifespan()`, `main.py`, `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Configuration & Settings`** (4 nodes): `BaseSettings`, `Settings`, `config.py`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Structured Logging`** (4 nodes): `get_logger()`, `_JSONFormatter`, `.format()`, `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Architecture Diagrams`** (2 nodes): `Architecture Request Flow`, `Service Map`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Request Flow Concept`** (1 nodes): `Request Flow`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Structure`** (1 nodes): `Project Directory Structure`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tutorial: LangGraph Orchestrator (Phase 1)` connect `Tutorial & Learning Concepts` to `Architecture & Design Decisions`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `Research Orchestrator Service` connect `Architecture & Design Decisions` to `Tutorial & Learning Concepts`, `Observability & Infrastructure`, `Event-Driven Messaging`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `Phase 1 — Foundation: API Gateway + In-Process LangGraph` connect `Observability & Infrastructure` to `Architecture & Design Decisions`, `Event-Driven Messaging`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` (e.g. with `Phase 2 — gRPC Agent Decomposition` and `Phase 4 — Observability: Prometheus, Grafana, Loki, OpenTelemetry`) actually correct?**
  _`Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Request Flow`, `gRPC Conventions`, `Kafka/Redpanda Conventions` to the rest of the system?**
  _39 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Tutorial & Learning Concepts` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._
- **Should `Architecture & Design Decisions` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._