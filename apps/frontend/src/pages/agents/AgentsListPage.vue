<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  Box,
  CircleCheck,
  Connection,
  DataAnalysis,
  DocumentAdd,
  Filter,
  Guide,
  Plus,
  Search,
  Setting,
} from '@element-plus/icons-vue'
import type { AgentWorkflowDTO } from '../../types/agents'
import { useAgentsStore } from '../../stores/agents'

const router = useRouter()
const agentsStore = useAgentsStore()

const searchKeyword = ref('')
const typeFilter = ref('all')

const typeOptions = [
  { label: '全部类型', value: 'all' },
  { label: '内置流程', value: 'builtin' },
  { label: '项目子 Agent', value: 'project' },
  { label: '自定义', value: 'custom' },
]

const builtinCount = computed(() => agentsStore.workflows.filter((workflow) => workflow.sourceType === 'builtin').length)
const projectAgentCount = computed(() =>
  agentsStore.workflows.filter((workflow) => ['project', 'project_agent'].includes(workflow.sourceType)).length,
)
const recentRunCount = computed(() => {
  return agentsStore.workflows.reduce((total, workflow) => {
    const definition = workflow.definition ?? {}
    const value = Number(definition.recent_run_count ?? definition.recentRunCount ?? 0)
    return total + (Number.isFinite(value) ? value : 0)
  }, 0)
})

const visibleWorkflows = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return agentsStore.workflows.filter((workflow) => {
    const matchType =
      typeFilter.value === 'all' ||
      workflow.sourceType === typeFilter.value ||
      (typeFilter.value === 'project' && workflow.sourceType === 'project_agent') ||
      (typeFilter.value === 'custom' && !['builtin', 'project', 'project_agent'].includes(workflow.sourceType))
    const matchKeyword =
      !keyword ||
      [workflow.name, workflow.description, workflow.slug, workflow.sourceType]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    return matchType && matchKeyword
  })
})

const activeTypeLabel = computed(() => typeOptions.find((option) => option.value === typeFilter.value)?.label ?? '全部类型')

onMounted(() => {
  agentsStore.loadWorkflows()
})

function openWorkflow(workflowId: string) {
  router.push(`/agents/${workflowId}`)
}

function clearFilters() {
  typeFilter.value = 'all'
  searchKeyword.value = ''
}

function typeLabel(workflow: AgentWorkflowDTO) {
  if (workflow.sourceType === 'builtin') return '内置流程'
  if (['project', 'project_agent'].includes(workflow.sourceType)) return '项目子 Agent'
  return '自定义'
}

function statusLabel(status: string) {
  if (status === 'active') return '可用'
  if (status === 'disabled') return '停用'
  return status || '可用'
}

function formatDate(value: string | null) {
  if (!value) return '未同步'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未同步'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<template>
  <div class="page-shell agents-page-shell">
    <header class="module-header agents-page-header">
      <div>
        <h2>智能体</h2>
        <p>组织和管理研究工作流、可复用于 Agent 与执行链，提升研究效率与一致性。</p>
      </div>
      <div class="page-actions">
        <el-button>
          <el-icon><DocumentAdd /></el-icon>
          导入配置
        </el-button>
        <el-button type="primary">
          <el-icon><Plus /></el-icon>
          新建智能体
        </el-button>
      </div>
    </header>

    <section class="agents-stat-grid" aria-label="智能体概览">
      <article class="agent-stat-card agent-stat-card--blue">
        <div class="agent-stat-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div>
          <span>智能体总数</span>
          <strong>{{ agentsStore.workflows.length }}</strong>
          <small>已创建智能体</small>
        </div>
      </article>
      <article class="agent-stat-card agent-stat-card--green">
        <div class="agent-stat-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div>
          <span>内置流程</span>
          <strong>{{ builtinCount }}</strong>
          <small>可直接使用</small>
        </div>
      </article>
      <article class="agent-stat-card agent-stat-card--orange">
        <div class="agent-stat-icon">
          <el-icon><Box /></el-icon>
        </div>
        <div>
          <span>项目子 Agent</span>
          <strong>{{ projectAgentCount }}</strong>
          <small>项目专属 Agent</small>
        </div>
      </article>
      <article class="agent-stat-card agent-stat-card--violet">
        <div class="agent-stat-icon">
          <el-icon><Guide /></el-icon>
        </div>
        <div>
          <span>最近运行</span>
          <strong>{{ recentRunCount }}</strong>
          <small>近 7 天运行次数</small>
        </div>
      </article>
    </section>

    <el-alert v-if="agentsStore.errorMessage" :title="agentsStore.errorMessage" type="error" show-icon />

    <div class="agents-content-grid">
      <section class="agents-directory-panel" v-loading="agentsStore.isLoading">
        <div class="agents-directory-head">
          <div>
            <h3>智能体列表</h3>
            <p>点击智能体进入详情，查看流程节点、执行器、子 Agent 与上下游传递配置。</p>
          </div>
          <span>{{ visibleWorkflows.length }} / {{ agentsStore.workflows.length }}</span>
        </div>

        <div class="agents-toolbar">
          <el-select v-model="typeFilter" class="agents-type-select" :prefix-icon="Filter">
            <el-option
              v-for="option in typeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-input v-model="searchKeyword" clearable placeholder="搜索智能体名称、描述或类型">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>

        <div class="agents-list-scroll">
          <button
            v-for="workflow in visibleWorkflows"
            :key="workflow.id"
            class="agent-list-card"
            type="button"
            @click="openWorkflow(workflow.id)"
          >
            <span class="agent-list-avatar">
              <el-icon><DataAnalysis /></el-icon>
            </span>
            <span class="agent-list-body">
              <span class="agent-list-title-row">
                <strong>{{ workflow.name }}</strong>
                <em>{{ typeLabel(workflow) }}</em>
              </span>
              <span class="agent-list-description">{{ workflow.description }}</span>
              <span class="agent-list-meta">
                {{ statusLabel(workflow.status) }} · {{ workflow.nodeCount }} 个节点 · v{{ workflow.version }} · 最近更新 {{ formatDate(workflow.updatedAt) }}
              </span>
            </span>
            <span class="agent-list-link">
              查看详情
              <el-icon><ArrowRight /></el-icon>
            </span>
          </button>

          <div v-if="!agentsStore.isLoading && !visibleWorkflows.length" class="agents-empty-state">
            <el-icon><Search /></el-icon>
            <p>没有匹配的智能体</p>
            <el-button @click="clearFilters">清除筛选</el-button>
          </div>
        </div>
      </section>

      <aside class="agents-side-rail">
        <section class="agents-side-card">
          <div class="agents-side-card-head">
            <h3>当前筛选</h3>
            <el-icon><Filter /></el-icon>
          </div>
          <div class="agents-filter-row">
            <span>类型</span>
            <strong>{{ activeTypeLabel }}</strong>
          </div>
          <div class="agents-filter-row">
            <span>状态</span>
            <strong>全部可用</strong>
          </div>
          <el-button class="full-width" @click="clearFilters">清除筛选</el-button>
        </section>

        <section class="agents-side-card">
          <div class="agents-side-card-head">
            <h3>使用说明</h3>
            <el-icon><Guide /></el-icon>
          </div>
          <p>智能体可作为完整研究流程运行，也可以作为节点内的子 Agent 被流程调度。</p>
          <p>进入详情页后，可查看节点关系并为每个节点配置执行器、备用执行器和模型槽位。</p>
          <el-button text type="primary">查看帮助文档</el-button>
        </section>

        <section class="agents-side-card">
          <div class="agents-side-card-head">
            <h3>配置重点</h3>
            <el-icon><Setting /></el-icon>
          </div>
          <ul class="agents-check-list">
            <li>
              <el-icon><CircleCheck /></el-icon>
              节点覆盖配置保存到用户维度
            </li>
            <li>
              <el-icon><CircleCheck /></el-icon>
              子 Agent 只展示当前流程声明的节点
            </li>
            <li>
              <el-icon><CircleCheck /></el-icon>
              运行记录与后台任务保持关联
            </li>
          </ul>
          <el-button text type="primary" @click="router.push('/models')">前往模型配置</el-button>
        </section>
      </aside>
    </div>
  </div>
</template>
