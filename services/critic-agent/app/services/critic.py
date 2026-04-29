import asyncio
import json
import logging

import grpc
from langchain_core.messages import HumanMessage
from langchain_openrouter import ChatOpenRouter

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import critic_pb2, critic_pb2_grpc

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


class CriticServicer(critic_pb2_grpc.CriticServiceServicer):
    async def Critique(self, request, context):
        prompt = f"""You are a research critic. Evaluate this summary for: {request.user_query}

Summary:
{request.summary}

Return a JSON object with:
- "score": float 0.0-1.0 (quality)
- "missing_points": list of topics not covered
- "needs_more_research": boolean

Return only valid JSON. No markdown fences."""

        try:
            response = await asyncio.wait_for(
                _llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            critique = _parse_json_object(str(response.content))
        except Exception as exc:
            logger.warning("Critic returned invalid JSON; falling back: %s", exc)
            critique = {
                "score": 0.8,
                "missing_points": [],
                "needs_more_research": False,
            }

        return critic_pb2.CritiqueResponse(
            score=float(critique.get("score", 0.8)),
            missing_points=critique.get("missing_points") or [],
            needs_more_research=bool(critique.get("needs_more_research", False)),
        )
