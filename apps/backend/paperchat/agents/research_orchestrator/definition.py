from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from paperchat.agents.research_orchestrator import RESEARCH_ORCHESTRATOR_AGENT_NAME

SMART_RESEARCH_ASSISTANT_SLUG = "smart_research_assistant"


@dataclass(frozen=True)
class BuiltinAgentWorkflow:
    slug: str
    name: str
    description: str
    version: str
    definition: dict[str, Any]


SMART_RESEARCH_ASSISTANT_DEFINITION: dict[str, Any] = {
    "kind": "workflow",
    "runtime": RESEARCH_ORCHESTRATOR_AGENT_NAME,
    "agent_name": RESEARCH_ORCHESTRATOR_AGENT_NAME,
    "entry_node": "search",
    "model_policy": "conversation_model",
    "summary": "内置主流程研究编排器，负责搜索、阅读、分析、引用补全与最终回答。",
    "executors": [
        "通用模型",
        "SearchAgent",
        "ReadingAgent",
        "AnalyseAgent",
        "WritingAgent",
        "ReportAgent",
        "PaperClusterAgent",
        "DeepAnalyseAgent",
        "GlobalanalyseAgent",
        "WritingDirectorAgent",
        "RetrievalAgent",
        "ReviewAgent",
    ],
    "nodes": [
        {
            "id": "search",
            "title": "搜索节点",
            "type": "workflow_node",
            "executor_key": "SearchAgent",
            "fallback_executor_key": "通用模型",
            "model_slot": "conversation_model",
            "input_source": "用户研究需求",
            "output_target": "阅读节点",
            "description": "将自然语言研究需求转换为检索条件，并收集候选论文元数据。",
            "handoff_rule": "检索条件、论文标题、摘要、年份和来源链接会传递给阅读节点。",
            "sub_nodes": [],
        },
        {
            "id": "reading",
            "title": "阅读节点",
            "type": "workflow_node",
            "executor_key": "ReadingAgent",
            "fallback_executor_key": "通用模型",
            "model_slot": "conversation_model",
            "input_source": "搜索节点输出",
            "output_target": "分析节点",
            "description": "阅读候选论文摘要与可用正文，抽取核心问题、方法、贡献和局限。",
            "handoff_rule": "结构化论文摘要、关键方法和贡献列表会传递给分析节点。",
            "sub_nodes": [],
        },
        {
            "id": "analyse",
            "title": "分析节点",
            "type": "sub_agent_node",
            "executor_key": "AnalyseAgent",
            "fallback_executor_key": "DeepAnalyseAgent",
            "model_slot": "conversation_model",
            "input_source": "阅读节点输出",
            "output_target": "写作节点",
            "description": "对论文集合做主题聚类、深度分析和全局趋势总结。",
            "handoff_rule": "主题簇、深入分析和全局洞察会传递给写作节点。",
            "sub_nodes": [
                {
                    "id": "analyse.cluster",
                    "title": "聚类分析",
                    "executor_key": "PaperClusterAgent",
                    "description": "按研究主题将论文归并成若干主题簇。",
                },
                {
                    "id": "analyse.deep_analyse",
                    "title": "深度分析",
                    "executor_key": "DeepAnalyseAgent",
                    "description": "围绕每个主题簇分析技术路线、方法差异和局限。",
                },
                {
                    "id": "analyse.global_analyse",
                    "title": "全局分析",
                    "executor_key": "GlobalanalyseAgent",
                    "description": "汇总所有主题簇，形成研究热点、趋势和建议。",
                },
            ],
        },
        {
            "id": "writing",
            "title": "写作节点",
            "type": "sub_agent_node",
            "executor_key": "WritingAgent",
            "fallback_executor_key": "ReviewAgent",
            "model_slot": "conversation_model",
            "input_source": "分析节点输出",
            "output_target": "报告节点",
            "description": "生成报告大纲并完成章节草稿、检索增强和评审润色。",
            "handoff_rule": "章节草稿、引用候选和审阅建议会传递给报告节点。",
            "sub_nodes": [
                {
                    "id": "writing.writing_director",
                    "title": "写作规划",
                    "executor_key": "WritingDirectorAgent",
                    "description": "根据全局分析生成报告大纲和章节任务。",
                },
                {
                    "id": "writing.parallel_writing",
                    "title": "并行章节写作",
                    "executor_key": "WritingAgent",
                    "description": "为每个章节生成可合并的章节内容。",
                },
                {
                    "id": "writing.retrieval",
                    "title": "检索增强",
                    "executor_key": "RetrievalAgent",
                    "description": "从本次运行的论文摘要和分析产物中补充证据。",
                },
                {
                    "id": "writing.review",
                    "title": "评审润色",
                    "executor_key": "ReviewAgent",
                    "description": "检查章节连贯性、论据覆盖和表达质量。",
                },
            ],
        },
        {
            "id": "report",
            "title": "报告节点",
            "type": "workflow_node",
            "executor_key": "ReportAgent",
            "fallback_executor_key": "通用模型",
            "model_slot": "conversation_model",
            "input_source": "写作节点输出",
            "output_target": "任务产物",
            "description": "将章节内容组装成完整 Markdown 研究报告。",
            "handoff_rule": "最终报告写入任务产物，并在完成后回流到聊天。",
            "sub_nodes": [],
        },
    ],
}


BUILTIN_AGENT_WORKFLOWS: tuple[BuiltinAgentWorkflow, ...] = (
    BuiltinAgentWorkflow(
        slug=SMART_RESEARCH_ASSISTANT_SLUG,
        name="Research Orchestrator",
        description="内置主流程研究编排器，负责搜索、阅读、分析、引用补全与最终回答。",
        version="1.0.0",
        definition=SMART_RESEARCH_ASSISTANT_DEFINITION,
    ),
)


def get_builtin_workflow(slug: str) -> BuiltinAgentWorkflow | None:
    return next((workflow for workflow in BUILTIN_AGENT_WORKFLOWS if workflow.slug == slug), None)
