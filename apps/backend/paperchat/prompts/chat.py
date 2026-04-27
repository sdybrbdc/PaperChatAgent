from __future__ import annotations


CHAT_CONTEXT_LOADING_MESSAGE = "正在整理当前会话语境"
CHAT_READY_MESSAGE = "已准备好继续当前对话"

CHAT_SYSTEM_PROMPT = (
    "你是 PaperChatAgent 的聊天研究助手。"
    "\n\n"
    "## 职责\n"
    "1. 正常回答用户问题，保持自然、专业、克制。\n"
    "2. 帮助用户逐步澄清研究方向、目标和边界。\n"
    "3. 在不知道答案时明确说明不确定性，不要编造事实。\n"
    "4. 不要把右侧专业提示区的结构直接混进主回答里，主回答仍然是自然聊天。"
    "\n\n"
    "## 回复偏好\n"
    "- 如果用户只是普通交流，直接自然回答。\n"
    "- 如果用户正在探索方向，优先帮助其厘清目标、对象、资料和产出。\n"
    "- 如果用户问题已较清晰，给出下一步建议，但主回答保持自然可读。"
    "\n\n"
    "## 工具调用规则\n"
    "- 当用户明确要求深入研究、生成调研/研究报告、执行研究方案，或点名调用智能研究助手时，调用 start_smart_research_assistant。\n"
    "- start_smart_research_assistant 会创建后台长任务，工具返回任务入口后需要把入口转述给用户。\n"
    "- 普通问答、方向澄清和闲聊不要调用工具。"
    "\n\n"
    "## 约束\n"
    "- 不编造论文、实验结论、引用来源或外部事实。\n"
    "- 不暴露系统内部实现、表结构或接口细节。\n"
    "- 使用 Markdown 组织回答，但不要过度模板化。"
)


def _format_conversation_memory(conversation_memory: dict | None) -> str:
    if not conversation_memory:
        return ""

    summary = str(conversation_memory.get("summary") or "").strip()
    key_points = [str(item).strip() for item in conversation_memory.get("key_points") or [] if str(item).strip()]
    user_preferences = [
        str(item).strip() for item in conversation_memory.get("user_preferences") or [] if str(item).strip()
    ]
    open_questions = [str(item).strip() for item in conversation_memory.get("open_questions") or [] if str(item).strip()]

    if not summary and not key_points and not user_preferences and not open_questions:
        return ""

    lines = ["## 短期会话记忆"]
    if summary:
        lines.append(summary)
    if key_points:
        lines.append("关键进展：")
        lines.extend(f"- {item}" for item in key_points[:6])
    if user_preferences:
        lines.append("当前已知偏好：")
        lines.extend(f"- {item}" for item in user_preferences[:6])
    if open_questions:
        lines.append("待继续澄清：")
        lines.extend(f"- {item}" for item in open_questions[:6])
    return "\n".join(lines)


def _format_user_memories(user_memories: list[dict] | None) -> str:
    if not user_memories:
        return ""

    lines = ["## 用户长期记忆"]
    visible = 0
    for memory in user_memories:
        content = str(memory.get("content") or "").strip()
        if not content:
            continue
        kind = str(memory.get("memory_type") or "memory").strip()
        title = str(memory.get("title") or "").strip()
        if title:
            lines.append(f"- [{kind}] {title}：{content}")
        else:
            lines.append(f"- [{kind}] {content}")
        visible += 1
        if visible >= 8:
            break
    return "\n".join(lines) if visible else ""


def build_chat_system_prompt(
    *,
    conversation_memory: dict | None = None,
    user_memories: list[dict] | None = None,
) -> str:
    memory_sections = [
        section
        for section in (
            _format_conversation_memory(conversation_memory),
            _format_user_memories(user_memories),
        )
        if section
    ]
    if not memory_sections:
        return CHAT_SYSTEM_PROMPT

    return (
        CHAT_SYSTEM_PROMPT
        + "\n\n"
        + "## 记忆上下文\n"
        + "以下内容是系统整理出的辅助记忆，仅在与当前问题相关时参考。"
        + "如果它与用户本轮最新表述冲突，以用户本轮最新表述为准。\n\n"
        + "\n\n".join(memory_sections)
    )
