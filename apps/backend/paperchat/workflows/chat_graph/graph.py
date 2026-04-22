from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from paperchat.providers import get_conversation_chat_model


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
        writer({"kind": "info", "detail": "正在加载当前会话上下文"})

        if state.get("memory_summary_text", "").strip():
            writer({"kind": "info", "detail": "已加载当前会话长期摘要"})

        return {
            "context_summary": state.get("memory_summary_text", "").strip(),
        }

    async def maybe_retrieve_context(state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": "当前无额外上下文检索"})
        return {"retrieved_context": ""}

    async def call_model(state: ChatGraphState):
        system_prompt = (
            "你是 PaperChatAgent 的研究助手。请基于上下文帮助用户收束研究问题，"
            "给出下一步建议，并保持回答简洁、专业、可执行。"
        )
        if state["context_summary"]:
            system_prompt += f"\n\n当前会话长期摘要：\n{state['context_summary']}"
        if state["retrieved_context"]:
            system_prompt += f"\n\n补充上下文：\n{state['retrieved_context']}"

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
