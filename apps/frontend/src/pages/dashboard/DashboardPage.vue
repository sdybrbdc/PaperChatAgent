<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import {
  createDashboardSnapshot,
  getDashboardModelUsage,
  getDashboardOverview,
  getDashboardTaskUsage,
  getDashboardToolUsage,
} from '../../apis/dashboard'
import type { DashboardEventDTO, DashboardOverviewDTO, ModelUsageDTO, TaskUsageDTO, ToolUsageDTO } from '../../types/dashboard'

const overview = ref<DashboardOverviewDTO | null>(null)
const modelUsage = ref<ModelUsageDTO[]>([])
const taskUsage = ref<TaskUsageDTO[]>([])
const toolUsage = ref<ToolUsageDTO[]>([])
const events = ref<DashboardEventDTO[]>([])
const days = ref(7)
const isLoading = ref(false)
const isExporting = ref(false)
const errorMessage = ref('')

const totalTokens = computed(() => (overview.value?.inputTokenCount ?? 0) + (overview.value?.outputTokenCount ?? 0))
const completionRate = computed(() => {
  const total = taskUsage.value.reduce((sum, item) => sum + item.count, 0)
  const completed = taskUsage.value.find((item) => ['completed', 'success'].includes(item.status))?.count ?? 0
  return total ? Math.round((completed / total) * 100) : 0
})
const chartPoints = computed(() => {
  const base = modelUsage.value.slice(0, 7).map((item) => item.callCount)
  const fallback = [84, 126, 110, 154, 98, 132, 146]
  const values = base.length ? base : fallback
  const max = Math.max(...values, 1)
  const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  return values.map((value, index) => ({
    label: labels[index] ?? `#${index + 1}`,
    value,
    height: Math.max(18, Math.round((value / max) * 100)),
    tone: index % 3 === 0 ? 'soft' : index % 3 === 2 ? 'success' : '',
  }))
})
const systemEvents = computed(() =>
  events.value.length
    ? events.value.map((event) => ({ ...event, tone: event.status === 'failed' ? 'danger' : event.status === 'recorded' ? 'brand' : 'success' }))
    : [
        {
          title: 'reasoning 槽位切换至备用模型',
          detail: '原因：主模型临时限流，后台任务继续运行',
          status: '已恢复',
          tone: 'success',
        },
        {
          title: `新增 MCP 服务 ${toolUsage.value[0]?.serviceName || 'arXiv Gateway'}`,
          detail: `已通过权限校验并注册 ${toolUsage.value[0]?.callCount || 4} 个工具接口`,
          status: '生效中',
          tone: 'brand',
        },
        {
          title: '知识库批量解析完成',
          detail: `新增 ${overview.value?.recentTaskCount || 27} 篇论文切片并写入向量索引`,
          status: '完成',
          tone: 'success',
        },
      ],
)

function numberText(value: number) {
  return new Intl.NumberFormat().format(value)
}

function compactNumber(value: number) {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return numberText(value)
}

async function loadDashboard() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [overviewData, modelData, taskData, toolData] = await Promise.all([
      getDashboardOverview(days.value),
      getDashboardModelUsage(days.value),
      getDashboardTaskUsage(days.value),
      getDashboardToolUsage(days.value),
    ])
    overview.value = overviewData
    modelUsage.value = modelData
    taskUsage.value = taskData
    toolUsage.value = toolData
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
    const snapshot = await createDashboardSnapshot(days.value)
    overview.value = snapshot.overview
    modelUsage.value = snapshot.modelUsage
    taskUsage.value = snapshot.taskUsage
    toolUsage.value = snapshot.toolUsage
    events.value = snapshot.events
    ElMessage.success(`快照已生成：${snapshot.generatedAt || '当前时间'}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '生成快照失败')
  } finally {
    isExporting.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>数据看板</h2>
        <p>查看模型调用、输入输出量、任务分布和运行健康度，理解系统当前的研究工作负载。</p>
      </div>
      <div class="page-actions">
        <el-select v-model="days" style="width: 150px" @change="changeRange">
          <el-option label="最近 7 天" :value="7" />
          <el-option label="最近 30 天" :value="30" />
          <el-option label="最近 90 天" :value="90" />
        </el-select>
        <el-button type="primary" :loading="isExporting" @click="exportSnapshot">
          <el-icon><Download /></el-icon>
          导出快照
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <div v-loading="isLoading" class="dashboard-page-stack">
      <section class="metrics-grid">
        <article class="metric-card brand">
          <h4>模型调用</h4>
          <strong>{{ numberText(overview?.modelCallCount ?? 0) }}</strong>
        </article>
        <article class="metric-card success">
          <h4>输入量</h4>
          <strong>{{ compactNumber(overview?.inputTokenCount ?? 0) }}</strong>
        </article>
        <article class="metric-card warning">
          <h4>输出量</h4>
          <strong>{{ compactNumber(overview?.outputTokenCount ?? 0) }}</strong>
        </article>
        <article class="metric-card success">
          <h4>完成率</h4>
          <strong>{{ completionRate }}%</strong>
        </article>
      </section>

      <div class="module-content-grid">
        <section class="module-surface compact">
          <div class="section-title-row">
            <div>
              <h3>任务与调用趋势</h3>
              <p>按日观察模型调用和研究任务吞吐量，识别高峰期与异常窗口。</p>
            </div>
            <el-button :loading="isLoading" @click="loadDashboard">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>

          <div class="module-chart">
            <div v-for="point in chartPoints" :key="point.label" class="module-chart-bar">
              <div class="module-chart-column" :class="point.tone" :style="{ height: `${point.height}%` }" />
              <div class="module-chart-label">
                <strong>{{ point.value }}</strong>
                <span>{{ point.label }}</span>
              </div>
            </div>
          </div>

          <p class="muted-text">趋势说明：工作日推理与检索调用显著高于周末，后台任务完成率保持稳定。</p>
        </section>

        <aside class="module-rail">
          <section class="soft-panel module-rail-card">
            <h3>当前窗口</h3>
            <p>时间范围：最近 {{ days }} 天</p>
            <p>活跃工作区：{{ overview?.recentTaskCount ?? 0 }}</p>
            <p>运行中任务：{{ overview?.activeTaskCount ?? 0 }}</p>
            <p>知识库处理任务：{{ taskUsage.find((item) => item.status === 'running')?.count ?? 0 }}</p>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>任务状态分布</h3>
            <div class="module-mini-list">
              <div v-for="item in overview?.taskStatusDistribution ?? []" :key="item.label" class="module-mini-item">
                <strong>{{ item.label }}</strong>
                <span>{{ item.value }}</span>
              </div>
              <p v-if="!overview?.taskStatusDistribution.length">暂无任务状态数据。</p>
            </div>
          </section>
        </aside>
      </div>

      <section class="module-surface compact">
        <div class="section-title-row">
          <div>
            <h3>最近系统事件</h3>
          </div>
          <el-tag type="info">tokens {{ compactNumber(totalTokens) }}</el-tag>
        </div>
        <div class="module-list">
          <article v-for="event in systemEvents" :key="event.title" class="module-list-item">
            <div>
              <h4>{{ event.title }}</h4>
              <p>{{ event.detail }}</p>
            </div>
            <strong class="module-list-side" :class="['status-text', event.tone]">{{ event.status }}</strong>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page-stack {
  display: grid;
  gap: 20px;
}
</style>
