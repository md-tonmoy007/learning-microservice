from typing import TypedDict


class ResearchState(TypedDict):
    task_id: str
    user_query: str
    research_plan: list[str]       # search queries produced by planner
    report_sections: list[str]     # section headings produced by planner
    search_results: list[dict]     # raw results from Tavily
    summaries: list[str]           # one summary string per iteration
    critique: dict                 # {"score": float, "missing_points": [...], "needs_more_research": bool}
    final_report: str
    iteration_count: int
    status: str
