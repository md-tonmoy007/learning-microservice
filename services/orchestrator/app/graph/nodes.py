from app.grpc_clients.critic import critique_summary
from app.grpc_clients.planner import create_plan
from app.grpc_clients.report import generate_final_report
from app.grpc_clients.search import search_queries
from app.grpc_clients.summarizer import summarize_search_results
from app.graph.state import ResearchState


async def plan_research(state: ResearchState) -> dict:
    plan = await create_plan(state["task_id"], state["user_query"])
    return {
        "research_plan": plan["search_queries"],
        "report_sections": plan["report_sections"],
        "status": "planned",
    }


async def search_web(state: ResearchState) -> dict:
    new_results = await search_queries(state["task_id"], state["research_plan"][:3])
    return {
        "search_results": state.get("search_results", []) + new_results,
        "status": "searched",
    }


async def summarize_results(state: ResearchState) -> dict:
    summary = await summarize_search_results(
        task_id=state["task_id"],
        user_query=state["user_query"],
        results=state["search_results"][-10:],
    )
    return {
        "summaries": state.get("summaries", []) + [summary["summary"]],
        "status": "summarized",
    }


async def critique_answer(state: ResearchState) -> dict:
    summary = state["summaries"][-1] if state["summaries"] else ""
    critique = await critique_summary(
        task_id=state["task_id"],
        user_query=state["user_query"],
        summary=summary,
    )
    return {
        "critique": critique,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "status": "critiqued",
    }


async def generate_report(state: ResearchState) -> dict:
    report = await generate_final_report(
        task_id=state["task_id"],
        user_query=state["user_query"],
        summaries=state.get("summaries", []),
    )
    return {"final_report": report, "status": "completed"}


def should_continue(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
        return "search_web"
    return "generate_report"
