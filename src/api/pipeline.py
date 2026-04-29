"""
Pipeline introspection endpoints.

GET /api/v1/pipeline/graph         — Mermaid diagram source (text)
GET /api/v1/pipeline/graph/png     — PNG image of the graph
GET /api/v1/pipeline/trace/{event_id}  — SSE stream of per-node events
"""
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response, StreamingResponse

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])


def _get_mermaid() -> str:
    from src.graph.pipeline import pipeline
    return pipeline.get_graph().draw_mermaid()


@router.get(
    "/graph",
    response_class=PlainTextResponse,
    summary="Mermaid source of the LangGraph pipeline — paste at https://mermaid.live",
)
def get_graph_mermaid() -> str:
    return _get_mermaid()


@router.get(
    "/graph/png",
    responses={200: {"content": {"image/png": {}}}},
    summary="PNG image of the LangGraph pipeline",
)
def get_graph_png() -> Response:
    from src.graph.pipeline import pipeline
    try:
        png_bytes = pipeline.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception as exc:
        # Fallback: return the Mermaid source as plain text with instructions
        mmd = _get_mermaid()
        return PlainTextResponse(
            content=(
                f"PNG rendering unavailable ({exc}).\n\n"
                f"Paste the Mermaid source below at https://mermaid.live\n\n{mmd}"
            ),
            status_code=200,
        )


@router.get(
    "/trace/{event_id}",
    response_class=StreamingResponse,
    summary="SSE stream of per-node execution events for a pipeline run",
)
async def trace_event(event_id: str) -> StreamingResponse:
    """
    Subscribe to live per-node events for a specific pipeline run.
    Each SSE message has:
      event: node_start | node_end | pipeline_complete | pipeline_error
      data:  JSON with node, iteration, status, finding/decision
    """
    from src import events as event_bus

    async def _generate():
        async for payload in event_bus.subscribe(event_id):
            import json
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
