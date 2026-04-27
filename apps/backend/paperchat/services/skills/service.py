from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from paperchat.api.errcode import AppError
from paperchat.schemas.skills import SkillCreate, SkillImportRequest, SkillTestRequest, SkillUpdate
from paperchat.services.cc_switch import cc_switch_discovery
from paperchat.services.skills.repository import InMemorySkillRepository, SQLSkillRepository


class SkillService:
    def __init__(self) -> None:
        self._sql_repository = SQLSkillRepository()
        self._memory_repository = InMemorySkillRepository()

    @property
    def repository(self):
        return self._sql_repository if self._sql_repository.available else self._memory_repository

    def list_skills_payload(self, user_id: str) -> dict[str, Any]:
        return {"items": [self._skill_payload(item) for item in self.repository.list_skills(user_id)]}

    def list_cc_switch_skills_payload(self) -> dict[str, Any]:
        return {
            "source": cc_switch_discovery.source_payload(),
            "items": [self._discovered_skill_payload(item) for item in cc_switch_discovery.discover_skills()],
        }

    def sync_cc_switch_skills_payload(self, user_id: str) -> dict[str, Any]:
        discovered = cc_switch_discovery.discover_skills()
        existing = self.repository.list_skills(user_id)
        created = 0
        updated = 0
        items: list[dict[str, Any]] = []
        for item in discovered:
            match = self._find_existing_cc_switch_skill(existing, item)
            values = {
                "name": item["name"],
                "description": item["description"],
                "source_type": item["source_type"],
                "source_uri": item["source_uri"],
                "entrypoint": item["entrypoint"],
                "status": item["status"],
                "manifest": item["manifest"],
                "input_schema": item["input_schema"],
                "output_schema": item["output_schema"],
                "metadata": item["metadata"],
            }
            if match:
                record = self.repository.update_skill(user_id, match["id"], values) or match
                updated += 1
            else:
                record = self.repository.create_skill(user_id, values)
                created += 1
            items.append(self._skill_payload(record))
        return {
            "source": cc_switch_discovery.source_payload(),
            "created": created,
            "updated": updated,
            "total": len(items),
            "items": items,
        }

    def create_skill_payload(self, user_id: str, payload: SkillCreate) -> dict[str, Any]:
        record = self.repository.create_skill(user_id, payload.model_dump())
        return self._skill_payload(record)

    def import_skill_payload(self, user_id: str, payload: SkillImportRequest) -> dict[str, Any]:
        source_path = Path(payload.source_uri).expanduser()
        manifest = self._load_local_manifest(source_path)
        create_payload = SkillCreate(
            name=str(manifest.get("name") or source_path.name),
            description=str(manifest.get("description") or ""),
            source_type="local",
            source_uri=str(source_path),
            entrypoint=str(manifest.get("entrypoint") or manifest.get("run") or ""),
            status=payload.status,
            manifest=manifest,
            input_schema=dict(manifest.get("input_schema") or {}),
            output_schema=dict(manifest.get("output_schema") or {}),
            metadata={
                "imported_from": str(source_path),
                "manifest_files_checked": self._manifest_file_names(),
                "placeholder": True,
            },
        )
        return self.create_skill_payload(user_id, create_payload)

    def get_skill_payload(self, user_id: str, skill_id: str) -> dict[str, Any]:
        return self._skill_payload(self._require_skill(user_id, skill_id))

    def update_skill_payload(self, user_id: str, skill_id: str, payload: SkillUpdate) -> dict[str, Any]:
        record = self.repository.update_skill(user_id, skill_id, payload.model_dump(exclude_unset=True))
        if record is None:
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return self._skill_payload(record)

    def delete_skill_payload(self, user_id: str, skill_id: str) -> dict[str, Any]:
        if not self.repository.delete_skill(user_id, skill_id):
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return {"deleted": True, "id": skill_id}

    def test_skill_payload(self, user_id: str, skill_id: str, payload: SkillTestRequest) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        validation = self._validate_input(skill.get("input_schema") or {}, payload.input)
        return {
            "ok": validation["ok"],
            "executed": False,
            "message": (
                "Skill input schema check passed; execution is a placeholder until the skill executor is integrated"
                if validation["ok"]
                else "Skill input does not satisfy the configured schema"
            ),
            "output": {},
            "validation": validation,
        }

    def _require_skill(self, user_id: str, skill_id: str) -> dict[str, Any]:
        record = self.repository.get_skill(user_id, skill_id)
        if record is None:
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return record

    def _find_existing_cc_switch_skill(
        self,
        existing: list[dict[str, Any]],
        discovered: dict[str, Any],
    ) -> dict[str, Any] | None:
        cc_switch_id = discovered["metadata"].get("cc_switch_id")
        source_uri = discovered.get("source_uri")
        for item in existing:
            metadata = item.get("metadata") or {}
            if metadata.get("source") == "cc-switch" and metadata.get("cc_switch_id") == cc_switch_id:
                return item
            if item.get("source_uri") == source_uri:
                return item
        return None

    def _load_local_manifest(self, source_path: Path) -> dict[str, Any]:
        if not source_path.exists():
            raise AppError(status_code=400, code="SKILL_SOURCE_NOT_FOUND", message="Skill 本地路径不存在")
        if source_path.is_file():
            return self._load_manifest_file(source_path)
        for file_name in self._manifest_file_names():
            manifest_path = source_path / file_name
            if manifest_path.exists():
                return self._load_manifest_file(manifest_path)
        skill_md = source_path / "SKILL.md"
        if skill_md.exists():
            return {
                "name": source_path.name,
                "description": self._extract_markdown_summary(skill_md),
                "version": "0.0.0",
                "format": "SKILL.md",
            }
        return {"name": source_path.name, "description": "", "version": "0.0.0", "format": "directory"}

    def _manifest_file_names(self) -> list[str]:
        return ["skill.json", "manifest.json", "skill.yaml", "skill.yml"]

    def _load_manifest_file(self, manifest_path: Path) -> dict[str, Any]:
        try:
            text = manifest_path.read_text(encoding="utf-8")
            if manifest_path.suffix.lower() == ".json":
                data = json.loads(text)
            else:
                data = yaml.safe_load(text) or {}
        except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
            raise AppError(status_code=400, code="SKILL_MANIFEST_INVALID", message="Skill manifest 解析失败") from exc
        if not isinstance(data, dict):
            raise AppError(status_code=400, code="SKILL_MANIFEST_INVALID", message="Skill manifest 必须是对象")
        data.setdefault("manifest_path", str(manifest_path))
        return data

    def _extract_markdown_summary(self, skill_md: Path) -> str:
        try:
            for line in skill_md.read_text(encoding="utf-8").splitlines():
                clean = line.strip().lstrip("#").strip()
                if clean:
                    return clean[:255]
        except OSError:
            return ""
        return ""

    def _validate_input(self, schema: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        required = schema.get("required") if isinstance(schema, dict) else None
        missing = [key for key in required or [] if key not in payload]
        return {
            "ok": not missing,
            "missing_required": missing,
            "schema_checked": bool(schema),
            "placeholder": True,
        }

    def _skill_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["id"],
            "name": record["name"],
            "description": record.get("description", ""),
            "source_type": record.get("source_type", "local"),
            "source_uri": record.get("source_uri", ""),
            "entrypoint": record.get("entrypoint", ""),
            "status": record.get("status", "disabled"),
            "version": str((record.get("manifest") or {}).get("version") or ""),
            "manifest": record.get("manifest", {}),
            "input_schema": record.get("input_schema", {}),
            "output_schema": record.get("output_schema", {}),
            "metadata": record.get("metadata", {}),
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }

    def _discovered_skill_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": record["cc_switch_id"],
            "name": record["name"],
            "description": record["description"],
            "source_type": record["source_type"],
            "source_uri": record["source_uri"],
            "entrypoint": record["entrypoint"],
            "status": record["status"],
            "version": str((record.get("manifest") or {}).get("version") or ""),
            "manifest": record.get("manifest", {}),
            "input_schema": record.get("input_schema", {}),
            "output_schema": record.get("output_schema", {}),
            "metadata": record.get("metadata", {}),
            "created_at": None,
            "updated_at": None,
        }


skill_service = SkillService()
