from __future__ import annotations

from autogen_agentchat.agents import AssistantAgent

from paperchat.providers import get_autogen_reasoning_model_client
from paperchat.workflows.state import ReviewResult


REVIEW_AGENT_PROMPT = """
你是一个专业的学术审查助手，负责检查章节草稿质量。

审查要求：
1. 检查章节是否回应当前小节任务。
2. 检查逻辑是否清晰，语言是否学术化。
3. 检查是否存在明显编造、空泛或重复。

如果章节没有明显问题，只输出：APPROVE
如果章节需要修改，给出具体修改意见，不要输出 APPROVE。
"""


def create_review_agent() -> AssistantAgent:
    return AssistantAgent(
        name="review_agent",
        description="负责审核章节草稿质量。",
        model_client=get_autogen_reasoning_model_client(),
        system_message=REVIEW_AGENT_PROMPT,
        model_client_stream=True,
    )


def parse_review_result(text: str) -> ReviewResult:
    approved = "APPROVE" in text.upper()
    return {
        "approved": approved,
        "feedback": "APPROVE" if approved else text.strip(),
    }
