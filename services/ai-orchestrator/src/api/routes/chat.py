"""
Chat endpoint — accepts clinical queries, streams AI responses via SSE.

The .NET gateway proxies SSE from this endpoint to the Angular frontend.
Each token arrives as a server-sent event so the UI renders progressively.
"""

import json
import logging
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config import Settings, get_settings
from src.models.clinical_state import QueryType, initial_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    patient_id: str = Field(..., min_length=1)
    encounter_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    stream: bool = Field(default=True)


class ChatResponse(BaseModel):
    trace_id: str
    answer: str
    agents_used: list[str]
    model_used: str
    prompt_version: str
    citation_count: int
    insufficient_data: bool


async def _run_agent_graph(
    request: ChatRequest,
    trace_id: str,
    settings: Settings,
) -> dict:
    """Run the full LangGraph agent pipeline and return the final state."""
    from src.agents.supervisor import build_graph
    from src.llm.cache import SemanticCache

    cache = SemanticCache(settings)

    # Level 1: Exact cache check
    cached = cache.get_exact(request.query, request.patient_id)
    if cached:
        logger.info(f"[{trace_id}] Exact cache HIT")
        return {"answer": cached, "from_cache": True}

    # Build and run graph
    state = initial_state(
        query=request.query,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        user_id=request.user_id,
        trace_id=trace_id,
    )

    graph = build_graph(settings)
    final_state = graph.invoke(state)

    if final_state.get("error"):
        raise HTTPException(status_code=500, detail=final_state["error"])

    response = final_state.get("final_response")
    if not response:
        raise HTTPException(status_code=500, detail="No response generated")

    # Cache the result
    cache.set_exact(request.query, request.patient_id, response.answer)

    return {"response": response, "from_cache": False}


async def _stream_response(
    request: ChatRequest,
    trace_id: str,
    settings: Settings,
) -> AsyncGenerator[dict, None]:
    """
    Generate SSE events for a streaming chat response.

    Event types:
      - "token"    — a single word/token chunk for progressive rendering
      - "citation" — a citation badge (chunk reference)
      - "metadata" — final metadata (agents used, model, cost)
      - "done"     — signals stream completion
      - "error"    — error event
    """
    try:
        yield {"event": "start", "data": json.dumps({"trace_id": trace_id})}

        result = await _run_agent_graph.__wrapped__(request, trace_id, settings) \
            if hasattr(_run_agent_graph, "__wrapped__") \
            else await _run_agent_graph(request, trace_id, settings)

        if "answer" in result and result.get("from_cache"):
            # Stream cached answer word by word
            for word in result["answer"].split():
                yield {"event": "token", "data": word + " "}
        else:
            response = result["response"]
            # Stream answer tokens
            for word in response.answer.split():
                yield {"event": "token", "data": word + " "}

            # Emit citation events
            for chunk in response.citations:
                yield {
                    "event": "citation",
                    "data": json.dumps({
                        "chunk_id": chunk.chunk_id,
                        "source_type": chunk.source_type,
                        "timestamp": chunk.timestamp,
                        "score": chunk.rerank_score or chunk.similarity_score,
                    }),
                }

            # Final metadata event
            yield {
                "event": "metadata",
                "data": json.dumps({
                    "agents_used": [a.value for a in response.agents_used],
                    "model_used": response.model_used,
                    "prompt_version": response.prompt_version,
                    "insufficient_data": response.insufficient_data,
                    "citation_count": len(response.citations),
                }),
            }

        yield {"event": "done", "data": ""}

    except Exception as e:
        logger.error(f"[{trace_id}] Streaming error: {e}")
        yield {"event": "error", "data": json.dumps({"message": str(e)})}


@router.post("/stream", summary="Stream clinical AI response via SSE")
async def chat_stream(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Stream a clinical AI response using Server-Sent Events.

    The Angular frontend connects via EventSource and renders tokens progressively.
    Citations appear inline as they are identified.
    """
    trace_id = str(uuid.uuid4())
    logger.info(
        f"[{trace_id}] Chat request: patient={request.patient_id} "
        f"query='{request.query[:60]}...'"
    )

    return EventSourceResponse(
        _stream_response(request, trace_id, settings),
        media_type="text/event-stream",
    )


@router.post("", response_model=ChatResponse, summary="Non-streaming clinical AI response")
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """Non-streaming endpoint for programmatic access (evaluation pipeline, tests)."""
    trace_id = str(uuid.uuid4())
    result = await _run_agent_graph(request, trace_id, settings)

    if result.get("from_cache"):
        return ChatResponse(
            trace_id=trace_id,
            answer=result["answer"],
            agents_used=[],
            model_used="cache",
            prompt_version="cached",
            citation_count=0,
            insufficient_data=False,
        )

    response = result["response"]
    return ChatResponse(
        trace_id=trace_id,
        answer=response.answer,
        agents_used=[a.value for a in response.agents_used],
        model_used=response.model_used,
        prompt_version=response.prompt_version,
        citation_count=len(response.citations),
        insufficient_data=response.insufficient_data,
    )
