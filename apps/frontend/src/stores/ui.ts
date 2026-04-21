import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', () => {
  const currentNav = ref('chat')
  const featureCollapsed = ref(false)
  const historyCollapsed = ref(false)

  function setCurrentNav(nav: string) {
    currentNav.value = nav
  }

  function toggleFeatureCollapsed() {
    featureCollapsed.value = !featureCollapsed.value
  }

  function toggleHistoryCollapsed() {
    historyCollapsed.value = !historyCollapsed.value
  }

  return {
    currentNav,
    featureCollapsed,
    historyCollapsed,
    setCurrentNav,
    toggleFeatureCollapsed,
    toggleHistoryCollapsed,
  }
})
