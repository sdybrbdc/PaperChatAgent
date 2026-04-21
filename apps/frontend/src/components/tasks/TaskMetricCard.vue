<script setup lang="ts">
import type { TaskMetricDTO } from '../../types/tasks'

defineProps<{
  metric: TaskMetricDTO
}>()
</script>

<template>
  <article class="metric-card" :class="metric.tone">
    <h4>{{ metric.label }}</h4>
    <strong>{{ metric.value }}</strong>
  </article>
</template>
