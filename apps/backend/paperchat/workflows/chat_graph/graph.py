from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from paperchat.prompts import CHAT_CONTEXT_LOADING_MESSAGE, CHAT_READY_MESSAGE, build_chat_system_prompt
from paperchat.providers import get_conversation_chat_model
from paperchat.services.agents import agent_service

try:
    from langchain.agents import create_agent
    from langchain.tools import tool
except Exception:  # pragma: no cover - optional until LangChain v1 is installed
    create_agent = None
    tool = None


class ChatGraphState(TypedDict):
    user_id: str
    conversation_id: str
    user_input: str
    recent_messages: list[BaseMessage]
    conversation_memory: dict[str, Any] | None
    user_memories: list[dict[str, Any]]
    response_text: str


RESEARCH_TRIGGER_WORDS = ("调用智能研究助手", "智能研究助手", "开始研究", "深入研究", "生成调研报告", "生成研究报告", "执行研究方案")


def should_start_research_tool(user_input: str) -> bool:
    return any(keyword in user_input for keyword in RESEARCH_TRIGGER_WORDS)


def _last_agent_message_content(result: dict[str, Any]) -> str:
    messages = result.get("messages", []) if isinstance(result, dict) else []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item) for item in content)
    return str(content)


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if text:
                    parts.append(str(text))
                continue
            text = getattr(item, "text", "") or getattr(item, "content", "")
            if text:
                parts.append(str(text))
        return "".join(parts)
    text = getattr(content, "text", "") or getattr(content, "content", "")
    if text:
        return str(text)
    return str(content) if content else ""


def build_chat_graph():
    model = get_conversation_chat_model()

    async def load_memory(state: ChatGraphState):
        writer = get_stream_writer()
        conversation_memory = state.get("conversation_memory") or {}
        user_memories = state.get("user_memories") or []
        if conversation_memory.get("summary"):
            writer({"kind": "info", "detail": "已载入短期会话记忆摘要"})
        if user_memories:
            writer({"kind": "info", "detail": f"已载入 {len(user_memories)} 条用户长期记忆"})
        return {}

    async def load_context(_state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": CHAT_CONTEXT_LOADING_MESSAGE})
        writer({"kind": "info", "detail": CHAT_READY_MESSAGE})
        return {}

    async def call_model(state: ChatGraphState):
        writer = get_stream_writer()
        system_prompt = build_chat_system_prompt(
            conversation_memory=state.get("conversation_memory"),
            user_memories=state.get("user_memories") or [],
        )

        async def start_research(topic: str, max_papers: int = 6) -> str:
            payload = await agent_service.create_smart_research_run_from_chat(
                user_id=state["user_id"],
                conversation_id=state["conversation_id"],
                topic=topic,
                max_papers=max_papers,
            )
            return (
                "已创建智能研究助手任务。\n\n"
                f"- 任务：{payload['title']}\n"
                f"- 状态：{payload['status']}\n"
                f"- 运行 ID：{payload['id']}\n"
                f"- [查看任务进度与报告]({payload['detail_url']})"
            )

        if create_agent is not None and tool is not None:
            @tool
            async def start_smart_research_assistant(topic: str, max_papers: int = 6) -> str:
                """启动智能研究助手长任务，适用于用户要求深入研究、生成研究报告或执行研究方案。"""
                return await start_research(topic=topic, max_papers=max_papers)

            agent = create_agent(
                model,
                tools=[start_smart_research_assistant],
                system_prompt=system_prompt,
            )
            try:
                result = await agent.ainvoke(
                    {
                        "messages": [
                            *state.get("recent_messages", []),
                            HumanMessage(content=state["user_input"]),
                        ]
                    }
                )
                response_text = _last_agent_message_content(result).strip()
                if response_text:
                    if should_start_research_tool(state["user_input"]) and "/agents/runs/" not in response_text:
                        return {"response_text": await start_research(topic=state["user_input"])}
                    return {"response_text": response_text}
            except Exception:
                if should_start_research_tool(state["user_input"]):
                    return {"response_text": await start_research(topic=state["user_input"])}

        if should_start_research_tool(state["user_input"]):
            return {"response_text": await start_research(topic=state["user_input"])}

        chunks: list[str] = []
        async for response_chunk in model.astream(
            [
                SystemMessage(content=system_prompt),
                *state.get("recent_messages", []),
                HumanMessage(content=state["user_input"]),
            ]
        ):
            delta = _content_to_text(getattr(response_chunk, "content", ""))
            if not delta:
                continue
            chunks.append(delta)
            writer({"kind": "delta", "delta": delta})

        response_text = "".join(chunks)
        if response_text.strip():
            return {"response_text": response_text}

        response = await model.ainvoke(
            [
                SystemMessage(content=system_prompt),
                *state.get("recent_messages", []),
                HumanMessage(content=state["user_input"]),
            ]
        )
        return {"response_text": response.content}

    graph = StateGraph(ChatGraphState)
    graph.add_node("load_memory", load_memory)
    graph.add_node("load_context", load_context)
    graph.add_node("call_model", call_model)
    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "load_context")
    graph.add_edge("load_context", "call_model")
    graph.add_edge("call_model", END)
    return graph.compile()
