from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import asc, select

from paperchat.database.sql import db_session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: Any) -> str | None:
    return value.isoformat() if value else None


SKILL_CONFIG_TABLE = "paperchat_skill_configs"
SKILL_VERSION_TABLE = "paperchat_skill_versions"
SKILL_CONFIG_RECORD = "PaperChatSkillConfigRecord"
SKILL_VERSION_RECORD = "PaperChatSkillVersionRecord"


def _skill_records():
    from paperchat.database.models import tables

    return getattr(tables, SKILL_CONFIG_RECORD, None), getattr(tables, SKILL_VERSION_RECORD, None)


def _skill_payload(record: Any) -> dict[str, Any]:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "name": record.name,
        "description": record.description,
        "source_type": record.source_type,
        "source_uri": record.source_uri,
        "entrypoint": record.entrypoint,
        "status": record.status,
        "manifest": dict(record.manifest_json or {}),
        "input_schema": dict(record.input_schema_json or {}),
        "output_schema": dict(record.output_schema_json or {}),
        "metadata": dict(record.metadata_json or {}),
        "created_at": iso(record.created_at),
        "updated_at": iso(record.updated_at),
    }


class SQLSkillRepository:
    @property
    def available(self) -> bool:
        config_record, version_record = _skill_records()
        return config_record is not None and version_record is not None

    def _require_records(self):
        config_record, version_record = _skill_records()
        if config_record is None or version_record is None:
            raise RuntimeError(f"ORM records {SKILL_CONFIG_RECORD}/{SKILL_VERSION_RECORD} are not registered yet")
        return config_record, version_record

    def list_skills(self, user_id: str) -> list[dict[str, Any]]:
        config_record, _version_record = self._require_records()
        with db_session() as session:
            records = session.scalars(
                select(config_record)
                .where(config_record.user_id == user_id, config_record.status != "deleted")
                .order_by(asc(config_record.created_at))
            )
            return [_skill_payload(record) for record in records]

    def create_skill(self, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        config_record, version_record = self._require_records()
        with db_session() as session:
            record = config_record(
                user_id=user_id,
                name=values["name"],
                description=values.get("description", ""),
                source_type=values.get("source_type", "local"),
                source_uri=values.get("source_uri", ""),
                entrypoint=values.get("entrypoint", ""),
                status=values.get("status", "disabled"),
                manifest_json=values.get("manifest", {}),
                input_schema_json=values.get("input_schema", {}),
                output_schema_json=values.get("output_schema", {}),
                metadata_json=values.get("metadata", {}),
            )
            session.add(record)
            session.flush()
            version = str((values.get("manifest") or {}).get("version") or "0.0.0")
            session.add(
                version_record(
                    skill_id=record.id,
                    version=version,
                    manifest_json=values.get("manifest", {}),
                    checksum="",
                )
            )
            session.flush()
            return _skill_payload(record)

    def get_skill(self, user_id: str, skill_id: str) -> dict[str, Any] | None:
        config_record, _version_record = self._require_records()
        with db_session() as session:
            record = session.get(config_record, skill_id)
            if record is None or record.user_id != user_id or record.status == "deleted":
                return None
            return _skill_payload(record)

    def update_skill(self, user_id: str, skill_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        config_record, _version_record = self._require_records()
        column_map = {
            "manifest": "manifest_json",
            "input_schema": "input_schema_json",
            "output_schema": "output_schema_json",
            "metadata": "metadata_json",
        }
        with db_session() as session:
            record = session.get(config_record, skill_id)
            if record is None or record.user_id != user_id or record.status == "deleted":
                return None
            for key, value in values.items():
                setattr(record, column_map.get(key, key), value)
            record.updated_at = utcnow()
            session.flush()
            return _skill_payload(record)

    def delete_skill(self, user_id: str, skill_id: str) -> bool:
        return self.update_skill(user_id, skill_id, {"status": "deleted"}) is not None


class InMemorySkillRepository:
    def __init__(self) -> None:
        self._skills: dict[str, dict[str, Any]] = {}
        self._versions: dict[str, list[dict[str, Any]]] = {}

    def list_skills(self, user_id: str) -> list[dict[str, Any]]:
        return [
            dict(record)
            for record in sorted(self._skills.values(), key=lambda item: item["created_at"] or "")
            if record["user_id"] == user_id and record["status"] != "deleted"
        ]

    def create_skill(self, user_id: str, values: dict[str, Any]) -> dict[str, Any]:
        now = utcnow().isoformat()
        record = {
            "id": str(uuid4()),
            "user_id": user_id,
            "name": values["name"],
            "description": values.get("description", ""),
            "source_type": values.get("source_type", "local"),
            "source_uri": values.get("source_uri", ""),
            "entrypoint": values.get("entrypoint", ""),
            "status": values.get("status", "disabled"),
            "manifest": values.get("manifest", {}),
            "input_schema": values.get("input_schema", {}),
            "output_schema": values.get("output_schema", {}),
            "metadata": values.get("metadata", {}),
            "created_at": now,
            "updated_at": now,
        }
        self._skills[record["id"]] = record
        self._versions.setdefault(record["id"], []).append(
            {
                "id": str(uuid4()),
                "skill_id": record["id"],
                "version": str(record["manifest"].get("version") or "0.0.0"),
                "manifest": record["manifest"],
                "checksum": "",
                "created_at": now,
            }
        )
        return dict(record)

    def get_skill(self, user_id: str, skill_id: str) -> dict[str, Any] | None:
        record = self._skills.get(skill_id)
        if record is None or record["user_id"] != user_id or record["status"] == "deleted":
            return None
        return dict(record)

    def update_skill(self, user_id: str, skill_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        record = self._skills.get(skill_id)
        if record is None or record["user_id"] != user_id or record["status"] == "deleted":
            return None
        record.update(values)
        record["updated_at"] = utcnow().isoformat()
        return dict(record)

    def delete_skill(self, user_id: str, skill_id: str) -> bool:
        return self.update_skill(user_id, skill_id, {"status": "deleted"}) is not None
