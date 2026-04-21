# PaperChatAgent V1 Requirements Document

## 1. Project Overview

### 1.1 Background

Researchers and students usually go through several stages during paper research, including topic clarification, paper retrieval, material collection, content reading, viewpoint comparison, and result consolidation. Existing tools often solve only one part of this process, such as search, translation, summarization, or Q&A, but rarely provide a unified workspace for sustained topic-based research.

PaperChatAgent aims to become an intelligent paper research tool for researchers and students. It uses conversation as the entry point, the research workspace as the persistent container, and the research task as the execution unit, helping users continuously explore a topic, organize topic-level corpora, and conduct citation-grounded Q&A.

### 1.2 Problem Statement

Common pain points in paper research include:

- Users often cannot clearly define their research question at the beginning and need iterative discussion before the scope becomes actionable.
- Search, upload, reading, note-taking, and follow-up questioning are usually split across different tools.
- Research context is difficult to preserve over time, and historical conversations are not stably linked to materials.
- Answers about papers often lack clear sources and are therefore hard to trust in research and writing scenarios.

### 1.3 Product Goals

The goals of PaperChatAgent V1 are:

- Provide a chat-first research workbench for paper exploration.
- Let users clarify research needs through conversation and upload papers or related materials during the discussion.
- Allow AI to propose a research task once the direction is sufficiently clear, then let the user confirm it and create a research workspace.
- Turn external search results and uploaded materials into reusable topic-level research context.
- Deliver follow-up Q&A with explicit citation evidence instead of source-free summaries.

### 1.4 V1 Positioning

PaperChatAgent V1 is a paper Q&A assistant built on top of topic-level corpora. It is not a formal survey report generator. Its first responsibility is to solve the loop of topic clarification, topic exploration, material consolidation, and grounded Q&A.

## 2. Target Users And Scenarios

### 2.1 Target Users

The primary users of V1 are graduate students and PhD students. It may also serve research engineers and advanced undergraduate users with paper research needs.

### 2.2 Core Scenarios

- Topic exploration: the user has not fully decided on a research direction and wants to discuss and narrow the scope with AI.
- Topic research: the user wants to collect papers, compare viewpoints, and build an understanding of one research theme.
- Paper understanding: the user uploads one or more papers and expects the system to help read, summarize, and answer questions.
- Continued follow-up: the user wants repeated Q&A on top of an existing research context rather than restarting from scratch each time.

### 2.3 User Value

- Lower the cost of starting research by helping users move from vague intent to a usable research workspace.
- Improve research organization by unifying chat, papers, tasks, and results inside one workbench.
- Improve trustworthiness by attaching citation evidence to answers.

## 3. Product Information Architecture

### 3.1 Overall Structure

V1 uses a login-based workbench structure. After login, the default landing page is the chat page. The overall interface includes:

- Top-level access: login and registration
- Main workbench: default chat home
- Upper section of the left sidebar: feature navigation
- Lower section of the left sidebar: conversation history grouped by workspace, with an interaction style inspired by Codex

### 3.2 Feature Navigation

The upper section of the sidebar includes:

- Chat
- Knowledge Base
- MCP Services
- Skills
- Agents
- Background Tasks
- Dashboard

Modules that are part of the V1 core flow:

- Chat
- Knowledge Base
- Agents
- Background Tasks
- Dashboard

Modules that are only reserved in V1:

- MCP Services
- Skills

### 3.3 Core Object Definitions

To keep the product model consistent, V1 uses the following objects:

- `User`: a logged-in PaperChatAgent user
- `Default inbox conversation`: the initial chat thread used for need clarification before a workspace exists
- `Research workspace`: a long-lived space for one research topic, organizing conversations, tasks, knowledge, and results
- `Research task`: an asynchronous workflow triggered after user confirmation, covering retrieval, parsing, indexing, topic exploration, and result generation
- `Global knowledge base`: the account-level reusable paper and material collection shared across that user's workspaces
- `Workspace private knowledge base`: a topic-specific supplemental material collection limited to one workspace
- `Topic exploration package`: the reusable research context produced by a completed research task, including paper sets and structured analysis
- `Preset research agent`: a system-provided research workflow agent and its orchestration view
- `Citation evidence`: the source information attached to answers, shown at paper level by default and optionally at finer granularity

### 3.4 Core Object Relationships

- The first conversation exists inside the `default inbox conversation`.
- Once the topic becomes clear enough, the `default inbox conversation` can become part of a `research workspace` context.
- The knowledge model is `account-level global library + workspace private supplement`.
- A completed `research task` produces a `topic exploration package`, which then flows back into the chat experience for continued Q&A.

## 4. Core Business Flow

The V1 core business flow is:

`Login -> Default chat -> Clarify need / upload materials -> AI proposes research task -> User confirms -> Create workspace -> Run in background -> Feed results back into Q&A`

### 4.1 Detailed Flow

1. The user logs in or registers and lands on the default chat page.
2. The system opens or creates the user's `default inbox conversation`.
3. The user discusses a research topic and may upload PDF papers or related materials.
4. AI helps narrow the research direction, keywords, question boundaries, and material scope.
5. Once the direction is actionable, AI proposes a research task.
6. The user reviews a lightweight confirmation panel and may adjust topic, keywords, time range, sources, and uploaded materials.
7. After confirmation, the system creates a `research workspace` and the corresponding `research task`.
8. The background task asynchronously performs retrieval, parsing, knowledge ingestion, and topic exploration.
9. The output is stored as a `topic exploration package`, then fed back into the chat as reusable research context.
10. The user continues asking questions inside the workspace while viewing tasks, materials, and grouped history.

## 5. Functional Requirements

### 5.1 Login And Registration

#### User Value

Provide the identity foundation required to persist conversations, knowledge, and workspaces.

#### Page Responsibility

- Provide login and registration pages
- Support email-and-password authentication

#### Core Behaviors

- Users can register with email and password
- Users can log in with email and password
- After login, users enter the default chat page

#### Boundaries

- V1 does not require third-party login
- V1 does not require a complex role model
- All logged-in users have the same functional permissions

### 5.2 Chat Home And Default Inbox Conversation

#### User Value

Allow users to start with a conversation before creating any project or workspace.

#### Page Responsibility

- Act as the default post-login home
- Handle need clarification, material upload, topic alignment, and task proposal

#### Core Behaviors

- The system opens the `default inbox conversation` by default
- Users can discuss research direction in multiple turns
- Users can upload PDFs or research materials inside chat
- AI can propose the next research task based on the conversation
- Before a workspace exists, the conversation remains inside the default inbox thread

#### Boundaries

- The chat home is not a final report page
- No formal workspace is created until the user confirms the task

### 5.3 Research Workspace

#### User Value

Provide a stable space for long-term accumulation around a research topic.

#### Page Responsibility

- Organize conversations, tasks, knowledge, and results around one topic
- Receive context promoted from the default inbox conversation

#### Core Behaviors

- A workspace is automatically created once the user confirms a research task
- The workspace contains topic-related conversations, tasks, and result assets
- History is grouped by workspace for fast return to an older topic
- The workspace supports read-only sharing links

#### Boundaries

- V1 does not support collaborative editing
- V1 does not support complex team permissions

### 5.4 Knowledge Base

#### User Value

Help users manage papers and research materials in one place and connect them to the research process.

#### Page Responsibility

- Manage both the account-level global library and workspace private knowledge bases
- Provide upload, browsing, attachment, and reuse capabilities

#### Core Behaviors

- Users can upload PDF files
- The system can ingest papers from arXiv
- The account-level global library can be reused across workspaces
- Workspace private libraries can hold topic-specific supplements
- Users can attach materials to workspaces or research tasks

#### Boundaries

- V1 does not include a heavy manual annotation editor
- The knowledge base is not the primary research entry point; chat remains the entry point

### 5.5 Agents Page

#### User Value

Help users understand how the system executes a research task through multiple staged agents and workflow nodes.

#### Page Responsibility

- Display the preset research agents and the research workflow orchestration view
- Show the role, order, and status of major workflow nodes

#### Core Behaviors

- The page uses the six-node Paper-Agent workflow as the orchestration blueprint
- Users can inspect node responsibility and execution status
- Users primarily use preset research agents instead of freely building complex agents in V1

#### Boundaries

- V1 does not treat the agents page as a full configuration center
- V1 does not promise formal survey report generation
- Report-related nodes are shown only as part of the long-term workflow blueprint, not as V1 deliverables

### 5.6 Background Tasks

#### User Value

Move long-running research work out of the chat loop and keep the interaction responsive.

#### Page Responsibility

- Display research task status, progress, and result summary
- Serve as the execution module for confirmed research workflows

#### Core Behaviors

- After AI proposes a research task, the user can start it from a lightweight confirmation panel
- Tasks run asynchronously and cover retrieval, download, parsing, indexing, and topic exploration
- Users can inspect queued, running, completed, and failed states
- Task results are fed back into both chat and workspace

#### Boundaries

- V1 background tasks focus on research workflows, not scheduled subscriptions or system maintenance jobs
- V1 does not require a complex visual workflow editor

### 5.7 Dashboard

#### User Value

Expose lightweight system-level operating metrics inside the main workbench.

#### Page Responsibility

- Live in the main sidebar as a visible module
- Show system operation indicators

#### Core Behaviors

- Show system-level indicators such as task volume, status distribution, activity, or similar platform metrics
- Remain part of the main workbench rather than a separate admin console

#### Boundaries

- V1 does not split out a dedicated admin backend
- V1 dashboard is primarily read-only

### 5.8 MCP Services / Skills Reservation

#### User Value

Reserve product space for future tool integration and skill-based enhancement.

#### Page Responsibility

- Provide navigation entries for MCP Services and Skills
- Reserve future configuration surfaces

#### Core Behaviors

- V1 provides basic pages or placeholders
- These modules do not participate in the core research loop

#### Boundaries

- V1 does not require real MCP integration
- V1 does not require Skills to drive research tasks

## 6. Data And System Constraints

### 6.1 Technical Baseline

The V1 technical baseline is:

- Frontend: Vue 3 + Vite
- Workflow orchestration: LangGraph
- Relational data: MySQL
- Vector retrieval: ChromaDB
- Asynchronous tasks: Redis queue + Worker
- Object storage: MinIO

### 6.2 System Design Constraints

- The system follows a multi-stage research flow, but V1 focuses on topic exploration and grounded Q&A.
- LangGraph is the primary orchestration framework for preset research agents.
- MinIO is the unified object storage layer for uploaded files, source papers, and durable generated artifacts.
- MySQL stores structured product data such as users, conversations, workspaces, tasks, and knowledge relations.
- ChromaDB stores topic-level vector indexes for retrieval.
- Redis Worker executes long-running research tasks.

### 6.3 Source Constraints

- V1 supports only arXiv and user-uploaded PDF files as input sources.
- Paper processing follows an `abstract first, full text when available` strategy.

### 6.4 Citation Constraints

- All research answers must include `citation evidence`
- The default citation view is paper-level
- If the parsing result supports it, finer-grained evidence such as paragraph or segment references may be shown

## 7. Non-Functional Requirements

### 7.1 Performance And Responsiveness

- Default chat should remain continuously usable
- Long-running research jobs must execute asynchronously with visible progress

### 7.2 Traceability

- Every research answer should be traceable to source papers or materials
- Users should be able to understand which tasks and materials produced a given topic exploration package

### 7.3 Usability

- Users should be able to enter chat immediately after login without understanding the full system first
- The transition from chat to workspace should feel natural and low-friction

### 7.4 Permission Boundaries

- All logged-in users share the same feature permissions in V1
- Workspaces and private materials are private by default
- External sharing is read-only

## 8. V1 Non-Goals

The following are explicitly out of scope for V1:

- Third-party platform integrations such as Feishu, Slack, or Enterprise WeChat
- Formal survey report generation and export
- Multi-user collaborative workspace editing
- Deep integration of MCP Services and Skills into the core research loop
- Complex admin consoles and multi-role permission systems
- Advanced manual annotation, snippet refinement, or deep knowledge operations tooling

## 9. Acceptance Criteria

### 9.1 Login And Registration

- Users can register and log in with email and password
- Successful login lands on the default chat page

### 9.2 Default Chat Page

- The system creates or opens the default inbox conversation
- Users can upload PDFs inside chat and continue the conversation
- AI can propose a research task once the topic becomes sufficiently clear

### 9.3 Workspace

- The system creates a research workspace after task confirmation
- History is grouped by workspace
- Workspaces support read-only sharing links

### 9.4 Knowledge Base

- Users can manage both the account-level global library and workspace private libraries
- Materials can come from arXiv or user upload
- Materials can be attached to workspaces or research tasks

### 9.5 Agents

- The page displays the orchestration view of the six-node Paper-Agent workflow
- Users can see node responsibilities and states

### 9.6 Background Tasks

- Users can start a research task from a lightweight confirmation panel
- Tasks support at least queued, running, completed, and failed states
- Task outputs flow back into chat and workspace

### 9.7 Dashboard

- The dashboard is accessible from the main sidebar
- The dashboard shows basic system operating metrics

### 9.8 MCP Services / Skills

- Both modules exist in navigation
- They provide placeholder or reserved configuration pages without blocking the core loop

### 9.9 Q&A And Citations

- A completed research task produces a reusable topic exploration package
- Follow-up answers must include citation evidence

## 10. Future Directions

After V1, the product may expand to:

- Survey report generation
- Third-party platform integrations
- Deeper MCP / Skills integration
- Stronger collaboration capabilities

