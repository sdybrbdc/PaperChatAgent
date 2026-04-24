<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, ArrowRight, Plus } from '@element-plus/icons-vue'
import AppLogoBlock from './AppLogoBlock.vue'
import { useAuthStore } from '../../stores/auth'
import { useConversationStore } from '../../stores/conversation'
import { useUiStore } from '../../stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const uiStore = useUiStore()

const navItems = [
  { key: 'chat', label: '聊天', to: '/chat', disabled: false },
  { key: 'knowledge', label: '知识库', disabled: true },
  { key: 'mcp', label: 'MCP 服务', disabled: true },
  { key: 'skills', label: 'Skills', disabled: true },
  { key: 'agents', label: '智能体', to: '/agents', disabled: false },
  { key: 'models', label: '模型', disabled: true },
  { key: 'tasks', label: '后台任务', disabled: true },
  { key: 'dashboard', label: '数据看板', disabled: true },
]

const currentUserName = computed(() => authStore.currentUser?.displayName ?? 'sdybdc')

async function handleCreateConversation() {
  await conversationStore.createNewConversation()
  await router.push('/chat')
}

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
      <span>最近会话已同步</span>
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
          <router-link
            v-if="!item.disabled"
            :to="item.to!"
            class="nav-item"
            :class="{ active: uiStore.currentNav === item.key }"
          >
            <span>{{ item.label }}</span>
          </router-link>
          <div v-else class="nav-item disabled">
            <span>{{ item.label }}</span>
          </div>
        </template>
      </nav>
    </section>

    <div class="sidebar-history-area">
      <section class="sidebar-history-section">
        <button class="sidebar-section-trigger" type="button" @click="uiStore.toggleHistoryCollapsed()">
          <span>最近会话</span>
          <el-icon>
            <ArrowDown v-if="!uiStore.historyCollapsed" />
            <ArrowRight v-else />
          </el-icon>
        </button>
        <el-button class="new-chat-button" type="primary" plain @click="handleCreateConversation">
          <el-icon><Plus /></el-icon>
          新聊天
        </el-button>
        <div v-show="!uiStore.historyCollapsed" class="sidebar-scroll">
          <div class="history-group recent-chat-list">
            <button
              v-for="session in conversationStore.conversations"
              :key="session.id"
              type="button"
              class="recent-chat-item"
              :class="{ active: session.active }"
              @click="conversationStore.selectConversation(session.id)"
            >
              <div class="recent-chat-title">{{ session.title }}</div>
            </button>
          </div>
        </div>
      </section>
    </div>

    <div class="sidebar-footer">
      <el-button plain @click="handleLogout">退出登录</el-button>
    </div>
  </aside>
</template>
