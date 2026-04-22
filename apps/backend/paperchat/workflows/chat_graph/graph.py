from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from paperchat.providers import get_conversation_chat_model


class ChatGraphState(TypedDict):
    session_scope: str
    user_input: str
    context_summary: str
    retrieved_context: str
    response_text: str


def build_chat_graph():
    model = get_conversation_chat_model()

    async def load_context(state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": "正在加载会话上下文"})
        return {"context_summary": "已加载最近的会话上下文"}

    async def maybe_retrieve_context(state: ChatGraphState):
        writer = get_stream_writer()
        if state["session_scope"] == "workspace":
            writer(
                {
                    "kind": "tool",
                    "status": "started",
                    "tool": "retrieve_workspace_context",
                    "detail": "开始检索工作区上下文",
                }
            )
            writer(
                {
                    "kind": "tool",
                    "status": "completed",
                    "tool": "retrieve_workspace_context",
                    "detail": "已检索到主题探索包与知识片段",
                }
            )
            return {"retrieved_context": "工作区上下文：已绑定主题探索包与知识库片段"}

        writer({"kind": "info", "detail": "当前为默认收件箱会话，不触发工作区检索"})
        return {"retrieved_context": ""}

    async def call_model(state: ChatGraphState):
        system_prompt = (
            "你是 PaperChatAgent 的研究助手。请基于上下文帮助用户收束研究问题，"
            "给出下一步建议，并保持回答简洁、专业、可执行。"
        )
        if state["retrieved_context"]:
            system_prompt += f"\n\n可用上下文：{state['retrieved_context']}"
        response = await model.ainvoke(
            [
                SystemMessage(content=system_prompt),
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
