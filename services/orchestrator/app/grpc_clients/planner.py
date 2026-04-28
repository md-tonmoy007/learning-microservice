import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import planner_pb2, planner_pb2_grpc

GRPC_TIMEOUT_SECONDS = 75


async def create_plan(task_id: str, user_query: str) -> dict:
    async with grpc.aio.insecure_channel(settings.planner_agent_address) as channel:
        stub = planner_pb2_grpc.PlannerServiceStub(channel)
        try:
            response = await stub.CreatePlan(
                planner_pb2.PlanRequest(task_id=task_id, user_query=user_query),
                timeout=GRPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            raise RuntimeError(f"Planner gRPC failed: {exc.details()}") from exc

    return {
        "search_queries": list(response.search_queries) or [user_query],
        "report_sections": list(response.report_sections),
    }
