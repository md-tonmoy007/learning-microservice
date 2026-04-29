import asyncio

import grpc

from app.core.config import settings
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import report_pb2_grpc
from app.services.report import ReportServicer


async def serve() -> None:
    server = grpc.aio.server()
    report_pb2_grpc.add_ReportServiceServicer_to_server(ReportServicer(), server)
    server.add_insecure_port(f"[::]:{settings.grpc_port}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
