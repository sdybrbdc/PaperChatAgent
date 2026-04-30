<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import WorkbenchSidebar from '../components/shared/WorkbenchSidebar.vue'
import { useUiStore } from '../stores/ui'

const route = useRoute()
const uiStore = useUiStore()

const navKey = computed(() => String(route.meta.navKey ?? 'chat'))

watch(
  navKey,
  (value) => {
    uiStore.setCurrentNav(value)
  },
  { immediate: true },
)
</script>

<template>
  <div class="workbench-layout">
    <WorkbenchSidebar />
    <main class="main-area">
      <router-view />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.workbench-layout {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
  background: var(--pc-bg);
}

.main-area {
  min-width: 0;
  height: 100vh;
  padding: 24px;
  overflow: hidden;
}
</style>
