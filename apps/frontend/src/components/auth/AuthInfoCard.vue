<script setup lang="ts">
defineProps<{
  title: string
  description: string
  items: string[]
  pill: string
  pillClass?: string
}>()
</script>

<template>
  <div class="info-card">
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <ul class="info-list">
      <li v-for="item in items" :key="item">{{ item }}</li>
    </ul>
    <span class="info-pill" :class="pillClass">{{ pill }}</span>
  </div>
</template>
