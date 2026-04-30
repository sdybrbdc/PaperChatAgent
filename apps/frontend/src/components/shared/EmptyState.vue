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

<style lang="scss" scoped>
.page-empty {
  display: grid;
  place-items: center;
  min-height: 240px;
  padding: 32px;
  border-radius: 20px;
  border: 1px dashed var(--pc-border);
  color: var(--pc-text-muted);
  background: rgba(255, 255, 255, 0.4);
}
</style>
