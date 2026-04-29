import asyncio
import json
import logging

import grpc
from langchain_core.messages import HumanMessage
from langchain_openrouter import ChatOpenRouter

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import summarizer_pb2, summarizer_pb2_grpc

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


class SummarizerServicer(summarizer_pb2_grpc.SummarizerServiceServicer):
    async def Summarize(self, request, context):
        results_text = "\n\n".join(
            f"Source: {result.url or 'unknown'}\n{result.content[:500]}"
            for result in request.results
        )

        prompt = f"""Summarize the following research results for: {request.user_query}

Results:
{results_text}

Return a JSON object with:
- "summary": a structured paragraph with key facts, preserving source URLs
- "key_points": list of 3-5 concise strings highlighting the most important findings

Return only valid JSON. No markdown fences."""

        try:
            response = await asyncio.wait_for(
                _llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            parsed = _parse_json_object(str(response.content))
        except Exception as exc:
            logger.warning("Summarizer returned invalid JSON; falling back: %s", exc)
            parsed = {
                "summary": " ".join(
                    result.content[:300] for result in request.results[:3]
                ),
                "key_points": [],
            }

        citations = [result.url for result in request.results if result.url]
        return summarizer_pb2.SummarizeResponse(
            summary=parsed.get("summary", ""),
            key_points=parsed.get("key_points") or [],
            citations=citations,
        )
