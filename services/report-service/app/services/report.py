import asyncio

import grpc
from langchain_core.messages import HumanMessage
from langchain_openrouter import ChatOpenRouter

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import report_pb2, report_pb2_grpc

LLM_TIMEOUT_SECONDS = 60

_llm = ChatOpenRouter(
    model=settings.openrouter_model,
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
    temperature=0,
)


class ReportServicer(report_pb2_grpc.ReportServiceServicer):
    async def GenerateReport(self, request, context):
        combined = "\n\n---\n\n".join(request.summaries)

        prompt = f"""Generate a comprehensive research report for: {request.user_query}

Research findings:
{combined}

        Format in markdown with clear sections, key findings, and a conclusion."""

        try:
            response = await asyncio.wait_for(
                _llm.ainvoke([HumanMessage(content=prompt)]),
                timeout=LLM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            report = f"""# Research Report

## Findings

{combined or "No research findings were available."}

## Conclusion

The report service could not synthesize a model-written final report: {exc}
"""
            return report_pb2.ReportResponse(report_markdown=report)

        return report_pb2.ReportResponse(report_markdown=response.content)
