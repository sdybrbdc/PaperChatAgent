from __future__ import annotations


CHAT_CONTEXT_LOADING_MESSAGE = "正在加载当前会话上下文"
CHAT_MEMORY_LOADED_MESSAGE = "已加载当前会话长期摘要"
CHAT_NO_EXTRA_CONTEXT_MESSAGE = "当前无额外上下文检索"

CHAT_STREAM_NODE_DETAILS = {
    "load_context": "会话上下文已加载",
    "maybe_retrieve_context": "附加上下文阶段已完成",
    "call_model": "模型生成阶段已完成",
}

CHAT_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 的研究助手。"
    "请基于当前会话上下文帮助用户收束研究问题，"
    "给出下一步建议，并保持回答简洁、专业、可执行。"
)


def build_chat_system_prompt(*, memory_summary_text: str = "", retrieved_context: str = "") -> str:
    prompt = CHAT_SYSTEM_PROMPT
    if memory_summary_text.strip():
        prompt += f"\n\n当前会话长期摘要：\n{memory_summary_text.strip()}"
    if retrieved_context.strip():
        prompt += f"\n\n补充上下文：\n{retrieved_context.strip()}"
    return prompt


def build_session_memory_summary_prompt(*, existing_summary: str = "", conversation_text: str) -> str:
    return (
        "请把以下聊天历史压缩成后续对话可复用的长期摘要，"
        "保留：用户目标、已确认的约束、重要结论、待跟进问题。"
        "输出简洁中文摘要。\n\n"
        f"已有摘要：\n{existing_summary or '（暂无）'}\n\n"
        f"新增历史：\n{conversation_text}"
    )
