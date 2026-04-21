<script setup lang="ts">
import type { WorkflowNodeDTO } from '../../types/agents'

defineProps<{
  node: WorkflowNodeDTO
}>()
</script>

<template>
  <article class="workflow-card" :class="node.tone">
    <h3>{{ node.title }}</h3>
    <p>{{ node.description }}</p>
  </article>
</template>
