from __future__ import annotations

import json


MEMORY_SUMMARY_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 的会话记忆压缩器。"
    "\n\n"
    "你的任务不是回答用户，而是把较早的会话内容压缩成适合后续聊天继续参考的短期记忆。"
    "你必须输出严格 JSON，不要输出解释文字、Markdown 或代码块。"
)

MEMORY_EXTRACTION_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 的长期记忆提取器。"
    "\n\n"
    "你的任务是从最近对话中提取适合长期保存的稳定用户信息。"
    "只保留对后续交流长期有价值的内容，例如偏好、长期目标、约束、背景、身份信息。"
    "你必须输出严格 JSON，不要输出解释文字、Markdown 或代码块。"
)


def build_memory_summary_prompt(
    *,
    conversation_title: str,
    existing_summary: dict | None,
    transcript: str,
    compressed_message_count: int,
) -> str:
    return (
        "请把下面较早的对话压缩成会话短期记忆 JSON。"
        "\n\n"
        "返回字段必须包含：summary, key_points, user_preferences, open_questions。"
        "\n"
        "summary 是一段精炼文字，描述到目前为止对话已经确认的背景与进展。"
        "\n"
        "key_points, user_preferences, open_questions 必须是字符串数组。"
        "\n"
        "如果历史摘要里已有内容，请在其基础上增量合并，不要丢失仍然重要的信息。"
        "\n"
        "不要记录系统内部实现细节，不要虚构事实。"
        "\n\n"
        f"当前会话标题：{conversation_title}\n"
        f"已经压缩过的消息数：{compressed_message_count}\n"
        f"已有历史摘要：{json.dumps(existing_summary, ensure_ascii=False) if existing_summary else 'null'}\n\n"
        "需要压缩的新会话内容：\n"
        f"{transcript}\n\n"
        "请返回 JSON，格式如下：\n"
        '{'
        '"summary":"",'
        '"key_points":[""],'
        '"user_preferences":[""],'
        '"open_questions":[""]'
        '}'
    )


def build_memory_extraction_prompt(
    *,
    conversation_title: str,
    transcript: str,
    existing_memories: list[dict],
) -> str:
    return (
        "请从下面最近一轮或几轮对话中提取适合长期保存的用户记忆 JSON。"
        "\n\n"
        "只保留稳定、可复用、对后续交流长期有帮助的信息。"
        "\n"
        "以下内容通常可以保存：用户偏好、长期目标、固定约束、背景信息、身份特征。"
        "\n"
        "以下内容通常不要保存：一次性临时请求、明显过期的信息、纯上下文噪音。"
        "\n"
        "返回字段必须包含 memories。"
        "\n"
        "memories 必须是数组，每个元素必须包含：memory_type, title, content, tags, confidence。"
        "\n"
        "memory_type 只能是：preference, goal, constraint, background, identity。"
        "\n"
        "tags 必须是字符串数组，confidence 是 0 到 100 的整数。"
        "\n"
        "如果没有值得长期保存的内容，请返回 {\"memories\":[]}。"
        "\n\n"
        f"当前会话标题：{conversation_title}\n"
        f"已有相关长期记忆：{json.dumps(existing_memories, ensure_ascii=False) if existing_memories else '[]'}\n\n"
        "最近对话内容：\n"
        f"{transcript}\n\n"
        "请返回 JSON，格式如下：\n"
        '{'
        '"memories":['
        '{"memory_type":"preference","title":"","content":"","tags":[""],"confidence":80}'
        ']'
        '}'
    )
