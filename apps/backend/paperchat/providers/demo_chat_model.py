from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Iterator

from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


def _chunk_text(text: str, size: int = 4) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]


class DemoStreamingChatModel(BaseChatModel):
    model_name: str = "paperchat-demo-streaming-model"

    @property
    def _llm_type(self) -> str:
        return "paperchat-demo-streaming-model"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.model_name}

    def _compose_response(self, messages: list[BaseMessage]) -> str:
        user_input = ""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                user_input = str(message.content)
                break

        if not user_input:
            return "你好，我已经准备好帮助你梳理论文研究任务。"

        return (
            "我先帮你把这个研究问题收束成一个可执行范围："
            f"\n1. 当前主题：{user_input}"
            "\n2. 建议先确定研究对象、资料来源和最终产物"
            "\n3. 下一步可以继续补充关键词、代表论文和边界限制"
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        response_text = self._compose_response(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response_text))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        response_text = self._compose_response(messages)
        for token in _chunk_text(response_text):
            message_chunk = AIMessageChunk(content=token)
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=message_chunk)
            yield ChatGenerationChunk(message=message_chunk)

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        response_text = self._compose_response(messages)
        for token in _chunk_text(response_text):
            await asyncio.sleep(0.03)
            message_chunk = AIMessageChunk(content=token)
            if run_manager:
                await run_manager.on_llm_new_token(token, chunk=message_chunk)
            yield ChatGenerationChunk(message=message_chunk)
