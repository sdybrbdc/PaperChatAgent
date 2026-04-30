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

<style lang="scss" scoped>
.page-shell {
  height: calc(100vh - 48px);
  padding: 24px 28px 28px;
  border-radius: 28px;
  border: 1px solid var(--pc-border);
  background: var(--pc-surface);
  box-shadow: var(--pc-shadow);
  overflow: hidden;

  &:not(.chat-page-shell) {
    overflow-y: auto;
  }
}

.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-shrink: 0;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 28px;
  }

  p {
    max-width: 640px;
    margin: 8px 0 0;
    color: var(--pc-text-muted);
    font-size: 15px;
  }
}

.page-actions {
  display: flex;
  gap: 12px;
}

.agents-page-shell {
  display: flex;
  min-height: 0;
  flex-direction: column;
  overflow: hidden !important;
}

.agents-page-header {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.agents-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex-shrink: 0;
  gap: 14px;
  margin-bottom: 18px;
}

.agent-stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 104px;
  padding: 16px 18px;
  border: 1px solid transparent;
  border-radius: 18px;

  &--blue {
    background: #eef4ff;
    border-color: #d7e4ff;
  }

  &--green {
    background: #ebfdf4;
    border-color: #d2f7e5;
  }

  &--orange {
    background: #fff7e8;
    border-color: #ffedc7;
  }

  &--violet {
    background: #f3edff;
    border-color: #e5d8ff;
  }

  span,
  small {
    display: block;
    color: var(--pc-text-muted);
    font-size: 13px;
  }

  strong {
    display: block;
    margin: 2px 0;
    color: var(--pc-text);
    font-size: 30px;
    line-height: 1.1;
  }
}

.agent-stat-icon {
  display: grid;
  place-items: center;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--pc-brand);
  font-size: 20px;
}

.agents-content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  flex: 1;
  min-height: 0;
  gap: 18px;
  overflow: hidden;
}

.agents-directory-panel {
  border: 1px solid var(--pc-border);
  border-radius: 18px;
  background: var(--pc-surface-soft);
  display: flex;
  min-height: 0;
  flex-direction: column;
  padding: 20px;
}

.agents-directory-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    color: var(--pc-text);
    font-size: 20px;
  }

  p {
    margin: 6px 0 0;
    color: var(--pc-text-muted);
    font-size: 14px;
    line-height: 1.55;
  }

  span {
    padding: 6px 12px;
    border-radius: 999px;
    background: var(--pc-surface);
    color: var(--pc-text-secondary);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }
}

.agents-toolbar {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  gap: 12px;
  flex-shrink: 0;
  margin-bottom: 16px;
}

.agents-type-select {
  width: 100%;
}

.agents-list-scroll {
  display: grid;
  align-content: start;
  flex: 1;
  min-height: 0;
  gap: 12px;
  overflow-y: auto;
  padding-right: 6px;
}

.agent-list-card {
  display: grid;
  grid-template-columns: 52px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  width: 100%;
  min-height: 118px;
  padding: 18px 20px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
  color: var(--pc-text);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;

  &:hover {
    border-color: var(--pc-brand);
    background: #fbfdff;
    box-shadow: 0 10px 24px rgba(37, 99, 235, 0.1);
  }
}

.agent-list-avatar {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: #edf4ff;
  color: var(--pc-brand);
  font-size: 22px;
}

.agent-list-body {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.agent-list-title-row {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;

  strong {
    overflow: hidden;
    color: var(--pc-text);
    font-size: 18px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  em {
    flex: 0 0 auto;
    padding: 3px 9px;
    border-radius: 999px;
    background: var(--pc-brand-soft);
    color: var(--pc-brand);
    font-size: 12px;
    font-style: normal;
    font-weight: 600;
  }
}

.agent-list-description,
.agent-list-meta {
  overflow: hidden;
  color: var(--pc-text-muted);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-list-meta {
  color: var(--pc-text-secondary);
  font-size: 13px;
}

.agent-list-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--pc-brand);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}

.agents-empty-state {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 58px 0;
  color: var(--pc-text-muted);

  .el-icon {
    font-size: 28px;
  }

  p {
    margin: 0;
  }
}

.agents-side-rail {
  display: grid;
  align-content: start;
  min-width: 0;
  gap: 14px;
  overflow-y: auto;
  padding-right: 4px;
}

.agents-side-card {
  padding: 18px;

  h3 {
    margin: 0;
    color: var(--pc-text);
    font-size: 20px;
  }

  p {
    margin: 6px 0 0;
    color: var(--pc-text-muted);
    font-size: 14px;
    line-height: 1.55;
  }
}

.agents-side-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;

  .el-icon {
    color: var(--pc-brand);
    font-size: 19px;
  }
}

.agents-filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--pc-surface);
  font-size: 13px;

  span {
    color: var(--pc-text-muted);
  }

  strong {
    color: var(--pc-text-secondary);
  }
}

.agents-check-list {
  display: grid;
  gap: 9px;
  margin: 0 0 8px;
  padding: 0;
  list-style: none;

  li {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--pc-text-secondary);
    font-size: 13px;
  }

  .el-icon {
    flex: 0 0 auto;
    color: var(--pc-success-text);
  }
}

.full-width {
  width: 100%;
}
</style>
