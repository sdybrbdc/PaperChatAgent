from __future__ import annotations

from autogen_core.models import ModelInfo
from autogen_ext.models.openai import OpenAIChatCompletionClient

from paperchat.providers.manager import ChatSlot, _get_chat_slot_config


def _infer_model_family(model_name: str) -> str:
    lowered = model_name.lower()
    if "qwen" in lowered:
        return "qwen"
    if "deepseek" in lowered:
        return "deepseek"
    if "gpt" in lowered or lowered.startswith(("o1", "o3", "o4")):
        return "openai"
    return "openai"


def get_autogen_model_client(
    slot: ChatSlot,
    *,
    vision: bool = False,
    function_calling: bool = True,
    json_output: bool = True,
    structured_output: bool = True,
) -> OpenAIChatCompletionClient:
    config = _get_chat_slot_config(slot)
    model_info: ModelInfo = {
        "vision": vision,
        "function_calling": function_calling,
        "json_output": json_output,
        "family": _infer_model_family(config.model_name),
        "structured_output": structured_output,
    }
    return OpenAIChatCompletionClient(
        model=config.model_name,
        api_key=config.api_key,
        base_url=config.base_url,
        model_info=model_info,
        parallel_tool_calls=False,
    )


def get_autogen_conversation_model_client() -> OpenAIChatCompletionClient:
    return get_autogen_model_client("conversation_model", function_calling=False)


def get_autogen_guidance_model_client() -> OpenAIChatCompletionClient:
    return get_autogen_model_client("guidance_model", function_calling=False)


def get_autogen_tool_call_model_client() -> OpenAIChatCompletionClient:
    return get_autogen_model_client("tool_call_model", function_calling=True)


def get_autogen_reasoning_model_client() -> OpenAIChatCompletionClient:
    return get_autogen_model_client("reasoning_model", function_calling=False)


def get_autogen_vision_model_client() -> OpenAIChatCompletionClient:
    return get_autogen_model_client("qwen_vl", vision=True, function_calling=False)
