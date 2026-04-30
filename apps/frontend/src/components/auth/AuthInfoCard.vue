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

<style lang="scss" scoped>
.info-card {
  width: 360px;
  margin-top: 48px;
  padding: 32px;
  border-radius: 24px;
  background: var(--pc-surface);
  border: 1px solid var(--pc-border);
  box-shadow: var(--pc-shadow);

  h2 {
    margin: 0 0 16px;
    font-size: 36px;
    line-height: 1.1;
  }

  p {
    margin: 0 0 28px;
    color: var(--pc-text-muted);
    font-size: 16px;
  }
}

.info-list {
  display: grid;
  gap: 18px;
  margin: 0 0 28px;
  padding: 0;
  list-style: none;
  font-size: 17px;
}

.info-pill {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border-radius: 999px;
  background: var(--pc-brand-soft);
  color: var(--pc-brand);
  font-size: 14px;
  font-weight: 600;

  &.success {
    background: var(--pc-success-bg);
    color: var(--pc-success-text);
  }
}
</style>
