import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', () => {
  const currentNav = ref('chat')
  const featureCollapsed = ref(false)
  const historyCollapsed = ref(false)
  const sidebarCollapsed = ref(false)
  const chatPanelOpen = ref(true)

  function setCurrentNav(nav: string) {
    currentNav.value = nav
    chatPanelOpen.value = nav === 'chat'
  }

  function toggleFeatureCollapsed() {
    featureCollapsed.value = !featureCollapsed.value
  }

  function toggleHistoryCollapsed() {
    historyCollapsed.value = !historyCollapsed.value
  }

  function toggleSidebarCollapsed() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    if (sidebarCollapsed.value) {
      chatPanelOpen.value = false
    } else if (currentNav.value === 'chat') {
      chatPanelOpen.value = true
    }
  }

  function openChatPanel() {
    sidebarCollapsed.value = false
    chatPanelOpen.value = true
  }

  return {
    currentNav,
    featureCollapsed,
    historyCollapsed,
    sidebarCollapsed,
    chatPanelOpen,
    setCurrentNav,
    toggleFeatureCollapsed,
    toggleHistoryCollapsed,
    toggleSidebarCollapsed,
    openChatPanel,
  }
})
