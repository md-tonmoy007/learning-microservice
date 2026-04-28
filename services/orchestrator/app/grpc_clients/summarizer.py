import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import summarizer_pb2, summarizer_pb2_grpc

GRPC_TIMEOUT_SECONDS = 75


async def summarize_search_results(
    task_id: str,
    user_query: str,
    results: list[dict],
) -> dict:
    request_results = [
        summarizer_pb2.SearchResult(
            url=str(result.get("url", "")),
            content=str(result.get("content", "")),
        )
        for result in results
    ]

    async with grpc.aio.insecure_channel(settings.summarizer_agent_address) as channel:
        stub = summarizer_pb2_grpc.SummarizerServiceStub(channel)
        try:
            response = await stub.Summarize(
                summarizer_pb2.SummarizeRequest(
                    task_id=task_id,
                    user_query=user_query,
                    results=request_results,
                ),
                timeout=GRPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            raise RuntimeError(f"Summarizer gRPC failed: {exc.details()}") from exc

    return {
        "summary": response.summary,
        "key_points": list(response.key_points),
        "citations": list(response.citations),
    }
