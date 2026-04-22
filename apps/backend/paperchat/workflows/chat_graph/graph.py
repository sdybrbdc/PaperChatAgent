from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from paperchat.providers import get_conversation_chat_model
from paperchat.prompts import (
    CHAT_CONTEXT_LOADING_MESSAGE,
    CHAT_MEMORY_LOADED_MESSAGE,
    CHAT_NO_EXTRA_CONTEXT_MESSAGE,
    build_chat_system_prompt,
)


class ChatGraphState(TypedDict):
    session_scope: str
    session_id: str
    user_input: str
    context_summary: str
    retrieved_context: str
    recent_messages: list[BaseMessage]
    memory_summary_text: str
    response_text: str


def build_chat_graph():
    model = get_conversation_chat_model()

    async def load_context(state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": CHAT_CONTEXT_LOADING_MESSAGE})

        summary_text = (state.get("memory_summary_text") or "").strip()
        if summary_text:
            writer({"kind": "info", "detail": CHAT_MEMORY_LOADED_MESSAGE})

        return {
            "context_summary": summary_text,
        }

    async def maybe_retrieve_context(state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": CHAT_NO_EXTRA_CONTEXT_MESSAGE})
        return {"retrieved_context": ""}

    async def call_model(state: ChatGraphState):
        system_prompt = build_chat_system_prompt(
            memory_summary_text=state["context_summary"],
            retrieved_context=state["retrieved_context"],
        )

        response = await model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                *state.get("recent_messages", []),
                HumanMessage(content=state["user_input"]),
            ]
        )
        return {"response_text": response.content}

    graph = StateGraph(ChatGraphState)
    graph.add_node("load_context", load_context)
    graph.add_node("maybe_retrieve_context", maybe_retrieve_context)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "maybe_retrieve_context")
    graph.add_edge("maybe_retrieve_context", "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()
