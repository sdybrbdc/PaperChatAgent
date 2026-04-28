from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LarkCliCommand:
    args: list[str]
    reason: str
    read_only: bool = True


class LarkCliSkillRuntime:
    """Small, guarded bridge from lark-* Skills to the local lark-cli binary."""

    DEFAULT_TIMEOUT_SECONDS = 45
    OUTPUT_LIMIT = 24000

    def can_handle(self, skill: dict[str, Any]) -> bool:
        name = str(skill.get("name") or "").lower()
        manifest_name = str((skill.get("manifest") or {}).get("name") or "").lower()
        return name.startswith("lark-") or manifest_name.startswith("lark-")

    async def execute(
        self,
        *,
        skill: dict[str, Any],
        input_payload: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        binary = shutil.which("lark-cli")
        if not binary:
            return {
                "available": False,
                "executed": False,
                "message": "本机未找到 lark-cli，请先安装并确保它在 PATH 中。",
            }

        command = self._command_from_payload(input_payload) or self._infer_command(
            skill=skill,
            user_input=str(input_payload.get("user_input") or input_payload.get("instruction") or ""),
        )
        if command is None:
            return {
                "available": True,
                "executed": False,
                "message": "已加载 Lark Skill，但暂未从用户请求中推断出安全的只读 lark-cli 命令。",
            }
        if not command.read_only:
            return {
                "available": True,
                "executed": False,
                "requires_confirmation": True,
                "command": ["lark-cli", *command.args],
                "message": "该 Skill 需要执行写入或修改类命令，必须先获得用户明确确认。",
            }
        if dry_run:
            return {
                "available": True,
                "executed": False,
                "dry_run": True,
                "command": ["lark-cli", *command.args],
                "reason": command.reason,
            }

        proc = await asyncio.create_subprocess_exec(
            binary,
            *command.args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.DEFAULT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "available": True,
                "executed": True,
                "ok": False,
                "command": ["lark-cli", *command.args],
                "reason": command.reason,
                "returncode": -1,
                "stderr": f"lark-cli 执行超过 {self.DEFAULT_TIMEOUT_SECONDS} 秒，已终止。",
            }

        stdout = self._clip(stdout_bytes.decode("utf-8", errors="replace"))
        stderr = self._clip(stderr_bytes.decode("utf-8", errors="replace"), limit=6000)
        parsed = self._parse_json(stdout)
        items = self._extract_result_items(parsed)
        return {
            "available": True,
            "executed": True,
            "ok": proc.returncode == 0,
            "command": ["lark-cli", *command.args],
            "reason": command.reason,
            "returncode": proc.returncode,
            "summary": self._summarize_result(parsed, stdout, items),
            "items": items,
            "stdout": stdout,
            "stderr": stderr,
            "json": parsed,
        }

    def _command_from_payload(self, input_payload: dict[str, Any]) -> LarkCliCommand | None:
        raw_args = input_payload.get("lark_cli_args")
        if not isinstance(raw_args, list) or not all(isinstance(item, str) for item in raw_args):
            return None
        args = [item for item in raw_args if item]
        if args and args[0] == "lark-cli":
            args = args[1:]
        if not self._is_read_only_args(args):
            return LarkCliCommand(args=args, reason="用户或路由器提供了 lark-cli 参数", read_only=False)
        return LarkCliCommand(args=args, reason="用户或路由器提供了 lark-cli 参数")

    def _infer_command(self, *, skill: dict[str, Any], user_input: str) -> LarkCliCommand | None:
        name = str(skill.get("name") or (skill.get("manifest") or {}).get("name") or "").lower()
        if name == "lark-doc":
            return self._infer_doc_command(user_input)
        return None

    def _infer_doc_command(self, user_input: str) -> LarkCliCommand | None:
        query = self._extract_doc_query(user_input)
        if query is None:
            return None
        args = ["docs", "+search", "--as", "user", "--page-size", "10", "--format", "json"]
        if query:
            args.extend(["--query", query])
        return LarkCliCommand(
            args=args,
            reason="根据 lark-doc Skill，将飞书文档资源发现请求映射到 docs +search。",
        )

    def _extract_doc_query(self, user_input: str) -> str | None:
        text = re.sub(r"\s+", " ", user_input).strip()
        if not text:
            return None
        lowered = text.lower()
        has_lark_context = any(token in lowered for token in ("飞书", "lark", "feishu"))
        has_doc_context = any(token in text for token in ("文档", "云空间", "知识库", "wiki", "表格", "报表"))
        if not (has_lark_context and has_doc_context):
            return None

        quoted = re.search(r"[「『“\"']([^」』”\"']{1,80})[」』”\"']", text)
        if quoted:
            candidate = quoted.group(1).strip()
            if candidate and not any(token in candidate for token in ("文档", "哪些", "所有")):
                return candidate

        match = re.search(r"(?:搜索|查找|查询|找|搜)(?:一下|下|看看)?(?:飞书)?(?:里|下|中的)?(?:关于|标题为|名为|叫)?(.+)", text)
        if match:
            candidate = self._clean_query(match.group(1))
            if candidate:
                return candidate

        if any(token in text for token in ("哪些文档", "有哪些文档", "所有文档", "最近文档", "文档列表")):
            return ""
        if "文档" in text and any(token in text for token in ("哪些", "有什么", "列出", "查看")):
            return ""
        return ""

    def _clean_query(self, value: str) -> str:
        clean = re.sub(r"^(飞书|云空间|文档|文件|资料|里面|下|里|的)+", "", value.strip())
        clean = re.sub(r"[，,。？?！!].*$", "", clean).strip()
        clean = clean.strip("「」『』“”\"' ")
        if clean in {"文档", "有哪些文档", "哪些文档", "所有文档", "文档列表"}:
            return ""
        return clean[:80]

    def _is_read_only_args(self, args: list[str]) -> bool:
        if len(args) < 2:
            return False
        domain = args[0]
        operation = args[1]
        readonly_shortcuts = {
            "docs": {"+search", "+fetch", "+media-download"},
            "wiki": {"spaces", "nodes"},
            "drive": {"files", "folders", "permissions", "comments"},
            "sheets": {"+read", "+find"},
            "base": {"+table", "+field", "+record", "+view"},
        }
        if domain not in readonly_shortcuts:
            return False
        if operation not in readonly_shortcuts[domain]:
            return False
        return not any(arg in {"--data", "--dry-run=false"} for arg in args)

    def _parse_json(self, text: str) -> Any:
        clean = text.strip()
        if not clean:
            return None
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            return None

    def _extract_result_items(self, parsed: Any) -> list[dict[str, Any]]:
        if not isinstance(parsed, dict):
            return []
        data = parsed.get("data") if isinstance(parsed.get("data"), dict) else parsed
        raw_items = data.get("results") or data.get("items") or data.get("files") or []
        if not isinstance(raw_items, list):
            return []
        items: list[dict[str, Any]] = []
        for raw in raw_items[:10]:
            if not isinstance(raw, dict):
                continue
            meta = raw.get("result_meta") if isinstance(raw.get("result_meta"), dict) else {}
            title = str(raw.get("title_highlighted") or meta.get("title") or "").strip()
            title = re.sub(r"</?h[b]?>", "", title)
            items.append(
                {
                    "title": title,
                    "entity_type": raw.get("entity_type") or meta.get("entity_type") or "",
                    "doc_type": meta.get("doc_types") or meta.get("obj_type") or meta.get("type") or "",
                    "url": meta.get("url") or raw.get("url") or "",
                    "owner_name": meta.get("owner_name") or "",
                    "update_time": meta.get("update_time_iso") or meta.get("update_time") or "",
                    "last_open_time": meta.get("last_open_time_iso") or meta.get("last_open_time") or "",
                }
            )
        return items

    def _summarize_result(self, parsed: Any, stdout: str, items: list[dict[str, Any]] | None = None) -> str:
        if isinstance(parsed, dict):
            data = parsed.get("data") if isinstance(parsed.get("data"), dict) else parsed
            if items:
                has_more = data.get("has_more") if isinstance(data, dict) else None
                suffix = "，还有更多结果" if has_more else ""
                return f"lark-cli 返回 {len(items)} 条结果{suffix}。"
            for key in ("items", "data", "results"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return f"lark-cli 返回 {len(value)} 条结果。"
                if isinstance(value, dict):
                    for nested_key in ("items", "docs", "files", "list"):
                        nested = value.get(nested_key)
                        if isinstance(nested, list):
                            return f"lark-cli 返回 {len(nested)} 条结果。"
            if isinstance(parsed.get("code"), int) and parsed.get("code") != 0:
                return str(parsed.get("msg") or parsed.get("message") or "lark-cli 返回错误。")[:600]
        return stdout[:600] if stdout else "lark-cli 已执行。"

    def _clip(self, text: str, *, limit: int | None = None) -> str:
        max_len = limit or self.OUTPUT_LIMIT
        if len(text) <= max_len:
            return text
        return text[:max_len] + "\n[输出过长，已截断]"


lark_cli_skill_runtime = LarkCliSkillRuntime()
