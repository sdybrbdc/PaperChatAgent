<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import AppLogoBlock from './AppLogoBlock.vue'
import { useAuthStore } from '../../stores/auth'
import { useConversationStore } from '../../stores/conversation'
import { useUiStore } from '../../stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const uiStore = useUiStore()

const navItems = [
  { key: 'chat', label: '聊天', to: '/chat' },
  { key: 'knowledge', label: '知识库', to: '/knowledge' },
  { key: 'mcp', label: 'MCP 服务', tag: '预留', disabled: true },
  { key: 'skills', label: 'Skills', tag: '预留', disabled: true },
  { key: 'agents', label: '智能体', to: '/agents' },
  { key: 'tasks', label: '后台任务', to: '/tasks' },
  { key: 'dashboard', label: '数据看板', tag: '预留', disabled: true },
]

const currentUserName = computed(() => authStore.currentUser?.displayName ?? 'sdybdc')

onMounted(() => {
  if (conversationStore.historyGroups.length === 0) {
    conversationStore.load()
  }
})

async function handleLogout() {
  await authStore.logout()
  await router.push('/login')
}
</script>

<template>
  <aside class="sidebar">
    <AppLogoBlock />

    <div class="user-chip">
      <strong>{{ currentUserName }}</strong>
      <span>研究工作台已登录</span>
    </div>

    <section>
      <button class="sidebar-section-trigger" type="button" @click="uiStore.toggleFeatureCollapsed()">
        <span>功能区</span>
        <el-icon>
          <ArrowDown v-if="!uiStore.featureCollapsed" />
          <ArrowRight v-else />
        </el-icon>
      </button>
      <nav v-show="!uiStore.featureCollapsed" class="nav-list">
        <template v-for="item in navItems" :key="item.key">
          <RouterLink
            v-if="!item.disabled"
            :to="item.to!"
            class="nav-item"
            :class="{ active: uiStore.currentNav === item.key }"
          >
            <span>{{ item.label }}</span>
            <span v-if="item.tag" class="nav-item-tag">{{ item.tag }}</span>
          </RouterLink>
          <div v-else class="nav-item disabled">
            <span>{{ item.label }}</span>
            <span v-if="item.tag" class="nav-item-tag">{{ item.tag }}</span>
          </div>
        </template>
      </nav>
    </section>

    <div class="sidebar-history-area">
      <section class="sidebar-history-section">
        <button class="sidebar-section-trigger" type="button" @click="uiStore.toggleHistoryCollapsed()">
          <span>工作区与会话</span>
          <el-icon>
            <ArrowDown v-if="!uiStore.historyCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
        <div v-show="!uiStore.historyCollapsed" class="sidebar-scroll">
          <div class="history-group">
            <template v-for="group in conversationStore.historyGroups" :key="group.id">
              <div v-if="group.type === 'inbox'" class="history-card inbox">
                <p class="history-card-title">{{ group.title }}</p>
                <p class="history-card-subtitle">{{ group.subtitle }}</p>
              </div>
              <div v-else class="workspace-block">
                <h4>{{ group.title }}</h4>
                <div v-for="item in group.items" :key="item" class="workspace-child">{{ item }}</div>
              </div>
            </template>
          </div>
        </div>
      </section>
    </div>

    <div class="sidebar-footer">
      <el-button plain @click="handleLogout">退出登录</el-button>
    </div>
  </aside>
</template>
