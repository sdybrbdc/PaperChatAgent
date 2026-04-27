from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from sqlalchemy import asc, select

from paperchat.database.sql import db_session
from paperchat.settings import get_settings
from paperchat.services.model_router.records import (
    PaperChatModelProviderRecord,
    PaperChatModelRouteRecord,
    PaperChatModelUsageLogRecord,
    utcnow,
)


DEFAULT_ROUTE_SLOTS = [
    ("conversation", "会话模型", "conversation_model", "chat"),
    ("tool_call", "工具调用模型", "tool_call_model", "chat"),
    ("reasoning", "推理模型", "reasoning_model", "chat"),
    ("embedding", "Embedding 模型", "embedding", "embedding"),
    ("rerank", "Rerank 模型", "rerank", "rerank"),
    ("summary", "摘要模型", "guidance_model", "chat"),
]


class ModelRouterRepository:
    def _key_from_name(self, name: str) -> str:
        key = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower()).strip("_")
        return key or "model"

    def ensure_default_configuration(self, *, user_id: str) -> None:
        settings = get_settings()
        with db_session() as session:
            provider = session.scalar(
                select(PaperChatModelProviderRecord)
                .where(
                    PaperChatModelProviderRecord.user_id == user_id,
                    PaperChatModelProviderRecord.status != "deleted",
                )
                .order_by(asc(PaperChatModelProviderRecord.created_at))
            )
            if provider is None:
                conversation_config = settings.multi_models.conversation_model
                provider = PaperChatModelProviderRecord(
                    user_id=user_id,
                    provider_key="default",
                    display_name="Default Provider",
                    base_url=conversation_config.base_url,
                    api_key_secret_ref="settings.multi_models",
                    status="active",
                    metadata_json={"provider_type": "openai_compatible", "source": "settings"},
                )
                session.add(provider)
                session.flush()

            existing_route_keys = set(
                session.scalars(
                    select(PaperChatModelRouteRecord.route_key).where(
                        PaperChatModelRouteRecord.user_id == user_id,
                        PaperChatModelRouteRecord.status != "deleted",
                    )
                )
            )
            for route_key, display_name, settings_key, model_type in DEFAULT_ROUTE_SLOTS:
                if route_key in existing_route_keys:
                    continue
                endpoint = getattr(settings.multi_models, settings_key)
                route = PaperChatModelRouteRecord(
                    user_id=user_id,
                    provider_id=provider.id,
                    route_key=route_key,
                    model_name=endpoint.model_name or f"{route_key}-model",
                    status="active",
                    config_json={
                        "display_name": display_name,
                        "model_type": model_type,
                        "priority": 100,
                        "is_default": route_key == "conversation",
                        "source": "settings",
                    },
                )
                session.add(route)
            session.flush()

    def list_providers(self, *, user_id: str, include_deleted: bool = False):
        with db_session() as session:
            statement = (
                select(PaperChatModelProviderRecord)
                .where(PaperChatModelProviderRecord.user_id == user_id)
                .order_by(asc(PaperChatModelProviderRecord.created_at))
            )
            if not include_deleted:
                statement = statement.where(PaperChatModelProviderRecord.status != "deleted")
            return list(session.scalars(statement))

    def get_provider(self, *, user_id: str, provider_id: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatModelProviderRecord).where(
                    PaperChatModelProviderRecord.id == provider_id,
                    PaperChatModelProviderRecord.user_id == user_id,
                    PaperChatModelProviderRecord.status != "deleted",
                )
            )

    def create_provider(self, *, user_id: str, payload):
        with db_session() as session:
            provider = PaperChatModelProviderRecord(
                user_id=user_id,
                provider_key=self._key_from_name(payload.name),
                display_name=payload.name,
                base_url=payload.base_url,
                api_key_secret_ref=payload.api_key_ref,
                status=payload.status,
                metadata_json={"provider_type": payload.provider_type, **payload.config},
            )
            session.add(provider)
            session.flush()
            return provider

    def update_provider(self, *, user_id: str, provider_id: str, changes: dict[str, Any]):
        with db_session() as session:
            provider = session.scalar(
                select(PaperChatModelProviderRecord).where(
                    PaperChatModelProviderRecord.id == provider_id,
                    PaperChatModelProviderRecord.user_id == user_id,
                    PaperChatModelProviderRecord.status != "deleted",
                )
            )
            if provider is None:
                return None
            for key, value in changes.items():
                if key == "config":
                    provider.metadata_json = {**(provider.metadata_json or {}), **value}
                elif key == "name":
                    provider.display_name = value
                    provider.provider_key = self._key_from_name(value)
                elif key == "provider_type":
                    metadata = provider.metadata_json or {}
                    metadata["provider_type"] = value
                    provider.metadata_json = metadata
                elif key == "api_key_ref":
                    provider.api_key_secret_ref = value
                else:
                    setattr(provider, key, value)
            provider.updated_at = utcnow()
            session.flush()
            return provider

    def list_routes(self, *, user_id: str, include_deleted: bool = False):
        with db_session() as session:
            statement = (
                select(PaperChatModelRouteRecord)
                .where(PaperChatModelRouteRecord.user_id == user_id)
                .order_by(asc(PaperChatModelRouteRecord.created_at))
            )
            if not include_deleted:
                statement = statement.where(PaperChatModelRouteRecord.status != "deleted")
            return list(session.scalars(statement))

    def get_route(self, *, user_id: str, route_id: str):
        with db_session() as session:
            return session.scalar(
                select(PaperChatModelRouteRecord).where(
                    (PaperChatModelRouteRecord.id == route_id) | (PaperChatModelRouteRecord.route_key == route_id),
                    PaperChatModelRouteRecord.user_id == user_id,
                    PaperChatModelRouteRecord.status != "deleted",
                )
            )

    def create_route(self, *, user_id: str, payload):
        with db_session() as session:
            route = PaperChatModelRouteRecord(
                user_id=user_id,
                provider_id=payload.provider_id,
                route_key=self._key_from_name(payload.name),
                model_name=payload.model_name,
                status=payload.status,
                config_json={
                    **payload.config,
                    "display_name": payload.name,
                    "model_type": payload.model_type,
                    "priority": payload.priority,
                    "is_default": payload.is_default,
                },
            )
            session.add(route)
            session.flush()
            return route

    def update_route(self, *, user_id: str, route_id: str, changes: dict[str, Any]):
        with db_session() as session:
            route = session.scalar(
                select(PaperChatModelRouteRecord).where(
                    (PaperChatModelRouteRecord.id == route_id) | (PaperChatModelRouteRecord.route_key == route_id),
                    PaperChatModelRouteRecord.user_id == user_id,
                    PaperChatModelRouteRecord.status != "deleted",
                )
            )
            if route is None:
                return None
            for key, value in changes.items():
                if key == "config":
                    route.config_json = {**(route.config_json or {}), **value}
                elif key == "name":
                    config = route.config_json or {}
                    config["display_name"] = value
                    route.config_json = config
                    route.route_key = self._key_from_name(value)
                elif key in {"model_type", "priority", "is_default"}:
                    config = route.config_json or {}
                    config[key] = value
                    route.config_json = config
                else:
                    setattr(route, key, value)
            route.updated_at = utcnow()
            session.flush()
            return route

    def get_active_provider_for_route(self, *, user_id: str, route):
        with db_session() as session:
            return session.scalar(
                select(PaperChatModelProviderRecord).where(
                    PaperChatModelProviderRecord.id == route.provider_id,
                    PaperChatModelProviderRecord.user_id == user_id,
                    PaperChatModelProviderRecord.status == "active",
                )
            )

    def create_usage_log(self, *, user_id: str, payload):
        total_tokens = payload.total_tokens
        if total_tokens is None:
            total_tokens = payload.prompt_tokens + payload.completion_tokens
        route = None
        provider = None
        if payload.route_id:
            route = session_route = self.get_route(user_id=user_id, route_id=payload.route_id)
            if session_route is not None:
                provider = self.get_provider(user_id=user_id, provider_id=session_route.provider_id)
        if provider is None and payload.provider_id:
            provider = self.get_provider(user_id=user_id, provider_id=payload.provider_id)
        with db_session() as session:
            record = PaperChatModelUsageLogRecord(
                user_id=user_id,
                conversation_id=payload.conversation_id,
                task_id=payload.task_id,
                workflow_run_id=payload.workflow_run_id,
                route_key=route.route_key if route is not None else "",
                provider_key=provider.provider_key if provider is not None else "",
                model_name=payload.model_name,
                input_tokens=payload.prompt_tokens,
                output_tokens=payload.completion_tokens,
                status=payload.status,
                latency_ms=payload.latency_ms,
                error_code="ERROR" if payload.error_text else "",
                metadata_json={
                    **payload.metadata,
                    "provider_id": payload.provider_id,
                    "route_id": payload.route_id,
                    "operation": payload.operation,
                    "tool_name": payload.tool_name,
                    "total_tokens": total_tokens,
                    "cost_usd": payload.cost_usd,
                    "error_text": payload.error_text,
                },
                created_at=payload.created_at or utcnow(),
            )
            session.add(record)
            session.flush()
            return record

    def list_usage_logs(self, *, user_id: str, start_at: datetime | None = None, limit: int = 100):
        with db_session() as session:
            statement = (
                select(PaperChatModelUsageLogRecord)
                .where(PaperChatModelUsageLogRecord.user_id == user_id)
                .order_by(PaperChatModelUsageLogRecord.created_at.desc())
                .limit(limit)
            )
            if start_at is not None:
                statement = statement.where(PaperChatModelUsageLogRecord.created_at >= start_at)
            return list(session.scalars(statement))


model_router_repository = ModelRouterRepository()
