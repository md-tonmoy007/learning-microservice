import grpc
from langchain_community.tools.tavily_search import TavilySearchResults

from app.grpc_generated_path import ensure_grpc_generated_on_path

ensure_grpc_generated_on_path()

from app.grpc_generated import search_pb2, search_pb2_grpc

_search = TavilySearchResults(max_results=5)


class SearchServicer(search_pb2_grpc.SearchServiceServicer):
    async def Search(self, request, context):
        response_results = []

        for query in list(request.queries)[:3]:
            try:
                results = await _search.ainvoke(query)
            except Exception as exc:
                await context.abort(grpc.StatusCode.INTERNAL, str(exc))

            if not isinstance(results, list):
                continue

            for result in results:
                response_results.append(
                    search_pb2.SearchResult(
                        title=str(result.get("title", "")),
                        url=str(result.get("url", "")),
                        content=str(result.get("content", "")),
                        source_type=str(result.get("source_type", "web")),
                    )
                )

        return search_pb2.SearchResponse(results=response_results)
