# PaperChatAgent V1 Requirements

## 1. Project Overview

### 1.1 Background

Researchers usually move back and forth between topic clarification, paper collection, reading, repeated Q&A, and result consolidation. Most existing tools only solve one part of this loop. They may be good at search, summarization, translation, or chat, but they rarely provide a chat-first product that naturally connects materials, tools, and long-running research workflows.

PaperChatAgent V1 is designed as a chat-first research assistant. Users start from conversation, clarify the topic, upload or collect materials, let the model decide when retrieval or tool use is needed, and observe long-running research execution through a dedicated task view.

### 1.2 Problem Statement

Common pain points include:

- Users often begin with vague research intent and need multiple rounds of discussion before the topic becomes actionable.
- Documents, search results, Q&A history, and conclusions are scattered across different tools.
- Historical context and uploaded materials are not stably connected.
- Model answers often lack retrieval grounding or citation evidence.
- Multi-step research execution is opaque and difficult to monitor.

### 1.3 Product Goals

PaperChatAgent V1 aims to:

- Provide a GPT-like chat-first research experience.
- Let users clarify research goals, upload documents, and continue asking follow-up questions in chat.
- Treat the knowledge base as an independent module for parsing, chunking, vectorization, and retrieval sources.
- Treat agents as an independent module for extensible research workflows.
- Let the model decide during chat whether it should retrieve from the knowledge base or call agents, MCP services, or Skills.
- Show async agent/workflow progress in the background task module after the topic has been confirmed.

### 1.4 V1 Positioning

PaperChatAgent V1 is a chat-first research assistant. It is not a formal survey-report platform and not a knowledge-operations tool.

Its primary loop is:

`chat clarification -> material grounding -> autonomous retrieval/tool use -> async research execution -> answer back in chat`

## 2. Target Users And Scenarios

### 2.1 Target Users

V1 primarily serves:

- graduate students
- PhD students
- research engineers who need paper research support
- advanced undergraduates working on research projects or theses

### 2.2 Core Scenarios

- `Topic exploration`: the user has not fully decided on a direction and wants AI to help narrow it down.
- `Paper understanding`: the user uploads one or more papers and wants help reading, summarizing, and questioning them.
- `Ongoing topic research`: the user keeps collecting materials and asking questions on top of an evolving knowledge context.
- `Workflow execution`: the user confirms a topic and wants the system to run async research steps while exposing progress.

### 2.3 User Value

- Lower the cost of getting started with research.
- Keep conversations, materials, tools, and workflow execution in one product.
- Improve trustworthiness by grounding answers in retrieved materials when needed.
- Improve transparency by exposing workflow progress in the background task page.

## 3. Product Information Architecture

### 3.1 Overall Structure

V1 uses a login-based application structure with chat as the default landing page. Chat is the only primary entry. Other modules act as capability, configuration, or observability layers.

The main interface includes:

- top-level entry: login and registration
- main content: chat page
- left navigation: module navigation
- recent-history area: chat session list

### 3.2 Module Navigation

The main navigation is:

- Chat
- Knowledge Base
- Agents
- MCP Services
- Skills
- Models
- Background Tasks
- Dashboard

Role of each module:

- `Chat`: primary user flow
- `Knowledge Base`: material parsing and retrieval-source management
- `Agents`: built-in workflows and future extensions
- `MCP Services`: external tool configuration
- `Skills`: skill configuration
- `Models`: model configuration and routing
- `Background Tasks`: async agent/workflow progress monitoring
- `Dashboard`: system observability

### 3.3 Core Objects

PaperChatAgent V1 uses the following core objects:

- `User`: a logged-in user
- `ChatSession`: the primary long-lived object used by the user
- `Message`: one message in a chat session
- `KnowledgeBase`: a container for files, parsed content, and retrieval sources
- `KnowledgeFile`: one uploaded or imported document inside a knowledge base
- `ResearchTask`: an async task triggered after topic confirmation
- `WorkflowRun`: one actual execution of an agent workflow
- `WorkflowNodeRun`: one node-level execution record inside a workflow run
- `AgentWorkflow`: a built-in or future extensible workflow definition
- `McpServerConfig`: one MCP server configuration
- `SkillConfig`: one Skill configuration
- `ModelRouteConfig`: model-slot and provider routing configuration
- `DashboardMetric`: one system-level observable metric

### 3.4 Core Relationships

- Chat happens inside `ChatSession`.
- `KnowledgeBase` is independent, but it can be queried from chat when the model decides retrieval is needed.
- Users may upload materials in chat and bind them to an existing or newly created knowledge base.
- Once the topic is actionable, chat can trigger `ResearchTask`.
- `ResearchTask` creates a `WorkflowRun`, and the background task page shows node-level progress.
- Agents, MCP services, and Skills can all appear as callable capabilities during chat.

## 4. Core User Flow

The V1 primary flow is:

`login -> chat -> clarify topic / upload materials -> bind or create a knowledge base -> model decides whether retrieval or tool use is needed -> confirm topic -> trigger background task -> monitor agent progress -> continue in chat`

### 4.1 Detailed Flow

1. The user logs in and enters the chat page.
2. The system opens the latest session or creates the first one.
3. The user describes the research goal and may upload PDFs or related materials.
4. The system helps clarify the topic, keywords, boundaries, and expected output.
5. If materials are uploaded, the system lets the user bind them to an existing knowledge base or create a new one. The name may be user-defined or AI-suggested.
6. During chat, the model may decide whether it should retrieve from the knowledge base or call agents, MCP services, or Skills.
7. Once the topic is clear enough, the system triggers research-task confirmation.
8. The background task runs asynchronously and exposes workflow-node progress.
9. Results, summaries, and findings are fed back into chat for continued questioning.

## 5. Functional Requirements

### 5.1 Login And Registration

- Email/password registration and login
- Successful login lands on the chat page
- No third-party login is required in V1

### 5.2 Chat

- Chat is the default post-login entry
- Users can create and switch chat sessions
- A session may begin as ordinary exploration and later transition into deeper research
- Users can clarify research goals, upload materials, and continue asking follow-up questions
- The chat page can surface dynamic research guidance based on the current conversation state
- When enough information is available, the chat page can synthesize a research draft from the live conversation
- The model can decide whether to retrieve from the knowledge base
- The model can call agents, MCP services, or Skills when appropriate
- Confirmed topics can trigger research tasks
- Completed task output returns to chat

### 5.3 Knowledge Base

- Users can create knowledge bases and upload documents
- Knowledge bases are presented as a named list rather than workspace-based buckets
- Users can click a knowledge base to enter a detail page that shows files and processing status
- The system may also suggest creating a knowledge base during chat
- Files move through parsing, chunking, vectorization, and indexing stages
- The knowledge base is not the primary entry point; it mainly supports chat-time retrieval

### 5.4 Agents

- The module provides an agent list page and an agent detail page
- Built-in agents, custom agents, and project sub-agents can all appear in the list
- In the detail view, each node can be configured with a model slot or another agent executor
- A node may route its output into a general model or into another custom or project agent
- Future workflows and agents can be added later

### 5.5 MCP Services

- Show configured MCP services in a list
- Support importing local MCP services
- Support adding new MCP service configurations

### 5.6 Skills

- Show configured Skills in a list
- Support importing local Skills
- Support adding custom Skills

### 5.7 Models

- Show logical model slots and provider configuration
- Support routing across slots such as `conversation`, `tool_call`, `reasoning`, `embedding`, and `rerank`
- Treat the model layer as configuration and routing infrastructure, not a research entry point

### 5.8 Background Tasks

- Trigger async research tasks after topic confirmation
- Show task list, workflow status, current node, node progress, and result summary
- Keep the page focused on monitoring agent/workflow execution, not generic task administration

### 5.9 Dashboard

- Show model call counts, input/output volume, task distribution, and other basic metrics
- Act as a lightweight observability module rather than a full BI backend

## 6. System Constraints

- Chat is the only primary user flow.
- Knowledge base, agents, MCP services, Skills, models, background tasks, and dashboard are independent modules.
- The model decides during chat whether retrieval or tool use is necessary.
- Background tasks focus on exposing agent/workflow progress.

## 7. Non-Functional Requirements

- Chat should remain responsive even when long-running work exists.
- Async workflow execution must be observable from the task page.
- Retrieved answers and task outputs should remain traceable to sessions, materials, or workflow runs.
- Agents, MCP services, Skills, and model routing should all remain extensible.

## 8. V1 Non-Goals

- formal survey-report platform delivery
- multi-user collaborative editing
- advanced permissions and role systems
- heavy knowledge-operations tooling
- free-form agent orchestration builders
- full business-intelligence backends

## 9. Acceptance Criteria

- Users can register and log in with email and password.
- Users land on chat after login.
- Users can create and use chat sessions.
- Users can upload materials and bind them to knowledge bases.
- The knowledge-base module exposes parsing and indexing status.
- The agents module exposes the built-in research workflow.
- MCP services and Skills can be listed and configured.
- The model module can express model-slot routing.
- Background tasks can display agent/workflow progress.
- The dashboard can show model-call and task-distribution metrics.

## 10. UI Mapping

### 10.1 Global Workbench Layout

- After login, the product uses a consistent `left navigation + right main view` workbench layout.
- The left navigation must include `Chat / Knowledge Base / MCP Services / Skills / Agents / Models / Background Tasks / Dashboard`.
- Chat, Knowledge Base, and Agents keep a recent-session area to support context switching in the primary research flow.
- Agents, Models, MCP Services, Skills, Background Tasks, and Dashboard use a `main content area + auxiliary detail cards` structure to emphasize workflow explanation, configuration, or observability.
- The overall visual language stays as a light productivity workbench rather than a marketing or landing-page presentation.

### 10.2 Page-Level UI Coverage

- `Login`: brand explainer panel plus login form
- `Register`: account-value explainer panel plus registration form
- `Chat`: conversation stream, upload entry, dynamic research guidance rail, and bottom composer
- `Knowledge Base List`: named knowledge-base list with creation and upload entry points
- `Knowledge Base Detail`: file list, parsing status, and index configuration for a selected knowledge base
- `MCP Services`: service health, connection list, exposed capabilities, and connection detail
- `Skills`: skill inventory, enablement state, I/O summary, and usage scenarios
- `Agents List`: built-in, custom, and project-agent inventory
- `Agents Detail`: node graph, node-level executor configuration, and handoff rules
- `Models`: logical model slots, provider settings, and routing or fallback strategy
- `Background Tasks`: task metrics, task list, node progress, and output summary
- `Dashboard`: model-call metrics, token volume, task distribution, and recent system events

### 10.3 Design Constraints

- Navigation must stay consistent across all workbench pages so module entry points never disappear.
- `Models` must appear as a first-class navigation item instead of an implicit config surface.
- `MCP Services` and `Skills` should no longer appear as reserved placeholders; they need complete configuration-page structure.
- Knowledge Base and Agents should each be represented as a two-level prototype: list page plus detail page.
- The chat right rail should be a dynamic research-guidance surface rather than a fixed inbox or workspace confirmation panel.
- Background Tasks and Dashboard must remain visually distinct: the first focuses on workflow execution, the second on system-level observability.
