<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck,
  Clock,
  Document,
  Download,
  Filter,
  Link,
  Loading,
  More,
  Plus,
  Refresh,
  Warning,
} from '@element-plus/icons-vue'
import { createTask, getTaskDetail, getTasks } from '../../apis/tasks'
import type { TaskDTO, TaskDetailDTO, TaskNodeRunDTO } from '../../types/tasks'

const tasks = ref<TaskDTO[]>([])
const selectedTaskId = ref('')
const detail = ref<TaskDetailDTO | null>(null)
const status = ref('')
const isLoading = ref(false)
const isDetailLoading = ref(false)
const isCreating = ref(false)
const createVisible = ref(false)
const errorMessage = ref('')
const taskForm = ref({
  topic: '',
  workflowId: 'smart_research_assistant',
  conversationId: '',
  maxPapers: 6,
  startBackground: true,
})

const selectedTask = computed(() => tasks.value.find((item) => item.id === selectedTaskId.value) ?? null)
const activeTask = computed<TaskDTO | TaskDetailDTO | null>(() => detail.value ?? selectedTask.value)
const taskNodes = computed(() => detail.value?.nodes ?? [])
const taskArtifacts = computed(() => detail.value?.artifacts ?? [])
const pendingCount = computed(() => tasks.value.filter((task) => ['pending', 'queued'].includes(normalizedStatus(task.status))).length)
const runningCount = computed(() => tasks.value.filter((task) => ['running', 'started'].includes(normalizedStatus(task.status))).length)
const completedCount = computed(() => tasks.value.filter((task) => ['completed', 'success'].includes(normalizedStatus(task.status))).length)
const failedCount = computed(() => tasks.value.filter((task) => ['failed', 'error'].includes(normalizedStatus(task.status))).length)
const outputPath = computed(() => {
  const task = activeTask.value
  if (!task) return '-'
  const explicit = String(task.output?.output_path ?? task.output?.path ?? task.payload?.output_path ?? '')
  return explicit || `/workspace/outputs/task-${task.id.slice(0, 8)}/`
})
const generatedFileCount = computed(() => {
  const value = activeTask.value?.output?.generated_files
  return Array.isArray(value) ? value.length : taskArtifacts.value.length
})
const selectedTaskRows = computed(() => {
  const task = activeTask.value
  if (!task) return []
  return [
    ['任务 ID', task.id],
    ['任务名称', task.title || `任务 #${task.id.slice(0, 6)}`],
    ['任务类型', task.workflowName || task.workflowId || '研究任务'],
    ['创建时间', formatDate(task.createdAt)],
    ['优先级', priorityLabel(task)],
    ['触发方式', task.conversationId ? '会话触发' : '手动创建'],
  ]
})

function normalizedStatus(value: string) {
  return value.trim().toLowerCase()
}

function statusTone(value: string) {
  const current = normalizedStatus(value)
  if (['completed', 'success'].includes(current)) return 'success'
  if (['failed', 'error', 'canceled'].includes(current)) return 'danger'
  if (['running', 'started'].includes(current)) return 'brand'
  return 'warning'
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    canceled: '已取消',
    completed: '已完成',
    error: '失败',
    failed: '失败',
    pending: '待执行',
    queued: '待执行',
    running: '执行中',
    started: '执行中',
    success: '已完成',
  }
  const label = labels[normalizedStatus(value)] ?? value
  return label ? label : '待执行'
}

function statusIcon(value: string) {
  const tone = statusTone(value)
  if (tone === 'success') return CircleCheck
  if (tone === 'danger') return Warning
  if (tone === 'brand') return Loading
  return Clock
}

function taskNumber(task: TaskDTO) {
  const match = task.title.match(/#?\d+/)
  return match?.[0]?.replace('#', '') ?? task.id.slice(0, 6)
}

function taskSummary(task: TaskDTO) {
  if (task.summary) return task.summary
  const topic = task.payload?.topic ?? task.payload?.request
  return topic ? String(topic) : '等待任务调度'
}

function currentStep(task: TaskDTO) {
  return task.currentNode || task.summary || '等待调度'
}

function priorityLabel(task: TaskDTO) {
  const priority = String(task.payload?.priority ?? task.payload?.importance ?? 'medium')
  if (['high', 'urgent', '高'].includes(priority)) return '高'
  if (['low', '低'].includes(priority)) return '低'
  return '中'
}

function formatDate(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatShortDate(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatDuration(task: TaskDTO) {
  const start = new Date(task.startedAt || task.createdAt || '').getTime()
  const end = new Date(task.completedAt || task.updatedAt || '').getTime()
  if (!start || !end || Number.isNaN(start) || Number.isNaN(end) || end <= start) return '排队中'
  const seconds = Math.max(1, Math.round((end - start) / 1000))
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (minutes <= 0) return `${seconds}s`
  return `${minutes}m ${rest}s`
}

function stepStatusLabel(node: TaskNodeRunDTO) {
  if (node.status === 'completed') return '完成'
  if (['running', 'started'].includes(node.status)) return '进行中'
  if (node.status === 'failed') return '失败'
  return '等待中'
}

async function loadTasks() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    tasks.value = await getTasks({ status: status.value || undefined, limit: 50 })
    if (!selectedTaskId.value && tasks.value.length > 0) await selectTask(tasks.value[0].id)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '任务列表加载失败'
  } finally {
    isLoading.value = false
  }
}

async function selectTask(taskId: string) {
  selectedTaskId.value = taskId
  isDetailLoading.value = true
  try {
    detail.value = await getTaskDetail(taskId)
  } catch (error) {
    detail.value = null
    ElMessage.error(error instanceof Error ? error.message : '任务详情加载失败')
  } finally {
    isDetailLoading.value = false
  }
}

async function submitTask() {
  if (!taskForm.value.topic.trim()) {
    ElMessage.warning('请输入研究主题')
    return
  }
  isCreating.value = true
  try {
    const created = await createTask({
      topic: taskForm.value.topic.trim(),
      workflowId: taskForm.value.workflowId,
      conversationId: taskForm.value.conversationId.trim() || undefined,
      maxPapers: taskForm.value.maxPapers,
      startBackground: taskForm.value.startBackground,
    })
    tasks.value.unshift(created)
    detail.value = created
    selectedTaskId.value = created.id
    createVisible.value = false
    taskForm.value = {
      topic: '',
      workflowId: 'smart_research_assistant',
      conversationId: '',
      maxPapers: 6,
      startBackground: true,
    }
    ElMessage.success('研究任务已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建任务失败')
  } finally {
    isCreating.value = false
  }
}

onMounted(loadTasks)
</script>

<template>
  <div class="page-shell task-page-shell">
    <header class="module-header task-page-header">
      <div>
        <h2>后台任务</h2>
        <p>管理异步研究任务，解析、构建与追踪运行状态。</p>
      </div>
      <div class="page-actions">
        <el-button @click="loadTasks">
          <el-icon><Filter /></el-icon>
          筛选任务
        </el-button>
        <el-button type="primary" @click="createVisible = true">
          <el-icon><Plus /></el-icon>
          创建研究任务
        </el-button>
        <el-button circle>
          <el-icon><More /></el-icon>
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <section class="task-stat-grid">
      <article class="task-stat-card blue">
        <span><el-icon><Clock /></el-icon></span>
        <div>
          <small>待执行</small>
          <strong>{{ pendingCount }}</strong>
          <em>等待调度执行</em>
        </div>
      </article>
      <article class="task-stat-card brand">
        <span><el-icon><Loading /></el-icon></span>
        <div>
          <small>执行中</small>
          <strong>{{ runningCount }}</strong>
          <em>正在执行中</em>
        </div>
      </article>
      <article class="task-stat-card green">
        <span><el-icon><CircleCheck /></el-icon></span>
        <div>
          <small>已完成</small>
          <strong>{{ completedCount }}</strong>
          <em>成功完成</em>
        </div>
      </article>
      <article class="task-stat-card red">
        <span><el-icon><Warning /></el-icon></span>
        <div>
          <small>失败</small>
          <strong>{{ failedCount }}</strong>
          <em>执行失败</em>
        </div>
      </article>
    </section>

    <div class="task-layout">
      <main class="task-list-panel" v-loading="isLoading">
        <div class="task-list-head">
          <h3>研究任务列表</h3>
          <div class="task-list-actions">
            <el-select v-model="status" clearable placeholder="全部状态" @change="loadTasks">
              <el-option label="待执行" value="pending" />
              <el-option label="执行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
              <el-option label="已取消" value="canceled" />
            </el-select>
            <el-button :loading="isLoading" @click="loadTasks">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <div class="task-table-header">
          <span>任务信息</span>
          <span>当前步骤</span>
          <span>创建时间</span>
          <span>状态</span>
          <span></span>
        </div>

        <div class="task-list-scroll">
          <el-empty v-if="!tasks.length && !isLoading" description="暂无任务" />
          <button
            v-for="task in tasks"
            :key="task.id"
            class="task-row-card"
            :class="{ active: selectedTaskId === task.id }"
            type="button"
            @click="selectTask(task.id)"
          >
            <span class="task-row-main">
              <span :class="['task-row-icon', statusTone(task.status)]">
                <el-icon><component :is="statusIcon(task.status)" /></el-icon>
              </span>
              <span>
                <strong>任务 #{{ taskNumber(task) }} · {{ task.title || '研究任务' }}</strong>
                <small>{{ taskSummary(task) }}</small>
              </span>
            </span>
            <span class="task-row-step">
              <strong>{{ currentStep(task) }}</strong>
              <small>{{ statusTone(task.status) === 'brand' ? `正在${currentStep(task)}...` : task.summary || statusLabel(task.status) }}</small>
            </span>
            <span class="task-row-time">
              <strong>{{ formatShortDate(task.createdAt) }}</strong>
              <small>耗时 {{ formatDuration(task) }}</small>
            </span>
            <span>
              <em :class="['task-status-pill', statusTone(task.status)]">{{ statusLabel(task.status) }}</em>
            </span>
            <span class="task-row-more">
              <el-button text circle @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
            </span>
          </button>
        </div>

        <footer class="task-list-footer">
          <span>共 {{ tasks.length }} 条</span>
          <div>
            <el-button text>‹</el-button>
            <strong>1</strong>
            <el-button text>›</el-button>
            <el-button>10 条 / 页</el-button>
          </div>
        </footer>
      </main>

      <aside class="task-side-rail" v-loading="isDetailLoading">
        <section class="task-side-card">
          <div class="task-side-title">
            <h3>选中任务详情</h3>
            <em v-if="activeTask" :class="['task-status-pill', statusTone(activeTask.status)]">{{ statusLabel(activeTask.status) }}</em>
          </div>
          <template v-if="activeTask">
            <div class="task-detail-list">
              <div v-for="[label, value] in selectedTaskRows" :key="label">
                <span>{{ label }}</span>
                <strong>{{ value }}</strong>
              </div>
            </div>
            <p class="task-detail-desc">{{ activeTask.summary || taskSummary(activeTask) }}</p>
          </template>
          <p v-else class="task-empty-copy">请选择一个任务查看详情。</p>
        </section>

        <section class="task-side-card">
          <h3>步骤进度</h3>
          <div class="task-step-list">
            <p v-if="!taskNodes.length">暂无节点进度。</p>
            <div v-for="node in taskNodes" :key="node.id" :class="['task-step-item', statusTone(node.status)]">
              <span></span>
              <strong>{{ node.title || node.nodeId }}</strong>
              <em>{{ stepStatusLabel(node) }}</em>
              <small>{{ node.detail || node.errorText || `${Math.round(node.progress)}%` }}</small>
            </div>
          </div>
        </section>

        <section class="task-side-card">
          <div class="task-side-title">
            <h3>输出结果</h3>
            <em class="task-status-pill warning">部分可用</em>
          </div>
          <div class="task-output-block">
            <span>输出位置</span>
            <strong>{{ outputPath }}</strong>
            <span>生成文件</span>
            <strong>{{ generatedFileCount }}/{{ Math.max(generatedFileCount, 1) }}</strong>
            <span>日志</span>
            <el-button>
              查看运行日志
              <el-icon><Link /></el-icon>
            </el-button>
          </div>
          <div class="task-artifact-list">
            <p v-if="!taskArtifacts.length">暂无输出文件。</p>
            <article v-for="artifact in taskArtifacts" :key="artifact.id">
              <el-icon><Document /></el-icon>
              <div>
                <strong>{{ artifact.title || artifact.artifactType }}</strong>
                <small>{{ artifact.uri || formatDate(artifact.createdAt) }}</small>
              </div>
              <el-button text circle>
                <el-icon><Download /></el-icon>
              </el-button>
            </article>
          </div>
        </section>
      </aside>
    </div>

    <el-dialog v-model="createVisible" title="创建研究任务" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="研究主题">
          <el-input v-model="taskForm.topic" type="textarea" :rows="3" placeholder="例如 多智能体论文问答中的引用可追溯性" />
        </el-form-item>
        <el-form-item label="工作流">
          <el-input v-model="taskForm.workflowId" placeholder="smart_research_assistant" />
        </el-form-item>
        <el-form-item label="关联会话 ID">
          <el-input v-model="taskForm.conversationId" clearable placeholder="可选" />
        </el-form-item>
        <el-form-item label="最大论文数">
          <el-input-number v-model="taskForm.maxPapers" :min="1" :max="20" />
        </el-form-item>
        <el-form-item label="后台启动">
          <el-switch v-model="taskForm.startBackground" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="isCreating" @click="submitTask">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.task-page-shell {
  display: flex;
  min-height: 0;
  flex-direction: column;
  overflow: hidden !important;
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

.task-page-header {
  flex-shrink: 0;
  margin-bottom: 18px;
}

.task-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex-shrink: 0;
  gap: 14px;
  margin-bottom: 18px;
}

.task-stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 96px;
  padding: 18px 20px;
  border: 1px solid var(--pc-border);
  border-radius: 14px;
  background: var(--pc-surface);

  > span {
    display: grid;
    place-items: center;
    flex: 0 0 50px;
    width: 50px;
    height: 50px;
    border-radius: 16px;
    font-size: 24px;
  }

  &.blue > span {
    background: #eaf2ff;
    color: var(--pc-brand);
  }

  &.green > span {
    background: #e8f8ef;
    color: var(--pc-success-text);
  }

  &.brand > span {
    background: #f1eaff;
    color: #7c3aed;
  }

  &.red > span {
    background: #fff1e8;
    color: #ef4444;
  }

  small,
  em {
    display: block;
    color: var(--pc-text-muted);
    font-size: 13px;
    font-style: normal;
  }

  strong {
    display: block;
    color: var(--pc-text);
    font-size: 26px;
    line-height: 1.15;
  }
}

.task-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  flex: 1;
  min-height: 0;
  gap: 18px;
  overflow: hidden;
}

.task-list-panel,
.task-side-card {
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
}

.task-list-head,
.task-side-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-list-head h3,
.task-side-card h3 {
  margin: 0;
  color: var(--pc-text);
  font-size: 18px;
}

.task-row-card strong,
.task-detail-list strong,
.task-output-block strong {
  overflow: hidden;
  color: var(--pc-text);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-row-card small,
.task-detail-list span,
.task-output-block span,
.task-step-item small {
  display: block;
  color: var(--pc-text-muted);
  font-size: 12px;
}

.task-empty-copy {
  margin: 12px 0 0;
  color: var(--pc-text-muted);
}

.task-side-rail {
  display: grid;
  align-content: start;
  min-height: 0;
  gap: 14px;
  overflow-y: auto;
  padding-right: 4px;
}

.task-side-card {
  padding: 18px;
}

.task-list-panel {
  display: flex;
  min-height: 0;
  flex-direction: column;
  padding: 18px;
}

.task-list-actions {
  display: flex;
  align-items: center;
  gap: 10px;

  .el-select {
    width: 150px;
  }
}

.task-table-header,
.task-row-card {
  display: grid;
  grid-template-columns: minmax(330px, 1.55fr) minmax(190px, 0.85fr) minmax(150px, 0.75fr) 120px 44px;
  align-items: center;
  min-width: 890px;
}

.task-table-header {
  flex-shrink: 0;
  margin-top: 18px;
  padding: 0 18px 10px;
  color: var(--pc-text-muted);
  font-size: 13px;
  font-weight: 650;
}

.task-list-scroll {
  display: grid;
  align-content: start;
  min-height: 0;
  gap: 10px;
  overflow: auto;
  padding: 0 4px 4px;
}

.task-row-card {
  width: 100%;
  min-height: 88px;
  padding: 0 18px;
  border: 1px solid var(--pc-border);
  border-radius: 12px;
  background: var(--pc-surface);
  color: var(--pc-text-secondary);
  text-align: left;
  cursor: pointer;

  &.active {
    border-color: var(--pc-brand);
    box-shadow: 0 10px 22px rgba(37, 99, 235, 0.1);
  }
}

.task-row-main {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.task-row-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  font-size: 20px;

  &.brand {
    background: #eaf2ff;
    color: var(--pc-brand);
  }

  &.success {
    background: var(--pc-success-bg);
    color: var(--pc-success-text);
  }

  &.warning {
    background: #eef4ff;
    color: var(--pc-brand);
  }

  &.danger {
    background: var(--pc-danger-bg);
    color: var(--pc-danger-text);
  }
}

.task-row-step,
.task-row-time {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.task-status-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 26px;
  padding: 4px 9px;
  border-radius: 7px;
  font-size: 12px;
  font-style: normal;
  font-weight: 650;

  &.brand {
    background: #eaf2ff;
    color: var(--pc-brand);
  }

  &.success {
    background: var(--pc-success-bg);
    color: var(--pc-success-text);
  }

  &.warning {
    background: var(--pc-warning-bg);
    color: var(--pc-warning-text);
  }

  &.danger {
    background: var(--pc-danger-bg);
    color: var(--pc-danger-text);
  }
}

.task-row-more {
  justify-self: end;
}

.task-list-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding-top: 14px;
  color: var(--pc-text-secondary);
  font-size: 14px;

  div {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  strong {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--pc-brand);
    color: #ffffff;
  }
}

.task-detail-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 14px;

  div {
    display: grid;
    gap: 4px;
    min-width: 0;
  }
}

.task-detail-desc {
  margin: 14px 0 0;
  color: var(--pc-text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.task-step-list {
  display: grid;
  gap: 0;
  margin-top: 12px;

  > p {
    margin: 0;
    color: var(--pc-text-muted);
    font-size: 13px;
  }
}

.task-step-item {
  position: relative;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  grid-template-rows: auto auto;
  gap: 2px 10px;
  padding: 0 0 18px;

  &::before {
    position: absolute;
    top: 20px;
    bottom: 0;
    left: 7px;
    width: 1px;
    background: var(--pc-border);
    content: "";
  }

  &:last-child::before {
    display: none;
  }

  > span {
    grid-row: 1 / 3;
    width: 16px;
    height: 16px;
    margin-top: 2px;
    border: 2px solid var(--pc-border);
    border-radius: 999px;
    background: var(--pc-surface);
  }

  &.brand > span {
    border-color: var(--pc-brand);
    background: var(--pc-brand);
  }

  &.success > span {
    border-color: var(--pc-brand);
    background: var(--pc-brand);
  }

  &.danger > span {
    border-color: var(--pc-danger-text);
    background: var(--pc-danger-text);
  }

  strong {
    color: var(--pc-text-secondary);
    font-size: 13px;
  }

  em {
    color: var(--pc-brand);
    font-size: 12px;
    font-style: normal;
  }
}

.task-output-block {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  gap: 10px 12px;
  margin-top: 12px;
}

.task-artifact-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;

  p {
    margin: 0;
    color: var(--pc-text-muted);
    font-size: 13px;
  }

  article {
    display: grid;
    grid-template-columns: 28px minmax(0, 1fr) 32px;
    align-items: center;
    gap: 10px;
    padding: 10px;
    border: 1px solid var(--pc-border);
    border-radius: 10px;
    background: var(--pc-surface-soft);

    > :deep(.el-icon) {
      color: var(--pc-text-muted);
      font-size: 18px;
    }
  }

  strong {
    display: block;
    overflow: hidden;
    color: var(--pc-text-secondary);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
