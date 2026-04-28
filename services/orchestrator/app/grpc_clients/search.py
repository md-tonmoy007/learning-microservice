import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import search_pb2, search_pb2_grpc

GRPC_TIMEOUT_SECONDS = 45


async def search_queries(task_id: str, queries: list[str]) -> list[dict]:
    async with grpc.aio.insecure_channel(settings.search_agent_address) as channel:
        stub = search_pb2_grpc.SearchServiceStub(channel)
        try:
            response = await stub.Search(
                search_pb2.SearchRequest(task_id=task_id, queries=queries),
                timeout=GRPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            raise RuntimeError(f"Search gRPC failed: {exc.details()}") from exc

    return [
        {
            "title": result.title,
            "url": result.url,
            "content": result.content,
            "source_type": result.source_type,
        }
        for result in response.results
    ]
