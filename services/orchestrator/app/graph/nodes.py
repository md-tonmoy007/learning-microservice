import json

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.graph.state import ResearchState

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_search = TavilySearchResults(max_results=5)


async def plan_research(state: ResearchState) -> dict:
    prompt = f"""You are a research planner. Given the user question, return a JSON object with:
- "search_queries": list of 3-5 specific search queries
- "report_sections": list of section headings for the final report

User question: {state["user_query"]}

Return only valid JSON. No markdown fences."""

    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    try:
        plan = json.loads(response.content)
        queries = plan.get("search_queries", [state["user_query"]])
    except json.JSONDecodeError:
        queries = [state["user_query"]]

    return {"research_plan": queries, "status": "planned"}


async def search_web(state: ResearchState) -> dict:
    new_results: list[dict] = []
    for query in state["research_plan"][:3]:  # cap at 3 queries per iteration
        try:
            results = await _search.ainvoke(query)
            if isinstance(results, list):
                new_results.extend(results)
        except Exception:
            pass

    return {
        "search_results": state.get("search_results", []) + new_results,
        "status": "searched",
    }


async def summarize_results(state: ResearchState) -> dict:
    results_text = "\n\n".join(
        f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')[:500]}"
        for r in state["search_results"][-10:]
    )

    prompt = f"""Summarize the following research results for: {state["user_query"]}

Results:
{results_text}

Write a structured summary with key facts. Preserve source URLs."""

    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    return {
        "summaries": state.get("summaries", []) + [response.content],
        "status": "summarized",
    }


async def critique_answer(state: ResearchState) -> dict:
    summary = state["summaries"][-1] if state["summaries"] else ""

    prompt = f"""You are a research critic. Evaluate this summary for: {state["user_query"]}

Summary:
{summary}

Return a JSON object with:
- "score": float 0.0-1.0 (quality)
- "missing_points": list of topics not covered
- "needs_more_research": boolean

Return only valid JSON. No markdown fences."""

    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    try:
        critique = json.loads(response.content)
    except json.JSONDecodeError:
        critique = {"score": 0.8, "missing_points": [], "needs_more_research": False}

    return {
        "critique": critique,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "status": "critiqued",
    }


async def generate_report(state: ResearchState) -> dict:
    combined = "\n\n---\n\n".join(state.get("summaries", []))

    prompt = f"""Generate a comprehensive research report for: {state["user_query"]}

Research findings:
{combined}

Format in markdown with clear sections, key findings, and a conclusion."""

    response = await _llm.ainvoke([HumanMessage(content=prompt)])
    return {"final_report": response.content, "status": "completed"}


def should_continue(state: ResearchState) -> str:
    critique = state.get("critique", {})
    if critique.get("needs_more_research") and state.get("iteration_count", 0) < 3:
        return "search_web"
    return "generate_report"
