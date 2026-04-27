# OpenAI 官方 SDK 学习笔记

这份文档用于个人学习 OpenAI 官方 SDK。它只介绍官方 `OpenAI API SDK` 和 `OpenAI Agents SDK` 两条路线，不绑定任何具体项目实现。示例代码统一使用 Python。

> 说明：OpenAI 模型、工具和 SDK 参数会持续更新。本文示例中的模型名和能力范围以官方文档为准，实际运行前建议检查当前账号可用模型。

## 目录

- [1. OpenAI SDK 总览](#1-openai-sdk-总览)
- [2. 环境准备](#2-环境准备)
- [3. OpenAI API SDK](#3-openai-api-sdk)
- [4. OpenAI Agents SDK](#4-openai-agents-sdk)
- [5. API SDK 与 Agents SDK 对比](#5-api-sdk-与-agents-sdk-对比)
- [6. 学习路线](#6-学习路线)
- [7. 官方资料索引](#7-官方资料索引)

## 1. OpenAI SDK 总览

OpenAI 官方 SDK 可以理解为两层：

- `OpenAI API SDK`：最基础的 API 客户端，负责 API Key、请求封装、流式返回、响应对象、文件上传等通用能力。
- `OpenAI Agents SDK`：更高层的 agent 开发工具，负责 agent loop、工具调用、handoff、guardrails、tracing、sessions、sandbox、voice agents 等。

官方 API SDK 支持 JavaScript/TypeScript、Python、.NET、Java、Go。本文只写 Python。

```python
from openai import OpenAI

# OpenAI() 默认从环境变量 OPENAI_API_KEY 读取密钥。
# 如果需要连接非默认地址，可以传 base_url。
client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",  # 模型名，以官方模型文档和账号可用范围为准。
    input="用一句话解释 OpenAI API SDK 和 Agents SDK 的区别。",
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `OpenAI()` | 创建 API SDK 客户端 | 是 | `client = OpenAI()` | 默认读取 `OPENAI_API_KEY` |
| `model` | 指定模型 | 是 | `gpt-5.5` | 以官方模型文档为准 |
| `input` | 输入内容 | 是 | 字符串或消息数组 | 简单任务可用字符串 |
| `response.output_text` | 读取聚合后的文本输出 | 否 | `print(response.output_text)` | 适合快速读取文本结果 |

## 2. 环境准备

建议分别安装两个包：

```bash
pip install openai
pip install openai-agents
export OPENAI_API_KEY="your_api_key_here"
```

下面的 Python 脚本用于检查环境变量并发起一个最小请求。

```python
import os
from openai import OpenAI

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("请先设置 OPENAI_API_KEY 环境变量")

client = OpenAI(
    api_key=api_key,  # 可省略；默认读取 OPENAI_API_KEY。
    timeout=30.0,  # 请求超时时间，单位秒。
    max_retries=2,  # 网络错误或限流时的 SDK 重试次数。
)

response = client.responses.create(
    model="gpt-5.5",
    input="Say hello in Chinese.",
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `OPENAI_API_KEY` | API 访问密钥 | 是 | `sk-...` | 不要提交到代码仓库 |
| `api_key` | 显式传入密钥 | 否 | `api_key=os.getenv(...)` | 通常使用环境变量更安全 |
| `base_url` | API 基础地址 | 否 | 默认 OpenAI API 地址 | 只有特殊环境才需要改 |
| `timeout` | 请求超时时间 | 否 | `30.0` | 长输出或文件任务可适当增大 |
| `max_retries` | 自动重试次数 | 否 | `2` | 不适合替代业务级重试策略 |

## 3. OpenAI API SDK

API SDK 是直接调用 OpenAI 平台能力的基础方式。学习主线建议从 `Responses API` 开始，因为它是新项目的推荐入口，支持文本、图像、工具调用、结构化输出、流式输出和多轮状态。

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",  # API SDK 主线入口通常从 Responses API 开始。
    input="列出 OpenAI API SDK 最值得先学习的 3 个能力。",
    max_output_tokens=200,
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `OpenAI` | API SDK 客户端 | 是 | `client = OpenAI()` | 默认读取环境变量 |
| `responses.create` | 创建模型响应 | 是 | `client.responses.create(...)` | 新项目优先学习 |
| `model` | 指定模型 | 是 | `gpt-5.5` | 以官方模型文档为准 |
| `max_output_tokens` | 控制输出长度 | 否 | `200` | 适合学习时控制成本 |

### 3.1 Client 基础

Client 负责读取认证信息、配置请求参数、管理重试和超时。大多数示例只需要 `OpenAI()`。

```python
import os
from openai import OpenAI

default_client = OpenAI()

custom_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),  # 显式传入 API Key。
    base_url="https://api.openai.com/v1",  # 默认地址，一般不需要写。
    timeout=20.0,  # 单次请求最长等待时间。
    max_retries=2,  # SDK 层自动重试次数。
)

response = custom_client.responses.create(
    model="gpt-5.5",
    input="请用一句话说明 Client 的作用。",
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `api_key` | 认证密钥 | 否 | `os.getenv("OPENAI_API_KEY")` | 默认自动读取环境变量 |
| `base_url` | API 基础地址 | 否 | `https://api.openai.com/v1` | 通常不需要设置 |
| `organization` | 组织标识 | 否 | `org_...` | 多组织账号才常用 |
| `project` | 项目标识 | 否 | `proj_...` | 用于项目级隔离 |
| `timeout` | 请求超时 | 否 | `20.0` | 可为复杂任务增大 |
| `max_retries` | 自动重试 | 否 | `2` | 避免盲目设置过大 |

### 3.2 Responses API

`Responses API` 是新项目推荐使用的统一接口。它可以处理文本、图像输入、工具调用、结构化输出和多轮状态。

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",  # 模型名。
    instructions="你是一个简洁的 Python 教学助手。",  # 当前请求的高优先级行为说明。
    input="用三点解释 Python list 和 tuple 的区别。",  # 用户输入。
    reasoning={"effort": "low"},  # 推理强度，具体支持范围以模型文档为准。
    temperature=0.3,  # 输出随机性，越低越稳定。
    max_output_tokens=400,  # 限制最大输出 token。
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `model` | 指定模型 | 是 | `gpt-5.5` | 以官方模型文档为准 |
| `input` | 输入内容 | 是 | 字符串或消息数组 | 可包含文本、图像、文件等内容 |
| `instructions` | 当前请求的开发者指令 | 否 | `"回答要简洁"` | 只作用于当前请求 |
| `reasoning` | 控制推理行为 | 否 | `{"effort": "low"}` | 不是所有模型都支持同样选项 |
| `tools` | 可用工具列表 | 否 | `web_search`、`file_search` | 可用工具以官方文档为准 |
| `stream` | 是否流式返回 | 否 | `True` / `False` | 流式返回需要处理事件 |
| `previous_response_id` | 关联上一轮响应 | 否 | `resp_...` | 用于服务端状态延续 |

### 3.3 文本生成

文本生成可以从简单字符串开始，也可以使用消息数组表达不同角色和多轮上下文。

```python
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model="gpt-5.5",
    input=[
        {
            "role": "developer",  # 应用开发者指令，优先级高于 user。
            "content": "你只能用三句话以内回答。",
        },
        {
            "role": "user",  # 终端用户输入。
            "content": "解释什么是递归，并给一个生活类比。",
        },
        {
            "role": "assistant",  # 可手动提供上一轮模型输出。
            "content": "递归是函数直接或间接调用自身。",
        },
        {
            "role": "user",
            "content": "再给一个 Python 例子。",
        },
    ],
    max_output_tokens=300,
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `input` 字符串 | 最简单输入方式 | 是 | `"讲一个故事"` | 适合单轮任务 |
| `input` 消息数组 | 表达角色和历史 | 是 | `[{role, content}]` | 适合多轮或强控制任务 |
| `role` | 消息角色 | 是 | `developer`、`user`、`assistant` | 角色含义不同 |
| `content` | 消息内容 | 是 | 文本或内容数组 | 多模态输入时通常用数组 |

### 3.4 多轮对话与 conversation state

多轮状态有三种常见方式：手动维护历史、使用 `previous_response_id`、使用 `conversation`。学习时先掌握手动 history，再看服务端状态。

```python
from openai import OpenAI

client = OpenAI()

# 方式 1：手动维护 history。
history = [{"role": "user", "content": "给我讲一个关于栈的数据结构例子。"}]
first = client.responses.create(
    model="gpt-5.5",
    input=history,
    store=False,  # 不要求 OpenAI 端保存本次响应状态。
)
print(first.output_text)

history += [{"role": item.role, "content": item.content} for item in first.output]
history.append({"role": "user", "content": "把这个例子改成 Python 代码。"})

second = client.responses.create(
    model="gpt-5.5",
    input=history,
    store=False,
)
print(second.output_text)

# 方式 2：使用 previous_response_id 让后续请求引用上一轮响应。
third = client.responses.create(
    model="gpt-5.5",
    previous_response_id=second.id,  # 接续上一轮上下文。
    input="再补充一个常见错误。",
)
print(third.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `store` | 是否保存响应状态 | 否 | `False` / `True` | 与数据保留策略相关 |
| `previous_response_id` | 引用上一轮响应 | 否 | `second.id` | 仍会计入相关输入 token |
| `conversation` | 使用 Conversations API 状态 | 否 | `conv_...` | 适合跨设备或长会话 |
| 手动 `history` | 应用自行维护上下文 | 否 | `list[dict]` | 控制力最高，也最需要自己管理长度 |

### 3.5 Streaming 流式输出

流式输出适合长回答和实时 UI。Responses API 会返回带类型的事件，常见文本增量事件是 `response.output_text.delta`。

```python
from openai import OpenAI

client = OpenAI()

stream = client.responses.create(
    model="gpt-5.5",
    input="写一段 150 字以内的 Python 学习建议。",
    stream=True,  # 开启流式输出。
)

for event in stream:
    if event.type == "response.output_text.delta":
        print(event.delta, end="", flush=True)
    elif event.type == "response.completed":
        print("\n\n[completed]")
    elif event.type == "error":
        print(f"\n[error] {event}")
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `stream` | 开启流式输出 | 否 | `True` | 开启后返回事件迭代器 |
| `response.output_text.delta` | 文本增量事件 | 否 | `event.delta` | 用于逐字显示 |
| `response.completed` | 响应完成事件 | 否 | `event.type` | 可在此收尾 UI |
| `error` | 错误事件 | 否 | `event.type == "error"` | 生产环境要记录和重试 |

### 3.6 Structured Outputs

结构化输出适合需要稳定 JSON 的场景，例如抽取字段、分类、生成配置。Python SDK 可结合 Pydantic 定义 schema。

```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class StudyPlan(BaseModel):
    topic: str
    days: int
    tasks: list[str]

response = client.responses.parse(
    model="gpt-5.5",
    input="为 Python 初学者生成一个 3 天学习计划。",
    text_format=StudyPlan,  # 使用 Pydantic 模型定义结构化输出。
)

plan = response.output_parsed
print(plan.topic)
print(plan.tasks)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| schema / Pydantic 模型 | 定义输出结构 | 是 | `StudyPlan` | 字段越清晰越稳定 |
| `strict` | 严格遵守 schema | 否 | `True` | REST JSON Schema 常见参数 |
| `refusal` | 安全拒答信息 | 否 | 响应字段 | 需要和正常解析结果区分 |
| `output_parsed` | 解析后的对象 | 否 | `response.output_parsed` | Python SDK 便捷字段 |

### 3.7 Function Calling / Tools

Function Calling 让模型决定何时调用你提供的函数。核心流程是：声明工具，模型产生 tool call，应用执行函数，再把结果回传给模型。

```python
import json
from openai import OpenAI

client = OpenAI()

def get_weather(city: str) -> dict:
    # 真实应用里这里可以调用天气 API。
    return {"city": city, "temperature": "22C", "condition": "sunny"}

tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定城市的当前天气。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如 Beijing",
                }
            },
            "required": ["city"],
            "additionalProperties": False,
        },
    }
]

response = client.responses.create(
    model="gpt-5.5",
    input="北京今天天气如何？",
    tools=tools,  # 告诉模型有哪些工具可用。
    tool_choice="auto",  # 让模型自行判断是否调用。
)

for item in response.output:
    if item.type == "function_call" and item.name == "get_weather":
        args = json.loads(item.arguments)
        tool_result = get_weather(**args)

        follow_up = client.responses.create(
            model="gpt-5.5",
            previous_response_id=response.id,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(tool_result, ensure_ascii=False),
                }
            ],
        )
        print(follow_up.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `tools` | 声明可用工具 | 否 | `[{type: "function", ...}]` | 工具越清晰越容易正确调用 |
| `tool_choice` | 控制工具选择 | 否 | `auto`、指定工具 | 强制工具调用需谨慎 |
| `name` | 工具名 | 是 | `get_weather` | 建议稳定、简短、语义明确 |
| `description` | 工具用途说明 | 是 | `"查询天气"` | 影响模型是否调用 |
| `parameters` | 工具参数 JSON Schema | 是 | `object` schema | 建议关闭额外字段 |

### 3.8 Hosted Tools

Hosted Tools 是 OpenAI 平台托管的工具，例如 web search、file search、image generation、code interpreter。它们不需要你自己执行工具代码。

```python
from openai import OpenAI

client = OpenAI()

web_response = client.responses.create(
    model="gpt-5.5",
    input="总结最近 OpenAI API 文档里 Responses API 的定位。",
    tools=[{"type": "web_search"}],  # 托管网页搜索工具。
)
print(web_response.output_text)

file_response = client.responses.create(
    model="gpt-5.5",
    input="从我的知识库中找出关于 SDK 的说明。",
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": ["vs_123"],  # 替换为真实 vector store id。
        }
    ],
)
print(file_response.output_text)

image_response = client.responses.create(
    model="gpt-5.5",
    input="Draw a small diagram explaining API SDK vs Agents SDK.",
    tools=[{"type": "image_generation"}],  # 图像生成工具。
)
print(image_response.output)

code_response = client.responses.create(
    model="gpt-5.5",
    input="用 Python 计算 1 到 100 的平方和，并解释结果。",
    tools=[{"type": "code_interpreter"}],  # 托管代码解释器工具。
)
print(code_response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `type` | 工具类型 | 是 | `web_search`、`file_search`、`image_generation`、`code_interpreter` | 支持范围以官方文档为准 |
| `vector_store_ids` | file search 的知识库 | file search 必填 | `["vs_123"]` | 需要先创建 vector store |
| `tools` | 托管工具列表 | 否 | `[{...}]` | 模型会决定是否使用 |
| 适用场景 | 选择工具 | 否 | 搜索、检索、画图、代码执行 | 涉及成本、延迟和权限 |

### 3.9 Files、Vector Stores、Retrieval

文件和向量库常用于检索增强。典型流程是上传文件，创建 vector store，把文件加入 vector store，然后用 `file_search` 查询。

```python
from openai import OpenAI

client = OpenAI()

uploaded_file = client.files.create(
    file=open("notes.md", "rb"),
    purpose="assistants",  # 文件用途，具体可选值以官方文档为准。
)

vector_store = client.vector_stores.create(
    name="sdk-learning-notes",
)

client.vector_stores.files.create(
    vector_store_id=vector_store.id,
    file_id=uploaded_file.id,
)

response = client.responses.create(
    model="gpt-5.5",
    input="根据我的学习笔记，总结 API SDK 的重点。",
    tools=[
        {
            "type": "file_search",
            "vector_store_ids": [vector_store.id],
            "ranking_options": {
                "score_threshold": 0.2,  # 最低相关性阈值。
            },
        }
    ],
)

print(response.output_text)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `purpose` | 文件用途 | 是 | `assistants` | 以 Files API 文档为准 |
| `vector_store_id` | 向量库 ID | 是 | `vs_...` | 由创建 vector store 返回 |
| `file_ids` | 文件 ID 列表 | 否 | `["file_..."]` | 可批量绑定 |
| `ranking_options` | 检索排序配置 | 否 | `score_threshold` | 阈值过高可能无结果 |

### 3.10 Embeddings

Embeddings 把文本转换成向量，可用于搜索、聚类、推荐、分类和相似度计算。

```python
import math
from openai import OpenAI

client = OpenAI()

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)

result = client.embeddings.create(
    model="text-embedding-3-small",  # embedding 模型。
    input=[
        "OpenAI API SDK 是基础客户端。",
        "Agents SDK 用来构建 agent 应用。",
    ],
    dimensions=512,  # 可选，部分 embedding 模型支持缩短维度。
)

v1 = result.data[0].embedding
v2 = result.data[1].embedding
print(cosine_similarity(v1, v2))
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `model` | embedding 模型 | 是 | `text-embedding-3-small` | 以模型文档为准 |
| `input` | 待向量化文本 | 是 | 字符串或字符串数组 | 批量输入更高效 |
| `dimensions` | 输出向量维度 | 否 | `512` | 不是所有模型都支持 |
| `data[].embedding` | 返回向量 | 否 | `list[float]` | 可用于相似度计算 |

### 3.11 Images and Vision

图像能力分两类：让模型理解图像输入，以及生成或编辑图像。Responses API 可以把图像作为输入，也可以通过 `image_generation` 工具生成图像。

```python
import base64
from openai import OpenAI

client = OpenAI()

vision_response = client.responses.create(
    model="gpt-5.5",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "请描述这张图片里最重要的信息。"},
                {
                    "type": "input_image",
                    "image_url": "https://example.com/demo.png",  # 也可使用 base64 data URL 或 file_id。
                },
            ],
        }
    ],
)
print(vision_response.output_text)

image_response = client.responses.create(
    model="gpt-5.5",
    input="Generate a simple icon for learning SDKs.",
    tools=[
        {
            "type": "image_generation",
            "size": "1024x1024",
            "quality": "medium",
            "format": "png",
        }
    ],
)

for output in image_response.output:
    if output.type == "image_generation_call":
        with open("sdk_icon.png", "wb") as f:
            f.write(base64.b64decode(output.result))
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `input_image` | 图像输入类型 | 图像任务必填 | `{"type": "input_image"}` | 可用 URL、data URL 或 file id |
| `image_url` | 图像地址 | 否 | `https://...` | 生产环境注意权限和有效期 |
| `tools` | 图像生成工具 | 生成图像必填 | `image_generation` | 可用模型以官方文档为准 |
| `size` | 输出尺寸 | 否 | `1024x1024` | 尺寸影响成本和延迟 |
| `quality` | 输出质量 | 否 | `low`、`medium`、`high` | 高质量更慢更贵 |
| `format` | 输出格式 | 否 | `png`、`jpeg`、`webp` | 以当前 API 支持为准 |

### 3.12 Audio

Audio 包括 speech to text、text to speech，以及更低延迟的 Realtime 语音交互。先学习转写和合成，再学习 Realtime。

```python
from pathlib import Path
from openai import OpenAI

client = OpenAI()

# Speech to text：把音频转文字。
transcript = client.audio.transcriptions.create(
    model="gpt-4o-mini-transcribe",
    file=open("meeting.mp3", "rb"),
    response_format="text",  # 可选 text、json 等，以官方文档为准。
)
print(transcript)

# Text to speech：把文字转音频并写入文件。
with client.audio.speech.with_streaming_response.create(
    model="gpt-4o-mini-tts",
    voice="alloy",  # 声音名，以官方文档为准。
    input="这是一个 OpenAI SDK 学习示例。",
    instructions="用清晰、平稳、适合教学的语气朗读。",
    response_format="mp3",  # 输出音频格式，默认也是 mp3。
) as speech:
    speech.stream_to_file(Path("sdk_intro.mp3"))
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `model` | 音频模型 | 是 | `gpt-4o-mini-transcribe`、`gpt-4o-mini-tts` | 以官方模型文档为准 |
| `file` | 输入音频文件 | 转写必填 | `open("meeting.mp3", "rb")` | 注意文件大小和格式 |
| `voice` | TTS 声音 | TTS 必填 | `alloy` | 需要告知用户声音为 AI 生成 |
| `format` | 文件格式概念 | 否 | `mp3`、`wav`、`pcm` | TTS Python SDK 中常用 `response_format` 设置 |
| `response_format` | 转写或语音输出格式 | 否 | `text`、`json`、`mp3`、`wav` | 不同音频接口支持值不同 |

### 3.13 Moderation / Safety

Moderation 用于在输入或输出进入业务流程前做安全检查。它不能替代完整的产品安全策略，但适合作为第一层过滤。

```python
from openai import OpenAI

client = OpenAI()

result = client.moderations.create(
    model="omni-moderation-latest",  # 审核模型，以官方文档为准。
    input="这里放需要检查的用户输入或模型输出。",
)

item = result.results[0]
print("flagged:", item.flagged)
print("categories:", item.categories)
print("scores:", item.category_scores)

if item.flagged:
    print("建议：阻止、降级、转人工或要求用户改写。")
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `model` | 审核模型 | 是 | `omni-moderation-latest` | 以官方文档为准 |
| `input` | 待审核内容 | 是 | 字符串或内容数组 | 可检查输入和输出 |
| `flagged` | 是否触发风险 | 否 | `True` / `False` | 需要结合业务策略处理 |
| 分类结果字段 | 风险类别 | 否 | `categories`、`category_scores` | 阈值策略由业务决定 |
| 处理建议 | 后续动作 | 否 | 阻止、降级、转人工 | 不建议只靠单一规则 |

### 3.14 Batch API

Batch API 适合不需要立即返回的批处理任务，例如批量分类、批量摘要、批量 embedding。输入通常是 `.jsonl`。

```python
import json
from openai import OpenAI

client = OpenAI()

requests = [
    {
        "custom_id": "sdk-summary-1",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": "gpt-5.5",
            "input": "用一句话解释 Responses API。",
        },
    },
    {
        "custom_id": "sdk-summary-2",
        "method": "POST",
        "url": "/v1/responses",
        "body": {
            "model": "gpt-5.5",
            "input": "用一句话解释 Agents SDK。",
        },
    },
]

with open("batch_input.jsonl", "w", encoding="utf-8") as f:
    for request in requests:
        f.write(json.dumps(request, ensure_ascii=False) + "\n")

input_file = client.files.create(
    file=open("batch_input.jsonl", "rb"),
    purpose="batch",
)

batch = client.batches.create(
    input_file_id=input_file.id,
    endpoint="/v1/responses",  # 批处理目标 endpoint。
    completion_window="24h",  # 官方 Batch API 常见完成窗口。
    metadata={"job": "sdk-learning"},
)

print(batch.id)
print(client.batches.retrieve(batch.id).status)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `input_file_id` | batch 输入文件 ID | 是 | `file_...` | 文件内容为 JSONL |
| `endpoint` | 批处理 endpoint | 是 | `/v1/responses` | 同一个 batch 通常面向一个 endpoint |
| `completion_window` | 完成窗口 | 是 | `24h` | 不适合实时场景 |
| `metadata` | 业务元数据 | 否 | `{"job": "..."}` | 方便追踪 |

### 3.15 Fine-tuning

Fine-tuning 用于让模型更稳定地适配特定任务。一般流程是准备 JSONL 训练集，上传文件，创建 fine-tuning job，查询训练状态。

```python
from openai import OpenAI

client = OpenAI()

training_file = client.files.create(
    file=open("training.jsonl", "rb"),
    purpose="fine-tune",
)

job = client.fine_tuning.jobs.create(
    model="gpt-4.1-mini-2025-04-14",  # 可微调模型以官方文档为准。
    training_file=training_file.id,
    # validation_file="file_validation_id",  # 可选：验证集文件。
    suffix="sdk-learning-demo",  # 可选：方便识别模型。
    method={
        "type": "supervised",  # 微调方法，以官方文档为准。
    },
)

print(job.id)
print(client.fine_tuning.jobs.retrieve(job.id).status)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `model` | 基础模型 | 是 | `gpt-4.1-mini-2025-04-14` | 可微调模型以官方文档为准 |
| `training_file` | 训练数据文件 ID | 是 | `file_...` | 文件需符合 fine-tuning 格式 |
| `method` | 微调方法 | 否 | `supervised` | SFT、DPO、RFT 等支持范围会变化 |
| `validation_file` | 验证数据文件 ID | 否 | `file_...` | 用于评估训练效果 |
| `suffix` | 模型后缀 | 否 | `sdk-learning-demo` | 方便在模型列表中识别 |

## 4. OpenAI Agents SDK

Agents SDK 用于构建 agentic 应用。它的核心是：`Agent` 定义角色和工具，`Runner` 执行 agent loop，SDK 负责工具调用、handoff、guardrails、sessions 和 tracing。

```python
from agents import Agent, Runner

agent = Agent(
    name="SDK Learning Agent",
    instructions="你负责帮助用户按阶段学习 OpenAI 官方 SDK。",
    model="gpt-5.5",
)

result = Runner.run_sync(
    agent,
    "给我一个学习 Agents SDK 的最小路线。",
    max_turns=3,  # 限制 agent loop 轮数。
)

print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `Agent` | 定义 agent | 是 | `Agent(name=..., instructions=...)` | 负责角色、模型、工具配置 |
| `Runner` | 执行 agent loop | 是 | `Runner.run_sync(...)` | 负责模型调用和工具循环 |
| `model` | agent 使用的模型 | 否 | `gpt-5.5` | 可在 agent 或 run config 设置 |
| `max_turns` | 最大运行轮数 | 否 | `3` | 防止复杂流程跑太久 |

### 4.1 安装与 Hello World

先安装 `openai-agents`，再定义一个最简单的 agent。

```python
from agents import Agent, Runner

agent = Agent(
    name="Assistant",  # agent 名称，用于 trace 和调试。
    instructions="你是一个简洁的中文学习助手。",  # agent 行为说明。
    model="gpt-5.5",  # 可省略，默认模型以 SDK 配置为准。
)

result = Runner.run_sync(
    agent,
    "用一句话解释什么是 SDK。",
)

print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `name` | agent 名称 | 是 | `Assistant` | 建议语义清楚 |
| `instructions` | agent 指令 | 否 | `"你是..."` | 决定行为和风格 |
| `model` | agent 默认模型 | 否 | `gpt-5.5` | 可在 run config 中覆盖 |

### 4.2 Agent / Runner 基础

`Runner.run` 是异步方法，`Runner.run_sync` 是同步包装。`max_turns` 可限制 agent loop 最大轮数，避免工具循环。

```python
import asyncio
from agents import Agent, Runner

agent = Agent(
    name="Python Tutor",
    instructions="用简短例子解释 Python 概念。",
)

sync_result = Runner.run_sync(
    agent,
    "解释 list comprehension。",
    max_turns=3,  # 限制 agent loop，防止过多工具或 handoff 回合。
)
print(sync_result.final_output)

async def main():
    async_result = await Runner.run(
        agent,
        "解释 generator。",
        max_turns=3,
    )
    print(async_result.final_output)

asyncio.run(main())
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `Runner.run` | 异步运行 agent | 是 | `await Runner.run(...)` | Web 服务中更常用 |
| `Runner.run_sync` | 同步运行 agent | 是 | `Runner.run_sync(...)` | 脚本和学习示例方便 |
| `max_turns` | 最大 agent loop 轮数 | 否 | `3`、`10` | 防止无限工具调用 |
| `final_output` | 最终输出 | 否 | `result.final_output` | 最常读取的结果 |

### 4.3 Instructions、model、context

`instructions` 可以是静态字符串，也可以根据上下文动态生成。`context` 可传入任意 Python 对象，供指令或工具读取。

```python
from dataclasses import dataclass
from agents import Agent, RunContextWrapper, Runner

@dataclass
class UserContext:
    name: str
    level: str

def dynamic_instructions(ctx: RunContextWrapper[UserContext], agent: Agent) -> str:
    return (
        f"你正在辅导 {ctx.context.name}。"
        f"对方水平是 {ctx.context.level}，请调整解释深度。"
    )

agent = Agent[UserContext](
    name="Adaptive Tutor",
    instructions=dynamic_instructions,  # 根据 context 动态生成指令。
    model="gpt-5.5",
)

result = Runner.run_sync(
    agent,
    "解释 Python 装饰器。",
    context=UserContext(name="小陈", level="初学者"),
)

print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `instructions` | 静态或动态指令 | 否 | 字符串或函数 | 动态函数可读取 context |
| `model` | agent 模型 | 否 | `gpt-5.5` | 可在不同 agent 使用不同模型 |
| `context` | 运行期上下文 | 否 | dataclass、dict | 不会自动暴露给模型，除非指令或工具使用 |

### 4.4 Function tools

`@function_tool` 可以把 Python 函数转成 agent 可调用工具。函数签名、类型注解和 docstring 会影响工具 schema。

```python
from agents import Agent, Runner, function_tool

@function_tool
def calculate_bmi(weight_kg: float, height_m: float) -> str:
    """根据体重和身高计算 BMI。"""
    bmi = weight_kg / (height_m ** 2)
    return f"BMI is {bmi:.1f}"

agent = Agent(
    name="Health Helper",
    instructions="需要计算 BMI 时调用工具，并解释结果。",
    tools=[calculate_bmi],  # 把 Python 函数暴露为工具。
)

result = Runner.run_sync(
    agent,
    "我 70kg，1.75m，BMI 是多少？",
)

print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| 函数签名 | 定义工具参数 | 是 | `weight_kg: float` | 类型越明确越好 |
| docstring | 工具说明 | 建议 | `"""计算 BMI"""` | 影响模型选择工具 |
| 参数类型 | 生成 schema | 建议 | `str`、`float`、Pydantic 模型 | 复杂输入建议用结构化类型 |
| 返回值 | 工具结果 | 是 | 字符串、JSON 可序列化对象 | 返回内容会给模型继续处理 |

### 4.5 Agents as tools

可以把一个专门 agent 包装成另一个 agent 的工具。适合 manager agent 保持控制权，同时调用专家 agent 完成子任务。

```python
from agents import Agent, Runner

summary_agent = Agent(
    name="Summary Agent",
    instructions="把输入压缩成三个要点。",
)

translator_agent = Agent(
    name="Translator Agent",
    instructions="把输入翻译成自然中文。",
)

manager = Agent(
    name="Manager",
    instructions="根据用户需要选择合适工具，并整合最终回答。",
    tools=[
        summary_agent.as_tool(
            tool_name="summarize_text",
            tool_description="把长文本总结成三个要点。",
        ),
        translator_agent.as_tool(
            tool_name="translate_to_chinese",
            tool_description="把文本翻译成中文。",
        ),
    ],
)

result = Runner.run_sync(manager, "Summarize: OpenAI SDKs help developers build AI apps.")
print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `as_tool` | 把 agent 变成工具 | 是 | `agent.as_tool(...)` | manager 仍拥有最终回答权 |
| `tool_name` | 工具名称 | 是 | `summarize_text` | 命名要稳定 |
| `tool_description` | 工具说明 | 是 | `"总结长文本"` | 决定何时调用 |
| 专家 agent | 子任务执行者 | 是 | `summary_agent` | 指令要专注 |

### 4.6 Handoffs

Handoff 表示当前 agent 把对话控制权交给另一个 agent。适合客服、分诊、专家路由等场景。

```python
from agents import Agent, Runner

billing_agent = Agent(
    name="Billing Specialist",
    handoff_description="处理账单、发票、付款问题。",
    instructions="你专门回答账单相关问题。",
)

tech_agent = Agent(
    name="Technical Specialist",
    handoff_description="处理 API、SDK、报错和集成问题。",
    instructions="你专门回答技术支持问题。",
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="判断用户问题类型，并在需要时 handoff 给专家。",
    handoffs=[billing_agent, tech_agent],  # 可交接的专家列表。
)

result = Runner.run_sync(
    triage_agent,
    "我的 Python SDK 调用一直超时，应该怎么排查？",
)

print(result.final_output)
print("last agent:", result.last_agent.name)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `handoffs` | 可转交 agent 列表 | 否 | `[tech_agent]` | 转交后专家接管当前任务 |
| `handoff_description` | 路由说明 | 建议 | `"处理技术问题"` | 帮助 triage agent 判断 |
| 输入过滤 | 控制转交内容 | 否 | handoff input filter | 可移除敏感或无关上下文 |
| `last_agent` | 最终回答 agent | 否 | `result.last_agent` | 用于调试路由结果 |

### 4.7 Guardrails

Guardrails 用于在 agent 运行前后做校验。输入 guardrail 可提前拦截不合规请求，输出 guardrail 可检查最终回答。

```python
from pydantic import BaseModel
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    Runner,
    input_guardrail,
)

class SafetyCheck(BaseModel):
    is_homework_cheating: bool
    reason: str

guardrail_agent = Agent(
    name="Safety Checker",
    instructions="判断用户是否要求直接代写作业答案。",
    output_type=SafetyCheck,
)

@input_guardrail
async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_homework_cheating,
    )

agent = Agent(
    name="Tutor",
    instructions="帮助用户学习，但不要直接代写作业。",
    input_guardrails=[homework_guardrail],
)

try:
    result = Runner.run_sync(agent, "直接帮我写完这份作业。")
    print(result.final_output)
except InputGuardrailTripwireTriggered:
    print("触发输入 guardrail：需要改为引导式辅导。")
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| guardrail function | 校验逻辑 | 是 | `@input_guardrail` | 可异步调用模型或规则 |
| `tripwire_triggered` | 是否触发阻断 | 是 | `True` / `False` | 触发后会中断运行 |
| 失败处理 | 捕获异常 | 建议 | `InputGuardrailTripwireTriggered` | 用户体验要友好 |
| `output_info` | 校验详情 | 否 | Pydantic 对象 | 方便日志和调试 |

### 4.8 Sessions / Memory

Sessions 让 SDK 自动维护多轮历史，不需要手动调用 `to_input_list()`。本地学习可先用 `SQLiteSession`。

```python
from agents import Agent, Runner, SQLiteSession

agent = Agent(
    name="Memory Assistant",
    instructions="回答要简洁，并记住当前对话上下文。",
)

session = SQLiteSession(
    "sdk_learning_user_001",  # session id。
    "sdk_learning.db",  # 可选：SQLite 文件路径。
)

first = Runner.run_sync(
    agent,
    "我正在学习 OpenAI API SDK。",
    session=session,
)
print(first.final_output)

second = Runner.run_sync(
    agent,
    "我刚才说我在学什么？",
    session=session,
)
print(second.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| session 类型 | 选择记忆后端 | 是 | `SQLiteSession`、Redis、SQLAlchemy | 以官方 SDK 支持为准 |
| session id | 区分会话 | 是 | `sdk_learning_user_001` | 建议稳定且可追踪 |
| 存储后端 | 保存历史 | 否 | SQLite 文件、Redis、数据库 | 生产环境需考虑并发和隐私 |
| `session` | Runner 参数 | 否 | `session=session` | 不能和某些服务端状态方式混用 |

### 4.9 Streaming agent runs

Agents SDK 支持流式运行。可以读取 agent 更新、原始模型事件、工具调用事件和最终结果。

```python
import asyncio
from agents import Agent, Runner

agent = Agent(
    name="Streaming Assistant",
    instructions="用两段话回答，并保持简洁。",
)

async def main():
    result = Runner.run_streamed(
        agent,
        "解释为什么 streaming 对聊天产品很重要。",
    )

    async for event in result.stream_events():
        if event.type == "raw_response_event":
            # 原始 Responses API 事件，通常可按需过滤。
            continue
        elif event.type == "run_item_stream_event":
            print("run item:", event.item.type)
        elif event.type == "agent_updated_stream_event":
            print("agent:", event.new_agent.name)
        else:
            print("event:", event.type)

    print(result.final_output)

asyncio.run(main())
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| event type | 事件类型 | 是 | `raw_response_event`、`run_item_stream_event` | 不同事件字段不同 |
| text delta | 文本增量 | 否 | 原始响应事件中读取 | 需要按官方事件类型解析 |
| tool call event | 工具调用事件 | 否 | run item | 可用于 UI 展示工具状态 |
| final event | 最终结果 | 否 | `result.final_output` | 流结束后读取完整结果 |

### 4.10 Results and state

`RunResult` 包含最终输出、新增 items、最后 agent、工具调用和可继续传入下一轮的状态。

```python
from agents import Agent, Runner, function_tool

@function_tool
def get_course_outline(topic: str) -> list[str]:
    """返回某个主题的学习大纲。"""
    return ["概念", "核心 API", "示例", "练习"]

agent = Agent(
    name="Course Planner",
    instructions="需要学习大纲时调用工具，再输出学习建议。",
    tools=[get_course_outline],
)

result = Runner.run_sync(agent, "给我一个 OpenAI SDK 学习大纲。")

print(result.final_output)
print("last agent:", result.last_agent.name)

for item in result.new_items:
    print("new item:", item.type)

next_input = result.to_input_list() + [
    {"role": "user", "content": "把上面的学习大纲压缩成 3 项。"}
]
next_result = Runner.run_sync(agent, next_input)
print(next_result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `RunResult` | 运行结果对象 | 是 | `result` | 包含最终结果和中间状态 |
| `new_items` | 本轮新增项目 | 否 | tool call、message 等 | 适合调试和审计 |
| `final_output` | 最终回答 | 否 | `result.final_output` | 最常用字段 |
| `to_input_list()` | 转成下一轮输入 | 否 | `result.to_input_list()` | 手动维护多轮时很有用 |

### 4.11 Tracing / Observability

Tracing 用于观察 agent 的完整运行过程，包括模型调用、工具调用、handoff 和错误。默认通常会记录 trace，也可通过配置补充 workflow name 和 metadata。

```python
from agents import Agent, RunConfig, Runner

agent = Agent(
    name="Trace Demo",
    instructions="回答要简短。",
)

result = Runner.run_sync(
    agent,
    "解释 tracing 对调试 agent 的价值。",
    run_config=RunConfig(
        workflow_name="sdk-learning-trace",  # trace 工作流名称。
        group_id="learning-session-001",  # 可把多次运行归为一组。
        trace_metadata={
            "doc": "SDK.md",
            "chapter": "Agents SDK tracing",
        },
    ),
)

print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| trace name / `workflow_name` | trace 工作流名 | 否 | `sdk-learning-trace` | 便于 dashboard 检索 |
| `group_id` | trace 分组 | 否 | `learning-session-001` | 适合关联多次运行 |
| `metadata` / `trace_metadata` | 附加信息 | 否 | `{"chapter": "..."}` | 不要放敏感数据 |
| tracing 开关 | 是否记录 trace | 否 | `tracing_disabled=True` | 隐私场景要特别注意 |

### 4.12 Sandbox execution

Sandbox agents 用于让 agent 在受控工作区中检查或修改文件、运行命令。此能力变化较快，实际使用前务必对照官方 Sandbox agents 文档。

```python
import asyncio

from agents import Runner
from agents.run import RunConfig
from agents.sandbox import SandboxAgent, SandboxRunConfig
from agents.sandbox.sandboxes.unix_local import UnixLocalSandboxClient

async def main():
    agent = SandboxAgent(
        name="Code Reviewer",
        instructions="在 sandbox 中阅读文件，只给出问题摘要。",
    )

    result = await Runner.run(
        agent,
        "检查 sandbox 工作区里的 README，并指出需要补充的地方。",
        max_turns=5,
        run_config=RunConfig(
            sandbox=SandboxRunConfig(
                client=UnixLocalSandboxClient(),  # 本地学习常用；生产环境可换 Docker 或托管 sandbox。
            )
        ),
    )
    print(result.final_output)

asyncio.run(main())
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| sandbox 配置 | 定义受控环境 | 是 | 本地、Docker、远程 sandbox | 以官方文档为准 |
| 文件输入 | 提供工作区文件 | 否 | workspace entries | 注意敏感文件 |
| 权限边界 | 控制可读写范围 | 是 | filesystem、shell 权限 | 默认应最小权限 |
| `max_turns` | 限制执行轮数 | 否 | `5` | 防止长时间执行 |

### 4.13 Human in the loop

Human in the loop 用于在高风险工具调用前暂停，等待人工批准或拒绝，再恢复运行。

```python
from agents import Agent, Runner, function_tool

@function_tool(
    needs_approval=True,  # 工具调用前需要人工审批。
)
def send_email(to: str, subject: str, body: str) -> str:
    """发送邮件。"""
    return f"sent to {to}"

agent = Agent(
    name="Email Assistant",
    instructions="帮用户起草邮件。真正发送邮件前必须等待审批。",
    tools=[send_email],
)

result = Runner.run_sync(
    agent,
    "给 alice@example.com 发邮件，主题是 SDK 学习，正文说我今天完成了第一章。",
)

if result.interruptions:
    state = result.to_state()
    for interruption in result.interruptions:
        # 真实产品里应展示给用户确认。
        state.approve(interruption)

    resumed = Runner.run_sync(agent, state)
    print(resumed.final_output)
else:
    print(result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| approval request | 审批请求 | 否 | `result.interruptions` | 高风险操作才需要 |
| approve | 批准工具调用 | 否 | `state.approve(...)` | 需要记录审计日志 |
| reject | 拒绝工具调用 | 否 | `state.reject(...)` | 应给模型可理解的拒绝原因 |
| resume | 恢复运行 | 否 | `Runner.run(agent, state)` | 需保留 run state |

### 4.14 Realtime / Voice agents

Realtime agents 面向低延迟语音或实时交互。学习时先理解事件流、transport、音频格式和中断处理。

```python
import asyncio
from agents.realtime import RealtimeAgent, RealtimeRunner

agent = RealtimeAgent(
    name="Voice Tutor",
    instructions="你是一个简洁的语音 Python 教学助手。",
)

runner = RealtimeRunner(
    starting_agent=agent,
    config={
        "model_settings": {
            "model_name": "gpt-realtime-1.5",  # 实时模型，以官方文档为准。
            "audio": {
                "input": {
                    "format": "pcm16",
                    "turn_detection": {"type": "semantic_vad", "interrupt_response": True},
                },
                "output": {
                    "format": "pcm16",
                    "voice": "alloy",
                },
            },
        }
    },
)

async def main():
    session = await runner.run()
    async with session:
        await session.send_message("用一句话介绍 OpenAI Realtime agents。")

        async for event in session:
            if event.type == "audio":
                # 真实应用里把音频 bytes 送到播放器。
                print("audio chunk")
            elif event.type == "history_updated":
                print("history updated")
            elif event.type == "error":
                print("error:", event)

asyncio.run(main())
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| transport | 实时连接方式 | 是 | WebRTC、WebSocket | 取决于前端和后端架构 |
| audio format | 音频格式 | 是 | `pcm16` | 输入输出要和客户端一致 |
| interruptions | 打断处理 | 否 | 自动或手动 | 语音体验关键能力 |
| session | 实时会话 | 是 | `runner.run()` 返回 | 要处理连接生命周期 |

### 4.15 Usage tracking

Usage tracking 用于记录请求数、输入 token、输出 token、总 token 和每次请求明细，适合成本监控和限额控制。

```python
from agents import Agent, Runner

agent = Agent(
    name="Usage Demo",
    instructions="回答要简洁。",
)

result = Runner.run_sync(
    agent,
    "用两句话解释 token usage 为什么重要。",
)

usage = result.context_wrapper.usage

print("requests:", usage.requests)
print("input_tokens:", usage.input_tokens)
print("output_tokens:", usage.output_tokens)
print("total_tokens:", usage.total_tokens)

for entry in usage.request_usage_entries:
    print(entry)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `input_tokens` | 输入 token 数 | 否 | `usage.input_tokens` | 用于成本估算 |
| `output_tokens` | 输出 token 数 | 否 | `usage.output_tokens` | 长回答成本更高 |
| `total_tokens` | 总 token 数 | 否 | `usage.total_tokens` | 可用于限额 |
| `request_usage_entries` | 每次请求明细 | 否 | `list` | 多工具、多轮 agent 很有用 |

## 5. API SDK 与 Agents SDK 对比

API SDK 适合直接控制请求。Agents SDK 适合让 SDK 管理 agent loop、工具调用、handoff 和状态。

| 维度 | OpenAI API SDK | OpenAI Agents SDK |
| --- | --- | --- |
| 抽象层级 | 低层，贴近 HTTP API | 高层，面向 agent 应用 |
| 适用场景 | 单次生成、结构化输出、批处理、文件、向量、音频、图像 | 多工具、多 agent、handoff、guardrails、sessions、tracing |
| 学习成本 | 先低后高 | 先中等，复杂场景更省心 |
| 可控性 | 请求和状态完全自己控制 | SDK 管理 agent loop |
| 工具调用方式 | 自己声明、执行、回传工具结果 | `@function_tool` 和 Runner 自动循环 |
| 状态管理方式 | 手动 history、`previous_response_id`、`conversation` | sessions、`to_input_list()`、run state |

同一个“天气查询工具”的两种写法：

```python
import json
from openai import OpenAI
from agents import Agent, Runner, function_tool

# API SDK 写法：你自己处理 tool call。
client = OpenAI()

def get_weather(city: str) -> str:
    return f"{city}: 22C, sunny"

api_response = client.responses.create(
    model="gpt-5.5",
    input="北京天气怎么样？",
    tools=[
        {
            "type": "function",
            "name": "get_weather",
            "description": "查询城市天气。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        }
    ],
)

for item in api_response.output:
    if item.type == "function_call":
        args = json.loads(item.arguments)
        print(get_weather(**args))

# Agents SDK 写法：Runner 负责 tool loop。
@function_tool
def get_weather_tool(city: str) -> str:
    """查询城市天气。"""
    return get_weather(city)

agent = Agent(
    name="Weather Agent",
    instructions="需要天气时调用工具。",
    tools=[get_weather_tool],
)

agent_result = Runner.run_sync(agent, "北京天气怎么样？")
print(agent_result.final_output)
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| API SDK `tools` | 声明工具 schema | 否 | JSON Schema | 需要手动执行和回传 |
| Agents SDK `tools` | 注册 Python 工具 | 否 | `@function_tool` | Runner 自动执行循环 |
| `Runner` | 管理 agent loop | Agents SDK 必需 | `Runner.run_sync` | 适合复杂 agent 流程 |
| 选择标准 | 决定 SDK 路线 | 是 | 简单请求用 API SDK，复杂 agent 用 Agents SDK | 复杂度越高越适合 Agents SDK |

## 6. 学习路线

推荐先学 API SDK，再学 Agents SDK。这样能先理解底层 API，再理解更高层的 agent 编排。

```python
learning_path = [
    {
        "stage": 1,
        "goal": "API SDK 基础调用",
        "topics": ["Client", "Responses API", "Text generation"],
    },
    {
        "stage": 2,
        "goal": "控制输出和交互体验",
        "topics": ["Streaming", "Structured Outputs", "Function Calling"],
    },
    {
        "stage": 3,
        "goal": "连接数据和多模态能力",
        "topics": ["Files", "Vector Stores", "Embeddings", "Images", "Audio"],
    },
    {
        "stage": 4,
        "goal": "学习 agent 编排",
        "topics": ["Agent", "Runner", "Tools", "Handoffs", "Guardrails"],
    },
    {
        "stage": 5,
        "goal": "进入生产化能力",
        "topics": ["Tracing", "Sessions", "Realtime", "Batch", "Fine-tuning"],
    },
]

for item in learning_path:
    print(f"阶段 {item['stage']}: {item['goal']}")
    print("  ", ", ".join(item["topics"]))
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `stage` | 学习阶段 | 是 | `1` 到 `5` | 按顺序学习更顺 |
| `goal` | 阶段目标 | 是 | `"API SDK 基础调用"` | 用目标组织知识 |
| `topics` | 具体主题 | 是 | `["Responses API"]` | 每个主题都要跑最小示例 |
| 输出检查 | 确认学习进度 | 否 | 打印阶段 | 可以改成个人 checklist |

## 7. 官方资料索引

以下链接用于持续补充这份学习笔记。建议优先看官方文档，再看 Cookbook 和示例仓库。

```python
official_links = {
    "OpenAI Libraries": "https://platform.openai.com/docs/libraries",
    "Responses API": "https://platform.openai.com/docs/api-reference/responses",
    "Text generation": "https://platform.openai.com/docs/guides/text-generation",
    "Streaming": "https://platform.openai.com/docs/guides/streaming",
    "Function Calling": "https://platform.openai.com/docs/guides/function-calling",
    "Structured Outputs": "https://platform.openai.com/docs/guides/structured-outputs",
    "Conversation State": "https://platform.openai.com/docs/guides/conversation-state",
    "File Search": "https://platform.openai.com/docs/guides/tools-file-search",
    "Retrieval": "https://platform.openai.com/docs/guides/retrieval",
    "Embeddings": "https://platform.openai.com/docs/guides/embeddings",
    "Image Generation": "https://platform.openai.com/docs/guides/image-generation",
    "Audio and Speech": "https://platform.openai.com/docs/guides/audio",
    "Batch API": "https://platform.openai.com/docs/guides/batch",
    "Fine-tuning": "https://platform.openai.com/docs/guides/fine-tuning",
    "Agents SDK Overview": "https://openai.github.io/openai-agents-python/",
    "Agents SDK Quickstart": "https://openai.github.io/openai-agents-python/quickstart/",
    "Agents SDK Examples": "https://openai.github.io/openai-agents-python/examples/",
}

for title, url in official_links.items():
    print(f"- {title}: {url}")
```

| 参数 | 作用 | 是否必填 | 常用取值/示例 | 注意点 |
| --- | --- | --- | --- | --- |
| `title` | 资料名称 | 是 | `Responses API` | 用于快速定位 |
| `url` | 官方链接 | 是 | `https://...` | 链接可能随官方文档改版变化 |
| 资料类型 | 学习入口 | 否 | guide、reference、examples | guide 学概念，reference 查参数 |
| 更新策略 | 保持文档新鲜 | 否 | 定期复查 | 模型名和工具支持会变化 |

### 官方链接列表

- [OpenAI Libraries](https://platform.openai.com/docs/libraries)
- [Responses API](https://platform.openai.com/docs/api-reference/responses)
- [Text generation](https://platform.openai.com/docs/guides/text-generation)
- [Streaming](https://platform.openai.com/docs/guides/streaming)
- [Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [Conversation State](https://platform.openai.com/docs/guides/conversation-state)
- [File Search](https://platform.openai.com/docs/guides/tools-file-search)
- [Retrieval](https://platform.openai.com/docs/guides/retrieval)
- [Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Image Generation](https://platform.openai.com/docs/guides/image-generation)
- [Audio and Speech](https://platform.openai.com/docs/guides/audio)
- [Batch API](https://platform.openai.com/docs/guides/batch)
- [Fine-tuning](https://platform.openai.com/docs/guides/fine-tuning)
- [Agents SDK Overview](https://openai.github.io/openai-agents-python/)
- [Agents SDK Quickstart](https://openai.github.io/openai-agents-python/quickstart/)
- [Agents SDK Tools](https://openai.github.io/openai-agents-python/tools/)
- [Agents SDK Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Agents SDK Sessions](https://openai.github.io/openai-agents-python/sessions/)
- [Agents SDK Examples](https://openai.github.io/openai-agents-python/examples/)
