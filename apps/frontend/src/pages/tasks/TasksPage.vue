<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Filter, Plus, Refresh } from '@element-plus/icons-vue'
import { createTask, getTaskDetail, getTasks } from '../../apis/tasks'
import type { TaskDTO, TaskDetailDTO } from '../../types/tasks'

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
const pendingCount = computed(() => tasks.value.filter((task) => ['pending', 'queued'].includes(task.status)).length)
const runningCount = computed(() => tasks.value.filter((task) => ['running', 'started'].includes(task.status)).length)
const completedCount = computed(() => tasks.value.filter((task) => ['completed', 'success'].includes(task.status)).length)
const failedCount = computed(() => tasks.value.filter((task) => ['failed', 'error'].includes(task.status)).length)

function statusType(value: string) {
  if (['completed', 'success'].includes(value)) return 'success'
  if (['failed', 'error'].includes(value)) return 'danger'
  if (['running', 'started'].includes(value)) return 'brand'
  if (['paused', 'pending', 'queued'].includes(value)) return 'warning'
  return 'brand'
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 16)
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
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>后台任务</h2>
        <p>承接确认主题后的异步研究任务，追踪检索、解析、建库和主题探索的运行状态。</p>
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
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <section class="metrics-grid">
      <article class="metric-card warning">
        <h4>待执行</h4>
        <strong>{{ String(pendingCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card brand">
        <h4>执行中</h4>
        <strong>{{ String(runningCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card success">
        <h4>已完成</h4>
        <strong>{{ String(completedCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card danger">
        <h4>失败</h4>
        <strong>{{ String(failedCount).padStart(2, '0') }}</strong>
      </article>
    </section>

    <div class="module-content-grid">
      <section class="module-surface">
        <div class="section-title-row">
          <div>
            <h3>研究任务列表</h3>
          </div>
          <div class="page-actions">
            <el-select v-model="status" clearable placeholder="全部状态" style="width: 150px" @change="loadTasks">
              <el-option label="运行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
              <el-option label="暂停" value="paused" />
            </el-select>
            <el-button :loading="isLoading" @click="loadTasks">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
        </div>

        <div v-loading="isLoading" class="module-list">
          <el-empty v-if="!tasks.length && !isLoading" description="暂无任务" />
          <button
            v-for="task in tasks"
            :key="task.id"
            class="module-list-item"
            :class="{ active: selectedTaskId === task.id }"
            type="button"
            @click="selectTask(task.id)"
          >
            <div>
              <h4>{{ task.title || `任务 #${task.id.slice(0, 6)}` }}</h4>
              <p>当前步骤：{{ task.currentNode || task.summary || '等待调度' }}</p>
              <span>{{ task.workflowName || task.workflowId || '未关联工作流' }} · {{ Math.round(task.progress) }}% · {{ formatDate(task.updatedAt || task.createdAt) }}</span>
            </div>
            <strong class="module-list-side" :class="['status-text', statusType(task.status)]">{{ task.status }}</strong>
          </button>
        </div>
      </section>

      <aside class="module-rail">
        <section class="soft-panel module-rail-card">
          <h3>选中任务详情</h3>
          <div v-loading="isDetailLoading">
            <template v-if="detail || selectedTask">
              <p>{{ (detail || selectedTask)?.title || selectedTaskId }}</p>
              <p>工作区：{{ (detail || selectedTask)?.workflowName || (detail || selectedTask)?.workflowId || '-' }}</p>
              <p>状态：{{ (detail || selectedTask)?.status }} · 当前节点：{{ (detail || selectedTask)?.currentNode || '-' }}</p>
              <el-progress :percentage="Math.min(100, Math.max(0, Math.round((detail || selectedTask)?.progress || 0)))" />
            </template>
            <p v-else>请选择一个任务查看详情。</p>
          </div>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>步骤进度</h3>
          <div class="module-mini-list">
            <p v-if="!detail?.nodes.length">暂无节点进度。</p>
            <div v-for="(node, index) in detail?.nodes ?? []" :key="node.id" class="module-mini-item">
              <div>
                <strong>{{ index + 1 }}. {{ node.title || node.nodeId }}</strong>
                <span>{{ node.detail || node.errorText || node.status }}</span>
              </div>
              <span class="module-list-side" :class="['status-text', statusType(node.status)]">{{ node.status }}</span>
            </div>
          </div>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>输出结果</h3>
          <p v-if="!detail?.artifacts.length">预计产物：主题探索包、引用片段、可继续问答上下文。</p>
          <div class="module-mini-list">
            <div v-for="artifact in detail?.artifacts ?? []" :key="artifact.id" class="module-mini-item">
              <div>
                <strong>{{ artifact.title || artifact.artifactType }}</strong>
                <span>{{ artifact.uri || artifact.content || formatDate(artifact.createdAt) }}</span>
              </div>
            </div>
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
