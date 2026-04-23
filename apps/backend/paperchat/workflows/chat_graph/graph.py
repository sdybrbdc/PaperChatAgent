from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from paperchat.prompts import CHAT_CONTEXT_LOADING_MESSAGE, CHAT_READY_MESSAGE, build_chat_system_prompt
from paperchat.providers import get_conversation_chat_model


class ChatGraphState(TypedDict):
    conversation_id: str
    user_input: str
    recent_messages: list[BaseMessage]
    response_text: str


def build_chat_graph():
    model = get_conversation_chat_model()

    async def load_context(_state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": CHAT_CONTEXT_LOADING_MESSAGE})
        writer({"kind": "info", "detail": CHAT_READY_MESSAGE})
        return {}

    async def call_model(state: ChatGraphState):
        response = await model.ainvoke(
            [
                SystemMessage(content=build_chat_system_prompt()),
                *state.get("recent_messages", []),
                HumanMessage(content=state["user_input"]),
            ]
        )
        return {"response_text": response.content}

    graph = StateGraph(ChatGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()
