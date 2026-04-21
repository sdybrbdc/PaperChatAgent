<script setup lang="ts">
defineProps<{
  title: string
  lines: string[]
}>()
</script>

<template>
  <div class="rail-card">
    <h4>{{ title }}</h4>
    <div v-for="line in lines" :key="line">{{ line }}</div>
  </div>
</template>
