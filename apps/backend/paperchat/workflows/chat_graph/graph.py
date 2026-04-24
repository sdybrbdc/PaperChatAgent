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
    response_text: str


RESEARCH_TRIGGER_WORDS = ("调用智能研究助手", "智能研究助手", "开始研究", "深入研究", "生成调研报告", "生成研究报告", "执行研究方案")


def _should_start_research_tool(user_input: str) -> bool:
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


def build_chat_graph():
    model = get_conversation_chat_model()

    async def load_context(_state: ChatGraphState):
        writer = get_stream_writer()
        writer({"kind": "info", "detail": CHAT_CONTEXT_LOADING_MESSAGE})
        writer({"kind": "info", "detail": CHAT_READY_MESSAGE})
        return {}

    async def call_model(state: ChatGraphState):
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
                system_prompt=(
                    build_chat_system_prompt()
                    + "\n\n当用户明确要求深入研究、生成调研/研究报告、执行研究方案，或点名调用智能研究助手时，"
                    "调用 start_smart_research_assistant。该工具会创建后台长任务，工具返回任务入口后你需要把入口转述给用户。"
                    "普通问答、方向澄清和闲聊不要调用工具。"
                ),
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
                    if _should_start_research_tool(state["user_input"]) and "/agents/runs/" not in response_text:
                        return {"response_text": await start_research(topic=state["user_input"])}
                    return {"response_text": response_text}
            except Exception:
                if _should_start_research_tool(state["user_input"]):
                    return {"response_text": await start_research(topic=state["user_input"])}

        if _should_start_research_tool(state["user_input"]):
            return {"response_text": await start_research(topic=state["user_input"])}

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
