# Pencil MCP 接入说明

## 当前状态

这个仓库已经补齐了 Pencil 的项目内入口：

- 设计文件入口：`designs/paperchatagent-workbench.pen`
- 产品需求文档：`需求文档.md`、`requirements.md`

本机当前尚未检测到已安装并运行的 Pencil，因此还没有可直接连上的本地 Pencil MCP 服务。

## 官方接入方式

根据 Pencil 官方文档，Codex 的基础接入方式是：

1. 安装并启动 Pencil 桌面端，或在 Cursor / VS Code 中安装 Pencil 扩展
2. 在项目里打开 `.pen` 文件
3. 再打开 Codex
4. 在 Codex 中运行 `/mcp`
5. 确认 `Pencil` 出现在 MCP 列表中

官方说明的关键点：

- Pencil MCP 服务运行在本机，本地处理设计文件
- 对 Codex 的基础用法不需要手动写 MCP 配置
- Pencil 首次使用时可能会修改 `~/.codex/config.toml`

## 推荐接入流程

### 1. 安装 Pencil

推荐优先使用以下两种方式之一：

- macOS 桌面端
- Cursor 扩展

如果你希望我代你完成安装，需要你单独确认，因为这会在本机安装新软件。

### 2. 打开项目设计文件

在 Pencil 中打开：

`designs/paperchatagent-workbench.pen`

这个文件已经为 PaperChatAgent V1 准备了一个初始工作台草图，方便后续直接通过 MCP 让 AI 修改。

### 3. 验证 MCP

在 Codex 中进入本项目后执行：

```text
/mcp
```

预期结果：

- 列表中出现 `Pencil`

### 4. 开始联动

连通后，可以直接让 AI 在当前仓库里同时理解：

- PRD 文档
- `.pen` 设计文件
- 后续前端代码

例如：

```text
请根据需求文档，调整 paperchatagent-workbench.pen 的首页布局，做成左侧双区侧边栏 + 默认聊天主视图。
```

## 仓库内约定

- `designs/`：存放 Pencil 设计文件
- `docs/`：存放设计和接入说明
- `.pen` 文件应与 PRD 和前端代码一同放在仓库内，便于 AI 同时理解产品、设计和实现

## 后续建议

在 Pencil MCP 真正连通后，下一步最值得做的是：

1. 先完善工作台首页线框
2. 再补知识库、智能体、后台任务三个页面
3. 最后把页面结构映射到真实前端目录

