from __future__ import annotations

from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat

from paperchat.providers import get_autogen_reasoning_model_client
from paperchat.workflows.state import DeepAnalysisResult, ReadingNote

from .retrieval_agent import create_retrieval_agent
from .review_agent import create_review_agent
from .writing_agent import create_writing_agent


SELECTOR_PROMPT = """请根据当前对话情境，从以下智能体中选择下一位执行者：

可用智能体：
{roles}

当前对话记录：
{history}

请在以下参与者中选择一位：{participants}。

选择逻辑：
1. 初始任务由 writing_agent 开始。
2. 当 writing_agent 需要补充证据、资料或上下文时，选择 retrieval_agent。
3. 当 writing_agent 完成章节草稿后，选择 review_agent。
4. 如果 review_agent 发现事实依据不足或缺少材料，回到 retrieval_agent。
5. 如果 review_agent 发现结构、表达或完整性问题，回到 writing_agent。
6. 如果 review_agent 输出 APPROVE，则当前章节结束。

每次只返回一个参与者名字。
"""


def create_writing_group(
    *,
    reading_notes: list[ReadingNote],
    deep_analysis_results: list[DeepAnalysisResult],
    analysis_markdown: str,
):
    runtime_state: dict = {"retrieved_contexts": []}
    writing_agent = create_writing_agent()
    retrieval_agent = create_retrieval_agent(
        reading_notes=reading_notes,
        deep_analysis_results=deep_analysis_results,
        analysis_markdown=analysis_markdown,
        runtime_state=runtime_state,
    )
    review_agent = create_review_agent()

    team = SelectorGroupChat(
        [writing_agent, retrieval_agent, review_agent],
        model_client=get_autogen_reasoning_model_client(),
        termination_condition=TextMentionTermination("APPROVE", sources=["review_agent"]),
        selector_prompt=SELECTOR_PROMPT,
        allow_repeated_speaker=False,
        model_client_streaming=True,
    )
    return team, runtime_state
