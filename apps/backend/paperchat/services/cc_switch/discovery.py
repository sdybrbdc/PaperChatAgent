from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


class CCSwitchDiscovery:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path.home() / ".cc-switch"
        self.db_path = self.root / "cc-switch.db"
        self.skills_dir = self.root / "skills"

    def source_payload(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "db_path": str(self.db_path),
            "skills_dir": str(self.skills_dir),
            "db_exists": self.db_path.exists(),
            "skills_dir_exists": self.skills_dir.exists(),
        }

    def discover_skills(self) -> list[dict[str, Any]]:
        rows = self._query_all(
            "select id, name, description, directory, repo_owner, repo_name, repo_branch, readme_url, "
            "enabled_claude, enabled_codex, enabled_gemini, enabled_opencode, enabled_hermes, "
            "installed_at, updated_at, content_hash from skills order by name"
        )
        if not rows:
            rows = self._scan_skill_dirs()

        skills: list[dict[str, Any]] = []
        for row in rows:
            directory = str(row.get("directory") or row.get("name") or "")
            source_path = Path(directory).expanduser()
            if not source_path.is_absolute():
                source_path = self.skills_dir / directory
            skill_md = source_path / "SKILL.md"
            markdown = self._read_text(skill_md)
            markdown_summary = self._extract_markdown_summary(markdown)
            description = str(row.get("description") or markdown_summary or "")
            name = str(row.get("name") or source_path.name)
            enabled_apps = [
                app
                for app, key in (
                    ("claude", "enabled_claude"),
                    ("codex", "enabled_codex"),
                    ("gemini", "enabled_gemini"),
                    ("opencode", "enabled_opencode"),
                    ("hermes", "enabled_hermes"),
                )
                if bool(row.get(key))
            ]
            status = "enabled" if enabled_apps else "disabled"
            content_hash = row.get("content_hash") or self._content_hash(markdown)
            manifest = {
                "name": name,
                "description": description,
                "version": str(row.get("updated_at") or row.get("installed_at") or "0"),
                "format": "SKILL.md",
                "source": "cc-switch",
                "cc_switch_id": row.get("id") or f"local:{name}",
                "enabled_apps": enabled_apps,
                "repo": {
                    "owner": row.get("repo_owner") or "",
                    "name": row.get("repo_name") or "",
                    "branch": row.get("repo_branch") or "",
                    "readme_url": row.get("readme_url") or "",
                },
            }
            skills.append(
                {
                    "cc_switch_id": row.get("id") or f"local:{name}",
                    "name": name,
                    "description": description,
                    "source_type": "local",
                    "source_uri": str(source_path),
                    "entrypoint": str(skill_md) if skill_md.exists() else "",
                    "status": status,
                    "manifest": manifest,
                    "input_schema": {},
                    "output_schema": {},
                    "metadata": {
                        "source": "cc-switch",
                        "cc_switch_id": row.get("id") or f"local:{name}",
                        "directory": directory,
                        "skill_md_path": str(skill_md) if skill_md.exists() else "",
                        "content_hash": content_hash,
                        "installed_at": row.get("installed_at") or 0,
                        "updated_at": row.get("updated_at") or 0,
                        "enabled_apps": enabled_apps,
                    },
                }
            )
        return skills

    def discover_mcp_servers(self) -> list[dict[str, Any]]:
        rows = self._query_all(
            "select id, name, description, homepage, docs, tags, server_config, "
            "enabled_claude, enabled_codex, enabled_gemini, enabled_opencode, enabled_hermes "
            "from mcp_servers order by name"
        )
        servers: list[dict[str, Any]] = []
        for row in rows:
            config = self._safe_json(row.get("server_config"), {})
            transport_type = str(config.get("type") or "stdio")
            enabled_apps = [
                app
                for app, key in (
                    ("claude", "enabled_claude"),
                    ("codex", "enabled_codex"),
                    ("gemini", "enabled_gemini"),
                    ("opencode", "enabled_opencode"),
                    ("hermes", "enabled_hermes"),
                )
                if bool(row.get(key))
            ]
            status = "enabled" if enabled_apps or bool(config.get("enabled")) else "disabled"
            env = dict(config.get("env") or {})
            headers = dict(config.get("headers") or {})
            servers.append(
                {
                    "cc_switch_id": row.get("id"),
                    "name": str(row.get("name") or row.get("id") or "MCP Server"),
                    "description": str(row.get("description") or ""),
                    "transport_type": transport_type,
                    "command": str(config.get("command") or ""),
                    "args": [str(item) for item in config.get("args") or []],
                    "endpoint_url": str(config.get("url") or config.get("endpoint_url") or ""),
                    "headers": headers,
                    "env": env,
                    "secret_config": {
                        "source": "cc-switch",
                        "cc_switch_id": row.get("id"),
                        "homepage": row.get("homepage") or "",
                        "docs": row.get("docs") or "",
                        "tags": self._safe_json(row.get("tags"), []),
                        "enabled_apps": enabled_apps,
                        "timeout": config.get("timeout"),
                        "raw_config": self._redact_config(config),
                    },
                    "status": status,
                }
            )
        return servers

    def _query_all(self, sql: str) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        try:
            with sqlite3.connect(self.db_path) as connection:
                connection.row_factory = sqlite3.Row
                return [dict(row) for row in connection.execute(sql).fetchall()]
        except sqlite3.Error:
            return []

    def _scan_skill_dirs(self) -> list[dict[str, Any]]:
        if not self.skills_dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for skill_dir in sorted(path for path in self.skills_dir.iterdir() if path.is_dir()):
            rows.append(
                {
                    "id": f"local:{skill_dir.name}",
                    "name": skill_dir.name,
                    "description": "",
                    "directory": skill_dir.name,
                    "enabled_codex": True,
                    "installed_at": 0,
                    "updated_at": 0,
                }
            )
        return rows

    def _safe_json(self, value: Any, default: Any) -> Any:
        if isinstance(value, (dict, list)):
            return value
        if not value:
            return default
        try:
            return json.loads(str(value))
        except json.JSONDecodeError:
            return default

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _extract_markdown_summary(self, markdown: str) -> str:
        for line in markdown.splitlines():
            clean = line.strip()
            if not clean or clean.startswith("---"):
                continue
            return clean.lstrip("#").strip()[:500]
        return ""

    def _content_hash(self, text: str) -> str:
        if not text:
            return ""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _redact_config(self, config: dict[str, Any]) -> dict[str, Any]:
        redacted = dict(config)
        if redacted.get("env"):
            redacted["env"] = {key: "***" for key in dict(redacted["env"]).keys()}
        if redacted.get("headers"):
            redacted["headers"] = {key: "***" for key in dict(redacted["headers"]).keys()}
        return redacted


cc_switch_discovery = CCSwitchDiscovery()
