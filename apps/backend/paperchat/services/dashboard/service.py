from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select

from paperchat.database.models.tables import PaperChatResearchTaskRecord, PaperChatToolInvocationLogRecord
from paperchat.database.sql import db_session
from paperchat.services.model_router.records import PaperChatModelUsageLogRecord


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DashboardService:
    def _range(self, days: int) -> tuple[datetime, datetime]:
        end_at = utcnow()
        return end_at - timedelta(days=days), end_at

    def _range_payload(self, *, start_at: datetime, end_at: datetime, days: int) -> dict[str, Any]:
        return {"start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "days": days}

    def _usage_totals(self, *, user_id: str, start_at: datetime) -> dict[str, Any]:
        with db_session() as session:
            row = session.execute(
                select(
                    func.count(PaperChatModelUsageLogRecord.id),
                    func.coalesce(func.sum(PaperChatModelUsageLogRecord.input_tokens), 0),
                    func.coalesce(func.sum(PaperChatModelUsageLogRecord.output_tokens), 0),
                    func.coalesce(
                        func.sum(PaperChatModelUsageLogRecord.input_tokens + PaperChatModelUsageLogRecord.output_tokens),
                        0,
                    ),
                    func.coalesce(func.avg(PaperChatModelUsageLogRecord.latency_ms), 0),
                ).where(
                    PaperChatModelUsageLogRecord.user_id == user_id,
                    PaperChatModelUsageLogRecord.created_at >= start_at,
                )
            ).one()
        return {
            "request_count": int(row[0] or 0),
            "prompt_tokens": int(row[1] or 0),
            "completion_tokens": int(row[2] or 0),
            "total_tokens": int(row[3] or 0),
            "cost_usd": 0,
            "avg_latency_ms": float(row[4] or 0),
        }

    def _status_success_case(self, column):
        return case((column.in_(("success", "succeeded", "completed")), 1), else_=0)

    def _task_status_counts(self, *, user_id: str, start_at: datetime) -> dict[str, int]:
        with db_session() as session:
            rows = session.execute(
                select(PaperChatResearchTaskRecord.status, func.count(PaperChatResearchTaskRecord.id))
                .where(
                    PaperChatResearchTaskRecord.user_id == user_id,
                    PaperChatResearchTaskRecord.created_at >= start_at,
                )
                .group_by(PaperChatResearchTaskRecord.status)
            ).all()
        return {str(status or "unknown"): int(count or 0) for status, count in rows}

    def _tool_call_count(self, *, user_id: str, start_at: datetime) -> int:
        with db_session() as session:
            value = session.scalar(
                select(func.count(PaperChatToolInvocationLogRecord.id)).where(
                    PaperChatToolInvocationLogRecord.user_id == user_id,
                    PaperChatToolInvocationLogRecord.created_at >= start_at,
                )
            )
        return int(value or 0)

    def overview_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        usage = self._usage_totals(user_id=user_id, start_at=start_at)
        task_counts = self._task_status_counts(user_id=user_id, start_at=start_at)
        task_total = sum(task_counts.values())
        completed = task_counts.get("completed", 0) + task_counts.get("success", 0)
        failed = task_counts.get("failed", 0) + task_counts.get("error", 0)
        tool_call_count = self._tool_call_count(user_id=user_id, start_at=start_at)
        return {
            "range": self._range_payload(start_at=start_at, end_at=end_at, days=days),
            "model_call_count": usage["request_count"],
            "input_token_count": usage["prompt_tokens"],
            "output_token_count": usage["completion_tokens"],
            "token_count": usage["total_tokens"],
            "recent_task_count": task_total,
            "active_task_count": task_counts.get("running", 0) + task_counts.get("pending", 0),
            "failed_task_count": failed,
            "tool_call_count": tool_call_count,
            "task_status_distribution": task_counts,
            "usage": usage,
            "tasks": {
                "total": task_total,
                "completed": completed,
                "failed": failed,
                "running": task_counts.get("running", 0),
                "pending": task_counts.get("pending", 0),
                "by_status": task_counts,
                "completion_rate": completed / task_total if task_total else 0,
            },
            "health": {
                "task_completion_rate": completed / task_total if task_total else 0,
                "task_failure_rate": failed / task_total if task_total else 0,
                "avg_latency_ms": usage["avg_latency_ms"],
                "tool_call_count": tool_call_count,
            },
        }

    def model_usage_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        with db_session() as session:
            rows = session.execute(
                select(
                    PaperChatModelUsageLogRecord.model_name,
                    PaperChatModelUsageLogRecord.provider_key,
                    PaperChatModelUsageLogRecord.route_key,
                    func.count(PaperChatModelUsageLogRecord.id),
                    func.coalesce(func.sum(PaperChatModelUsageLogRecord.input_tokens), 0),
                    func.coalesce(func.sum(PaperChatModelUsageLogRecord.output_tokens), 0),
                    func.coalesce(
                        func.sum(PaperChatModelUsageLogRecord.input_tokens + PaperChatModelUsageLogRecord.output_tokens),
                        0,
                    ),
                    func.coalesce(func.avg(PaperChatModelUsageLogRecord.latency_ms), 0),
                    func.sum(self._status_success_case(PaperChatModelUsageLogRecord.status)),
                )
                .where(
                    PaperChatModelUsageLogRecord.user_id == user_id,
                    PaperChatModelUsageLogRecord.created_at >= start_at,
                )
                .group_by(
                    PaperChatModelUsageLogRecord.model_name,
                    PaperChatModelUsageLogRecord.provider_key,
                    PaperChatModelUsageLogRecord.route_key,
                )
                .order_by(func.count(PaperChatModelUsageLogRecord.id).desc())
            ).all()
        items = []
        for model_name, provider_key, route_key, count, input_tokens, output_tokens, tokens, latency, success in rows:
            request_count = int(count or 0)
            success_count = int(success or 0)
            items.append(
                {
                    "model_name": model_name or "unknown",
                    "provider_key": provider_key,
                    "provider_name": provider_key,
                    "route_key": route_key,
                    "request_count": request_count,
                    "call_count": request_count,
                    "success_count": success_count,
                    "error_count": request_count - success_count,
                    "success_rate": success_count / request_count if request_count else 0,
                    "total_tokens": int(tokens or 0),
                    "input_tokens": int(input_tokens or 0),
                    "output_tokens": int(output_tokens or 0),
                    "cost_usd": 0,
                    "avg_latency_ms": float(latency or 0),
                    "latency_ms": float(latency or 0),
                }
            )
        return {"range": self._range_payload(start_at=start_at, end_at=end_at, days=days), "items": items}

    def task_distribution_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        with db_session() as session:
            rows = session.execute(
                select(
                    PaperChatResearchTaskRecord.status,
                    PaperChatResearchTaskRecord.current_node,
                    func.count(PaperChatResearchTaskRecord.id),
                    func.coalesce(func.avg(PaperChatResearchTaskRecord.progress), 0),
                )
                .where(
                    PaperChatResearchTaskRecord.user_id == user_id,
                    PaperChatResearchTaskRecord.created_at >= start_at,
                )
                .group_by(PaperChatResearchTaskRecord.status, PaperChatResearchTaskRecord.current_node)
                .order_by(func.count(PaperChatResearchTaskRecord.id).desc())
            ).all()
        items = [
            {
                "status": status or "unknown",
                "current_node": current_node or "",
                "count": int(count or 0),
                "avg_progress": float(progress or 0),
                "average_progress": float(progress or 0),
            }
            for status, current_node, count, progress in rows
        ]
        return {"range": self._range_payload(start_at=start_at, end_at=end_at, days=days), "items": items}

    def tool_usage_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        with db_session() as session:
            rows = session.execute(
                select(
                    PaperChatToolInvocationLogRecord.capability_id,
                    PaperChatToolInvocationLogRecord.capability_type,
                    func.count(PaperChatToolInvocationLogRecord.id),
                    func.sum(self._status_success_case(PaperChatToolInvocationLogRecord.status)),
                    func.coalesce(func.avg(PaperChatToolInvocationLogRecord.latency_ms), 0),
                )
                .where(
                    PaperChatToolInvocationLogRecord.user_id == user_id,
                    PaperChatToolInvocationLogRecord.created_at >= start_at,
                )
                .group_by(PaperChatToolInvocationLogRecord.capability_id, PaperChatToolInvocationLogRecord.capability_type)
                .order_by(func.count(PaperChatToolInvocationLogRecord.id).desc())
            ).all()
        items = [
            {
                "tool_name": tool_name or "unknown",
                "service_name": operation or "tool_invocation",
                "operation": operation or "tool_invocation",
                "request_count": int(count or 0),
                "call_count": int(count or 0),
                "success_count": int(success or 0),
                "failure_count": int(count or 0) - int(success or 0),
                "success_rate": int(success or 0) / int(count or 1),
                "avg_latency_ms": float(latency or 0),
                "latency_ms": float(latency or 0),
            }
            for tool_name, operation, count, success, latency in rows
        ]
        return {"range": self._range_payload(start_at=start_at, end_at=end_at, days=days), "items": items}

    def activity_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        labels = self._date_labels(end_at=end_at, days=days)
        points = {
            label: {
                "date": label,
                "label": label[5:],
                "model_calls": 0,
                "tool_calls": 0,
                "task_count": 0,
                "token_count": 0,
            }
            for label in labels
        }
        with db_session() as session:
            model_rows = session.execute(
                select(
                    func.date(PaperChatModelUsageLogRecord.created_at),
                    func.count(PaperChatModelUsageLogRecord.id),
                    func.coalesce(
                        func.sum(PaperChatModelUsageLogRecord.input_tokens + PaperChatModelUsageLogRecord.output_tokens),
                        0,
                    ),
                ).where(
                    PaperChatModelUsageLogRecord.user_id == user_id,
                    PaperChatModelUsageLogRecord.created_at >= start_at,
                )
                .group_by(func.date(PaperChatModelUsageLogRecord.created_at))
            ).all()
            tool_rows = session.execute(
                select(
                    func.date(PaperChatToolInvocationLogRecord.created_at),
                    func.count(PaperChatToolInvocationLogRecord.id),
                ).where(
                    PaperChatToolInvocationLogRecord.user_id == user_id,
                    PaperChatToolInvocationLogRecord.created_at >= start_at,
                )
                .group_by(func.date(PaperChatToolInvocationLogRecord.created_at))
            ).all()
            task_rows = session.execute(
                select(
                    func.date(PaperChatResearchTaskRecord.created_at),
                    func.count(PaperChatResearchTaskRecord.id),
                ).where(
                    PaperChatResearchTaskRecord.user_id == user_id,
                    PaperChatResearchTaskRecord.created_at >= start_at,
                )
                .group_by(func.date(PaperChatResearchTaskRecord.created_at))
            ).all()

        for day, count, tokens in model_rows:
            key = self._day_key(day)
            if key in points:
                points[key]["model_calls"] = int(count or 0)
                points[key]["token_count"] = int(tokens or 0)
        for day, count in tool_rows:
            key = self._day_key(day)
            if key in points:
                points[key]["tool_calls"] = int(count or 0)
        for day, count in task_rows:
            key = self._day_key(day)
            if key in points:
                points[key]["task_count"] = int(count or 0)
        return {"range": self._range_payload(start_at=start_at, end_at=end_at, days=days), "items": list(points.values())}

    def snapshot_payload(self, *, user_id: str, days: int = 30) -> dict[str, Any]:
        start_at, end_at = self._range(days)
        overview = self.overview_payload(user_id=user_id, days=days)
        model_usage = self.model_usage_payload(user_id=user_id, days=days)
        task_usage = self.task_distribution_payload(user_id=user_id, days=days)
        tool_usage = self.tool_usage_payload(user_id=user_id, days=days)
        activity = self.activity_payload(user_id=user_id, days=days)
        events = self._system_events_payload(user_id=user_id, start_at=start_at)
        return {
            "generated_at": end_at.isoformat(),
            "range": self._range_payload(start_at=start_at, end_at=end_at, days=days),
            "overview": overview,
            "model_usage": model_usage["items"],
            "task_usage": task_usage["items"],
            "tool_usage": tool_usage["items"],
            "activity": activity["items"],
            "insights": self._insights_payload(overview=overview, model_usage=model_usage["items"], tool_usage=tool_usage["items"]),
            "events": events,
        }

    def _date_labels(self, *, end_at: datetime, days: int) -> list[str]:
        count = max(1, min(days, 31))
        end_date = end_at.date()
        return [(end_date - timedelta(days=offset)).isoformat() for offset in reversed(range(count))]

    def _day_key(self, value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()[:10]
        return str(value)[:10]

    def _insights_payload(
        self,
        *,
        overview: dict[str, Any],
        model_usage: list[dict[str, Any]],
        tool_usage: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        tasks = dict(overview.get("tasks") or {})
        usage = dict(overview.get("usage") or {})
        top_model = model_usage[0] if model_usage else {}
        top_tool = tool_usage[0] if tool_usage else {}
        return [
            {
                "label": "任务完成率",
                "value": tasks.get("completion_rate", 0),
                "unit": "ratio",
                "tone": "success" if float(tasks.get("completion_rate") or 0) >= 0.8 else "warning",
            },
            {
                "label": "平均延迟",
                "value": usage.get("avg_latency_ms", 0),
                "unit": "ms",
                "tone": "brand",
            },
            {
                "label": "主力模型",
                "value": top_model.get("model_name") or "暂无",
                "unit": "text",
                "tone": "brand",
            },
            {
                "label": "高频工具",
                "value": top_tool.get("tool_name") or "暂无",
                "unit": "text",
                "tone": "success",
            },
        ]

    def _system_events_payload(self, *, user_id: str, start_at: datetime) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with db_session() as session:
            task_rows = session.execute(
                select(
                    PaperChatResearchTaskRecord.title,
                    PaperChatResearchTaskRecord.summary,
                    PaperChatResearchTaskRecord.status,
                    PaperChatResearchTaskRecord.updated_at,
                )
                .where(
                    PaperChatResearchTaskRecord.user_id == user_id,
                    PaperChatResearchTaskRecord.updated_at >= start_at,
                )
                .order_by(PaperChatResearchTaskRecord.updated_at.desc())
                .limit(5)
            ).all()
            tool_rows = session.execute(
                select(
                    PaperChatToolInvocationLogRecord.capability_id,
                    PaperChatToolInvocationLogRecord.capability_type,
                    PaperChatToolInvocationLogRecord.created_at,
                )
                .where(
                    PaperChatToolInvocationLogRecord.user_id == user_id,
                    PaperChatToolInvocationLogRecord.created_at >= start_at,
                )
                .order_by(PaperChatToolInvocationLogRecord.created_at.desc())
                .limit(5)
            ).all()
        for title, summary, status, updated_at in task_rows:
            events.append(
                {
                    "event_type": "task",
                    "title": title or "研究任务更新",
                    "detail": summary or "后台任务状态已更新",
                    "status": status or "unknown",
                    "created_at": updated_at.isoformat() if updated_at else None,
                }
            )
        for capability_id, capability_type, created_at in tool_rows:
            events.append(
                {
                    "event_type": "tool",
                    "title": f"工具调用：{capability_id or 'unknown'}",
                    "detail": capability_type or "tool_invocation",
                    "status": "recorded",
                    "created_at": created_at.isoformat() if created_at else None,
                }
            )
        return sorted(events, key=lambda item: item.get("created_at") or "", reverse=True)[:8]


dashboard_service = DashboardService()
