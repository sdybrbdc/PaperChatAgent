<script setup lang="ts">
import { onMounted } from 'vue'
import EmptyState from '../../components/shared/EmptyState.vue'
import RightRailCard from '../../components/shared/RightRailCard.vue'
import TaskMetricCard from '../../components/tasks/TaskMetricCard.vue'
import TaskListItem from '../../components/tasks/TaskListItem.vue'
import { useTasksStore } from '../../stores/tasks'

const tasksStore = useTasksStore()

onMounted(() => {
  tasksStore.load()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <h2>后台任务</h2>
        <p>承接确认主题后的异步研究任务，追踪检索、解析、建库和主题探索的运行状态。</p>
      </div>
      <div class="page-actions">
        <el-button>筛选任务</el-button>
        <el-button type="primary">创建研究任务</el-button>
      </div>
    </header>

    <div v-if="tasksStore.metrics.length" class="metrics-grid">
      <TaskMetricCard v-for="metric in tasksStore.metrics" :key="metric.key" :metric="metric" />
    </div>
    <EmptyState v-else text="当前没有任务指标数据。" />

    <div class="workspace-grid">
      <div class="tasks-surface">
        <h3 style="margin: 0 0 16px; font-size: 18px;">研究任务列表</h3>
        <div v-if="tasksStore.tasks.length" class="task-list">
          <TaskListItem v-for="task in tasksStore.tasks" :key="task.id" :task="task" />
        </div>
        <EmptyState v-else text="当前没有后台任务记录。" />
      </div>

      <aside class="rail">
        <template v-if="tasksStore.railCards.length">
          <RightRailCard
            v-for="card in tasksStore.railCards"
            :key="card.title"
            :title="card.title"
            :lines="card.lines"
          />
        </template>
        <EmptyState v-else text="当前没有任务详情说明。" />
      </aside>
    </div>
  </section>
</template>
