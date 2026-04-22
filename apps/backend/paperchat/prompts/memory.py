from __future__ import annotations


def build_session_memory_summary_prompt(*, existing_summary: str = "", conversation_text: str) -> str:
    return (
        "请把以下聊天历史压缩成后续对话可复用的长期摘要，"
        "保留：用户目标、已确认的约束、重要结论、待跟进问题。"
        "输出简洁中文摘要。\n\n"
        f"已有摘要：\n{existing_summary or '（暂无）'}\n\n"
        f"新增历史：\n{conversation_text}"
    )
