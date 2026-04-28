import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import critic_pb2, critic_pb2_grpc

GRPC_TIMEOUT_SECONDS = 75


async def critique_summary(task_id: str, user_query: str, summary: str) -> dict:
    async with grpc.aio.insecure_channel(settings.critic_agent_address) as channel:
        stub = critic_pb2_grpc.CriticServiceStub(channel)
        try:
            response = await stub.Critique(
                critic_pb2.CritiqueRequest(
                    task_id=task_id,
                    user_query=user_query,
                    summary=summary,
                ),
                timeout=GRPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            raise RuntimeError(f"Critic gRPC failed: {exc.details()}") from exc

    return {
        "score": response.score,
        "missing_points": list(response.missing_points),
        "needs_more_research": response.needs_more_research,
    }
