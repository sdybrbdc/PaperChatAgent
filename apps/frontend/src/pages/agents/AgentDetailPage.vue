<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
    summary: '聚合阅读结果，并调度 3 个子节点完成主题归并、候选整理与结果复核。',
    chipLabel: 'Cluster',
    handoffRule:
      '上一节点摘要、候选文献和引用线索会先进入分析节点。分析阶段会调度子节点完成聚类、候选整理和结果复核，随后把主题结论传递给写作节点。',
    routeLabel: '阅读输出 → 分析分支 → 写作节点',
    upstream: '阅读节点输出',
    downstream: '写作节点',
  },
  'analyse.cluster': {
    title: '主题聚类',
    summary: '聚类与主题归并',
  },
  'analyse.deep_analyse': {
    title: '候选整理',
    summary: '清洗候选输入',
  },
  'analyse.global_analyse': {
    title: '结果复核',
    summary: '校对主题结论',
  },
  writing: {
    chipLabel: 'Writing',
    routeLabel: '分析输出 → 写作子流程 → 报告节点',
  },
  report: {
    chipLabel: 'Report',
  },
}

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()

const workflowId = computed(() => String(route.params.workflowId ?? ''))
const executorKey = ref('')
const fallbackExecutorKey = ref('')
const modelSlot = ref('conversation_model')

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

const expandedBranchNode = computed(() => selectedGroupNode.value)
const expandedBranchNodes = computed(() => {
  const branchNode = expandedBranchNode.value
  if (!branchNode) return []
  const preferredOrder: Record<string, string[]> = {
    analyse: ['analyse.cluster', 'analyse.deep_analyse', 'analyse.global_analyse'],
    writing: ['writing.writing_director', 'writing.parallel_writing', 'writing.retrieval', 'writing.review'],
  }
  const order = preferredOrder[branchNode.id]
  if (!order) return branchNode.subNodes
  return order
    .map((id) => branchNode.subNodes.find((node) => node.id === id))
    .filter((node): node is AgentWorkflowNodeDTO => Boolean(node))
})
const branchLabel = computed(() => {
  if (!expandedBranchNode.value) return '子节点分支'
  if (expandedBranchNode.value.id === 'analyse') return '分析分支'
  return `${resolveNodeDisplay(expandedBranchNode.value).title}子节点`
})
const branchMeta = computed(() => {
  if (!expandedBranchNode.value) return ''
  return `${resolveNodeDisplay(expandedBranchNode.value).title}已展开 ${expandedBranchNodes.value.length} 个子节点`
})
const branchGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(expandedBranchNodes.value.length, 1)}, minmax(96px, 1fr))`,
}))

const workflowDisplayName = computed(() => {
  const workflow = agentsStore.currentWorkflow
  if (!workflow) return '加载中'
  return WORKFLOW_DISPLAY_NAMES[workflow.slug] ?? workflow.name
})

const workflowMeta = computed(
  () => `${canvasNodes.value.length} 个主节点 · 当前展开 ${expandedBranchNodes.value.length} 个子节点 · 顺序研究工作流`,
)

const selectedNodeDisplay = computed(() => describeSelectedNode(selectedNode.value))

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
  selectedNode,
  (node) => {
    executorKey.value = node?.executorKey ?? ''
    fallbackExecutorKey.value = node?.fallbackExecutorKey ?? ''
    modelSlot.value = node?.modelSlot ?? 'conversation_model'
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

function isSelected(nodeId: string) {
  return agentsStore.selectedNodeId === nodeId
}

function stepNumber(index: number) {
  return String(index + 1).padStart(2, '0')
}

function branchStepNumber(index: number) {
  return `A${index + 1}`
}

function pickText(...values: Array<string | undefined>) {
  for (const value of values) {
    if (value && value.trim()) return value
  }
  return ''
}

function subNodeHint(node: AgentWorkflowNodeDTO) {
  if (!node.subNodes.length) return ''
  const labels = node.subNodes.slice(0, 2).map((item) => resolveNodeDisplay(item).title)
  const moreCount = node.subNodes.length - labels.length
  return moreCount > 0 ? `${labels.join(' / ')} +${moreCount}` : labels.join(' / ')
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
  <div class="page-shell agent-detail-shell">
    <header class="module-header agent-detail-header">
      <div>
        <h2>智能体详情</h2>
        <p>智能体 / {{ workflowDisplayName }}</p>
        <div class="agent-detail-meta">
          {{ workflowMeta }}
        </div>
      </div>
      <div class="page-actions agent-detail-actions">
        <el-button class="agent-detail-run-button" :loading="agentsStore.isStartingRun" @click="startRun">
          运行此智能体
        </el-button>
        <el-button @click="router.push('/agents')">返回列表</el-button>
        <el-button type="primary" :loading="agentsStore.isSaving" :disabled="!selectedNode" @click="saveNodeConfig">
          保存节点配置
        </el-button>
      </div>
    </header>

    <el-alert v-if="agentsStore.errorMessage" :title="agentsStore.errorMessage" type="error" show-icon />

    <div class="agent-detail-grid">
      <section class="agents-surface agent-detail-canvas" v-loading="agentsStore.isLoading">
        <div class="agent-detail-canvas-head">
          <div>
            <h3>流程画布</h3>
            <p>默认只显示主流程。选择某个带子节点的主节点后，画布会展开该节点的子节点。</p>
          </div>
          <span class="agent-detail-pill">{{ branchMeta || '未展开子节点' }}</span>
        </div>

        <div class="agent-detail-board">
          <div class="agent-main-flow">
            <div class="agent-board-label">主流程</div>
            <div class="agent-main-track" aria-hidden="true">
              <span class="agent-main-track-line"></span>
              <span class="agent-main-track-accent"></span>
            </div>
            <div class="agent-main-grid">
              <button
                v-for="(node, index) in canvasNodes"
                :key="node.id"
                type="button"
                class="agent-main-card"
                :class="{ active: isSelected(node.id) }"
                @click="agentsStore.selectNode(node.id)"
              >
                <div class="agent-main-card-head">
                  <span class="agent-main-step">{{ stepNumber(index) }}</span>
                  <span v-if="node.subNodes.length" class="agent-main-branch-count">
                    {{ node.id === 'analyse' ? `${node.subNodes.length} 分支` : `${node.subNodes.length} 子节点` }}
                  </span>
                </div>
                <h4>{{ resolveNodeDisplay(node).title }}</h4>
                <p>{{ resolveNodeDisplay(node).summary }}</p>
                <div v-if="node.subNodes.length" class="agent-main-subhint">
                  {{ subNodeHint(node) }}
                </div>
                <span class="agent-main-chip">{{ resolveNodeDisplay(node).chipLabel }}</span>
              </button>
            </div>
          </div>

          <div v-if="expandedBranchNodes.length" class="agent-branch-flow">
            <div class="agent-branch-stem" aria-hidden="true"></div>
            <div class="agent-board-label agent-branch-flow-label">{{ branchLabel }}</div>
            <div class="agent-branch-track" aria-hidden="true"></div>
            <div class="agent-branch-grid" :style="branchGridStyle">
              <button
                v-for="(node, index) in expandedBranchNodes"
                :key="node.id"
                type="button"
                class="agent-branch-card"
                :class="{ active: isSelected(node.id) }"
                @click="agentsStore.selectNode(node.id)"
              >
                <span class="agent-branch-step">{{ branchStepNumber(index) }}</span>
                <h4>{{ resolveNodeDisplay(node).title }}</h4>
                <p>{{ resolveNodeDisplay(node).summary }}</p>
              </button>
            </div>
          </div>

          <div class="agent-handoff-panel">
            <h4>流转说明</h4>
            <p>检索节点先生成候选文献，阅读节点抽取结构化摘要；分析节点展开 3 个子节点完成聚类、候选整理和结果复核，随后把主题结论传给写作节点；写作节点再调度内部子节点，最后由报告节点产出最终结果。</p>
            <div class="agent-handoff-chip-row">
              <span class="agent-handoff-chip">候选文献</span>
              <span class="agent-handoff-arrow">→</span>
              <span class="agent-handoff-chip">结构化摘要</span>
              <span class="agent-handoff-arrow">→</span>
              <span class="agent-handoff-chip">主题结论</span>
              <span class="agent-handoff-arrow">→</span>
              <span class="agent-handoff-chip">写作子流程</span>
              <span class="agent-handoff-arrow">→</span>
              <span class="agent-handoff-chip">最终报告</span>
            </div>
          </div>
        </div>
      </section>

      <aside class="agents-rail agent-detail-rail">
        <section class="soft-panel agents-rail-card">
          <h3>执行配置</h3>
          <p class="agent-side-caption">{{ selectedNodeDisplay.title }}</p>
          <p class="agent-side-helper">{{ selectedNodeDisplay.summary }}</p>
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
          <div class="agent-config-grid">
            <div>
              <label class="field-label">模型槽位</label>
              <el-input v-model="modelSlot" disabled :placeholder="selectedNode ? '' : '请选择节点'" />
            </div>
            <div>
              <label class="field-label">当前模型</label>
              <el-input :model-value="selectedNode?.currentModelName || '未配置'" disabled />
            </div>
          </div>
        </section>

        <section class="soft-panel agents-rail-card">
          <h3>传递规则</h3>
          <p class="agent-side-caption">{{ selectedNodeDisplay.title }}</p>
          <p>{{ selectedNodeDisplay.handoffRule }}</p>
          <div v-if="selectedNodeDisplay.routeLabel" class="agent-route-pill">
            {{ selectedNodeDisplay.routeLabel }}
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>
