<script setup lang="ts">
import type { TaskSuggestionDTO } from '../../types/chat'

defineProps<{
  suggestion: TaskSuggestionDTO
}>()
</script>

<template>
  <section class="task-suggestion">
    <h3>{{ suggestion.title }}</h3>
    <p><strong>研究主题：</strong>{{ suggestion.topic }}</p>
    <p><strong>资料来源：</strong>{{ suggestion.sources }}</p>
    <p><strong>关键产物：</strong>{{ suggestion.outputs }}</p>
    <p><strong>下一步：</strong>{{ suggestion.nextStep }}</p>
    <span class="task-chip">{{ suggestion.statusLabel }}</span>
  </section>
</template>
