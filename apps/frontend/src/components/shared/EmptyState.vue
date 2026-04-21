<script setup lang="ts">
defineProps<{
  text: string
}>()
</script>

<template>
  <div class="page-empty">
    <span>{{ text }}</span>
  </div>
</template>
