from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    critique_answer,
    generate_report,
    plan_research,
    search_web,
    should_continue,
    summarize_results,
)
from app.graph.state import ResearchState


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("plan_research", plan_research)
    graph.add_node("search_web", search_web)
    graph.add_node("summarize_results", summarize_results)
    graph.add_node("critique_answer", critique_answer)
    graph.add_node("generate_report", generate_report)

    graph.set_entry_point("plan_research")

    graph.add_edge("plan_research", "search_web")
    graph.add_edge("search_web", "summarize_results")
    graph.add_edge("summarize_results", "critique_answer")
    graph.add_conditional_edges(
        "critique_answer",
        should_continue,
        {
            "search_web": "search_web",
            "generate_report": "generate_report",
        },
    )
    graph.add_edge("generate_report", END)

    return graph.compile()


research_graph = build_graph()
