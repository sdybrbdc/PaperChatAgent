from __future__ import annotations

from langchain_openai import ChatOpenAI

from paperchat.providers.demo_chat_model import DemoStreamingChatModel
from paperchat.settings import get_settings


def get_conversation_chat_model():
    settings = get_settings()
    config = settings.multi_models.conversation_model
    if config.api_key and config.base_url and config.model_name:
        return ChatOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model_name,
            temperature=0,
        )
    return DemoStreamingChatModel()
