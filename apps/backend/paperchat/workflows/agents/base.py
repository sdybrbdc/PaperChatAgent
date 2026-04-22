from __future__ import annotations

from collections.abc import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from paperchat.api.errcode import AppError


ModelFactory = Callable[[], BaseChatModel]


class BaseWorkflowAgent:
    def __init__(self, *, name: str, system_prompt: str, model_factory: ModelFactory) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self._model_factory = model_factory

    async def ainvoke(self, prompt: str) -> str | None:
        try:
            model = self._model_factory()
        except AppError:
            return None
        except Exception:
            return None

        try:
            response = await model.ainvoke(
                [
                    SystemMessage(content=self.system_prompt),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception:
            return None

        content = response.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            flattened = "".join(part if isinstance(part, str) else str(part) for part in content)
            return flattened.strip()
        return str(content).strip()
