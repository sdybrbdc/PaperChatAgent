from __future__ import annotations

from datetime import datetime
from typing import Any

from paperchat.api.errcode import AppError
from paperchat.schemas.models import ModelUsageLogCreate
from paperchat.services.model_router.repository import model_router_repository


class ModelRouterService:
    def _provider_payload(self, provider) -> dict[str, Any]:
        metadata = provider.metadata_json or {}
        return {
            "id": provider.id,
            "name": provider.display_name,
            "provider_key": provider.provider_key,
            "provider_type": metadata.get("provider_type", "openai_compatible"),
            "base_url": provider.base_url,
            "api_key_ref": provider.api_key_secret_ref,
            "status": provider.status,
            "config": metadata,
            "created_at": provider.created_at.isoformat() if provider.created_at else None,
            "updated_at": provider.updated_at.isoformat() if provider.updated_at else None,
        }

    def _route_payload(self, route) -> dict[str, Any]:
        config = route.config_json or {}
        return {
            "id": route.id,
            "provider_id": route.provider_id,
            "provider_name": config.get("provider_name", ""),
            "name": config.get("display_name") or route.route_key,
            "label": config.get("display_name") or route.route_key,
            "route_key": route.route_key,
            "model_name": route.model_name,
            "model_type": config.get("model_type", "chat"),
            "priority": config.get("priority", 100),
            "status": route.status,
            "is_default": bool(config.get("is_default", False)),
            "temperature": route.temperature,
            "max_tokens": route.max_tokens,
            "config": config,
            "created_at": route.created_at.isoformat() if route.created_at else None,
            "updated_at": route.updated_at.isoformat() if route.updated_at else None,
        }

    def _usage_payload(self, usage) -> dict[str, Any]:
        metadata = usage.metadata_json or {}
        total_tokens = int(metadata.get("total_tokens") or (usage.input_tokens + usage.output_tokens))
        return {
            "id": usage.id,
            "provider_id": metadata.get("provider_id"),
            "route_id": metadata.get("route_id"),
            "provider_key": usage.provider_key,
            "route_key": usage.route_key,
            "conversation_id": usage.conversation_id,
            "workflow_run_id": usage.workflow_run_id,
            "task_id": usage.task_id,
            "tool_name": metadata.get("tool_name", ""),
            "model_name": usage.model_name,
            "operation": metadata.get("operation", "chat_completion"),
            "status": usage.status,
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": float(metadata.get("cost_usd") or 0),
            "latency_ms": usage.latency_ms,
            "error_text": metadata.get("error_text", usage.error_code),
            "metadata": metadata,
            "created_at": usage.created_at.isoformat() if usage.created_at else None,
        }

    def list_providers_payload(self, *, user_id: str) -> dict[str, Any]:
        model_router_repository.ensure_default_configuration(user_id=user_id)
        return {"items": [self._provider_payload(item) for item in model_router_repository.list_providers(user_id=user_id)]}

    def create_provider_payload(self, *, user_id: str, payload) -> dict[str, Any]:
        provider = model_router_repository.create_provider(user_id=user_id, payload=payload)
        return self._provider_payload(provider)

    def get_provider_payload(self, *, user_id: str, provider_id: str) -> dict[str, Any]:
        provider = model_router_repository.get_provider(user_id=user_id, provider_id=provider_id)
        if provider is None:
            raise AppError(status_code=404, code="MODEL_PROVIDER_NOT_FOUND", message="模型供应商不存在")
        return self._provider_payload(provider)

    def update_provider_payload(self, *, user_id: str, provider_id: str, payload) -> dict[str, Any]:
        changes = payload.model_dump(exclude_unset=True)
        provider = model_router_repository.update_provider(user_id=user_id, provider_id=provider_id, changes=changes)
        if provider is None:
            raise AppError(status_code=404, code="MODEL_PROVIDER_NOT_FOUND", message="模型供应商不存在")
        return self._provider_payload(provider)

    def delete_provider_payload(self, *, user_id: str, provider_id: str) -> dict[str, Any]:
        provider = model_router_repository.update_provider(
            user_id=user_id,
            provider_id=provider_id,
            changes={"status": "deleted"},
        )
        if provider is None:
            raise AppError(status_code=404, code="MODEL_PROVIDER_NOT_FOUND", message="模型供应商不存在")
        return {"deleted": True, "id": provider_id}

    def list_routes_payload(self, *, user_id: str) -> dict[str, Any]:
        model_router_repository.ensure_default_configuration(user_id=user_id)
        return {"items": [self._route_payload(item) for item in model_router_repository.list_routes(user_id=user_id)]}

    def create_route_payload(self, *, user_id: str, payload) -> dict[str, Any]:
        provider = model_router_repository.get_provider(user_id=user_id, provider_id=payload.provider_id)
        if provider is None:
            raise AppError(status_code=404, code="MODEL_PROVIDER_NOT_FOUND", message="模型供应商不存在")
        route = model_router_repository.create_route(user_id=user_id, payload=payload)
        return self._route_payload(route)

    def get_route_payload(self, *, user_id: str, route_id: str) -> dict[str, Any]:
        route = model_router_repository.get_route(user_id=user_id, route_id=route_id)
        if route is None:
            raise AppError(status_code=404, code="MODEL_ROUTE_NOT_FOUND", message="模型路由不存在")
        return self._route_payload(route)

    def update_route_payload(self, *, user_id: str, route_id: str, payload) -> dict[str, Any]:
        changes = payload.model_dump(exclude_unset=True)
        if "provider_id" in changes:
            provider = model_router_repository.get_provider(user_id=user_id, provider_id=changes["provider_id"])
            if provider is None:
                raise AppError(status_code=404, code="MODEL_PROVIDER_NOT_FOUND", message="模型供应商不存在")
        route = model_router_repository.update_route(user_id=user_id, route_id=route_id, changes=changes)
        if route is None:
            raise AppError(status_code=404, code="MODEL_ROUTE_NOT_FOUND", message="模型路由不存在")
        return self._route_payload(route)

    def delete_route_payload(self, *, user_id: str, route_id: str) -> dict[str, Any]:
        route = model_router_repository.update_route(
            user_id=user_id,
            route_id=route_id,
            changes={"status": "deleted"},
        )
        if route is None:
            raise AppError(status_code=404, code="MODEL_ROUTE_NOT_FOUND", message="模型路由不存在")
        return {"deleted": True, "id": route_id}

    def test_route_payload(self, *, user_id: str, route_id: str, prompt: str, metadata: dict[str, Any]) -> dict[str, Any]:
        model_router_repository.ensure_default_configuration(user_id=user_id)
        route = model_router_repository.get_route(user_id=user_id, route_id=route_id)
        if route is None:
            raise AppError(status_code=404, code="MODEL_ROUTE_NOT_FOUND", message="模型路由不存在")
        provider = model_router_repository.get_active_provider_for_route(user_id=user_id, route=route)
        if provider is None:
            raise AppError(status_code=400, code="MODEL_PROVIDER_INACTIVE", message="模型供应商不可用")
        usage = self.record_usage_payload(
            user_id=user_id,
            payload=ModelUsageLogCreate(
                provider_id=provider.id,
                route_id=route.id,
                model_name=route.model_name,
                operation="route_test",
                status="success",
                prompt_tokens=max(1, len(prompt) // 4),
                completion_tokens=1,
                latency_ms=0,
                metadata={"placeholder": True, **metadata},
            ),
        )
        return {
            "ok": True,
            "placeholder": True,
            "output": "PaperChatAgent 是一个以聊天为主链路、连接知识库和多智能体研究流程的论文调研助手。",
            "latency_ms": 0,
            "input_tokens": max(1, len(prompt) // 4),
            "output_tokens": 1,
            "message": "模型连通性测试占位成功，未请求真实模型 API",
            "provider": self._provider_payload(provider),
            "route": self._route_payload(route),
            "usage": usage,
        }

    def record_usage_payload(self, *, user_id: str, payload: ModelUsageLogCreate) -> dict[str, Any]:
        usage = model_router_repository.create_usage_log(user_id=user_id, payload=payload)
        return self._usage_payload(usage)

    def list_usage_payload(self, *, user_id: str, start_at: datetime | None = None, limit: int = 100) -> dict[str, Any]:
        return {
            "items": [
                self._usage_payload(item)
                for item in model_router_repository.list_usage_logs(user_id=user_id, start_at=start_at, limit=limit)
            ]
        }


model_router_service = ModelRouterService()
