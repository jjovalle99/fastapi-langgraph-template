import json
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from pydantic import UUID4

from app.models.api.requests import ChatbotRequest
from app.models.api.responses import ChatbotResponse

from ..dependencies import ChatRouteDependencies

router = APIRouter(tags=["chat"])


async def create_sse_stream(
    user_id: UUID4,
    thread_id: UUID4,
    request: ChatbotRequest,
    graph: CompiledStateGraph,
) -> AsyncIterator[str]:
    async for event in graph.astream_events(
        input={"messages": [{"role": "user", "content": request.content}]},
        config={
            "configurable": {
                "llm": request.chat_model_settings.model_dump(),
                "thread_id": str(thread_id),
            },
            "metadata": {"user_id": str(user_id)},
        },
        version="v2",
        exclude_names=["_write"],
        stream_mode=["custom"],
    ):
        kind = event.get("event", "")
        name = event.get("name", "")
        if kind == "on_chain_stream" and name == "LangGraph":
            jsonable_event = jsonable_encoder(obj=event)
            text = jsonable_event.get("data", {})["chunk"][1]
            payload = {"token": text}
            yield f"event: text-chunk\ndata: {json.dumps(payload)}\n\n"

    yield f"event: stream-end\ndata: {json.dumps({'status': 'success'})}\n\n"


@router.post(
    "/completion/{user_id}/{thread_id}",
    status_code=200,
    response_model=ChatbotResponse,
)
async def complete_chatbot_response(
    chat_dependencies: Annotated[
        ChatRouteDependencies, Depends(ChatRouteDependencies)
    ],
) -> dict[str, str]:
    graph_output = await chat_dependencies.graph.ainvoke(
        input={
            "messages": [
                {"role": "user", "content": chat_dependencies.request.content}
            ]
        },
        config={
            "configurable": {
                "llm": chat_dependencies.request.chat_model_settings.model_dump(),
                "thread_id": str(chat_dependencies.thread_id),
            },
            "metadata": {"user_id": str(chat_dependencies.user_id)},
        },
    )
    assistant_message = graph_output["messages"][-1]
    text = assistant_message["content"][0]["text"]

    return {"content": text}


@router.post(
    "/stream/{user_id}/{thread_id}",
    status_code=200,
)
async def stream_chatbot_response(
    chat_dependencies: Annotated[
        ChatRouteDependencies, Depends(ChatRouteDependencies)
    ],
) -> StreamingResponse:
    return StreamingResponse(
        content=create_sse_stream(
            user_id=chat_dependencies.user_id,
            thread_id=chat_dependencies.thread_id,
            request=chat_dependencies.request,
            graph=chat_dependencies.graph,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
