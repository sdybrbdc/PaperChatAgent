# Contributing

## 1. 目标

本文档定义 PaperChatAgent 的开发协作规范，重点覆盖：

- 分支策略
- 提交规范
- 合并规则
- 文档同步要求

当前仓库的默认原则是：

- `main` 保持稳定
- `develop` 作为当前开发主线
- 所有功能开发、修复和文档更新优先进入 `develop`
- **复查通过后才能合并到 `main`**

## 2. 分支策略

### 2.1 长期分支

- `main`
  - 只保留稳定、可回溯的版本
  - 不直接在 `main` 上开发
- `develop`
  - 当前开发阶段主分支
  - 所有日常功能集成都先进入这里

### 2.2 短期分支命名

从 `develop` 切出的常规分支：

- `feature/<name>`
  - 新功能开发
  - 示例：`feature/login-ui`
- `fix/<name>`
  - 功能缺陷修复
  - 示例：`fix/sidebar-scroll`
- `docs/<name>`
  - 文档更新
  - 示例：`docs/database-schema`
- `refactor/<name>`
  - 重构，不引入新功能
  - 示例：`refactor/chat-store`
- `chore/<name>`
  - 杂项维护、脚手架、依赖调整
  - 示例：`chore/vite-setup`

发布准备分支：

- `release/<version>`
  - 用于版本冻结、验收、发布前修正
  - 示例：`release/v0.1.0`

紧急修复分支：

- `hotfix/<name>`
  - 当 `main` 已发布且需要紧急修复时，从 `main` 切出
  - 修复后必须同时回合并到 `main` 和 `develop`

## 3. 推荐开发流程

### 3.1 功能开发

1. 从 `develop` 拉最新代码
2. 新建功能分支，例如：
   - `feature/chat-page`
3. 在功能分支开发
4. 本地自查通过后合并回 `develop`
5. `develop` 阶段复查通过后，再考虑合并到 `main`

### 3.2 修复问题

1. 从 `develop` 切 `fix/*`
2. 修复问题并验证
3. 合并回 `develop`

### 3.3 发布流程

1. 从 `develop` 切 `release/<version>`
2. 在 release 分支进行验收、文档校正和小修
3. 验收通过后合并到 `main`
4. 再把发布结果同步回 `develop`

### 3.4 紧急修复

1. 从 `main` 切 `hotfix/*`
2. 修复后先合并到 `main`
3. 再同步回 `develop`

## 4. 合并规则

### 4.1 合并到 `develop`

允许来源：

- `feature/*`
- `fix/*`
- `docs/*`
- `refactor/*`
- `chore/*`

要求：

- 代码或文档变更范围明确
- 本地构建通过
- 与当前技术文档一致

### 4.2 合并到 `main`

允许来源：

- `develop`
- `release/*`
- `hotfix/*`

要求：

- 已完成复查
- 核心功能可运行
- 文档已同步更新
- 没有明显的临时 mock 遗漏到稳定主线（除非当前阶段本来就是 mock 驱动）

**原则：未经复查，不直接合并到 `main`。**

## 5. 提交信息规范

建议使用 Conventional Commits 风格：

- `feat:`
- `fix:`
- `docs:`
- `refactor:`
- `chore:`
- `style:`
- `test:`

示例：

- `feat: add mock login and route guards`
- `fix: correct sidebar history scroll behavior`
- `docs: refine database schema and workflow details`
- `chore: initialize frontend foundation and project docs`

## 6. 开发前检查

提交前至少完成以下检查：

- 前端：
  - `pnpm build`
- 后端：
  - 相关测试或最小启动检查
- 文档：
  - 如果改了目录结构、模块职责或接口定义，相关文档必须同步更新

## 7. 文档同步要求

以下内容发生变化时，必须同步更新文档：

- 目录结构
- 模块职责
- 数据模型
- API 资源
- 工作流节点
- 设计稿主页面

重点同步文件：

- `README.md`
- `docs/architecture.md`
- `docs/technical-design.md`
- `docs/data-model.md`
- `docs/database-schema.md`
- `docs/dev-start.md`

如果改动了架构 tree：

- `README.md` 和 `docs/architecture.md` 两处必须同时更新

## 8. 当前阶段特别说明

当前阶段仍处于开发前期与前端第一阶段实现期，因此允许：

- mock 数据驱动页面
- 文档先行
- 设计稿与代码同步推进

但不允许：

- 在未复查情况下把实验性改动直接合到 `main`
- 改了实现却不更新文档
