<script setup lang="ts">
import type { ResearchTaskDTO } from '../../types/tasks'

defineProps<{
  task: ResearchTaskDTO
}>()
</script>

<template>
  <article class="task-item">
    <div>
      <h4>{{ task.title }}</h4>
      <p>{{ task.subtitle }}</p>
    </div>
    <span class="task-status" :class="task.status">
      {{
        task.status === 'queued'
          ? '待执行'
          : task.status === 'running'
            ? '执行中'
            : task.status === 'paused'
              ? '已暂停'
              : task.status === 'completed'
                ? '已完成'
                : '失败'
      }}
    </span>
  </article>
</template>
