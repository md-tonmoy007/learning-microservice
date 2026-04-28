import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import report_pb2, report_pb2_grpc

GRPC_TIMEOUT_SECONDS = 75


async def generate_final_report(
    task_id: str,
    user_query: str,
    summaries: list[str],
) -> str:
    async with grpc.aio.insecure_channel(settings.report_service_address) as channel:
        stub = report_pb2_grpc.ReportServiceStub(channel)
        try:
            response = await stub.GenerateReport(
                report_pb2.ReportRequest(
                    task_id=task_id,
                    user_query=user_query,
                    summaries=summaries,
                ),
                timeout=GRPC_TIMEOUT_SECONDS,
            )
        except grpc.aio.AioRpcError as exc:
            raise RuntimeError(f"Report gRPC failed: {exc.details()}") from exc

    return response.report_markdown
