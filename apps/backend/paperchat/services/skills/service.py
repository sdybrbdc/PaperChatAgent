from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml

from paperchat.api.errcode import AppError
from paperchat.schemas.skills import (
    SkillCreate,
    SkillFileAddRequest,
    SkillFileDeleteRequest,
    SkillFileUpdateRequest,
    SkillImportRequest,
    SkillTestRequest,
    SkillUpdate,
)
from paperchat.services.cc_switch import cc_switch_discovery
from paperchat.services.skills.repository import InMemorySkillRepository, SQLSkillRepository


class SkillService:
    """Manage AgentChat-style virtual Skill folders.

    The database schema already has a flexible metadata_json column, so the
    folder tree is stored in metadata["folder"] instead of introducing a table
    migration. Each folder item mirrors AgentChat:
    {name, path, type:"folder", folder:[...]} or {name, path, type:"file", content}.
    """

    SKILL_ROOTS = [
        Path.home() / ".agents" / "skills",
        Path.home() / ".codex" / "skills",
        Path.home() / ".claude" / "skills",
        Path.home() / ".cc-switch" / "skills",
    ]
    SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", "node_modules", "venv"}
    MAX_FILE_BYTES = 1024 * 1024
    DEFAULT_CONTENT_LIMIT = 24000

    def __init__(self) -> None:
        self._sql_repository = SQLSkillRepository()
        self._memory_repository = InMemorySkillRepository()

    @property
    def repository(self):
        return self._sql_repository if self._sql_repository.available else self._memory_repository

    def list_skills_payload(self, user_id: str) -> dict[str, Any]:
        return {"items": [self._skill_payload(item, include_folder=True) for item in self.repository.list_skills(user_id)]}

    def list_cc_switch_skills_payload(self) -> dict[str, Any]:
        return {
            "source": cc_switch_discovery.source_payload(),
            "items": [self._discovered_skill_payload(item) for item in cc_switch_discovery.discover_skills()],
        }

    def sync_cc_switch_skills_payload(self, user_id: str) -> dict[str, Any]:
        discovered = cc_switch_discovery.discover_skills()
        existing = self._list_existing_skill_keys(user_id)
        created = 0
        updated = 0
        items: list[dict[str, Any]] = []
        for item in discovered:
            match = self._find_existing_skill(existing, source_uri=str(item.get("source_uri") or ""), name=str(item["name"]))
            values = self._skill_values_from_local_path(
                Path(str(item["source_uri"])).expanduser(),
                status=str(item.get("status") or "enabled"),
                fallback_manifest=dict(item.get("manifest") or {}),
                fallback_metadata=dict(item.get("metadata") or {}),
            )
            if match:
                record = self.repository.update_skill(user_id, match["id"], values) or match
                updated += 1
            else:
                record = self.repository.create_skill(user_id, values)
                created += 1
            items.append(self._skill_payload(record, include_folder=True))
        return {
            "source": cc_switch_discovery.source_payload(),
            "created": created,
            "updated": updated,
            "total": len(items),
            "items": items,
        }

    def create_skill_payload(self, user_id: str, payload: SkillCreate) -> dict[str, Any]:
        values = self._prepare_create_values(payload.model_dump())
        duplicate = self._find_duplicate_skill(self._list_existing_skill_keys(user_id), values)
        if duplicate:
            raise AppError(status_code=409, code="SKILL_DUPLICATE", message=duplicate["message"])
        record = self.repository.create_skill(user_id, values)
        return self._skill_payload(record, include_folder=True)

    def import_skill_payload(self, user_id: str, payload: SkillImportRequest) -> dict[str, Any]:
        if not payload.source_uri.strip():
            return self.import_local_skills_payload(user_id=user_id, status=payload.status)

        source_path = Path(payload.source_uri).expanduser()
        values = self._skill_values_from_local_path(source_path, status=payload.status)
        duplicate = self._find_duplicate_skill(self._list_existing_skill_keys(user_id), values)
        if duplicate:
            return self.get_skill_payload(user_id, str(duplicate["id"]))
        record = self.repository.create_skill(user_id, values)
        return self._skill_payload(record, include_folder=True)

    def import_local_skills_payload(self, *, user_id: str, status: str = "enabled") -> dict[str, Any]:
        existing = self._list_existing_skill_keys(user_id)
        existing_sources = {str(item.get("source_uri") or "") for item in existing}
        created: list[str] = []
        skipped: list[str] = []
        failed: list[dict[str, str]] = []
        items: list[dict[str, Any]] = []
        sources = self._local_skill_sources()

        for source in sources:
            try:
                values = self._skill_values_from_local_path(source, status=status)
                name = str(values.get("name") or source.name)
                if str(source) in existing_sources:
                    skipped.append(name)
                    continue
                duplicate = self._find_duplicate_skill(existing, values)
                if duplicate:
                    skipped.append(name)
                    continue
                record = self.repository.create_skill(user_id, values)
                created.append(name)
                existing.append(self._skill_key_from_values(record))
                existing_sources.add(str(source))
                items.append(self._skill_payload(record, include_folder=True))
            except Exception as exc:
                failed.append({"name": source.name, "path": str(source), "error": str(exc)})

        return {
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "source_count": len(sources),
            "items": items,
        }

    def get_skill_payload(self, user_id: str, skill_id: str) -> dict[str, Any]:
        return self._skill_payload(self._require_skill(user_id, skill_id), include_folder=True)

    def update_skill_payload(self, user_id: str, skill_id: str, payload: SkillUpdate) -> dict[str, Any]:
        existing = self._require_skill(user_id, skill_id)
        values = self._prepare_update_values(existing, payload.model_dump(exclude_unset=True))
        duplicate = self._find_duplicate_skill(self._list_existing_skill_keys(user_id), values, ignore_id=skill_id)
        if duplicate:
            raise AppError(status_code=409, code="SKILL_DUPLICATE", message=duplicate["message"])
        record = self.repository.update_skill(user_id, skill_id, values)
        if record is None:
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return self._skill_payload(record, include_folder=True)

    def delete_skill_payload(self, user_id: str, skill_id: str) -> dict[str, Any]:
        if not self.repository.delete_skill(user_id, skill_id):
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return {"deleted": True, "id": skill_id}

    def update_skill_file_payload(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillFileUpdateRequest,
    ) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        folder = self._folder_from_skill(skill)
        target = self._find_file(folder, payload.path)
        if target is None:
            raise AppError(status_code=404, code="SKILL_FILE_NOT_FOUND", message="Skill 文件不存在")
        target["content"] = payload.content
        values = self._values_from_folder_update(skill, folder)
        duplicate = self._find_duplicate_skill(self._list_existing_skill_keys(user_id), values, ignore_id=skill_id)
        if duplicate:
            raise AppError(status_code=409, code="SKILL_DUPLICATE", message=duplicate["message"])
        record = self.repository.update_skill(user_id, skill_id, values) or skill
        return self._skill_payload(record, include_folder=True)

    def add_skill_file_payload(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillFileAddRequest,
    ) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        folder = self._folder_from_skill(skill)
        parent = self._find_folder(folder, payload.path)
        if parent is None:
            raise AppError(status_code=404, code="SKILL_FOLDER_NOT_FOUND", message="Skill 目录不存在")
        if not self._can_add_to_folder(parent):
            raise AppError(status_code=400, code="SKILL_FOLDER_READONLY", message="只能在 reference 或 scripts 目录下添加文件")
        name = payload.name.strip()
        if not name or "/" in name or "\\" in name:
            raise AppError(status_code=400, code="SKILL_FILE_NAME_INVALID", message="文件名不合法")
        children = parent.setdefault("folder", [])
        if any(item.get("name") == name for item in children):
            raise AppError(status_code=409, code="SKILL_FILE_EXISTS", message="同名文件已存在")
        children.append(
            {
                "name": name,
                "path": f"{str(parent['path']).rstrip('/')}/{name}",
                "type": "file",
                "content": payload.content or "",
            }
        )
        values = self._values_from_folder_update(skill, folder)
        duplicate = self._find_duplicate_skill(self._list_existing_skill_keys(user_id), values, ignore_id=skill_id)
        if duplicate:
            raise AppError(status_code=409, code="SKILL_DUPLICATE", message=duplicate["message"])
        record = self.repository.update_skill(user_id, skill_id, values) or skill
        return self._skill_payload(record, include_folder=True)

    def delete_skill_file_payload(
        self,
        *,
        user_id: str,
        skill_id: str,
        payload: SkillFileDeleteRequest,
    ) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        folder = self._folder_from_skill(skill)
        if payload.path.endswith("/SKILL.md"):
            raise AppError(status_code=400, code="SKILL_FILE_REQUIRED", message="不能删除 SKILL.md")
        deleted = self._delete_file(folder, payload.path)
        if not deleted:
            raise AppError(status_code=404, code="SKILL_FILE_NOT_FOUND", message="Skill 文件不存在")
        values = self._values_from_folder_update(skill, folder)
        record = self.repository.update_skill(user_id, skill_id, values) or skill
        return self._skill_payload(record, include_folder=True)

    def test_skill_payload(self, user_id: str, skill_id: str, payload: SkillTestRequest) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        validation = self._validate_input(skill.get("input_schema") or {}, payload.input)
        skill_md = self._skill_md_content(skill)
        return {
            "ok": validation["ok"],
            "executed": validation["ok"],
            "mode": "instruction_context",
            "message": (
                "Skill 指令上下文已加载，可在聊天中作为能力使用"
                if validation["ok"]
                else "Skill input does not satisfy the configured schema"
            ),
            "output": {
                "skill": self._skill_payload(skill, include_folder=False),
                "instruction_chars": len(skill_md),
                "instructions": self._clip_text(skill_md),
                "files": self._file_index(self._folder_from_skill(skill)),
            }
            if validation["ok"]
            else {},
            "validation": validation,
        }

    def execute_skill_payload(
        self,
        *,
        user_id: str,
        skill_id: str,
        input_payload: dict[str, Any],
        context: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        skill = self._require_skill(user_id, skill_id)
        validation = self._validate_input(skill.get("input_schema") or {}, input_payload)
        if not validation["ok"]:
            raise AppError(
                status_code=400,
                code="SKILL_INPUT_INVALID",
                message=f"Skill 输入缺少必要字段：{', '.join(validation['missing_required'])}",
            )
        folder = self._folder_from_skill(skill)
        skill_md = self._skill_md_content(skill)
        if not skill_md.strip():
            raise AppError(status_code=400, code="SKILL_INSTRUCTIONS_EMPTY", message="Skill 指令文件为空或不存在")
        return {
            "executed": not dry_run,
            "dry_run": dry_run,
            "mode": "instruction_context",
            "skill": self._skill_payload(skill, include_folder=False),
            "instructions": self._clip_text(skill_md, limit=self.DEFAULT_CONTENT_LIMIT),
            "files": self._load_context_files(folder, limit=self.DEFAULT_CONTENT_LIMIT),
            "input": input_payload,
            "context": context,
            "message": "已加载 Skill 文件夹上下文，聊天回复将按 SKILL.md 的说明执行。",
        }

    def _require_skill(self, user_id: str, skill_id: str) -> dict[str, Any]:
        record = self.repository.get_skill(user_id, skill_id)
        if record is None:
            raise AppError(status_code=404, code="SKILL_NOT_FOUND", message="Skill 不存在")
        return record

    def _find_existing_skill(
        self,
        existing: list[dict[str, Any]],
        *,
        source_uri: str,
        name: str,
    ) -> dict[str, Any] | None:
        for item in existing:
            if source_uri and item.get("source_uri") == source_uri:
                return item
            if name and item.get("name") == name:
                return item
        return None

    def _list_existing_skill_keys(self, user_id: str) -> list[dict[str, Any]]:
        list_keys = getattr(self.repository, "list_all_skill_keys", None)
        if callable(list_keys):
            return list_keys(user_id)
        return self.repository.list_skills(user_id)

    def _skill_key_from_values(self, values: dict[str, Any]) -> dict[str, str]:
        return {
            "id": str(values.get("id") or ""),
            "name": str(values.get("name") or ""),
            "source_uri": str(values.get("source_uri") or ""),
            "status": str(values.get("status") or ""),
            "content_hash": str((values.get("metadata") or {}).get("content_hash") or ""),
        }

    def _normalized_skill_name(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip()).casefold()

    def _find_duplicate_skill(
        self,
        existing: list[dict[str, Any]],
        values: dict[str, Any],
        *,
        ignore_id: str | None = None,
    ) -> dict[str, str] | None:
        name = self._normalized_skill_name(str(values.get("name") or ""))
        content_hash = str((values.get("metadata") or {}).get("content_hash") or "")
        for item in existing:
            item_id = str(item.get("id") or "")
            if ignore_id and item_id == ignore_id:
                continue
            if name and self._normalized_skill_name(str(item.get("name") or "")) == name:
                return {"id": item_id, "message": f"Skill 名称已存在：{values.get('name')}"}
            if content_hash and str(item.get("content_hash") or "") == content_hash:
                return {"id": item_id, "message": "Skill 内容已存在，不能重复导入"}
        return None

    def _local_skill_sources(self) -> list[Path]:
        skills_by_name: dict[str, Path] = {}
        for root in self.SKILL_ROOTS:
            if not root.exists():
                continue
            for current_root, dirnames, filenames in os.walk(root):
                dirnames[:] = [dirname for dirname in dirnames if dirname not in self.SKIP_DIR_NAMES]
                if "SKILL.md" not in filenames:
                    continue
                skill_dir = Path(current_root)
                skills_by_name.setdefault(skill_dir.name, skill_dir)
        return [skills_by_name[name] for name in sorted(skills_by_name)]

    def _prepare_create_values(self, values: dict[str, Any]) -> dict[str, Any]:
        name = str(values.get("name") or "").strip()
        description = str(values.get("description") or "").strip()
        content = str(values.get("content") or "").strip()
        folder = self._default_skill_folder(name=name, description=description, content=content)
        return self._record_values_from_folder(
            name=name,
            description=description,
            source_type=str(values.get("source_type") or "custom"),
            source_uri=str(values.get("source_uri") or ""),
            entrypoint=str(values.get("entrypoint") or ""),
            status=str(values.get("status") or "disabled"),
            folder=folder,
            manifest=dict(values.get("manifest") or {}),
            input_schema=dict(values.get("input_schema") or {}),
            output_schema=dict(values.get("output_schema") or {}),
            metadata=dict(values.get("metadata") or {}),
        )

    def _prepare_update_values(self, existing: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        folder = self._folder_from_skill(existing)
        metadata = dict(existing.get("metadata") or {})
        manifest = dict(existing.get("manifest") or {})

        def merged_value(key: str, fallback: Any) -> Any:
            return values[key] if key in values and values[key] is not None else fallback

        if values.get("content") is not None:
            skill_md = self._find_file(folder, f"/{folder['name']}/SKILL.md") or self._find_file_by_name(folder, "SKILL.md")
            if skill_md is None:
                folder.setdefault("folder", []).insert(
                    0,
                    {
                        "name": "SKILL.md",
                        "path": f"/{folder['name']}/SKILL.md",
                        "type": "file",
                        "content": str(values["content"] or ""),
                    },
                )
            else:
                skill_md["content"] = str(values["content"] or "")
        name = str(merged_value("name", existing.get("name") or folder.get("name") or "custom-skill")).strip()
        description = str(merged_value("description", existing.get("description") or "")).strip()
        if values.get("name"):
            folder["name"] = name
            folder["path"] = f"/{name}"
            self._refresh_paths(folder, folder["path"])
        values_for_record = self._record_values_from_folder(
            name=name,
            description=description,
            source_type=str(merged_value("source_type", existing.get("source_type") or "custom")),
            source_uri=str(merged_value("source_uri", existing.get("source_uri") or "")),
            entrypoint=str(merged_value("entrypoint", existing.get("entrypoint") or "")),
            status=str(merged_value("status", existing.get("status") or "disabled")),
            folder=folder,
            manifest={**manifest, **dict(values.get("manifest") or {})},
            input_schema=dict(merged_value("input_schema", existing.get("input_schema") or {})),
            output_schema=dict(merged_value("output_schema", existing.get("output_schema") or {})),
            metadata={**metadata, **dict(values.get("metadata") or {})},
        )
        return values_for_record

    def _skill_values_from_local_path(
        self,
        source_path: Path,
        *,
        status: str,
        fallback_manifest: dict[str, Any] | None = None,
        fallback_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not source_path.exists():
            raise AppError(status_code=400, code="SKILL_SOURCE_NOT_FOUND", message="Skill 本地路径不存在")
        skill_dir = source_path.parent if source_path.is_file() else source_path
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise AppError(status_code=400, code="SKILL_MD_NOT_FOUND", message="目录下没有 SKILL.md")
        content = self._read_local_skill_file(skill_md)
        frontmatter = self._extract_frontmatter(content)
        name = str(frontmatter.get("name") or skill_dir.name)
        description = str(frontmatter.get("description") or self._extract_markdown_summary_text(content) or "")
        manifest = {**dict(fallback_manifest or {}), **frontmatter}
        manifest.setdefault("name", name)
        manifest.setdefault("description", description)
        manifest.setdefault("version", "0.0.0")
        manifest.setdefault("format", "SKILL.md")
        manifest["skill_md_path"] = str(skill_md)
        metadata = {
            **dict(fallback_metadata or {}),
            "imported_from": str(skill_dir),
            "skill_md_path": str(skill_md),
            "content_source": "database",
        }
        return self._record_values_from_folder(
            name=name,
            description=description,
            source_type="local",
            source_uri=str(skill_dir),
            entrypoint=str(skill_md),
            status=status,
            folder=self._local_skill_folder(skill_dir),
            manifest=manifest,
            input_schema=dict(manifest.get("input_schema") or {}),
            output_schema=dict(manifest.get("output_schema") or {}),
            metadata=metadata,
        )

    def _record_values_from_folder(
        self,
        *,
        name: str,
        description: str,
        source_type: str,
        source_uri: str,
        entrypoint: str,
        status: str,
        folder: dict[str, Any],
        manifest: dict[str, Any],
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        skill_md = self._find_file_by_name(folder, "SKILL.md")
        skill_md_content = str((skill_md or {}).get("content") or "")
        frontmatter = self._extract_frontmatter(skill_md_content)
        manifest = {**manifest, **{key: value for key, value in frontmatter.items() if value not in (None, "")}}
        manifest.setdefault("name", name)
        manifest.setdefault("description", description)
        manifest.setdefault("version", "0.0.0")
        manifest.setdefault("format", "SKILL.md")
        trigger_phrases = self._trigger_phrases_from_values(name, description, manifest, metadata)
        metadata = {
            **metadata,
            "folder": folder,
            "file_count": self._count_files(folder),
            "content_hash": self._folder_content_hash(folder),
            "trigger_phrases": trigger_phrases,
            "as_tool_name": self._safe_tool_name(str(manifest.get("name") or name)),
        }
        return {
            "name": name,
            "description": description or str(manifest.get("description") or ""),
            "source_type": source_type,
            "source_uri": source_uri,
            "entrypoint": entrypoint,
            "status": status,
            "manifest": manifest,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "metadata": metadata,
        }

    def _values_from_folder_update(self, skill: dict[str, Any], folder: dict[str, Any]) -> dict[str, Any]:
        return self._record_values_from_folder(
            name=str(skill.get("name") or folder.get("name") or ""),
            description=str(skill.get("description") or ""),
            source_type=str(skill.get("source_type") or "custom"),
            source_uri=str(skill.get("source_uri") or ""),
            entrypoint=str(skill.get("entrypoint") or ""),
            status=str(skill.get("status") or "disabled"),
            folder=folder,
            manifest=dict(skill.get("manifest") or {}),
            input_schema=dict(skill.get("input_schema") or {}),
            output_schema=dict(skill.get("output_schema") or {}),
            metadata=dict(skill.get("metadata") or {}),
        )

    def _default_skill_folder(self, *, name: str, description: str, content: str = "") -> dict[str, Any]:
        safe_name = name.strip() or "custom-skill"
        safe_description = description.strip() or "Describe when this skill should be used and what workflow to follow."
        skill_content = content.strip() or (
            "---\n"
            f"name: {safe_name}\n"
            f"description: {safe_description}\n"
            "version: 0.0.1\n"
            "---\n\n"
            f"# {safe_name}\n\n"
            "## When To Use\n"
            f"{safe_description}\n\n"
            "## Workflow\n"
            "1. Read the user request and decide whether this skill is relevant.\n"
            "2. Follow the task-specific instructions in this file.\n"
            "3. Keep the response focused on the user's current goal.\n"
        )
        return {
            "name": safe_name,
            "path": f"/{safe_name}",
            "type": "folder",
            "folder": [
                {
                    "name": "SKILL.md",
                    "path": f"/{safe_name}/SKILL.md",
                    "type": "file",
                    "content": skill_content,
                },
                {"name": "reference", "path": f"/{safe_name}/reference", "type": "folder", "folder": []},
                {"name": "scripts", "path": f"/{safe_name}/scripts", "type": "folder", "folder": []},
            ],
        }

    def _local_skill_folder(self, skill_dir: Path) -> dict[str, Any]:
        def build_item(path: Path) -> dict[str, Any] | None:
            if path.name in self.SKIP_DIR_NAMES:
                return None
            relative_path = path.relative_to(skill_dir)
            item_path = f"/{skill_dir.name}"
            if str(relative_path) != ".":
                item_path = f"{item_path}/{relative_path.as_posix()}"
            if path.is_dir():
                children = [
                    item
                    for child in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
                    if (item := build_item(child)) is not None
                ]
                return {"name": path.name, "type": "folder", "path": item_path, "folder": children}
            return {
                "name": path.name,
                "type": "file",
                "path": item_path,
                "content": self._read_local_skill_file(path),
            }

        folder = build_item(skill_dir)
        if folder is None or folder.get("type") != "folder":
            raise AppError(status_code=400, code="SKILL_FOLDER_INVALID", message="Skill 目录结构无效")
        return folder

    def _folder_from_skill(self, skill: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(skill.get("metadata") or {})
        folder = metadata.get("folder")
        if isinstance(folder, dict):
            return json.loads(json.dumps(folder, ensure_ascii=False))
        custom_content = metadata.get("custom_content")
        if isinstance(custom_content, str):
            return self._default_skill_folder(
                name=str(skill.get("name") or "custom-skill"),
                description=str(skill.get("description") or ""),
                content=custom_content,
            )
        return self._default_skill_folder(
            name=str(skill.get("name") or "custom-skill"),
            description=str(skill.get("description") or ""),
            content=self._load_legacy_skill_content(skill),
        )

    def _load_legacy_skill_content(self, skill: dict[str, Any]) -> str:
        for candidate in (
            str(skill.get("entrypoint") or ""),
            str((skill.get("metadata") or {}).get("skill_md_path") or ""),
            str(skill.get("source_uri") or ""),
        ):
            if not candidate:
                continue
            path = Path(candidate).expanduser()
            if path.is_dir():
                path = path / "SKILL.md"
            try:
                if path.exists() and path.is_file():
                    return path.read_text(encoding="utf-8")
            except OSError:
                continue
        return ""

    def _find_folder(self, folder: dict[str, Any], path: str) -> dict[str, Any] | None:
        if folder.get("type") == "folder" and folder.get("path") == path:
            return folder
        for item in folder.get("folder") or []:
            if item.get("type") == "folder":
                found = self._find_folder(item, path)
                if found is not None:
                    return found
        return None

    def _find_file(self, folder: dict[str, Any], path: str) -> dict[str, Any] | None:
        for item in folder.get("folder") or []:
            if item.get("type") == "file" and item.get("path") == path:
                return item
            if item.get("type") == "folder":
                found = self._find_file(item, path)
                if found is not None:
                    return found
        return None

    def _find_file_by_name(self, folder: dict[str, Any], name: str) -> dict[str, Any] | None:
        for item in folder.get("folder") or []:
            if item.get("type") == "file" and item.get("name") == name:
                return item
            if item.get("type") == "folder":
                found = self._find_file_by_name(item, name)
                if found is not None:
                    return found
        return None

    def _delete_file(self, folder: dict[str, Any], path: str) -> bool:
        children = folder.get("folder") or []
        for index, item in enumerate(children):
            if item.get("type") == "file" and item.get("path") == path:
                del children[index]
                return True
            if item.get("type") == "folder" and self._delete_file(item, path):
                return True
        return False

    def _refresh_paths(self, item: dict[str, Any], path: str) -> None:
        item["path"] = path
        if item.get("type") != "folder":
            return
        for child in item.get("folder") or []:
            self._refresh_paths(child, f"{path.rstrip('/')}/{child.get('name')}")

    def _can_add_to_folder(self, folder: dict[str, Any]) -> bool:
        return str(folder.get("name") or "") in {"reference", "references", "scripts"}

    def _skill_md_content(self, skill: dict[str, Any]) -> str:
        folder = self._folder_from_skill(skill)
        file_item = self._find_file_by_name(folder, "SKILL.md")
        return str((file_item or {}).get("content") or "")

    def _file_index(self, folder: dict[str, Any]) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []

        def walk(item: dict[str, Any]) -> None:
            if item.get("type") == "file":
                files.append({"name": str(item.get("name") or ""), "path": str(item.get("path") or "")})
                return
            for child in item.get("folder") or []:
                walk(child)

        walk(folder)
        return files

    def _load_context_files(self, folder: dict[str, Any], *, limit: int) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        used = 0

        def walk(item: dict[str, Any]) -> None:
            nonlocal used
            if used >= limit:
                return
            if item.get("type") == "file":
                if item.get("name") == "SKILL.md":
                    return
                content = str(item.get("content") or "")
                remaining = max(limit - used, 0)
                clipped = self._clip_text(content, limit=min(remaining, 6000))
                used += len(clipped)
                files.append(
                    {
                        "name": str(item.get("name") or ""),
                        "path": str(item.get("path") or ""),
                        "content": clipped,
                    }
                )
                return
            for child in item.get("folder") or []:
                walk(child)

        walk(folder)
        return files

    def _count_files(self, folder: dict[str, Any]) -> int:
        return len(self._file_index(folder))

    def _folder_hash(self, folder: dict[str, Any]) -> str:
        text = json.dumps(folder, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _folder_content_hash(self, folder: dict[str, Any]) -> str:
        files: list[dict[str, str]] = []

        def walk(item: dict[str, Any], relative_prefix: str = "") -> None:
            if item.get("type") == "file":
                files.append(
                    {
                        "path": relative_prefix + str(item.get("name") or ""),
                        "content": str(item.get("content") or ""),
                    }
                )
                return
            for child in item.get("folder") or []:
                child_name = str(child.get("name") or "")
                next_prefix = relative_prefix
                if item is not folder:
                    next_prefix = f"{relative_prefix}{str(item.get('name') or '')}/"
                if child.get("type") == "folder":
                    walk(child, next_prefix)
                else:
                    walk(child, next_prefix)

        walk(folder)
        text = json.dumps(sorted(files, key=lambda item: item["path"]), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _read_local_skill_file(self, path: Path) -> str:
        try:
            if path.stat().st_size > self.MAX_FILE_BYTES:
                return f"[Skipped: file is larger than {self.MAX_FILE_BYTES} bytes]"
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return "[Skipped: binary or non-UTF-8 file]"
        except OSError:
            return ""

    def _validate_input(self, schema: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        required = schema.get("required") if isinstance(schema, dict) else None
        missing = [key for key in required or [] if key not in payload]
        return {
            "ok": not missing,
            "missing_required": missing,
            "schema_checked": bool(schema),
            "placeholder": False,
        }

    def _extract_frontmatter(self, markdown: str) -> dict[str, Any]:
        match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", markdown, flags=re.S)
        if not match:
            return {}
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
        return data if isinstance(data, dict) else {}

    def _strip_frontmatter(self, markdown: str) -> str:
        return re.sub(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", "", markdown, count=1, flags=re.S)

    def _extract_markdown_summary_text(self, markdown: str) -> str:
        body = self._strip_frontmatter(markdown)
        for line in body.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("```"):
                continue
            clean = clean.lstrip("#").strip()
            if clean:
                return clean[:255]
        return ""

    def _trigger_phrases_from_values(
        self,
        name: str,
        description: str,
        manifest: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        phrases: list[str] = []
        for value in (
            name,
            str((manifest or {}).get("name") or ""),
            str((metadata or {}).get("as_tool_name") or ""),
            *[str(item) for item in ((manifest or {}).get("aliases") or []) if item],
            *[str(item) for item in ((metadata or {}).get("trigger_phrases") or []) if item],
        ):
            clean = value.strip()
            if clean and clean not in phrases:
                phrases.append(clean)
        for token in re.split(r"[，,、/|;\s]+", description):
            clean = token.strip()
            if len(clean) >= 4 and clean not in phrases:
                phrases.append(clean)
            if len(phrases) >= 12:
                break
        return phrases[:12]

    def _safe_tool_name(self, name: str) -> str:
        tool_name = re.sub(r"[^A-Za-z0-9_]", "_", name).strip("_").lower()
        if not tool_name:
            tool_name = "local"
        if tool_name[0].isdigit():
            tool_name = f"_{tool_name}"
        if not tool_name.endswith("_skill"):
            tool_name = f"{tool_name}_skill"
        return tool_name

    def _clip_text(self, text: str, *, limit: int = 20000) -> str:
        if len(text) <= limit:
            return text
        return text[:limit] + "\n\n[内容过长，已截断]"

    def _preview_text(self, text: str, *, limit: int = 500) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) <= limit:
            return clean
        return clean[: limit - 3].rstrip() + "..."

    def _public_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        hidden_keys = {"folder", "custom_content"}
        return {key: value for key, value in metadata.items() if key not in hidden_keys}

    def _skill_payload(self, record: dict[str, Any], *, include_folder: bool = False) -> dict[str, Any]:
        folder = self._folder_from_skill(record)
        skill_md = self._skill_md_content(record)
        metadata = dict(record.get("metadata") or {})
        payload = {
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
            "metadata": self._public_metadata(metadata),
            "folder": folder if include_folder else None,
            "content": skill_md if include_folder else "",
            "content_preview": self._preview_text(skill_md),
            "content_source": "database",
            "file_count": self._count_files(folder),
            "as_tool_name": str(metadata.get("as_tool_name") or self._safe_tool_name(str(record.get("name") or ""))),
            "trigger_phrases": [
                str(item) for item in metadata.get("trigger_phrases") or [] if str(item).strip()
            ],
            "created_at": record.get("created_at"),
            "updated_at": record.get("updated_at"),
        }
        return payload

    def _discovered_skill_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(record.get("metadata") or {})
        content = ""
        skill_md_path = str(metadata.get("skill_md_path") or record.get("entrypoint") or "")
        if skill_md_path:
            try:
                content = Path(skill_md_path).expanduser().read_text(encoding="utf-8")
            except OSError:
                content = ""
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
            "folder": None,
            "content": "",
            "content_preview": self._preview_text(content),
            "content_source": "file" if content else "metadata",
            "file_count": 1 if content else 0,
            "as_tool_name": self._safe_tool_name(str(record.get("name") or "")),
            "trigger_phrases": self._trigger_phrases_from_values(
                str(record.get("name") or ""),
                str(record.get("description") or ""),
                dict(record.get("manifest") or {}),
                metadata,
            ),
            "created_at": None,
            "updated_at": None,
        }


skill_service = SkillService()
