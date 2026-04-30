import asyncio

import grpc
from opentelemetry.instrumentation.grpc import GrpcAioInstrumentorServer

from app.core.config import settings
from app.core.telemetry import setup_telemetry
from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import search_pb2_grpc
from app.services.search import SearchServicer

setup_telemetry("search-agent", settings.otel_endpoint)
GrpcAioInstrumentorServer().instrument()


async def serve() -> None:
    server = grpc.aio.server()
    search_pb2_grpc.add_SearchServiceServicer_to_server(SearchServicer(), server)
    server.add_insecure_port(f"[::]:{settings.grpc_port}")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())
