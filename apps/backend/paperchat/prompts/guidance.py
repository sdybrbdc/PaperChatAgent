from __future__ import annotations

import json


GUIDANCE_STATUS_DESCRIPTIONS = {
    "casual_chat": "普通交流，主要是了解问题或随意聊天。",
    "topic_exploration": "正在探索研究方向，但问题仍较宽泛。",
    "needs_more_info": "已经有明确研究意图，但还缺关键信息。",
    "ready_for_draft": "信息已基本充分，可以手动生成研究草案。",
    "draft_ready": "研究草案已经生成，可以继续迭代。",
}

GUIDANCE_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 右侧专业提示区的分析器。"
    "\n\n"
    "你的任务不是回答用户，而是从当前会话中提炼一个结构化分析结果。"
    "你必须输出严格 JSON，不要输出解释文字、Markdown 或代码块。"
)

DRAFT_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 的研究草案生成器。"
    "\n\n"
    "你必须基于当前会话和 guidance 信息生成一个结构化 draft JSON。"
    "你必须输出严格 JSON，不要输出解释文字、Markdown 或代码块。"
)


def build_guidance_prompt(
    *,
    conversation_title: str,
    transcript: str,
    existing_headline: str,
    existing_draft: dict | None,
    should_suggest_title: bool,
) -> str:
    return (
        "请根据下面的会话内容，生成右侧专业提示区所需的结构化分析 JSON。"
        "\n\n"
        "允许的 status 只有："
        + ", ".join(f"{key}（{value}）" for key, value in GUIDANCE_STATUS_DESCRIPTIONS.items())
        + "\n\n"
        "返回字段必须包含：status, headline, recognized, suggested_steps, missing_info, suggested_title。"
        "\n"
        "headline 必须是面向右侧提示区顶部的一句精炼提示。"
        "\n"
        "recognized 必须包含这些键：topic, audience, goal, outputs, materials, agents。"
        "\n"
        "outputs, materials, agents 必须是字符串数组。"
        "\n"
        "suggested_steps 和 missing_info 也必须是字符串数组。"
        "\n"
        "suggested_title 只有在需要生成会话标题时才填写，否则返回空字符串。"
        "\n\n"
        f"当前会话标题：{conversation_title}\n"
        f"已有提示 headline：{existing_headline or '无'}\n"
        f"已有草案：{json.dumps(existing_draft, ensure_ascii=False) if existing_draft else 'null'}\n\n"
        f"当前是否需要生成会话标题：{'是' if should_suggest_title else '否'}\n\n"
        "会话内容：\n"
        f"{transcript}\n\n"
        "请返回 JSON，格式如下：\n"
        '{'
        '"status":"casual_chat",'
        '"headline":"",'
        '"recognized":{"topic":"","audience":"","goal":"","outputs":[],"materials":[],"agents":[]},'
        '"suggested_steps":[""],'
        '"missing_info":[""],'
        '"suggested_title":""'
        '}'
    )


def build_draft_prompt(*, conversation_title: str, transcript: str, guidance: dict) -> str:
    return (
        "请根据下面的会话和 guidance 信息生成研究草案 JSON。"
        "\n\n"
        "draft 必须包含这些键：title, topic, objective, scope, suggested_materials, suggested_agents, next_actions。"
        "\n"
        "suggested_materials, suggested_agents, next_actions 必须是字符串数组。"
        "\n"
        "内容必须与当前会话相符，不要编造外部资料。"
        "\n\n"
        f"当前会话标题：{conversation_title}\n"
        f"当前 guidance：{json.dumps(guidance, ensure_ascii=False)}\n\n"
        "会话内容：\n"
        f"{transcript}\n\n"
        "请返回 JSON，格式如下：\n"
        '{'
        '"title":"",'
        '"topic":"",'
        '"objective":"",'
        '"scope":"",'
        '"suggested_materials":[""],'
        '"suggested_agents":[""],'
        '"next_actions":[""]'
        '}'
    )
