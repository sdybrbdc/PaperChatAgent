<script setup lang="ts">
import type { KnowledgeBaseDTO } from '../../types/knowledge'

defineProps<{
  section: KnowledgeBaseDTO
  twoColumns?: boolean
}>()
</script>

<template>
  <section class="section-card">
    <h3>{{ section.title }}</h3>
    <p>{{ section.description }}</p>
    <div :class="twoColumns ? 'knowledge-private-grid' : 'knowledge-file-grid'">
      <div v-for="file in section.files" :key="file.id" class="knowledge-file-card">
        <strong>{{ file.title }}</strong>
        <p>{{ file.subtitle }}</p>
      </div>
    </div>
  </section>
</template>
