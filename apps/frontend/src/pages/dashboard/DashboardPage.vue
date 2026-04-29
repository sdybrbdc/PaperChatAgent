<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck,
  Connection,
  Cpu,
  Download,
  Refresh,
  Timer,
  TrendCharts,
} from '@element-plus/icons-vue'
import { createDashboardSnapshot, getDashboardSnapshot } from '../../apis/dashboard'
import type { DashboardActivityDTO, DashboardSnapshotDTO } from '../../types/dashboard'

type ActivityKey = 'modelCalls' | 'toolCalls' | 'taskCount'

const snapshot = ref<DashboardSnapshotDTO | null>(null)
const days = ref(7)
const isLoading = ref(false)
const isExporting = ref(false)
const errorMessage = ref('')

const chartWidth = 640
const chartHeight = 250
const chartPadding = 26

const overview = computed(() => snapshot.value?.overview ?? null)
const modelUsage = computed(() => snapshot.value?.modelUsage ?? [])
const taskUsage = computed(() => snapshot.value?.taskUsage ?? [])
const toolUsage = computed(() => snapshot.value?.toolUsage ?? [])
const events = computed(() => snapshot.value?.events ?? [])
const activity = computed(() => snapshot.value?.activity ?? [])
const taskStatusGroups = [
  { key: 'completed', label: '已完成', color: '#10b981', aliases: ['completed', 'success', 'succeeded', 'done'] },
  { key: 'running', label: '执行中', color: '#2563eb', aliases: ['running', 'in_progress', 'processing'] },
  { key: 'pending', label: '等待中', color: '#f59e0b', aliases: ['pending', 'queued', 'created', 'waiting'] },
  { key: 'failed', label: '失败', color: '#ef4444', aliases: ['failed', 'error', 'cancelled', 'canceled'] },
]
const rowColors = ['#2563eb', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ef4444']

const totalTokens = computed(() => overview.value?.tokenCount || (overview.value?.inputTokenCount ?? 0) + (overview.value?.outputTokenCount ?? 0))
const trendMax = computed(() => {
  const values = activitySeries.value.flatMap((item) => [item.modelCalls, item.toolCalls, item.taskCount])
  return Math.max(...values, 1)
})

const activitySeries = computed<DashboardActivityDTO[]>(() => {
  if (activity.value.length) return activity.value
  return Array.from({ length: Math.min(days.value, 14) }, (_, index) => ({
    date: '',
    label: `D${index + 1}`,
    modelCalls: 0,
    toolCalls: 0,
    taskCount: 0,
    tokenCount: 0,
  }))
})

const kpiCards = computed(() => [
  {
    label: '模型调用',
    value: numberText(overview.value?.modelCallCount ?? 0),
    helper: `${modelUsage.value.length} 个模型路由`,
    tone: 'brand',
    icon: Cpu,
  },
  {
    label: 'Token 消耗',
    value: compactNumber(totalTokens.value),
    helper: `输入 ${compactNumber(overview.value?.inputTokenCount ?? 0)} / 输出 ${compactNumber(overview.value?.outputTokenCount ?? 0)}`,
    tone: 'info',
    icon: TrendCharts,
  },
  {
    label: '工具调用',
    value: numberText(overview.value?.toolCallCount ?? 0),
    helper: `${toolUsage.value.length} 个能力被调用`,
    tone: 'success',
    icon: Connection,
  },
  {
    label: '任务完成率',
    value: percentText(overview.value?.taskCompletionRate ?? 0),
    helper: `${overview.value?.activeTaskCount ?? 0} 个运行中 / ${overview.value?.failedTaskCount ?? 0} 个失败`,
    tone: overview.value?.failedTaskCount ? 'warning' : 'success',
    icon: CircleCheck,
  },
  {
    label: '平均延迟',
    value: latencyText(overview.value?.averageLatencyMs ?? 0),
    helper: `最近 ${days.value} 天`,
    tone: 'warning',
    icon: Timer,
  },
])

const modelLinePoints = computed(() => pointSeries('modelCalls'))
const toolLinePoints = computed(() => pointSeries('toolCalls'))
const taskLinePoints = computed(() => pointSeries('taskCount'))
const modelAreaPoints = computed(() => {
  const points = modelLinePoints.value
  if (!points.length) return ''
  const first = points[0]
  const last = points[points.length - 1]
  return `${points.map((point) => `${point.x},${point.y}`).join(' ')} ${last.x},${chartHeight - chartPadding} ${first.x},${chartHeight - chartPadding}`
})
const axisLabels = computed(() => {
  const step = Math.max(1, Math.ceil(activitySeries.value.length / 8))
  return activitySeries.value.filter((_, index) => index % step === 0 || index === activitySeries.value.length - 1)
})

const taskStatusItems = computed(() => {
  const distribution = overview.value?.taskStatusDistribution ?? []
  if (distribution.length) return distribution
  return taskUsage.value.map((item) => ({ label: item.status, value: item.count }))
})
const taskStatusCards = computed(() =>
  taskStatusGroups.map((group) => ({
    ...group,
    value: taskStatusItems.value.reduce((sum, item) => {
      const label = String(item.label || '').toLowerCase()
      return group.aliases.includes(label) ? sum + item.value : sum
    }, 0),
  })),
)
const taskTotal = computed(() => taskStatusCards.value.reduce((sum, item) => sum + item.value, 0))
const taskCompletionRate = computed(() => {
  if (overview.value) return overview.value.taskCompletionRate
  const completed = taskStatusCards.value.find((item) => item.key === 'completed')?.value ?? 0
  return taskTotal.value ? completed / taskTotal.value : 0
})
const donutStyle = computed(() => {
  if (!taskTotal.value) return { background: 'conic-gradient(#e8eef8 0 100%)' }
  let cursor = 0
  const segments = taskStatusCards.value.map((item) => {
    const start = cursor
    const size = (item.value / taskTotal.value) * 100
    cursor += size
    return `${item.color} ${start}% ${cursor}%`
  })
  return { background: `conic-gradient(${segments.join(', ')})` }
})

const modelRows = computed(() => {
  const max = Math.max(...modelUsage.value.map((item) => item.callCount), 1)
  const total = Math.max(modelUsage.value.reduce((sum, item) => sum + item.callCount, 0), 1)
  return modelUsage.value.map((item, index) => ({
    ...item,
    color: rowColors[index % rowColors.length],
    share: percentText(item.callCount / total),
    width: `${Math.max(4, (item.callCount / max) * 100)}%`,
  }))
})
const toolRows = computed(() => {
  const max = Math.max(...toolUsage.value.map((item) => item.callCount), 1)
  return toolUsage.value.map((item, index) => ({
    ...item,
    color: rowColors[index % rowColors.length],
    width: `${Math.max(4, (item.callCount / max) * 100)}%`,
  }))
})
const eventRows = computed(() =>
  events.value.length
    ? events.value
    : [
        { eventType: 'empty', title: '暂无系统事件', detail: '开始聊天、运行任务或调用工具后，这里会显示最新观测记录。', status: 'idle', createdAt: null },
      ],
)

function pointSeries(key: ActivityKey) {
  const values = activitySeries.value
  const step = (chartWidth - chartPadding * 2) / Math.max(values.length - 1, 1)
  return values.map((item, index) => {
    const x = values.length === 1 ? chartWidth / 2 : chartPadding + index * step
    const y = chartHeight - chartPadding - (item[key] / trendMax.value) * (chartHeight - chartPadding * 2)
    return { x, y, value: item[key], label: item.label }
  })
}

function numberText(value: number) {
  return new Intl.NumberFormat('zh-CN').format(Math.round(value || 0))
}

function compactNumber(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return numberText(value)
}

function percentText(value: number) {
  return `${Math.round((value || 0) * 100)}%`
}

function latencyText(value: number) {
  if (!value) return '0ms'
  if (value >= 1000) return `${(value / 1000).toFixed(1)}s`
  return `${Math.round(value)}ms`
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    completed: '已完成',
    success: '成功',
    running: '运行中',
    pending: '等待中',
    failed: '失败',
    error: '异常',
    recorded: '已记录',
    idle: '空闲',
  }
  return labels[value] || value || 'unknown'
}

function statusTone(value: string) {
  if (['failed', 'error'].includes(value)) return 'danger'
  if (['running', 'pending'].includes(value)) return 'warning'
  if (['completed', 'success', 'recorded'].includes(value)) return 'success'
  return 'brand'
}

function formatTime(value: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    snapshot.value = await getDashboardSnapshot(days.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '看板数据加载失败'
  } finally {
    isLoading.value = false
  }
}

async function changeRange(nextDays: number) {
  days.value = nextDays
  await loadDashboard()
}

async function exportSnapshot() {
  isExporting.value = true
  try {
    snapshot.value = await createDashboardSnapshot(days.value)
    ElMessage.success(`快照已生成：${snapshot.value.generatedAt || '当前时间'}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '生成快照失败')
  } finally {
    isExporting.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page-shell dashboard-shell">
    <header class="module-header dashboard-header">
      <div>
        <h2>数据看板</h2>
      </div>
      <div class="page-actions dashboard-actions">
        <el-select v-model="days" style="width: 150px" @change="changeRange">
          <el-option label="最近 7 天" :value="7" />
          <el-option label="最近 30 天" :value="30" />
          <el-option label="最近 90 天" :value="90" />
        </el-select>
        <el-button :loading="isLoading" @click="loadDashboard">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" :loading="isExporting" @click="exportSnapshot">
          <el-icon><Download /></el-icon>
          导出快照
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <div v-loading="isLoading" class="dashboard-page-stack">
      <section class="dashboard-kpi-grid">
        <article v-for="card in kpiCards" :key="card.label" class="dashboard-kpi-card" :class="card.tone">
          <div class="dashboard-kpi-icon">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
          <div>
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
            <p>{{ card.helper }}</p>
          </div>
        </article>
      </section>

      <section class="dashboard-main-grid">
        <article class="dashboard-panel dashboard-trend-panel">
          <div class="section-title-row">
            <div>
              <h3>调用趋势</h3>
              <p>近 {{ days }} 天模型调用、工具调用与任务完成变化</p>
            </div>
            <div class="dashboard-legend">
              <span><i class="legend-model" />模型</span>
              <span><i class="legend-tool" />工具</span>
              <span><i class="legend-task" />任务</span>
            </div>
          </div>

          <div class="dashboard-chart-shell">
            <span class="dashboard-peak-label">峰值 {{ compactNumber(trendMax) }}</span>
            <svg class="dashboard-trend-svg" :viewBox="`0 0 ${chartWidth} ${chartHeight}`" role="img" aria-label="模型调用趋势">
              <line
                v-for="index in 4"
                :key="index"
                :x1="chartPadding"
                :x2="chartWidth - chartPadding"
                :y1="chartPadding + (index - 1) * ((chartHeight - chartPadding * 2) / 3)"
                :y2="chartPadding + (index - 1) * ((chartHeight - chartPadding * 2) / 3)"
                class="dashboard-grid-line"
              />
              <polygon v-if="modelAreaPoints" :points="modelAreaPoints" class="dashboard-area-fill" />
              <polyline :points="modelLinePoints.map((point) => `${point.x},${point.y}`).join(' ')" class="dashboard-line model" />
              <polyline :points="toolLinePoints.map((point) => `${point.x},${point.y}`).join(' ')" class="dashboard-line tool" />
              <polyline :points="taskLinePoints.map((point) => `${point.x},${point.y}`).join(' ')" class="dashboard-line task" />
            </svg>
            <div class="dashboard-axis-labels">
              <span v-for="item in axisLabels" :key="item.label">{{ item.label }}</span>
            </div>
          </div>
        </article>

        <article class="dashboard-panel dashboard-status-panel">
          <div class="section-title-row">
            <div>
              <h3>任务状态</h3>
              <p>Agent 任务队列实时分布</p>
            </div>
          </div>
          <div class="dashboard-donut-wrap">
            <div class="dashboard-donut" :style="donutStyle">
              <div>
                <strong>{{ percentText(taskCompletionRate) }}</strong>
                <span>完成率</span>
              </div>
            </div>
            <div class="dashboard-status-list">
              <div v-for="item in taskStatusCards" :key="item.key" class="dashboard-status-row">
                <span><i :style="{ background: item.color }" />{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section class="dashboard-detail-grid">
        <article class="dashboard-panel">
          <div class="section-title-row">
            <div>
              <h3>模型调用排行</h3>
              <p>按最近 {{ days }} 天调用量统计</p>
            </div>
          </div>
          <div class="dashboard-rank-list dashboard-scroll-area">
            <div v-for="item in modelRows" :key="`${item.modelName}-${item.routeKey}`" class="dashboard-rank-row">
              <div class="dashboard-rank-head">
                <strong>{{ item.modelName || 'unknown' }}</strong>
                <span>{{ numberText(item.callCount) }}</span>
              </div>
              <div class="dashboard-rank-track"><i :style="{ width: item.width, background: item.color }" /></div>
              <div class="dashboard-rank-meta">
                <span>{{ item.routeKey || item.providerName || 'model' }}</span>
                <span>{{ item.share }}</span>
              </div>
            </div>
            <el-empty v-if="!modelRows.length" description="暂无模型调用数据" :image-size="80" />
          </div>
        </article>

        <article class="dashboard-panel">
          <div class="section-title-row">
            <div>
              <h3>工具调用健康度</h3>
              <p>MCP / Skill / RAG 工具观测</p>
            </div>
          </div>
          <div class="dashboard-tool-head">
            <span>工具</span>
            <span>次数</span>
            <span>成功率</span>
          </div>
          <div class="dashboard-tool-list dashboard-scroll-area">
            <div v-for="item in toolRows" :key="item.toolName" class="dashboard-tool-row">
              <div class="dashboard-tool-name">
                <i :style="{ background: item.color }" />
                <strong>{{ item.toolName }}</strong>
              </div>
              <span>{{ numberText(item.callCount) }}</span>
              <strong :class="{ danger: item.successRate < 0.9 }">{{ percentText(item.successRate || 0) }}</strong>
            </div>
            <el-empty v-if="!toolRows.length" description="暂无工具调用数据" :image-size="80" />
          </div>
        </article>

        <article class="dashboard-panel dashboard-events-panel">
          <div class="section-title-row">
            <div>
              <h3>系统事件</h3>
              <p>最近的会话、Skill 与任务事件</p>
            </div>
          </div>
          <div class="dashboard-timeline dashboard-scroll-area">
            <div v-for="event in eventRows" :key="`${event.title}-${event.createdAt}`" class="dashboard-event-row">
              <i :class="statusTone(event.status)" />
              <div>
                <span>{{ formatTime(event.createdAt) }}</span>
                <strong>{{ event.title }}</strong>
                <p>{{ event.detail }}</p>
              </div>
              <em :class="statusTone(event.status)">{{ statusLabel(event.status) }}</em>
            </div>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-shell {
  background: #f8fafd;
}

.dashboard-header {
  padding: 2px 0 6px;
}

.dashboard-actions {
  align-items: center;
}

.dashboard-page-stack {
  display: grid;
  gap: 18px;
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(420px, 0.72fr);
  gap: 18px;
  padding: 22px;
  border: 1px solid var(--pc-border);
  border-radius: 22px;
  background: var(--pc-surface);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
}

.dashboard-hero-copy {
  display: grid;
  align-content: center;
  gap: 8px;
}

.dashboard-eyebrow {
  color: var(--pc-brand);
  font-size: 12px;
  font-weight: 700;
}

.dashboard-hero h3 {
  margin: 0;
  font-size: 28px;
  letter-spacing: 0;
}

.dashboard-hero p {
  max-width: 720px;
  margin: 0;
  color: var(--pc-text-muted);
}

.dashboard-insights,
.dashboard-kpi-grid {
  display: grid;
  gap: 12px;
}

.dashboard-insights {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.dashboard-insight,
.dashboard-kpi-card,
.dashboard-panel {
  border: 1px solid var(--pc-border);
  background: var(--pc-surface);
}

.dashboard-insight {
  min-height: 92px;
  padding: 14px;
  border-radius: 16px;
}

.dashboard-insight span,
.dashboard-kpi-card span {
  display: block;
  color: var(--pc-text-muted);
  font-size: 13px;
}

.dashboard-insight strong {
  display: block;
  margin-top: 10px;
  color: var(--pc-text);
  font-size: 18px;
}

.dashboard-insight.brand strong,
.dashboard-insight.success strong {
  color: var(--pc-brand);
}

.dashboard-kpi-grid {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.dashboard-kpi-card {
  display: flex;
  gap: 14px;
  min-height: 128px;
  padding: 18px;
  border-radius: 18px;
}

.dashboard-kpi-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: var(--pc-surface-accent);
  color: var(--pc-brand);
}

.dashboard-kpi-card strong {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.1;
}

.dashboard-kpi-card p {
  margin: 8px 0 0;
  color: var(--pc-text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.dashboard-main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(300px, 0.75fr);
  gap: 18px;
}

.dashboard-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(320px, 0.8fr);
  gap: 18px;
}

.dashboard-panel {
  min-height: 0;
  padding: 20px;
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.dashboard-chart-shell {
  min-height: 330px;
}

.dashboard-trend-svg {
  display: block;
  width: 100%;
  height: 280px;
}

.dashboard-grid-line {
  stroke: #e5edf7;
  stroke-width: 1;
}

.dashboard-token-bar {
  fill: #e8f1ff;
}

.dashboard-area-fill {
  fill: rgba(37, 99, 235, 0.08);
}

.dashboard-line {
  fill: none;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.dashboard-line.model,
.dashboard-dot.model {
  stroke: var(--pc-brand);
  fill: var(--pc-brand);
}

.dashboard-line.tool {
  stroke: #16a34a;
}

.dashboard-line.task {
  stroke: #f59e0b;
}

.dashboard-axis-labels,
.dashboard-legend {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--pc-text-muted);
  font-size: 12px;
}

.dashboard-legend {
  justify-content: flex-start;
  margin-top: 14px;
  flex-wrap: wrap;
}

.dashboard-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dashboard-legend i {
  width: 10px;
  height: 10px;
  border-radius: 999px;
}

.legend-model {
  background: var(--pc-brand);
}

.legend-tool {
  background: #16a34a;
}

.legend-task {
  background: #f59e0b;
}

.legend-token {
  background: #e8f1ff;
  border: 1px solid var(--pc-border);
}

.dashboard-donut-wrap {
  display: grid;
  justify-items: center;
  gap: 18px;
}

.dashboard-donut {
  display: grid;
  place-items: center;
  width: 210px;
  height: 210px;
  border-radius: 50%;
}

.dashboard-donut > div {
  display: grid;
  place-items: center;
  width: 128px;
  height: 128px;
  border-radius: 50%;
  background: var(--pc-surface);
  border: 1px solid var(--pc-border);
}

.dashboard-donut strong {
  font-size: 32px;
  line-height: 1;
}

.dashboard-donut span {
  margin-top: 4px;
  color: var(--pc-text-muted);
  font-size: 13px;
}

.dashboard-status-list,
.dashboard-rank-list,
.dashboard-tool-list,
.dashboard-timeline {
  display: grid;
  gap: 14px;
}

.dashboard-status-list {
  width: 100%;
}

.dashboard-status-row,
.dashboard-rank-head,
.dashboard-rank-meta,
.dashboard-tool-row,
.dashboard-tool-side {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dashboard-status-row span {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--pc-text-secondary);
}

.dashboard-status-row i {
  width: 9px;
  height: 9px;
  border-radius: 999px;
}

.dashboard-rank-row {
  display: grid;
  gap: 8px;
}

.dashboard-rank-head strong,
.dashboard-tool-row strong,
.dashboard-event-row strong {
  color: var(--pc-text);
}

.dashboard-rank-head span,
.dashboard-rank-meta,
.dashboard-tool-row span,
.dashboard-event-row span {
  color: var(--pc-text-muted);
  font-size: 12px;
}

.dashboard-rank-track,
.dashboard-tool-meter {
  height: 8px;
  border-radius: 999px;
  overflow: hidden;
  background: #e8eef8;
}

.dashboard-rank-track i,
.dashboard-tool-meter i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--pc-brand);
}

.dashboard-tool-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 120px 62px;
  min-height: 56px;
}

.dashboard-tool-row > div:first-child {
  min-width: 0;
}

.dashboard-tool-row strong,
.dashboard-tool-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-tool-side {
  display: grid;
  justify-items: end;
  gap: 2px;
}

.dashboard-event-row {
  position: relative;
  display: grid;
  grid-template-columns: 14px minmax(0, 1fr);
  gap: 12px;
}

.dashboard-event-row > i {
  width: 10px;
  height: 10px;
  margin-top: 6px;
  border-radius: 999px;
  background: var(--pc-brand);
}

.dashboard-event-row > i.success {
  background: var(--pc-success-text);
}

.dashboard-event-row > i.warning {
  background: var(--pc-warning-text);
}

.dashboard-event-row > i.danger {
  background: var(--pc-danger-text);
}

.dashboard-event-row p {
  margin: 4px 0;
  color: var(--pc-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

@media (max-width: 1500px) {
  .dashboard-hero,
  .dashboard-main-grid,
  .dashboard-detail-grid {
    grid-template-columns: 1fr;
  }

  .dashboard-kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.page-shell.dashboard-shell {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
  overflow: hidden !important;
  background: #f8fafd;
}

.dashboard-header {
  align-items: center;
  margin-bottom: 18px;
  padding: 0;
}

.dashboard-header h2 {
  font-size: 28px;
  line-height: 1.15;
}

.dashboard-actions :deep(.el-select .el-select__wrapper),
.dashboard-actions :deep(.el-button) {
  min-height: 36px;
  border-radius: 8px;
}

.dashboard-page-stack {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: 130px minmax(0, 1fr) minmax(0, 1fr);
  gap: 18px;
  overflow: hidden;
}

.dashboard-kpi-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.dashboard-kpi-card {
  min-height: 0;
  height: 130px;
  align-items: flex-start;
  padding: 18px 20px;
  border-radius: 12px;
  overflow: hidden;
}

.dashboard-kpi-icon {
  width: 38px;
  height: 38px;
  border-radius: 999px;
}

.dashboard-kpi-card strong {
  margin-top: 22px;
  font-size: 28px;
}

.dashboard-kpi-card p {
  margin-top: 4px;
  color: #667085;
  line-height: 1.25;
  white-space: nowrap;
}

.dashboard-kpi-card.info .dashboard-kpi-icon {
  background: #ecfdf3;
  color: #10b981;
}

.dashboard-kpi-card.success .dashboard-kpi-icon {
  background: #f1e8ff;
  color: #8b5cf6;
}

.dashboard-kpi-card.warning .dashboard-kpi-icon {
  background: #fff7e8;
  color: #f97316;
}

.dashboard-main-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.72fr) minmax(330px, 0.78fr);
  gap: 18px;
}

.dashboard-detail-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(300px, 0.84fr) minmax(300px, 0.84fr);
  gap: 18px;
}

.dashboard-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 22px;
  border-radius: 20px;
  overflow: hidden;
}

.section-title-row {
  align-items: flex-start;
  flex-shrink: 0;
  gap: 14px;
  margin-bottom: 12px;
}

.section-title-row h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
}

.section-title-row p {
  margin: 8px 0 0;
  color: #667085;
  font-size: 12px;
  line-height: 1.3;
}

.dashboard-chart-shell {
  position: relative;
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 18px;
}

.dashboard-peak-label {
  position: absolute;
  top: 0;
  left: 28px;
  color: #98a2b3;
  font-size: 11px;
}

.dashboard-trend-svg {
  flex: 1;
  width: 100%;
  height: auto;
  min-height: 0;
}

.dashboard-area-fill {
  fill: rgba(37, 99, 235, 0.1);
}

.dashboard-axis-labels {
  flex-shrink: 0;
  padding: 0 26px;
}

.dashboard-legend {
  margin: 0;
  justify-content: flex-end;
  flex-wrap: nowrap;
  font-size: 12px;
}

.legend-token {
  display: none;
}

.dashboard-status-panel {
  min-width: 0;
}

.dashboard-donut-wrap {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(132px, 172px) minmax(0, 1fr);
  align-items: center;
  gap: 24px;
}

.dashboard-donut {
  width: 172px;
  height: 172px;
  box-shadow: inset 0 0 0 14px #edf1f7;
}

.dashboard-donut > div {
  width: 108px;
  height: 108px;
}

.dashboard-donut strong {
  font-size: 26px;
}

.dashboard-status-list {
  width: 100%;
  gap: 16px;
}

.dashboard-status-row {
  font-size: 14px;
}

.dashboard-scroll-area {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding-right: 6px;
}

.dashboard-scroll-area::-webkit-scrollbar {
  width: 6px;
}

.dashboard-scroll-area::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #d9e2ec;
}

.dashboard-rank-list {
  gap: 17px;
}

.dashboard-rank-row {
  gap: 8px;
}

.dashboard-rank-head strong,
.dashboard-rank-head span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-rank-head strong {
  min-width: 0;
  font-size: 14px;
}

.dashboard-rank-head span {
  color: #182230;
  font-size: 13px;
  font-weight: 700;
}

.dashboard-rank-track {
  height: 8px;
}

.dashboard-rank-meta {
  color: #667085;
  font-size: 12px;
}

.dashboard-tool-head,
.dashboard-tool-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 58px 68px;
  gap: 10px;
  align-items: center;
}

.dashboard-tool-head {
  flex-shrink: 0;
  padding: 0 6px 10px 0;
  color: #98a2b3;
  font-size: 11px;
  font-weight: 700;
  border-bottom: 1px solid #edf1f7;
}

.dashboard-tool-list {
  gap: 0;
}

.dashboard-tool-row {
  min-height: 48px;
  border-bottom: 1px solid #edf1f7;
}

.dashboard-tool-name {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.dashboard-tool-name i {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
  border-radius: 999px;
}

.dashboard-tool-row strong,
.dashboard-tool-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-tool-row > span {
  color: #475467;
  text-align: right;
}

.dashboard-tool-row > strong {
  color: #047857;
  text-align: right;
}

.dashboard-tool-row > strong.danger {
  color: #b42318;
}

.dashboard-timeline {
  position: relative;
  gap: 0;
}

.dashboard-timeline::before {
  content: "";
  position: absolute;
  top: 10px;
  bottom: 10px;
  left: 8px;
  width: 2px;
  background: #edf1f7;
}

.dashboard-event-row {
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: start;
  min-height: 58px;
  padding-bottom: 12px;
}

.dashboard-event-row > i {
  z-index: 1;
  width: 16px;
  height: 16px;
  margin-top: 3px;
  border: 3px solid #dbeafe;
  background: #ffffff;
}

.dashboard-event-row > i.success {
  border-color: #bbf7d0;
}

.dashboard-event-row > i.warning {
  border-color: #fed7aa;
}

.dashboard-event-row > i.danger {
  border-color: #fecaca;
}

.dashboard-event-row strong {
  display: block;
  margin-top: 4px;
  overflow: hidden;
  color: #182230;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-event-row p {
  display: -webkit-box;
  margin: 4px 0 0;
  overflow: hidden;
  color: #667085;
  font-size: 12px;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.dashboard-event-row em {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 48px;
  height: 22px;
  padding: 0 12px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
}

.dashboard-event-row em.success {
  background: #ecfdf3;
  color: #047857;
}

.dashboard-event-row em.warning {
  background: #fff7e8;
  color: #b54708;
}

.dashboard-event-row em.danger {
  background: #fef3f2;
  color: #b42318;
}
</style>
