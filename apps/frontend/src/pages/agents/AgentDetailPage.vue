<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Back,
  ChatDotRound,
  Check,
  Collection,
  Cpu,
  DataAnalysis,
  FullScreen,
  Minus,
  More,
  Plus,
  Reading,
  Search,
  VideoPlay,
} from '@element-plus/icons-vue'
import type { AgentWorkflowNodeDTO } from '../../types/agents'
import { useAgentsStore } from '../../stores/agents'

const DEFAULT_RUN_TOPIC = '梳理当前研究方向的代表论文、主题结构与趋势'
const WORKFLOW_DISPLAY_NAMES: Record<string, string> = {
  smart_research_assistant: 'Research Orchestrator',
}

const NODE_DISPLAY_OVERRIDES: Record<
  string,
  {
    title?: string
    summary?: string
    chipLabel?: string
    handoffRule?: string
    routeLabel?: string
    upstream?: string
    downstream?: string
  }
> = {
  search: {
    title: '搜索节点',
    summary: '召回候选论文与来源线索',
    chipLabel: 'Search',
  },
  reading: {
    title: '阅读节点',
    summary: '抽取结构化摘要与证据片段',
    chipLabel: 'Reading',
  },
  analyse: {
    title: '分析节点',
    summary: '聚合阅读结果，并调度子节点完成主题归并、候选整理与结果复核。',
    chipLabel: 'Cluster',
    handoffRule:
      '上一节点摘要、候选文献和引用线索会先进入分析节点。分析阶段会调度子节点完成聚类、候选整理和结果复核，随后把主题结论传递给引用节点。',
    routeLabel: '阅读输出 → 分析分支 → 引用节点',
    upstream: '阅读节点输出',
    downstream: '引用节点',
  },
  'analyse.cluster': {
    title: '主题聚类',
    summary: '按研究主题归并论文集合',
  },
  'analyse.deep_analyse': {
    title: '候选整理',
    summary: '清洗候选输入并生成主题分析',
  },
  'analyse.global_analyse': {
    title: '结果复核',
    summary: '汇总热点、趋势和建议',
  },
  writing: {
    title: '引用节点',
    summary: '补齐引用候选与章节证据',
    chipLabel: 'Citation',
    routeLabel: '分析输出 → 引用增强 → 回答节点',
    upstream: '分析节点输出',
    downstream: '回答节点',
  },
  report: {
    title: '回答节点',
    summary: '生成最终研究回答与报告产物',
    chipLabel: 'Answer',
  },
}

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

const CANVAS_BASE_WIDTH = 1180
const CANVAS_BASE_HEIGHT = 520
const MIN_CANVAS_ZOOM = 60
const MAX_CANVAS_ZOOM = 160

const workflowId = computed(() => String(route.params.workflowId ?? ''))
const executorKey = ref('')
const fallbackExecutorKey = ref('')
const modelSlot = ref('conversation_model')
const flowZoom = ref(100)
const canvasViewportRef = ref<HTMLElement | null>(null)
const isCanvasDragging = ref(false)
const canvasPanState = ref({
  startX: 0,
  startY: 0,
  scrollLeft: 0,
  scrollTop: 0,
})

const workflowNodes = computed(() => agentsStore.currentWorkflow?.nodes ?? [])
const selectedNode = computed(() => agentsStore.selectedNode)
const canvasNodes = computed(() => {
  const order = ['search', 'reading', 'analyse', 'writing', 'report']
  return order
    .map((id) => workflowNodes.value.find((node) => node.id === id))
    .filter((node): node is AgentWorkflowNodeDTO => Boolean(node))
})
const selectedGroupNode = computed(() => {
  const node = selectedNode.value
  if (!node) return null
  if (node.parentNodeId) {
    return workflowNodes.value.find((item) => item.id === node.parentNodeId) ?? null
  }
  return node.subNodes.length ? node : null
})
const activeGroupNode = computed(() => {
  return selectedGroupNode.value ?? workflowNodes.value.find((node) => node.id === 'analyse' && node.subNodes.length) ?? null
})
const subFlowNodes = computed(() => activeGroupNode.value?.subNodes ?? [])
const analysisSubNodeCount = computed(() => workflowNodes.value.find((node) => node.id === 'analyse')?.subNodes.length ?? 0)

const workflowDisplayName = computed(() => {
  const workflow = agentsStore.currentWorkflow
  if (!workflow) return '加载中'
  return WORKFLOW_DISPLAY_NAMES[workflow.slug] ?? workflow.name
})

const workflowMeta = computed(
  () => `${canvasNodes.value.length} 个主节点 · ${analysisSubNodeCount.value} 个分析子节点 · 顺序研究工作流`,
)

const selectedNodeDisplay = computed(() => describeSelectedNode(selectedNode.value))
const selectedNodeIndex = computed(() => {
  const node = selectedNode.value
  if (!node) return -1
  const lookupId = node.parentNodeId || node.id
  return canvasNodes.value.findIndex((item) => item.id === lookupId)
})
const selectedConfigRows = computed(() => {
  const node = selectedNode.value
  const config = node?.config ?? {}
  return [
    ['执行顺序', selectedNodeIndex.value >= 0 ? `${selectedNodeIndex.value + 1}/${canvasNodes.value.length}` : '-'],
    ['超时时间', formatConfigValue(config.timeout_seconds ?? config.timeoutSeconds, '120 秒')],
    ['最大重试', `${formatConfigValue(config.max_retries ?? config.maxRetries, 2)} 次`],
    ['失败策略', formatConfigValue(config.failure_strategy ?? config.failureStrategy, '跳过并继续')],
  ]
})
const canvasStageFrameStyle = computed(() => {
  const scale = flowZoom.value / 100
  return {
    width: `${CANVAS_BASE_WIDTH * scale}px`,
    height: `${CANVAS_BASE_HEIGHT * scale}px`,
  }
})
const canvasStageContentStyle = computed(() => ({
  width: `${CANVAS_BASE_WIDTH}px`,
  height: `${CANVAS_BASE_HEIGHT}px`,
  transform: `scale(${flowZoom.value / 100})`,
}))

watch(
  workflowId,
  (value) => {
    if (value) {
      agentsStore.loadWorkflow(value)
    }
  },
  { immediate: true },
)

watch(
  [workflowNodes, () => agentsStore.selectedNodeId],
  ([nodes, selectedId]) => {
    if (nodes.length && !selectedId) {
      const preferred = nodes.find((node) => node.id === 'analyse') ?? nodes[0]
      agentsStore.selectNode(preferred.id)
    }
  },
  { immediate: true },
)

watch(
  selectedNode,
  (node) => {
    executorKey.value = node?.executorKey ?? ''
    fallbackExecutorKey.value = node?.fallbackExecutorKey ?? ''
    modelSlot.value = node?.modelSlot ?? 'conversation_model'
  },
  { immediate: true },
)

watch(
  canvasNodes,
  (nodes) => {
    if (nodes.length) {
      nextTick(fitCanvas)
    }
  },
  { immediate: true },
)

function resolveNodeDisplay(node: AgentWorkflowNodeDTO | null | undefined) {
  if (!node) {
    return {
      title: '未命名节点',
      summary: '暂无节点说明',
      chipLabel: '',
      handoffRule: '',
      routeLabel: '',
      upstream: '',
      downstream: '',
    }
  }
  const override = NODE_DISPLAY_OVERRIDES[node.id] ?? {}
  return {
    title: override.title ?? node.title,
    summary: override.summary ?? node.description ?? '处理上游结果并传递给下一阶段。',
    chipLabel: override.chipLabel ?? node.executorKey,
    handoffRule: override.handoffRule ?? node.handoffRule,
    routeLabel: override.routeLabel ?? '',
    upstream: override.upstream ?? node.inputSource,
    downstream: override.downstream ?? node.outputTarget,
  }
}

function describeSelectedNode(node: AgentWorkflowNodeDTO | null) {
  if (!node) {
    return {
      title: '未选中节点',
      summary: '选择一个节点后，在这里编辑执行配置。',
      handoffRule: '选择节点后，可查看该节点如何接收上游输入并传递到下游。',
      routeLabel: '',
      upstream: '待选择节点',
      downstream: '待选择节点',
    }
  }
  const override = NODE_DISPLAY_OVERRIDES[node.id] ?? {}
  return {
    title: override.title ?? node.title,
    summary: override.summary ?? node.description ?? '处理上游结果并传递给下一阶段。',
    handoffRule: override.handoffRule ?? node.handoffRule ?? node.description ?? '上一节点输出会继续传递给下游节点。',
    routeLabel: override.routeLabel ?? '',
    upstream: pickText(override.upstream, node.inputSource, '待上游输入'),
    downstream: pickText(override.downstream, node.outputTarget, '等待后续节点'),
  }
}

function nodeIcon(nodeId: string) {
  if (nodeId === 'search') return Search
  if (nodeId === 'reading') return Reading
  if (nodeId === 'analyse') return DataAnalysis
  if (nodeId === 'writing') return Collection
  if (nodeId === 'report') return ChatDotRound
  return Cpu
}

function isSelected(nodeId: string) {
  return agentsStore.selectedNodeId === nodeId
}

function isInSelectedGroup(nodeId: string) {
  return activeGroupNode.value?.id === nodeId
}

function stepNumber(index: number) {
  return String(index + 1).padStart(2, '0')
}

function subStepNumber(index: number) {
  return `A${index + 1}`
}

function pickText(...values: Array<string | undefined>) {
  for (const value of values) {
    if (value && value.trim()) return value
  }
  return ''
}

function formatConfigValue(value: unknown, fallback: string | number) {
  if (value === null || value === undefined || value === '') return String(fallback)
  return String(value)
}

function nodeTypeLabel(node: AgentWorkflowNodeDTO | null) {
  if (!node) return '-'
  if (node.parentNodeId) return '子 Agent 节点'
  if (node.subNodes.length) return '主流程 / 子 Agent 调度'
  return '主流程节点'
}

function setZoom(nextValue: number) {
  const viewport = canvasViewportRef.value
  const previousScale = flowZoom.value / 100
  const nextZoom = clampZoom(nextValue)
  const nextScale = nextZoom / 100
  const centerPoint = viewport
    ? {
        x: (viewport.scrollLeft + viewport.clientWidth / 2) / previousScale,
        y: (viewport.scrollTop + viewport.clientHeight / 2) / previousScale,
      }
    : null

  flowZoom.value = nextZoom

  if (viewport && centerPoint) {
    nextTick(() => {
      viewport.scrollLeft = centerPoint.x * nextScale - viewport.clientWidth / 2
      viewport.scrollTop = centerPoint.y * nextScale - viewport.clientHeight / 2
    })
  }
}

function fitCanvas() {
  const viewport = canvasViewportRef.value
  if (!viewport) {
    flowZoom.value = 100
    return
  }
  const widthScale = (viewport.clientWidth - 48) / CANVAS_BASE_WIDTH
  const heightScale = (viewport.clientHeight - 48) / CANVAS_BASE_HEIGHT
  const fitZoom = Math.floor(Math.min(widthScale, heightScale, 1) * 100)
  flowZoom.value = clampZoom(fitZoom)
  nextTick(centerCanvas)
}

function centerCanvas() {
  const viewport = canvasViewportRef.value
  if (!viewport) return
  viewport.scrollLeft = Math.max((viewport.scrollWidth - viewport.clientWidth) / 2, 0)
  viewport.scrollTop = Math.max((viewport.scrollHeight - viewport.clientHeight) / 2, 0)
}

function clampZoom(value: number) {
  return Math.min(MAX_CANVAS_ZOOM, Math.max(MIN_CANVAS_ZOOM, value))
}

function handleCanvasWheel(event: WheelEvent) {
  if (!event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  setZoom(flowZoom.value + (event.deltaY < 0 ? 10 : -10))
}

function startCanvasPan(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest('button, .el-button, input, textarea, .el-select, .el-input')) return
  const viewport = canvasViewportRef.value
  if (!viewport) return
  isCanvasDragging.value = true
  canvasPanState.value = {
    startX: event.clientX,
    startY: event.clientY,
    scrollLeft: viewport.scrollLeft,
    scrollTop: viewport.scrollTop,
  }
  viewport.setPointerCapture(event.pointerId)
}

function moveCanvasPan(event: PointerEvent) {
  const viewport = canvasViewportRef.value
  if (!viewport || !isCanvasDragging.value) return
  viewport.scrollLeft = canvasPanState.value.scrollLeft - (event.clientX - canvasPanState.value.startX)
  viewport.scrollTop = canvasPanState.value.scrollTop - (event.clientY - canvasPanState.value.startY)
}

function stopCanvasPan(event: PointerEvent) {
  if (!isCanvasDragging.value) return
  isCanvasDragging.value = false
  const viewport = canvasViewportRef.value
  if (viewport?.hasPointerCapture(event.pointerId)) {
    viewport.releasePointerCapture(event.pointerId)
  }
}

async function saveNodeConfig() {
  if (!selectedNode.value) {
    ElMessage.warning('请先选择一个节点')
    return
  }
  await agentsStore.saveSelectedNodeConfig({
    executorKey: executorKey.value,
    fallbackExecutorKey: fallbackExecutorKey.value,
    modelSlot: modelSlot.value,
    config: {},
  })
  ElMessage.success('节点配置已保存')
}

async function startRun() {
  const run = await agentsStore.startRun(workflowId.value, DEFAULT_RUN_TOPIC)
  ElMessage.success('智能体任务已创建')
  router.push(`/agents/runs/${run.id}`)
}
</script>

<template>
  <div class="page-shell agent-detail-page-shell">
    <header class="module-header agent-detail-page-header">
      <div>
        <h2>智能体详情</h2>
        <p>
          智能体 / <strong>{{ workflowDisplayName }}</strong>
          <span class="agent-status-badge">已启用</span>
        </p>
        <div class="agent-detail-meta">{{ workflowMeta }}</div>
      </div>
      <div class="page-actions agent-detail-actions">
        <el-button @click="router.push('/agents')">
          <el-icon><Back /></el-icon>
          返回列表
        </el-button>
        <el-button class="agent-run-button" :loading="agentsStore.isStartingRun" @click="startRun">
          <el-icon><VideoPlay /></el-icon>
          运行此智能体
        </el-button>
        <el-button type="primary" :loading="agentsStore.isSaving" :disabled="!selectedNode" @click="saveNodeConfig">
          保存配置
        </el-button>
        <el-button class="agent-more-button" circle>
          <el-icon><More /></el-icon>
        </el-button>
      </div>
    </header>

    <el-alert v-if="agentsStore.errorMessage" :title="agentsStore.errorMessage" type="error" show-icon />

    <div class="agent-detail-content-grid">
      <main class="agent-detail-main-column">
        <section class="agent-flow-panel" v-loading="agentsStore.isLoading">
          <div class="agent-flow-panel-head">
            <div>
              <h3>流程画布</h3>
              <p>查看主流程、分析子节点与节点间传递关系，点击节点可切换右侧配置。</p>
            </div>
            <div class="agent-canvas-toolbar">
              <el-button circle @click="setZoom(flowZoom - 10)">
                <el-icon><Minus /></el-icon>
              </el-button>
              <span>{{ flowZoom }}%</span>
              <el-button circle @click="setZoom(flowZoom + 10)">
                <el-icon><Plus /></el-icon>
              </el-button>
              <el-button @click="fitCanvas">
                适应画布
                <el-icon><FullScreen /></el-icon>
              </el-button>
            </div>
          </div>

          <div
            ref="canvasViewportRef"
            class="agent-flow-canvas"
            :class="{ dragging: isCanvasDragging }"
            @pointerdown="startCanvasPan"
            @pointermove="moveCanvasPan"
            @pointerup="stopCanvasPan"
            @pointercancel="stopCanvasPan"
            @pointerleave="stopCanvasPan"
            @wheel="handleCanvasWheel"
          >
            <div class="agent-flow-stage-frame" :style="canvasStageFrameStyle">
              <div class="agent-flow-stage" :style="canvasStageContentStyle">
                <div class="agent-flow-row">
                  <template v-for="(node, index) in canvasNodes" :key="node.id">
                    <button
                      type="button"
                      class="agent-flow-node"
                      :class="{ active: isSelected(node.id), grouped: isInSelectedGroup(node.id) }"
                      @click="agentsStore.selectNode(node.id)"
                    >
                      <span class="agent-flow-node-icon">
                        <el-icon><component :is="nodeIcon(node.id)" /></el-icon>
                      </span>
                      <span class="agent-flow-node-body">
                        <span class="agent-flow-node-title">{{ resolveNodeDisplay(node).title }}</span>
                        <span class="agent-flow-node-summary">{{ resolveNodeDisplay(node).summary }}</span>
                        <span class="agent-flow-node-meta">
                          {{ stepNumber(index) }} · {{ resolveNodeDisplay(node).chipLabel }}
                        </span>
                      </span>
                      <span class="agent-node-status">正常</span>
                    </button>
                    <span v-if="index < canvasNodes.length - 1" class="agent-flow-arrow">
                      <el-icon><ArrowRight /></el-icon>
                    </span>
                  </template>
                </div>

                <div v-if="subFlowNodes.length" class="agent-subflow-box">
                  <div class="agent-subflow-head">
                    <span>{{ resolveNodeDisplay(activeGroupNode).title }}子节点</span>
                    <strong>{{ subFlowNodes.length }} 个分析子节点</strong>
                  </div>
                  <div class="agent-subflow-grid">
                    <button
                      v-for="(node, index) in subFlowNodes"
                      :key="node.id"
                      type="button"
                      class="agent-subflow-node"
                      :class="{ active: isSelected(node.id) }"
                      @click="agentsStore.selectNode(node.id)"
                    >
                      <span>{{ subStepNumber(index) }}</span>
                      <strong>{{ resolveNodeDisplay(node).title }}</strong>
                      <small>{{ resolveNodeDisplay(node).summary }}</small>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="agent-canvas-minimap" aria-hidden="true">
              <span v-for="node in canvasNodes" :key="node.id" :class="{ active: isSelected(node.id) }"></span>
            </div>
          </div>
        </section>

        <section class="agent-flow-notes-card">
          <div>
            <h3>流转说明</h3>
            <p>检索候选文献后，阅读节点抽取结构化摘要；分析节点展开子 Agent 完成聚类、候选整理和结果复核，再交给引用与回答节点生成最终产物。</p>
          </div>
          <div class="agent-timeline">
            <button
              v-for="(node, index) in canvasNodes"
              :key="node.id"
              type="button"
              :class="{ active: isSelected(node.id) || isInSelectedGroup(node.id) }"
              @click="agentsStore.selectNode(node.id)"
            >
              <span>{{ index + 1 }}</span>
              <strong>{{ resolveNodeDisplay(node).title }}</strong>
            </button>
          </div>
        </section>
      </main>

      <aside class="agent-detail-side-rail">
        <section class="agent-side-card agent-selected-node-card">
          <div class="agent-selected-node-head">
            <span class="agent-side-icon">
              <el-icon><component :is="nodeIcon(selectedNode?.parentNodeId || selectedNode?.id || 'analyse')" /></el-icon>
            </span>
            <div>
              <h3>{{ selectedNodeDisplay.title }}</h3>
              <p>{{ selectedNode ? selectedNode.id : '未选中节点' }}</p>
            </div>
            <em>正常</em>
          </div>
          <p class="agent-selected-node-summary">{{ selectedNodeDisplay.summary }}</p>
          <div class="agent-node-facts">
            <div>
              <span>节点类型</span>
              <strong>{{ nodeTypeLabel(selectedNode) }}</strong>
            </div>
            <div>
              <span>上游输入</span>
              <strong>{{ selectedNodeDisplay.upstream }}</strong>
            </div>
            <div>
              <span>下游输出</span>
              <strong>{{ selectedNodeDisplay.downstream }}</strong>
            </div>
          </div>
        </section>

        <section class="agent-side-card">
          <h3>执行配置</h3>
          <div class="agent-config-table">
            <div v-for="[label, value] in selectedConfigRows" :key="label">
              <span>{{ label }}</span>
              <strong>{{ value }}</strong>
            </div>
          </div>
          <label class="field-label">执行器</label>
          <el-select v-model="executorKey" class="full-width" :disabled="!selectedNode">
            <el-option
              v-for="item in agentsStore.nodeOptions ?? []"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
          <label class="field-label">备用执行</label>
          <el-select v-model="fallbackExecutorKey" class="full-width" clearable :disabled="!selectedNode">
            <el-option
              v-for="item in agentsStore.nodeOptions ?? []"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
          <label class="field-label">模型槽位</label>
          <el-input v-model="modelSlot" disabled :placeholder="selectedNode ? '' : '请选择节点'" />
        </section>

        <section class="agent-side-card">
          <h3>子节点概览（{{ subFlowNodes.length }}）</h3>
          <div class="agent-subnode-list">
            <button
              v-for="(node, index) in subFlowNodes"
              :key="node.id"
              type="button"
              :class="{ active: isSelected(node.id) }"
              @click="agentsStore.selectNode(node.id)"
            >
              <span>{{ subStepNumber(index) }}</span>
              <strong>{{ resolveNodeDisplay(node).title }}</strong>
              <em>
                <el-icon><Check /></el-icon>
                正常
              </em>
            </button>
            <p v-if="!subFlowNodes.length" class="agent-empty-copy">当前节点没有子 Agent。</p>
          </div>
          <el-button text type="primary">管理子节点</el-button>
        </section>

        <section class="agent-side-card">
          <h3>传递规则</h3>
          <p>{{ selectedNodeDisplay.handoffRule }}</p>
          <div class="agent-transfer-table">
            <div>
              <span>输入</span>
              <strong>{{ selectedNodeDisplay.upstream }}</strong>
            </div>
            <div>
              <span>输出</span>
              <strong>{{ selectedNodeDisplay.downstream }}</strong>
            </div>
            <div>
              <span>方式</span>
              <strong>{{ selectedNodeDisplay.routeLabel || '同步传递' }}</strong>
            </div>
          </div>
          <el-button text type="primary">查看传递规则</el-button>
        </section>
      </aside>
    </div>
  </div>
</template>
