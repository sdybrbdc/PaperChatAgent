from __future__ import annotations

from autogen_agentchat.agents import AssistantAgent

from paperchat.providers import get_autogen_reasoning_model_client


WRITING_AGENT_PROMPT = """
你是一位专业的学术作者，负责根据现有资料撰写当前章节。

要求：
1. 只围绕当前小节任务写作。
2. 优先利用检索结果和已有分析，不要虚构外部事实。
3. 保持学术化、克制、清晰。
4. 不要输出审查意见，也不要输出 APPROVE。
"""


def create_writing_agent() -> AssistantAgent:
    return AssistantAgent(
        name="writing_agent",
        description="负责撰写章节草稿。",
        model_client=get_autogen_reasoning_model_client(),
        system_message=WRITING_AGENT_PROMPT,
        model_client_stream=True,
    )
