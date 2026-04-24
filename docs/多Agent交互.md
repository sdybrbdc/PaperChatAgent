# 多Agent交互

这份文档是一份偏实施的多 Agent 交互手册，目标不是做百科式介绍，而是回答下面 4 个问题：

1. 多 Agent 到底有哪些常见交互模式
2. LangChain 和 AutoGen 分别如何表达这些模式
3. 每种模式的关键参数、状态和控制权在哪里
4. 如果要自己搭一个原型，最小实现应该怎么写

本文统一使用 **Python**，并优先引用官方文档。  
对于 LangChain，这里的“LangChain 实现”通常意味着：

- `langchain` 负责 Agent / tool 封装
- `langgraph` 负责状态图、路由、分支、并行

对于 AutoGen，这里的实现分为两层：

- `AgentChat`：现成的 Agent / Team / Group Chat / GraphFlow
- `Core`：更底层的消息协议、runtime、topic、设计模式

---

## 1. 先统一三件事

### 1.1 多 Agent 不等于多个 LLM 调用

下面两件事要分开：

- 一个 Agent 连续调用 3 次模型
- 3 个不同角色的 Agent 协作

只有当系统里存在：

- 不同角色
- 不同上下文
- 明确的控制权 / 消息流 / 状态转移

时，才更适合叫“多 Agent 交互”。

### 1.2 多 Agent 交互通常分成 4 个层面

虽然模式很多，但本质上多 Agent 系统一般围绕这 4 个层面设计：

1. **谁决定下一步由谁做**
2. **中间结果怎么传**
3. **上下文是共享还是隔离**
4. **什么时候停止**

你后面读任何框架的文档时，都可以用这 4 个问题去拆。

### 1.3 四种最容易混淆的东西

很多“多 Agent”其实是在混这四类机制：

- **工作流编排**：固定顺序、条件跳转、并行 fan-out / fan-in
- **控制权转移**：当前 Agent 把主导权交给别的 Agent
- **共享群聊**：多个 Agent 共享同一会话线程轮流说话
- **按需加载专长**：还是单 Agent 主控，只是动态加载某种能力

这也是为什么不同框架命名差很多，但本质机制可以互相映射。

---

## 2. 两个框架的术语映射

| 中文模式 | 核心机制 | LangChain 对应 | AutoGen 对应 | 是否共享上下文 | 是否支持并行 | 是否保留中心控制 |
|---|---|---|---|---|---|---|
| 中央调度 | 主控决定何时调用谁 | `Subagents` / supervisor | `SelectorGroupChat` / 自定义 orchestrator | 通常主控持有主上下文 | 可以 | 是 |
| 控制权转移 | 当前 Agent 把主导权交给下一个 | `Handoffs` | `Swarm` / Core `Handoffs` | 常见为共享或持久 state | 可选 | 否或弱化 |
| 固定流水线 | 预定义顺序逐步传递结果 | `Custom workflow` | `Sequential Workflow` / `GraphFlow` | 通常按节点控制 | 可以 | 是 |
| 路由分发 | 先分类再交给专用 Agent | `Router` | `Concurrent Agents` / `GraphFlow` | 通常局部隔离 | 可以 | 是 |
| 并行汇聚 | 多个 Agent 同时做，最后汇总 | `Router` / `Custom workflow` | `Concurrent Agents` / `GraphFlow` / `Mixture of Agents` | 常见隔离后汇总 | 是 | 是 |
| 反思闭环 | 生成者和评审者来回迭代 | `Custom workflow` | `Reflection` / Team 循环 | 常见共享最近产物 | 可选 | 常见有 |
| 讨论辩论 | 多个解题 Agent 互相交换观点后聚合 | `Custom workflow` | `Multi-Agent Debate` | 常见部分共享 | 是 | 常见有聚合者 |
| 共享群聊 | 多个 Agent 共享线程轮流说话 | 可用 workflow / subagents 近似 | `RoundRobinGroupChat` / `SelectorGroupChat` / Core `Group Chat` | 是 | 否，轮次式 | 常见有 manager |
| 技能加载 | 单 Agent 按需加载特定 prompt / 能力 | `Skills` | 常见用 tool / memory / workbench 近似 | 主上下文中加载 | 否 | 是 |
| 通用代理集群 | 预置多 Agent 系统处理开放任务 | 无官方单一成品 | `MagenticOneGroupChat` / `MagenticOne` | 是 | 内部决定 | 是 |

---

## 3. 模式选型总表

| 你当前的问题 | 优先模式 |
|---|---|
| 步骤固定，必须按顺序做 | 固定流水线 |
| 多个垂直领域专家，主控统一调度 | 中央调度 |
| 想让 Agent 自己把任务转给更合适的人 | 控制权转移 |
| 要同时查多个来源后再整合 | 路由分发 / 并行汇聚 |
| 要做“写作 -> 审稿 -> 修改” | 反思闭环 |
| 多个专家要互相辩论再投票 | 讨论辩论 |
| 多个角色共享一个会话线程轮流工作 | 共享群聊 |
| 仍想保留单 Agent，但按需加载特定专长 | 技能加载 |
| 想快速试一个泛化多 Agent 系统 | 通用代理集群 |

---

## 4. 中央调度 / Supervisor / Subagents

### 4.1 概念

中央调度模式的核心是：

- 有一个主控 Agent
- 主控决定什么时候调用哪个子 Agent
- 子 Agent 通常不直接和用户争夺控制权

这个模式适合：

- 任务存在多个专门领域
- 不希望所有 Agent 共享同样大的上下文
- 希望由一个中心统一规划和收口

### 4.2 核心参数 / 状态 / 角色

通常需要这几个元素：

- `supervisor`：主控 Agent
- `worker agents`：专长子 Agent
- `task state`：当前目标、阶段、中间结果
- `termination`：主控何时认为任务完成

关键设计点：

- 子 Agent 是“工具”还是“独立参与者”
- 中间结果回给主控还是广播给全体
- 子 Agent 能不能再次调用别的子 Agent

### 4.3 官方 API / 文档入口

**LangChain**

- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>
- Supervisor / Subagents 教程：<https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant>

**AutoGen**

- AgentChat 总览：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html>
- Teams 教程：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html>
- SelectorGroupChat：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html>

### 4.4 如何使用

判断是否该用中央调度模式，可以看三点：

1. 用户是否只需要一个统一入口
2. 各子 Agent 是否是明确分工的专业角色
3. 是否需要一个主控统一组合最终答案

### 4.5 工作原理

典型流程：

```text
用户请求
-> supervisor 接收任务
-> supervisor 判断需要哪个 worker
-> 调用一个或多个 worker
-> worker 返回局部结果
-> supervisor 汇总
-> 返回最终结果
```

### 4.6 LangChain 实现

下面示例里，主控 Agent 通过两个“子 Agent 工具”分别处理日历和邮件任务。

```python
import asyncio
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool


async def call_subagent(agent, task: str) -> str:
    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content


calendar_agent = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你是日历助手，只处理日程安排、时间冲突和会议建议。",
)

email_agent = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你是邮件助手，只处理起草、回复、润色邮件。",
)


@tool
async def ask_calendar(task: str) -> str:
    """把任务转给日历专家。"""
    return await call_subagent(calendar_agent, task)


@tool
async def ask_email(task: str) -> str:
    """把任务转给邮件专家。"""
    return await call_subagent(email_agent, task)


supervisor = create_agent(
    model="openai:gpt-4.1",
    tools=[ask_calendar, ask_email],
    system_prompt=(
        "你是主控助手。先判断任务属于日历、邮件，还是两者都需要。"
        "如果需要子专家，就调用对应工具；最后统一输出结果。"
    ),
)


async def main() -> None:
    task = "明天下午 3 点安排产品评审会，并起草一封通知邮件。"
    result = await supervisor.ainvoke({"messages": [{"role": "user", "content": task}]})
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
```

**运行后会发生什么**

- 用户只面对 `supervisor`
- `supervisor` 会调用 `ask_calendar` 和 `ask_email`
- 两个工具内部再去调用各自的子 Agent
- 最终由 `supervisor` 统一返回

### 4.7 AutoGen 实现

这里用 `SelectorGroupChat` 实现“中央调度”。  
`planner` 负责决定下一位谁发言，`calendar_agent` 和 `email_agent` 负责各自领域。

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")

    planner = AssistantAgent(
        "planner",
        model_client=model_client,
        description="任务总控，负责拆解任务并决定后续由谁处理。",
        system_message=(
            "你是总控。先拆任务，再选择 calendar_agent 或 email_agent。"
            "当两个子任务都完成后，请汇总并在最后一行输出 DONE。"
        ),
    )

    calendar_agent = AssistantAgent(
        "calendar_agent",
        model_client=model_client,
        description="处理日程、时间、会议安排。",
        system_message="你只处理日程安排相关事项，并给 planner 返回结构化建议。",
    )

    email_agent = AssistantAgent(
        "email_agent",
        model_client=model_client,
        description="处理邮件起草和润色。",
        system_message="你只处理邮件任务，并给 planner 返回邮件草稿。",
    )

    termination = TextMentionTermination("DONE")

    selector_prompt = """
你是发言选择器。
优先让 planner 先拆任务。
如果 planner 提到时间安排，就让 calendar_agent 发言。
如果 planner 提到邮件草稿，就让 email_agent 发言。
当所有子任务完成后，让 planner 收尾并输出 DONE。
"""

    team = SelectorGroupChat(
        [planner, calendar_agent, email_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
    )

    await Console(team.run_stream(task="明天下午 3 点安排产品评审会，并起草一封通知邮件。"))
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**运行后会发生什么**

- `planner` 是中心调度者
- 所有消息在一个共享上下文里流动
- 选择器决定下一位发言人
- 最终仍由 `planner` 统一收口

### 4.8 常见坑与边界

- 主控 prompt 不明确时，系统容易退化成“大家都在乱聊”
- 主控同时掌握过多细节时，可能失去上下文隔离优势
- 如果流程其实是确定的，中央调度可能不如固定流水线清晰

---

## 5. Handoff / Swarm / 状态切换

### 5.1 概念

Handoff 模式强调：

- 当前 Agent 可以把控制权交给另一个 Agent
- 或者通过状态切换改变系统当前行为

这个模式适合：

- 多阶段会话
- 每个阶段都要直接和用户交互
- 想让系统像“客服转接”一样工作

### 5.2 核心参数 / 状态 / 角色

常见元素：

- `active_agent` 或 `current_step`
- `handoff tool` / `state transition`
- 持久化对话状态
- 下一阶段可用的 prompt / tool 集合

关键设计点：

- handoff 后是否共享历史
- handoff 是显式工具还是条件路由
- 切换的是“Agent”还是“同一个 Agent 的配置”

### 5.3 官方 API / 文档入口

**LangChain**

- Handoffs：<https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs>

**AutoGen**

- Swarm：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/swarm.html>
- Core Handoffs：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/handoffs.html>

### 5.4 如何使用

优先在这些场景考虑 handoff：

- 需要先收集信息，再进入下一个阶段
- 每个阶段的工具权限不同
- 希望当前 Agent 自己决定何时转交

### 5.5 工作原理

典型流程：

```text
当前 Agent
-> 调用转交工具 / 更新状态
-> active_agent 或 current_step 改变
-> 下一轮由新 Agent / 新配置继续处理
```

### 5.6 LangChain 实现

下面示例里，系统根据 `current_step` 切换 prompt 和工具，表现得像“不同 Agent 接手”。

```python
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.messages import ToolMessage
from langchain.tools import tool, ToolRuntime
from langgraph.types import Command


class SupportState(TypedDict, total=False):
    current_step: str
    warranty_status: str
    issue_type: str


@tool
def record_warranty_status(status: str, runtime: ToolRuntime[None, SupportState]) -> Command:
    """记录保修状态并切换到问题分类阶段。"""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Warranty status recorded: {status}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "warranty_status": status,
            "current_step": "classify_issue",
        }
    )


@tool
def record_issue_type(issue_type: str, runtime: ToolRuntime[None, SupportState]) -> Command:
    """记录问题类型并切换到解决阶段。"""
    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Issue type recorded: {issue_type}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "issue_type": issue_type,
            "current_step": "resolution",
        }
    )


@tool
def provide_resolution() -> str:
    """输出解决方案。"""
    return "建议：安排硬件维修工单，并向用户发送维修流程。"


@wrap_model_call
def apply_dynamic_config(request: ModelRequest, handler) -> ModelResponse:
    step = request.state.get("current_step", "collect_warranty")
    configs = {
        "collect_warranty": {
            "prompt": "你正在收集用户保修状态。必须调用 record_warranty_status。",
            "tools": [record_warranty_status],
        },
        "classify_issue": {
            "prompt": "你正在分类问题。必须调用 record_issue_type。",
            "tools": [record_issue_type],
        },
        "resolution": {
            "prompt": "你正在给出最终解决方案。",
            "tools": [provide_resolution],
        },
    }
    config = configs[step]
    request = request.override(system_prompt=config["prompt"], tools=config["tools"])
    return handler(request)


agent = create_agent(
    model="openai:gpt-4.1",
    middleware=[apply_dynamic_config],
    state_schema=SupportState,
)
```

**运行后会发生什么**

- 同一个 Agent 外壳存在
- 但 `current_step` 不同，会动态切换 prompt 和可用工具
- 用户感知上像是“被转接到下一个阶段”

### 5.7 AutoGen 实现

这里用 `Swarm` 表达 handoff。  
每个 Agent 可以把任务移交给更合适的 Agent。

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")

    triage_agent = AssistantAgent(
        "triage_agent",
        model_client=model_client,
        system_message=(
            "你负责初始分流。"
            "如果是退款问题，移交给 refund_agent；"
            "如果是技术问题，移交给 tech_agent。"
        ),
        handoffs=["refund_agent", "tech_agent"],
    )

    refund_agent = AssistantAgent(
        "refund_agent",
        model_client=model_client,
        system_message="你负责退款流程与退款规则解释。",
        handoffs=["triage_agent"],
    )

    tech_agent = AssistantAgent(
        "tech_agent",
        model_client=model_client,
        system_message="你负责技术支持、排障与维修建议。",
        handoffs=["triage_agent"],
    )

    team = Swarm([triage_agent, refund_agent, tech_agent])
    await Console(team.run_stream(task="我的手机屏幕碎了，而且它还在保修期内。"))
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**运行后会发生什么**

- `triage_agent` 先接任务
- 它根据能力边界选择 handoff
- 所有 Agent 共享消息上下文
- 当前控制权跟着 handoff 走，而不是由中央选择器分配

### 5.8 常见坑与边界

- handoff 太自由时容易在多个 Agent 之间来回弹跳
- 如果没有显式终止条件，会导致对话拖长
- 如果每个阶段本质只是固定流程，Graph / workflow 可能更清晰

---

## 6. 固定流水线 / Sequential Workflow / GraphFlow

### 6.1 概念

固定流水线指：

- 步骤顺序预先确定
- 每个 Agent 负责一个确定阶段
- 上一步的输出传给下一步

适合：

- ETL 类流程
- 文档生成流水线
- 明确的多步处理链

### 6.2 核心参数 / 状态 / 角色

常见元素：

- `state`
- `entry node`
- `ordered steps`
- `join point`
- `termination`

如果要扩展到复杂工作流，还会有：

- 条件分支
- 循环
- 并行边

### 6.3 官方 API / 文档入口

**LangChain**

- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>
- Router / workflow 相关：<https://docs.langchain.com/oss/python/langchain/multi-agent/router>

**AutoGen**

- GraphFlow：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html>
- Core Sequential Workflow：<https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/sequential-workflow.html>

### 6.4 如何使用

如果你已经能清楚写出：

```text
A -> B -> C -> D
```

那么优先考虑流水线，而不是群聊。

### 6.5 工作原理

```text
输入
-> Agent A
-> Agent B
-> Agent C
-> 最终结果
```

每一步通常只关心：

- 当前输入
- 当前职责
- 下一步输出

### 6.6 LangChain 实现

下面示例使用 `StateGraph` 搭一个研究总结流水线：

```python
from typing import TypedDict

from langchain.agents import create_agent
from langgraph.graph import START, END, StateGraph


class PipelineState(TypedDict):
    task: str
    facts: str
    draft: str
    final: str


researcher = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你是研究员。提取任务的关键事实，输出简洁要点。",
)

writer = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你是写作者。根据事实写出一段说明。",
)

reviewer = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你是审核者。润色文字，输出最终版本。",
)


async def research_node(state: PipelineState) -> PipelineState:
    result = await researcher.ainvoke(
        {"messages": [{"role": "user", "content": state["task"]}]}
    )
    state["facts"] = result["messages"][-1].content
    return state


async def write_node(state: PipelineState) -> PipelineState:
    result = await writer.ainvoke(
        {"messages": [{"role": "user", "content": state["facts"]}]}
    )
    state["draft"] = result["messages"][-1].content
    return state


async def review_node(state: PipelineState) -> PipelineState:
    result = await reviewer.ainvoke(
        {"messages": [{"role": "user", "content": state["draft"]}]}
    )
    state["final"] = result["messages"][-1].content
    return state


graph = StateGraph(PipelineState)
graph.add_node("research", research_node)
graph.add_node("write", write_node)
graph.add_node("review", review_node)
graph.add_edge(START, "research")
graph.add_edge("research", "write")
graph.add_edge("write", "review")
graph.add_edge("review", END)

workflow = graph.compile()
```

**运行后会发生什么**

- `research` 输出事实
- `write` 消费事实生成草稿
- `review` 消费草稿输出最终版本

### 6.7 AutoGen 实现

这里分别给出两种官方表达：

- Core `Sequential Workflow`
- AgentChat `GraphFlow`

先看更接近日常项目接法的 `GraphFlow`：

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1")

    researcher = AssistantAgent(
        "researcher",
        model_client=client,
        system_message="提取任务的关键事实，输出简洁要点。",
    )
    writer = AssistantAgent(
        "writer",
        model_client=client,
        system_message="根据上一步内容生成一段说明。",
    )
    reviewer = AssistantAgent(
        "reviewer",
        model_client=client,
        system_message="润色并输出最终版本。",
    )

    builder = DiGraphBuilder()
    builder.add_node(researcher).add_node(writer).add_node(reviewer)
    builder.add_edge(researcher, writer)
    builder.add_edge(writer, reviewer)
    graph = builder.build()

    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
    )

    await Console(flow.run_stream(task="写一段关于边缘计算价值的简短说明。"))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**运行后会发生什么**

- 图上顺序固定
- `researcher -> writer -> reviewer`
- 每一步消息按图边传给下一步

### 6.8 常见坑与边界

- 本来是固定流程却硬用群聊，会让状态变模糊
- 节点输出格式不稳定时，下游很难稳定消费
- 如果后面会出现大量动态分叉，需要升级成 Graph / Router

---

## 7. Router / 路由分发

### 7.1 概念

Router 模式的核心是：

- 先做分类
- 再把任务发给一个或多个专门 Agent
- 最后把结果合成

适合：

- 多知识域检索
- 多来源查询
- 用户问题类别明显可分

### 7.2 核心参数 / 状态 / 角色

- `router`
- `route labels`
- `specialist agents`
- `synthesizer`
- `selected_targets`

关键设计点：

- 单路由还是多路由
- 路由是否保留历史
- 是否并行执行

### 7.3 官方 API / 文档入口

**LangChain**

- Router：<https://docs.langchain.com/oss/python/langchain/multi-agent/router>
- Router tutorial：<https://docs.langchain.com/oss/python/langchain/multi-agent/router-knowledge-base>

**AutoGen**

- Core Concurrent Agents：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/concurrent-agents.html>
- GraphFlow：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html>

### 7.4 如何使用

判断是否适合 router，通常看：

- 输入能否稳定分类
- 不同分类是否明显对应不同专长
- 多个分支结果是否需要统一合成

### 7.5 工作原理

```text
query
-> router
-> Agent A / Agent B / Agent C
-> synthesize
-> final answer
```

### 7.6 LangChain 实现

下面示例先用分类函数决定要查哪个专家，再把结果合并。

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class RouterState(TypedDict):
    query: str
    results: list[str]
    final: str


def classify_query(query: str) -> list[str]:
    labels = []
    if "价格" in query or "套餐" in query:
        labels.append("sales")
    if "报错" in query or "失败" in query:
        labels.append("support")
    return labels or ["general"]


def route_query(state: RouterState):
    labels = classify_query(state["query"])
    return [Send(label, {"query": state["query"], "results": []}) for label in labels]


def sales_node(state: RouterState) -> RouterState:
    return {"results": state.get("results", []) + ["销售专家：推荐企业版套餐。"]}


def support_node(state: RouterState) -> RouterState:
    return {"results": state.get("results", []) + ["技术支持：请先检查 API Key 和配额。"]}


def general_node(state: RouterState) -> RouterState:
    return {"results": state.get("results", []) + ["通用助手：先 уточнить 业务目标。"]}


def synthesize_node(state: RouterState) -> RouterState:
    joined = "\n".join(state["results"])
    return {"final": f"综合结果：\n{joined}"}


graph = StateGraph(RouterState)
graph.add_node("sales", sales_node)
graph.add_node("support", support_node)
graph.add_node("general", general_node)
graph.add_node("synthesize", synthesize_node)
graph.add_conditional_edges(START, route_query)
graph.add_edge("sales", "synthesize")
graph.add_edge("support", "synthesize")
graph.add_edge("general", "synthesize")
graph.add_edge("synthesize", END)

workflow = graph.compile()
```

**运行后会发生什么**

- `classify_query` 决定去哪些分支
- 如果命中多个标签，会并行 fan-out
- `synthesize_node` 汇总所有分支结果

### 7.7 AutoGen 实现

AutoGen 没有“就叫 Router 的一个 Team”，更常见做法是：

- 用 Core 的并发消息模式
- 或用 `GraphFlow` 做路由 + 合成

这里给一个 `GraphFlow` 风格的简单路由实现：

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1")

    router = AssistantAgent(
        "router",
        model_client=client,
        system_message=(
            "你负责分类问题。"
            "如果是销售问题，输出 SALES。"
            "如果是技术问题，输出 SUPPORT。"
            "如果都涉及，输出 SALES SUPPORT。"
        ),
    )

    sales = AssistantAgent(
        "sales",
        model_client=client,
        system_message="你只回答销售、套餐和商务方案问题。",
    )

    support = AssistantAgent(
        "support",
        model_client=client,
        system_message="你只回答技术支持和排障问题。",
    )

    synthesizer = AssistantAgent(
        "synthesizer",
        model_client=client,
        system_message="整合上游结果，输出一份统一答复。",
    )

    builder = DiGraphBuilder()
    builder.add_node(router).add_node(sales).add_node(support).add_node(synthesizer)
    builder.add_edge(router, sales, condition=lambda msg: "SALES" in msg.to_model_text())
    builder.add_edge(router, support, condition=lambda msg: "SUPPORT" in msg.to_model_text())
    builder.add_edge(sales, synthesizer)
    builder.add_edge(support, synthesizer)
    graph = builder.build()

    flow = GraphFlow(participants=builder.get_participants(), graph=graph)
    await Console(flow.run_stream(task="帮我排查付费套餐开通失败的问题，并说明商务升级选项。"))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 7.8 常见坑与边界

- 路由标签设计得太细，会让系统维护成本暴涨
- 多路由命中后，如果没有汇总层，输出容易散
- 多轮会话中，stateless router 往往不如 handoff / supervisor 自然

---

## 8. 并行汇聚 / Fan-out / Fan-in / Concurrent Agents

### 8.1 概念

并行汇聚模式指：

- 一个任务拆成多个独立子任务
- 多个 Agent 同时执行
- 最后再把结果汇总到一个 join 节点

适合：

- 多来源检索
- 多视角分析
- 审稿人并行评审

### 8.2 核心参数 / 状态 / 角色

- `fan_out_targets`
- `parallel workers`
- `join node`
- `partial_results`

关键设计点：

- 子任务之间是否独立
- 汇总节点等所有上游还是任意上游
- 汇总时是否需要保留来源标签

### 8.3 官方 API / 文档入口

**LangChain**

- Router：<https://docs.langchain.com/oss/python/langchain/multi-agent/router>
- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>

**AutoGen**

- Concurrent Agents：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/concurrent-agents.html>
- GraphFlow：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html>
- Mixture of Agents：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/mixture-of-agents.html>

### 8.4 如何使用

如果多个子任务满足：

- 可以独立跑
- 不需要共享中间推理
- 最后只要统一汇总

那就优先考虑并行汇聚。

### 8.5 工作原理

```text
task
-> worker1
-> worker2
-> worker3
-> join / synthesizer
-> final
```

### 8.6 LangChain 实现

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class FanoutState(TypedDict):
    topic: str
    findings: list[str]
    summary: str


def split_to_workers(state: FanoutState):
    return [
        Send("researcher_a", {"topic": state["topic"], "findings": []}),
        Send("researcher_b", {"topic": state["topic"], "findings": []}),
        Send("researcher_c", {"topic": state["topic"], "findings": []}),
    ]


def researcher_a(state: FanoutState) -> FanoutState:
    return {"findings": ["A 视角：关注技术成熟度。"]}


def researcher_b(state: FanoutState) -> FanoutState:
    return {"findings": ["B 视角：关注落地成本。"]}


def researcher_c(state: FanoutState) -> FanoutState:
    return {"findings": ["C 视角：关注监管与风险。"]}


def summarize(state: FanoutState) -> FanoutState:
    return {"summary": "\n".join(state["findings"])}


graph = StateGraph(FanoutState)
graph.add_node("researcher_a", researcher_a)
graph.add_node("researcher_b", researcher_b)
graph.add_node("researcher_c", researcher_c)
graph.add_node("summarize", summarize)
graph.add_conditional_edges(START, split_to_workers)
graph.add_edge("researcher_a", "summarize")
graph.add_edge("researcher_b", "summarize")
graph.add_edge("researcher_c", "summarize")
graph.add_edge("summarize", END)

workflow = graph.compile()
```

### 8.7 AutoGen 实现

这里给一个 `GraphFlow` 的并行 fan-out / fan-in 例子。

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1")

    writer = AssistantAgent("writer", model_client=client, system_message="先输出一段草稿。")
    grammar_editor = AssistantAgent("grammar_editor", model_client=client, system_message="只检查语法。")
    style_editor = AssistantAgent("style_editor", model_client=client, system_message="只检查风格。")
    reviewer = AssistantAgent("reviewer", model_client=client, system_message="整合两位编辑的结果。")

    builder = DiGraphBuilder()
    builder.add_node(writer).add_node(grammar_editor).add_node(style_editor).add_node(reviewer)
    builder.add_edge(writer, grammar_editor)
    builder.add_edge(writer, style_editor)
    builder.add_edge(grammar_editor, reviewer)
    builder.add_edge(style_editor, reviewer)
    graph = builder.build()

    flow = GraphFlow(participants=builder.get_participants(), graph=graph)
    await Console(flow.run_stream(task="写一段关于可再生能源转型的简短段落。"))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 8.8 常见坑与边界

- 并行分支之间如果需要共享推理过程，就不适合纯 fan-out
- 汇总节点必须提前定义好输入协议
- 汇总过晚会增加 token 成本，汇总过早会损失独立视角

---

## 9. Reflection / 生成-评审闭环

### 9.1 概念

Reflection 指：

- 一个 Agent 负责生成
- 另一个 Agent 负责批评 / 评审
- 两者迭代，直到达到停止条件

适合：

- 写作
- 代码生成
- 审稿 / 质检

### 9.2 核心参数 / 状态 / 角色

- `generator`
- `reviewer`
- `iteration_count`
- `max_rounds`
- `approval_signal`

关键设计点：

- reviewer 的意见是自然语言还是结构化反馈
- 停止条件是 `APPROVE` 还是最大轮数
- 是否保留完整历史

### 9.3 官方 API / 文档入口

**LangChain**

- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>
- Custom workflow 一般用 LangGraph 自建

**AutoGen**

- Reflection：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/reflection.html>

### 9.4 如何使用

这个模式最适合：

- 单次输出质量比响应速度更重要
- 可以接受多轮修订
- 有一个明确的评审标准

### 9.5 工作原理

```text
task
-> generator 输出草稿
-> reviewer 给反馈
-> generator 修改
-> reviewer 审核
-> APPROVE / 达到轮数上限
```

### 9.6 LangChain 实现

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


class ReflectionState(TypedDict):
    task: str
    draft: str
    review: str
    rounds: int


async def generator_node(state: ReflectionState) -> ReflectionState:
    draft = f"第 {state['rounds'] + 1} 版草稿：围绕任务“{state['task']}”生成的内容。"
    state["draft"] = draft
    return state


async def reviewer_node(state: ReflectionState) -> ReflectionState:
    if state["rounds"] >= 1:
        state["review"] = "APPROVE"
    else:
        state["review"] = "请补充风险分析，并把结论写得更明确。"
    state["rounds"] += 1
    return state


def route_after_review(state: ReflectionState) -> str:
    return END if "APPROVE" in state["review"] else "generator"


graph = StateGraph(ReflectionState)
graph.add_node("generator", generator_node)
graph.add_node("reviewer", reviewer_node)
graph.add_edge(START, "generator")
graph.add_edge("generator", "reviewer")
graph.add_conditional_edges("reviewer", route_after_review)

workflow = graph.compile()
```

### 9.7 AutoGen 实现

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4.1")

    generator = AssistantAgent(
        "generator",
        model_client=model_client,
        system_message="你负责生成方案。收到反馈后修改并给出新版本。",
    )

    reviewer = AssistantAgent(
        "reviewer",
        model_client=model_client,
        system_message=(
            "你负责审稿。若有问题给出明确反馈；"
            "如果已经满足要求，只输出 APPROVE。"
        ),
    )

    termination = TextMentionTermination("APPROVE") | MaxMessageTermination(8)

    team = RoundRobinGroupChat(
        [generator, reviewer],
        termination_condition=termination,
    )

    await Console(team.run_stream(task="写一段关于企业私有化部署 AI 的风险分析。"))
    await model_client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 9.8 常见坑与边界

- reviewer 太宽泛，容易给出不可执行反馈
- 如果没有最大轮数，系统可能无限循环
- 如果只是简单校对，单 Agent + self-reflection 可能更便宜

---

## 10. Debate / 多 Agent 讨论与聚合

### 10.1 概念

Debate 模式指：

- 多个 solver 独立或半独立提出答案
- 彼此交换中间观点
- 最终由聚合器做多数投票或综合判断

适合：

- 复杂推理
- 多视角决策
- 需要提高鲁棒性的问答

### 10.2 核心参数 / 状态 / 角色

- `solvers`
- `aggregator`
- `max_rounds`
- `topology`
- `vote / aggregate strategy`

关键设计点：

- solver 之间是否全连接
- 是直接投票还是生成综合说明
- 轮数如何控制

### 10.3 官方 API / 文档入口

**LangChain**

- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>
- 该模式通常用 `LangGraph` 自建，没有单独官方第一页

**AutoGen**

- Multi-Agent Debate：<https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/multi-agent-debate.html>

### 10.4 如何使用

当你希望：

- 一个答案来自多位解题者
- 不完全信任单个模型的推理
- 愿意用更多 token 换稳定性

时，再考虑 debate。

### 10.5 工作原理

```text
question
-> solver A / solver B / solver C
-> 交换中间结果
-> 再次更新答案
-> aggregator 聚合
-> final
```

### 10.6 LangChain 实现

下面示例用 LangGraph 搭一个简化版 debate：

```python
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send


class DebateState(TypedDict):
    question: str
    solver_outputs: list[str]
    final_answer: str


def fan_out(state: DebateState):
    return [
        Send("solver_a", {"question": state["question"], "solver_outputs": []}),
        Send("solver_b", {"question": state["question"], "solver_outputs": []}),
        Send("solver_c", {"question": state["question"], "solver_outputs": []}),
    ]


def solver_a(state: DebateState) -> DebateState:
    return {"solver_outputs": ["A：我认为核心原因是数据质量。"]}


def solver_b(state: DebateState) -> DebateState:
    return {"solver_outputs": ["B：我认为核心原因是评估指标选择不合理。"]}


def solver_c(state: DebateState) -> DebateState:
    return {"solver_outputs": ["C：我认为核心原因是训练分布和线上分布不一致。"]}


def aggregate(state: DebateState) -> DebateState:
    state["final_answer"] = "综合结论：问题主要来自数据与评估假设不一致。"
    return state


graph = StateGraph(DebateState)
graph.add_node("solver_a", solver_a)
graph.add_node("solver_b", solver_b)
graph.add_node("solver_c", solver_c)
graph.add_node("aggregate", aggregate)
graph.add_conditional_edges(START, fan_out)
graph.add_edge("solver_a", "aggregate")
graph.add_edge("solver_b", "aggregate")
graph.add_edge("solver_c", "aggregate")
graph.add_edge("aggregate", END)

workflow = graph.compile()
```

### 10.7 AutoGen 实现

AutoGen 官方有更完整的 debate 设计模式页，底层是：

- 多个 solver agent
- 一个 aggregator
- 通过 runtime / topic / direct messaging 协调

下面给一个缩略但结构完整的可读版本：

```python
import asyncio
from dataclasses import dataclass

from autogen_core import (
    DefaultTopicId,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    default_subscription,
    message_handler,
)


@dataclass
class Question:
    content: str


@dataclass
class SolverAnswer:
    source: str
    content: str


@default_subscription
class Solver(RoutedAgent):
    def __init__(self, name: str, answer: str) -> None:
        super().__init__(name)
        self._answer = answer

    @message_handler
    async def handle_question(self, message: Question, ctx) -> None:
        await self.publish_message(
            SolverAnswer(source=self.id.key, content=self._answer),
            topic_id=DefaultTopicId(type="answers"),
        )


@default_subscription
class Aggregator(RoutedAgent):
    def __init__(self, expected: int) -> None:
        super().__init__("Aggregator")
        self._expected = expected
        self._answers: list[SolverAnswer] = []

    @message_handler
    async def handle_answer(self, message: SolverAnswer, ctx) -> None:
        self._answers.append(message)
        if len(self._answers) == self._expected:
            print("最终聚合结果：")
            for ans in self._answers:
                print(f"- {ans.source}: {ans.content}")


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    await Solver.register(runtime, "solver_a", lambda: Solver("solver_a", "A 认为应先修数据。"))
    await Solver.register(runtime, "solver_b", lambda: Solver("solver_b", "B 认为应先修指标。"))
    await Solver.register(runtime, "solver_c", lambda: Solver("solver_c", "C 认为应先修线上采样。"))
    await Aggregator.register(runtime, "aggregator", lambda: Aggregator(expected=3))

    runtime.start()
    await runtime.publish_message(Question(content="线上效果下降的主因是什么？"), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
```

### 10.8 常见坑与边界

- Debate 会非常吃 token
- 如果 solver 之间没有真正信息差，收益有限
- 聚合策略若太弱，最后只是在拼接答案

---

## 11. 共享群聊 / Group Chat / Selector / Round Robin

### 11.1 概念

共享群聊模式指：

- 多个 Agent 共享同一个消息线程
- 每轮只有一个 Agent 发言
- 下一位由轮转、选择器或 manager 决定

适合：

- 协作写作
- 讨论式任务分解
- 需要共享上下文的多角色任务

### 11.2 核心参数 / 状态 / 角色

- `participants`
- `shared_history`
- `speaker_selection`
- `termination_condition`

关键设计点：

- 如何选下一位
- 是否允许同一 Agent 连续发言
- 是否需要人类代理加入

### 11.3 官方 API / 文档入口

**LangChain**

- Multi-agent 总览：<https://docs.langchain.com/oss/python/langchain/multi-agent/index>
- 官方没有和 AutoGen 等价的“GroupChat team”成品，一般用 workflow 自建

**AutoGen**

- Teams：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html>
- SelectorGroupChat：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html>
- Core Group Chat：<https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html>

### 11.4 如何使用

共享群聊适合“大家围着同一个上下文工作”的场景。  
如果每个角色都只需要自己的局部上下文，群聊通常不是最优解。

### 11.5 工作原理

```text
shared thread
-> speaker 1
-> speaker 2
-> speaker 3
-> ...
-> termination
```

### 11.6 LangChain 实现

LangChain 没有一个就叫 `GroupChat` 的高层 team，一般做法是自己维护共享 history，然后在图里轮流调用角色节点。

```python
from typing import TypedDict, List

from langgraph.graph import StateGraph, START, END


class ChatState(TypedDict):
    task: str
    history: List[str]
    turn: int


def writer(state: ChatState) -> ChatState:
    state["history"].append("writer：给出第一版草稿。")
    state["turn"] += 1
    return state


def reviewer(state: ChatState) -> ChatState:
    if state["turn"] >= 2:
        state["history"].append("reviewer：APPROVE")
    else:
        state["history"].append("reviewer：请补一个总结段。")
    state["turn"] += 1
    return state


def route(state: ChatState) -> str:
    if state["history"] and "APPROVE" in state["history"][-1]:
        return END
    return "writer" if state["turn"] % 2 == 0 else "reviewer"


graph = StateGraph(ChatState)
graph.add_node("writer", writer)
graph.add_node("reviewer", reviewer)
graph.add_edge(START, "writer")
graph.add_conditional_edges("writer", route)
graph.add_conditional_edges("reviewer", route)

workflow = graph.compile()
```

### 11.7 AutoGen 实现

这里分别用 `RoundRobinGroupChat` 和 `SelectorGroupChat`。

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1")

    writer = AssistantAgent("writer", model_client=client, system_message="根据任务写草稿。")
    reviewer = AssistantAgent(
        "reviewer",
        model_client=client,
        system_message="如果草稿够好就输出 APPROVE，否则提修改意见。",
    )

    team = RoundRobinGroupChat(
        [writer, reviewer],
        termination_condition=TextMentionTermination("APPROVE"),
    )

    await Console(team.run_stream(task="写一段关于向量数据库作用的说明。"))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

如果你需要模型选人，而不是固定轮转，把 `RoundRobinGroupChat` 换成 `SelectorGroupChat` 即可。

### 11.8 常见坑与边界

- 共享上下文会让 token 成本随轮数快速上涨
- 角色边界不清时，多个 Agent 会说重复的话
- 如果任务本身是确定流程，群聊不如 Graph 清晰

---

## 12. Skills / 按需加载专长

### 12.1 概念

Skills 模式的核心不是“多个 Agent 互相讲话”，而是：

- 仍由单 Agent 主控
- 但它能按需加载某个专长 prompt / 知识包 / 模板

所以它更像：

- 单 Agent + 渐进式披露能力

而不是经典意义上的 Team。

### 12.2 核心参数 / 状态 / 角色

- `skill registry`
- `load_skill()`
- `current_skill_context`
- 主控 Agent

关键设计点：

- skill 是纯 prompt 还是 prompt + assets
- 加载后是否保留在上下文中
- skill 能否继续引入更多 skill

### 12.3 官方 API / 文档入口

**LangChain**

- Skills：<https://docs.langchain.com/oss/python/langchain/multi-agent/skills>

**AutoGen**

- AgentChat 总览：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html>
- 这个模式没有 LangChain 那样单独成型的官方第一页；通常用 `tools`、`memory`、`workbench` 或自定义 prompt loader 实现

### 12.4 如何使用

当你：

- 不想维护很多真正的子 Agent
- 只是需要按需装载领域知识
- 仍希望单 Agent 保持统一控制

就优先考虑 skills。

### 12.5 工作原理

```text
用户任务
-> 主控 Agent 判断需要哪种 skill
-> 加载 skill prompt / 文档 / 模板
-> 在扩展上下文中继续完成任务
```

### 12.6 LangChain 实现

```python
import asyncio

from langchain.agents import create_agent
from langchain.tools import tool


SKILLS = {
    "sql_analyst": "你是 SQL 专家，擅长写 JOIN、CTE 和聚合查询。",
    "legal_reviewer": "你是法务审阅助手，关注条款风险和歧义表达。",
}


@tool
def load_skill(skill_name: str) -> str:
    """加载一个技能 prompt。"""
    return SKILLS[skill_name]


agent = create_agent(
    model="openai:gpt-4.1",
    tools=[load_skill],
    system_prompt=(
        "你是主控助手。先判断当前任务是否需要 skill。"
        "如果需要，调用 load_skill 获取额外提示，再继续完成任务。"
    ),
)


async def main() -> None:
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "帮我写一个统计月度营收 top10 客户的 SQL。"}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 12.7 AutoGen 实现

AutoGen 没有 LangChain 同名的 `Skills` 模式页，常用替代方式是：

- 用 `FunctionTool` 加载 skill prompt
- 由 `AssistantAgent` 自己决定是否调用

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_core.tools import FunctionTool
from autogen_ext.models.openai import OpenAIChatCompletionClient


SKILLS = {
    "sql_analyst": "你是 SQL 专家，优先生成可执行、可解释的查询。",
    "legal_reviewer": "你是法务审阅助手，关注风险条款、责任边界和定义歧义。",
}


def load_skill(skill_name: str) -> str:
    return SKILLS[skill_name]


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4.1")
    tool = FunctionTool(load_skill, description="按名称加载某个技能 prompt。")

    agent = AssistantAgent(
        "skill_agent",
        model_client=client,
        tools=[tool],
        system_message=(
            "你是单 Agent 主控。"
            "需要额外专长时调用 load_skill，再结合加载结果完成任务。"
        ),
    )

    result = await agent.run(task="帮我写一个统计月度营收 top10 客户的 SQL。")
    print(result.messages[-1].content)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 12.8 常见坑与边界

- skill 加载过多会重新把上下文堆大
- 如果 skill 之间需要强交互，还是应该升级成多 Agent
- skill registry 需要版本管理，否则 prompt 很快失控

---

## 13. 通用代理集群 / 预置协作系统

### 13.1 概念

这类模式指：

- 框架已经内建一套泛化的多 Agent 协作架构
- 用户不必从零设计每个角色和协议

适合：

- 快速试原型
- 开放式复杂任务
- 先验证“多 Agent 是否有价值”

### 13.2 核心参数 / 状态 / 角色

- 内置 orchestrator
- 预定义 specialist agents
- 全局任务 ledger / progress
- termination / retry policy

### 13.3 官方 API / 文档入口

**LangChain**

- 官方没有一个和 `MagenticOne` 对等的“成品通用代理集群”入口
- 通常通过 `create_agent + LangGraph` 自己组合

**AutoGen**

- Magentic-One：<https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html>

### 13.4 如何使用

当你：

- 不想先自己设计复杂协作协议
- 需要快速试一套开放任务系统
- 接受系统内部策略不完全透明

时，通用代理集群是好起点。

### 13.5 工作原理

以 `Magentic-One` 为例：

- 有一个总 orchestrator
- 它维护计划和进度 ledger
- 然后把子任务派给各类 specialist
- 根据进展动态调整计划

### 13.6 LangChain 实现

LangChain 没有同名成品，因此这里的“实现方式”是一个最小替代：  
用一个总控 + 多个 specialist + 图工作流，模拟通用代理集群。

```python
import asyncio

from langchain.agents import create_agent
from langchain.tools import tool


web_agent = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你负责网页信息搜集。",
)

file_agent = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你负责本地文件信息整理。",
)

coder_agent = create_agent(
    model="openai:gpt-4.1",
    tools=[],
    system_prompt="你负责脚本生成与数据处理建议。",
)


async def invoke(agent, task: str) -> str:
    result = await agent.ainvoke({"messages": [{"role": "user", "content": task}]})
    return result["messages"][-1].content


@tool
async def use_web(task: str) -> str:
    return await invoke(web_agent, task)


@tool
async def use_file(task: str) -> str:
    return await invoke(file_agent, task)


@tool
async def use_coder(task: str) -> str:
    return await invoke(coder_agent, task)


orchestrator = create_agent(
    model="openai:gpt-4.1",
    tools=[use_web, use_file, use_coder],
    system_prompt=(
        "你是通用任务总控。"
        "根据任务进度决定调用 web、file、coder 中哪一个或多个，"
        "最后给出统一交付结果。"
    ),
)
```

### 13.7 AutoGen 实现

如果你想直接试官方现成系统，`MagenticOneGroupChat` 是最直接的入口。

```python
import asyncio

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def main() -> None:
    client = OpenAIChatCompletionClient(model="gpt-4o")

    assistant = AssistantAgent(
        "assistant",
        model_client=client,
        system_message="你是一个泛化任务助手。",
    )

    team = MagenticOneGroupChat([assistant], model_client=client)
    await Console(team.run_stream(task="给我一个调研计划：如何评估企业是否适合引入内部知识库问答系统。"))
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 13.8 常见坑与边界

- 通用代理集群适合试验，不一定是生产最省 token 的方案
- 系统内部行为通常更复杂，调试成本更高
- 一旦任务边界清楚，常常应该退回更简单的专用模式

---

## 14. 哪些模式是框架原生支持，哪些需要你自己搭

| 模式 | LangChain | AutoGen |
|---|---|---|
| 中央调度 | 有明确文档（Subagents） | 可直接用 Team 或自定义 orchestrator |
| Handoff | 有明确文档 | 有明确文档（Swarm / Handoffs） |
| 固定流水线 | 主要靠 LangGraph 自建 | 有明确文档（Sequential / GraphFlow） |
| Router | 有明确文档 | 常用 GraphFlow / Core 并发模式搭建 |
| 并行汇聚 | 常用 LangGraph 自建 | 有明确文档（Concurrent / GraphFlow / MoA） |
| Reflection | 常用 LangGraph 自建 | 有明确文档 |
| Debate | 常用 LangGraph 自建 | 有明确文档 |
| 共享群聊 | 无单一成品 Team | 有明确文档（RoundRobin / Selector / Group Chat） |
| Skills | 有明确文档 | 常见用 tools / memory 近似 |
| 通用代理集群 | 无官方单一成品 | 有明确文档（Magentic-One） |

---

## 15. 实施建议与选型建议

### 15.1 不要一上来就用最复杂的模式

一个很好用的实践顺序是：

1. 先试单 Agent + tools
2. 不够再试 skills / supervisor
3. 明确流程后再上 graph / workflow
4. 只有在确实需要共享讨论时才上 group chat / debate

### 15.2 设计模式时先锁 5 件事

无论你用哪个框架，最好先把下面 5 件事写清楚：

1. 输入是什么
2. 由谁决定下一步
3. 中间结果如何传递
4. 谁持有共享状态
5. 什么时候结束

### 15.3 最常见的工程错误

- 把“固定流水线”误做成“群聊”
- 把“技能加载”误当成“真正多 Agent”
- 没有显式终止条件
- 没有统一中间结果格式
- 在本该局部隔离的场景里强行共享全部历史

### 15.4 选型速记

- **固定顺序**：Workflow / Graph
- **主控调度**：Supervisor / Selector
- **用户多轮转接**：Handoff / Swarm
- **多路并发后汇总**：Router / Concurrent / Graph fan-out
- **生成-审稿循环**：Reflection
- **共享协作讨论**：Group Chat
- **只想按需加载专长**：Skills
- **先快速试一套成品**：Magentic-One

---

## 16. 官方链接索引

### 16.1 LangChain

- Multi-agent 总览  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/index>

- Subagents / Supervisor 教程  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant>

- Handoffs  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs>

- Router  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/router>

- Router tutorial  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/router-knowledge-base>

- Skills  
  <https://docs.langchain.com/oss/python/langchain/multi-agent/skills>

### 16.2 AutoGen

- AgentChat 总览  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html>

- Teams 教程  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/teams.html>

- SelectorGroupChat  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/selector-group-chat.html>

- Swarm  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/swarm.html>

- GraphFlow  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html>

- Magentic-One  
  <https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/magentic-one.html>

- Core 设计模式总览  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/intro.html>

- Core Group Chat  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html>

- Core Handoffs  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/handoffs.html>

- Core Concurrent Agents  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/concurrent-agents.html>

- Core Reflection  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/reflection.html>

- Core Mixture of Agents  
  <https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/mixture-of-agents.html>

- Core Sequential Workflow  
  <https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/sequential-workflow.html>

- Core Multi-Agent Debate  
  <https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/multi-agent-debate.html>

> 说明：如果某个 AutoGen 设计模式在 `stable` 站点暂未提供对应页面，可以先参考 `dev` 文档中的设计模式页，等版本稳定后再切回 `stable`。
