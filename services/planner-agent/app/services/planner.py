import asyncio
import json
import logging

import grpc
from langchain_core.messages import HumanMessage
from langchain_openrouter import ChatOpenRouter

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import planner_pb2, planner_pb2_grpc

logger = logging.getLogger(__name__)
LLM_TIMEOUT_SECONDS = 60

_llm = ChatOpenRouter(
    model=settings.openrouter_model,
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
    temperature=0,
)


def _parse_json_object(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return json.loads(text)


class PlannerServicer(planner_pb2_grpc.PlannerServiceServicer):
    async def CreatePlan(self, request, context):
        prompt = f"""You are a research planner. Given the user question, return a JSON object with:
- "search_queries": list of 3-5 specific search queries
- "report_sections": list of section headings for the final report

User question: {request.user_query}

Return only valid JSON. No markdown fences."""

        try:
            response = await asyncio.wait_for(
                _llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            plan = _parse_json_object(str(response.content))
        except Exception as exc:
            logger.warning("Planner returned invalid JSON; falling back: %s", exc)
            plan = {
                "search_queries": [request.user_query],
                "report_sections": ["Overview", "Key Findings", "Conclusion"],
            }

        return planner_pb2.PlanResponse(
            search_queries=plan.get("search_queries") or [request.user_query],
            report_sections=plan.get("report_sections") or [],
        )
