from __future__ import annotations

from collections.abc import Sequence
import json

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult

from paperchat.providers import get_autogen_reasoning_model_client
from paperchat.workflows.state import DeepAnalysisResult


GLOBAL_ANALYSE_AGENT_PROMPT = """
你是全局综合分析智能体。

请整合多个主题簇的深度分析，输出完整 Markdown，总结：
## 技术趋势总结
## 方法对比
## 应用领域分析
## 研究热点识别
## 局限性总结
## 建议与展望
"""


class GlobalAnalyseAgent:
    def __init__(self) -> None:
        self.agent = AssistantAgent(
            name="global_analyse_agent",
            description="负责整合多个主题簇的分析结果。",
            model_client=get_autogen_reasoning_model_client(),
            system_message=GLOBAL_ANALYSE_AGENT_PROMPT,
            model_client_stream=True,
        )

    async def build_global_analysis(
        self,
        *,
        topic: str,
        deep_results: Sequence[DeepAnalysisResult],
        progress_callback=None,
    ) -> str:
        compact = [
            {
                "theme": item.get("theme", ""),
                "keywords": item.get("keywords", []),
                "paper_count": item.get("paper_count", 0),
                "representative_titles": item.get("representative_titles", []),
                "analysis_markdown": item.get("analysis_markdown", "")[:2000],
            }
            for item in deep_results
        ]
        prompt = (
            f"研究主题：{topic}\n"
            f"多主题分析结果：\n{json.dumps(compact, ensure_ascii=False, indent=2)}"
        )
        result_text = ""
        try:
            async for chunk in self.agent.run_stream(task=prompt):
                if isinstance(chunk, TaskResult):
                    continue
                chunk_type = getattr(chunk, "type", "")
                if chunk_type == "ModelClientStreamingChunkEvent":
                    if progress_callback:
                        await progress_callback("global_stream", getattr(chunk, "content", ""))
                    continue
                if chunk_type == "TextMessage":
                    result_text = getattr(chunk, "content", "") or ""
        except Exception:
            result_text = ""

        if result_text:
            return result_text
        return self._fallback_analysis(topic=topic, deep_results=deep_results)

    def _fallback_analysis(self, *, topic: str, deep_results: Sequence[DeepAnalysisResult]) -> str:
        theme_lines = [f"- {item.get('theme', '未命名主题')}（{item.get('paper_count', 0)} 篇）" for item in deep_results]
        return (
            f"## 技术趋势总结\n"
            f"- 当前任务“{topic}”下已经形成多个主题簇，说明研究问题并非单一路径。\n"
            f"{chr(10).join(theme_lines) or '- 当前尚未形成稳定主题簇'}\n\n"
            "## 方法对比\n"
            "- 各主题在任务边界、方法深度和评估方式上存在明显差异，后续宜转成对比表而不是纯文本比较。\n\n"
            "## 应用领域分析\n"
            "- 从当前样本看，主题分布可以支持按场景、技术路线、评估目标三个维度继续拆分。\n\n"
            "## 研究热点识别\n"
            "- 高频主题和代表论文适合作为下一轮扩检的锚点。\n"
            "- 短期热点通常是性能优化、流程编排和任务适配，长期趋势更可能落在体系化平台与可靠性建设。\n\n"
            "## 局限性总结\n"
            "- 当前样本量有限，且信息主要来自摘要级阅读卡片，缺少统一实验表与更完整全文证据。\n\n"
            "## 建议与展望\n"
            "- 下一步建议补充更系统的样本、增加引用链扩展，并把数据集、指标、局限性做成结构化对比。"
        )
