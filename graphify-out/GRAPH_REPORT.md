# Graph Report - .  (2026-04-27)

## Corpus Check
- Corpus is ~3,747 words - fits in a single context window. You may not need a graph.

## Summary
- 244 nodes · 316 edges · 25 communities detected
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 34 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Architecture & Design Decisions|Architecture & Design Decisions]]
- [[_COMMUNITY_Tutorial & Learning Vault|Tutorial & Learning Vault]]
- [[_COMMUNITY_Code Modules|Code Modules]]
- [[_COMMUNITY_Phase 1 Implementation|Phase 1 Implementation]]
- [[_COMMUNITY_Kafka & Event Streaming|Kafka & Event Streaming]]
- [[_COMMUNITY_Pydantic Schemas|Pydantic Schemas]]
- [[_COMMUNITY_gRPC Agent Services|gRPC Agent Services]]
- [[_COMMUNITY_LangGraph Node Functions|LangGraph Node Functions]]
- [[_COMMUNITY_Observability Stack|Observability Stack]]
- [[_COMMUNITY_Service Entry Points|Service Entry Points]]
- [[_COMMUNITY_Service Configuration|Service Configuration]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Database Layer|Database Layer]]
- [[_COMMUNITY_Structured Logging|Structured Logging]]
- [[_COMMUNITY_Kafka Topics & Messaging|Kafka Topics & Messaging]]
- [[_COMMUNITY_LangGraph Workflow|LangGraph Workflow]]
- [[_COMMUNITY_System Diagrams|System Diagrams]]
- [[_COMMUNITY_Project Overview|Project Overview]]
- [[_COMMUNITY_MVP Strategy|MVP Strategy]]
- [[_COMMUNITY_Container Orchestration|Container Orchestration]]
- [[_COMMUNITY_Telemetry & Metrics|Telemetry & Metrics]]
- [[_COMMUNITY_Package Management|Package Management]]
- [[_COMMUNITY_Development Conventions|Development Conventions]]
- [[_COMMUNITY_Request Flow|Request Flow]]
- [[_COMMUNITY_Project Directory Structure|Project Directory Structure]]

## God Nodes (most connected - your core abstractions)
1. `Multi-Agent Research Assistant` - 16 edges
2. `Orchestrator Service` - 15 edges
3. `gRPC Service Contracts` - 13 edges
4. `Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` - 11 edges
5. `Tutorial: LangGraph Orchestrator (Phase 1)` - 11 edges
6. `Kafka Event Design` - 10 edges
7. `Phase 2 — gRPC Agent Decomposition` - 10 edges
8. `Research Orchestrator Service` - 9 edges
9. `MVP Build Order (16 Steps)` - 9 edges
10. `Phase 1 — Foundation: API Gateway + In-Process LangGraph` - 9 edges

## Surprising Connections (you probably didn't know these)
- `MVP Build Order (CLAUDE.md)` --semantically_similar_to--> `MVP Build Order (16 Steps)`  [INFERRED] [semantically similar]
  CLAUDE.md → project.md
- `get_research()` --calls--> `TaskDetailResponse`  [INFERRED]
  D:\learning-microservice\services\orchestrator\app\api\research.py → D:\learning-microservice\services\orchestrator\app\schemas\research.py
- `create_research()` --calls--> `ResearchResponse`  [INFERRED]
  D:\learning-microservice\services\orchestrator\app\api\research.py → D:\learning-microservice\services\orchestrator\app\schemas\research.py
- `get_status()` --calls--> `TaskStatusResponse`  [INFERRED]
  D:\learning-microservice\services\orchestrator\app\api\research.py → D:\learning-microservice\services\orchestrator\app\schemas\research.py
- `ResearchTask` --uses--> `Base`  [INFERRED]
  D:\learning-microservice\services\orchestrator\app\models\research.py → D:\learning-microservice\services\orchestrator\app\core\database.py

## Hyperedges (group relationships)
- **Observability Stack: Metrics + Logs + Traces** — phase4_prometheus_metrics, phase4_loki_logging, phase4_opentelemetry_tracing, phase4_grafana_dashboards [EXTRACTED 0.90]
- **Agent gRPC Services Pattern: Proto + Server + Client** — phase2_proto_files, phase2_grpc_server_pattern, phase2_grpc_client_pattern, project_grpc_contracts [EXTRACTED 0.95]
- **LangGraph Core Triad: State + Nodes + Edges** — concept_langgraph_stategraph, concept_langgraph_nodes, concept_langgraph_edges, concept_langgraph_state_merging [EXTRACTED 0.95]
- **gRPC Agent Services Sharing Proto Definitions** — proto_shared, svc_planner_agent, svc_search_agent, svc_summarizer_agent, svc_critic_agent, svc_report_service [EXTRACTED 1.00]
- **LangGraph Workflow Core in Orchestrator** — svc_orchestrator, code_workflow_py, code_nodes_py, code_state_py [EXTRACTED 1.00]
- **Phase 1 Active Services Running in Docker Compose** — svc_api_gateway, svc_orchestrator, tech_postgresql [EXTRACTED 1.00]

## Communities

### Community 0 - "Architecture & Design Decisions"
Cohesion: 0.09
Nodes (40): Data Storage Strategy, Rationale: Why gRPC Between Services, Rationale: Why LangGraph in Orchestrator Only, System Architecture Overview, gRPC Conventions, LangGraph Conventions, MVP Build Order (CLAUDE.md), Tech Stack (+32 more)

### Community 1 - "Tutorial & Learning Vault"
Cohesion: 0.09
Nodes (33): Tutorial Obsidian Vault, FastAPI Background Tasks (Concept Note), BackgroundTasks DB Session Lifecycle Gotcha, LangGraph Concepts (Concept Note), LangGraph Conditional Edges, LangGraph Edges, LangGraph Nodes, LangGraph State Merging (+25 more)

### Community 2 - "Code Modules"
Cohesion: 0.13
Nodes (13): Base, create_research(), create_task(), get_research(), get_research_status(), get_status(), get_task(), Run the full LangGraph research workflow.      Creates its own DB session — th (+5 more)

### Community 3 - "Phase 1 Implementation"
Cohesion: 0.14
Nodes (20): Phase 1 Current Implementation, LangGraph Graph Node Functions (nodes.py), Research Tasks ORM Model (research.py), Shared Logging Utility (shared/logging.py), ResearchState TypedDict (state.py), LangGraph Workflow Definition (workflow.py), OPENAI_API_KEY Environment Variable, POSTGRES_URL Environment Variable (+12 more)

### Community 4 - "Kafka & Event Streaming"
Cohesion: 0.12
Nodes (18): Rationale: Why Kafka/Redpanda for Events, Rationale: Why Redpanda for Local Dev, Kafka/Redpanda Conventions, Comparison: BackgroundTasks vs Celery vs Kafka, Rationale: HTTP Between Gateway and Orchestrator in Phase 1, Rationale: Polling Instead of Streaming in Phase 1, aiokafka Consumer Pattern, aiokafka Producer Pattern (+10 more)

### Community 5 - "Pydantic Schemas"
Cohesion: 0.47
Nodes (6): BaseModel, CreateResearchRequest, ResearchRequest, ResearchResponse, TaskDetailResponse, TaskStatusResponse

### Community 6 - "gRPC Agent Services"
Cohesion: 0.29
Nodes (10): gRPC Async-Only Convention, Shared Proto Definitions (proto/), Critic Agent Service, Planner Agent Service, Report Service, Search Agent Service, Summarizer Agent Service, gRPC Internal Communication (+2 more)

### Community 7 - "LangGraph Node Functions"
Cohesion: 0.43
Nodes (6): critique_answer(), generate_report(), plan_research(), search_web(), should_continue(), summarize_results()

### Community 8 - "Observability Stack"
Cohesion: 0.32
Nodes (8): Observability Conventions, Grafana Dashboards, Loki Structured Logging, Phase 4 — Observability: Prometheus, Grafana, Loki, OpenTelemetry, OpenTelemetry Distributed Tracing, Prometheus Metrics Setup, Rationale: Why Observability Matters, Monitoring Plan

### Community 9 - "Service Entry Points"
Cohesion: 0.4
Nodes (2): health(), lifespan()

### Community 10 - "Service Configuration"
Cohesion: 0.33
Nodes (2): BaseSettings, Settings

### Community 11 - "Database Migrations"
Cohesion: 0.6
Nodes (3): do_run_migrations(), run_migrations_offline(), run_migrations_online()

### Community 12 - "Database Layer"
Cohesion: 0.5
Nodes (3): Base, get_db(), DeclarativeBase

### Community 13 - "Structured Logging"
Cohesion: 0.6
Nodes (2): get_logger(), _JSONFormatter

### Community 14 - "Kafka Topics & Messaging"
Cohesion: 0.5
Nodes (4): Kafka Topic Definitions (shared/kafka_events.py), Kafka Topic Centralization Convention, aiokafka Async Kafka Client, Redpanda Kafka-Compatible Messaging

### Community 15 - "LangGraph Workflow"
Cohesion: 0.67
Nodes (1): build_graph()

### Community 16 - "System Diagrams"
Cohesion: 1.0
Nodes (2): Architecture Request Flow, Service Map

### Community 17 - "Project Overview"
Cohesion: 1.0
Nodes (2): Multi-Agent Research Assistant, Personal Learning Project Purpose

### Community 18 - "MVP Strategy"
Cohesion: 1.0
Nodes (2): MVP First Architecture Decision, Rationale: Build MVP Before Adding Infra

### Community 19 - "Container Orchestration"
Cohesion: 1.0
Nodes (2): Docker Compose, Kubernetes with Helm

### Community 20 - "Telemetry & Metrics"
Cohesion: 1.0
Nodes (2): OpenTelemetry Distributed Tracing, Prometheus and Grafana Metrics

### Community 21 - "Package Management"
Cohesion: 1.0
Nodes (2): Rationale: Use uv Instead of pip, uv Package Manager

### Community 22 - "Development Conventions"
Cohesion: 1.0
Nodes (2): Small Focused Changes Convention, Tutorial Obsidian Vault Convention

### Community 47 - "Request Flow"
Cohesion: 1.0
Nodes (1): Request Flow

### Community 48 - "Project Directory Structure"
Cohesion: 1.0
Nodes (1): Project Directory Structure

## Knowledge Gaps
- **65 isolated node(s):** `Request Flow`, `gRPC Conventions`, `Kafka/Redpanda Conventions`, `LangGraph Conventions`, `Observability Conventions` (+60 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Service Entry Points`** (6 nodes): `main.py`, `main.py`, `health()`, `lifespan()`, `main.py`, `main.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Service Configuration`** (6 nodes): `BaseSettings`, `Settings`, `config.py`, `config.py`, `config.py`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Structured Logging`** (5 nodes): `logging.py`, `get_logger()`, `_JSONFormatter`, `.format()`, `logging.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `LangGraph Workflow`** (3 nodes): `workflow.py`, `workflow.py`, `build_graph()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `System Diagrams`** (2 nodes): `Architecture Request Flow`, `Service Map`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Overview`** (2 nodes): `Multi-Agent Research Assistant`, `Personal Learning Project Purpose`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `MVP Strategy`** (2 nodes): `MVP First Architecture Decision`, `Rationale: Build MVP Before Adding Infra`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Container Orchestration`** (2 nodes): `Docker Compose`, `Kubernetes with Helm`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Telemetry & Metrics`** (2 nodes): `OpenTelemetry Distributed Tracing`, `Prometheus and Grafana Metrics`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Package Management`** (2 nodes): `Rationale: Use uv Instead of pip`, `uv Package Manager`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Development Conventions`** (2 nodes): `Small Focused Changes Convention`, `Tutorial Obsidian Vault Convention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Request Flow`** (1 nodes): `Request Flow`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Project Directory Structure`** (1 nodes): `Project Directory Structure`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Tutorial: LangGraph Orchestrator (Phase 1)` connect `Tutorial & Learning Vault` to `Architecture & Design Decisions`?**
  _High betweenness centrality (0.048) - this node is a cross-community bridge._
- **Why does `Research Orchestrator Service` connect `Architecture & Design Decisions` to `Tutorial & Learning Vault`, `Kafka & Event Streaming`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `Phase 1 — Foundation: API Gateway + In-Process LangGraph` connect `Architecture & Design Decisions` to `Observability Stack`, `Kafka & Event Streaming`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Orchestrator Service` (e.g. with `Shared Logging Utility (shared/logging.py)` and `Pydantic v2`) actually correct?**
  _`Orchestrator Service` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` (e.g. with `Phase 2 — gRPC Agent Decomposition` and `Phase 4 — Observability: Prometheus, Grafana, Loki, OpenTelemetry`) actually correct?**
  _`Phase 3 — Event-Driven Architecture: Kafka/Redpanda + Redis` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Request Flow`, `gRPC Conventions`, `Kafka/Redpanda Conventions` to the rest of the system?**
  _65 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Architecture & Design Decisions` be split into smaller, more focused modules?**
  _Cohesion score 0.09 - nodes in this community are weakly interconnected._