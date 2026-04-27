from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal
import re

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from paperchat.api.errcode import AppError
from paperchat.settings import ModelEndpointSettings, get_settings


ChatSlot = Literal["conversation_model", "guidance_model", "tool_call_model", "reasoning_model", "qwen_vl"]
ENV_PLACEHOLDER_RE = re.compile(r"^\$\{?[A-Z0-9_]+\}?$")
_MODEL_SLOT_OVERRIDES: ContextVar[dict[str, str]] = ContextVar("paperchat_model_slot_overrides", default={})
SDK_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


def _is_missing_value(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    return bool(ENV_PLACEHOLDER_RE.fullmatch(stripped))


def _require_endpoint(slot: str, config: ModelEndpointSettings) -> ModelEndpointSettings:
    if (
        _is_missing_value(config.api_key)
        or _is_missing_value(config.base_url)
        or _is_missing_value(config.model_name)
    ):
        raise AppError(
            status_code=500,
            code="MODEL_CONFIG_MISSING",
            message=f"{slot} 配置不完整，请检查 apps/backend/paperchat/config.yaml",
        )
    return config


def get_model_slot_overrides() -> dict[str, str]:
    return dict(_MODEL_SLOT_OVERRIDES.get())


@contextmanager
def temporary_model_slot_overrides(overrides: dict[str, str] | None):
    if not overrides:
        yield
        return
    merged = get_model_slot_overrides()
    merged.update(overrides)
    token = _MODEL_SLOT_OVERRIDES.set(merged)
    try:
        yield
    finally:
        _MODEL_SLOT_OVERRIDES.reset(token)


def _get_chat_slot_config(slot: ChatSlot) -> ModelEndpointSettings:
    settings = get_settings()
    effective_slot = get_model_slot_overrides().get(slot, slot)
    config = getattr(settings.multi_models, effective_slot)
    return _require_endpoint(effective_slot, config)


def _sdk_default_headers(config: ModelEndpointSettings) -> dict[str, str] | None:
    # Some OpenAI-compatible gateways block the default OpenAI/Python user agent.
    if "aizhiwen.top" in config.base_url:
        return {"User-Agent": SDK_USER_AGENT}
    return None


def _build_openai_compatible_chat_client(slot: ChatSlot, *, temperature: float = 0) -> BaseChatModel:
    config = _get_chat_slot_config(slot)
    return ChatOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model_name,
        temperature=temperature,
        default_headers=_sdk_default_headers(config),
    )


def get_conversation_chat_model() -> BaseChatModel:
    return _build_openai_compatible_chat_client("conversation_model", temperature=0)


def get_guidance_chat_model() -> BaseChatModel:
    return _build_openai_compatible_chat_client("guidance_model", temperature=0)


def get_tool_call_chat_model() -> BaseChatModel:
    return _build_openai_compatible_chat_client("tool_call_model", temperature=0)


def get_reasoning_chat_model() -> BaseChatModel:
    return _build_openai_compatible_chat_client("reasoning_model", temperature=0)


def get_vision_chat_model() -> BaseChatModel:
    return _build_openai_compatible_chat_client("qwen_vl", temperature=0)


def get_embedding_client() -> OpenAIEmbeddings:
    settings = get_settings()
    config = _require_endpoint("embedding", settings.multi_models.embedding)
    return OpenAIEmbeddings(
        api_key=config.api_key,
        base_url=config.base_url,
        model=config.model_name,
        default_headers=_sdk_default_headers(config),
    )


@dataclass(frozen=True)
class HTTPModelClient:
    api_key: str
    base_url: str
    model_name: str

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


class Text2ImageClient(HTTPModelClient):
    async def generate(self, *, prompt: str, **parameters) -> dict:
        payload = {
            "model": self.model_name,
            "input": {"prompt": prompt},
            "parameters": parameters or {},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()


class RerankClient(HTTPModelClient):
    async def rerank(self, *, query: str, documents: list[str], top_n: int | None = None) -> dict:
        payload = {
            "model": self.model_name,
            "input": {
                "query": query,
                "documents": documents,
            },
        }
        if top_n is not None:
            payload["parameters"] = {"top_n": top_n}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()


def get_text2image_client() -> Text2ImageClient:
    settings = get_settings()
    config = _require_endpoint("text2image", settings.multi_models.text2image)
    return Text2ImageClient(
        api_key=config.api_key,
        base_url=config.base_url,
        model_name=config.model_name,
    )


def get_rerank_client() -> RerankClient:
    settings = get_settings()
    config = _require_endpoint("rerank", settings.multi_models.rerank)
    return RerankClient(
        api_key=config.api_key,
        base_url=config.base_url,
        model_name=config.model_name,
    )
