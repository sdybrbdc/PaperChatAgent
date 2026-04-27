from __future__ import annotations

from paperchat.prompts import CHAT_STREAM_NODE_DETAILS


def normalize_chat_stream_part(part: tuple | dict) -> dict:
    if isinstance(part, tuple) and len(part) == 2:
        return {"type": part[0], "data": part[1]}
    return part


def translate_chat_stream_part(part: tuple | dict) -> list[tuple[str, dict]]:
    translated: list[tuple[str, dict]] = []
    part = normalize_chat_stream_part(part)
    part_type = part.get("type")

    if part_type == "messages":
        message_chunk, _metadata = part["data"]
        delta = ""
        content = getattr(message_chunk, "content", "")
        if isinstance(content, str):
            delta = content
        elif isinstance(content, list):
            delta = "".join(str(item) for item in content)
        if delta:
            translated.append(("message.delta", {"delta": delta}))
        return translated

    if part_type == "updates":
        for node_name in part["data"].keys():
            translated.append(
                (
                    "message.progress",
                    {
                        "stage": node_name,
                        "node": node_name,
                        "status": "completed",
                        "detail": CHAT_STREAM_NODE_DETAILS.get(node_name, f"{node_name} 已完成"),
                    },
                )
            )
        return translated

    if part_type == "custom":
        payload = part["data"]
        if isinstance(payload, dict) and payload.get("kind") == "delta":
            translated.append(("message.delta", {"delta": str(payload.get("delta") or "")}))
        elif isinstance(payload, dict) and payload.get("kind") == "tool":
            translated.append(
                (
                    "message.tool",
                    {
                        "status": payload.get("status", "started"),
                        "tool": payload.get("tool", "unknown"),
                        "detail": payload.get("detail", ""),
                    },
                )
            )
        else:
            detail = payload.get("detail", "") if isinstance(payload, dict) else str(payload)
            translated.append(("message.info", {"detail": detail}))
        return translated

    return translated
