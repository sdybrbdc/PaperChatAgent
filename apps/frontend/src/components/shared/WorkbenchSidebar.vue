<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  Connection,
  Cpu,
  DataBoard,
  Expand,
  Fold,
  FolderOpened,
  Notebook,
  Plus,
  QuestionFilled,
  Right,
  Setting,
  Tools,
} from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import { useConversationStore } from '../../stores/conversation'
import { useUiStore } from '../../stores/ui'

const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()
const uiStore = useUiStore()

const navGroups = [
  {
    title: '研究',
    items: [
      { key: 'chat', label: '聊天', to: '/chat', icon: ChatDotRound },
      { key: 'agents', label: '智能体', to: '/agents', icon: Cpu },
      { key: 'tasks', label: '后台任务', to: '/tasks', icon: FolderOpened },
    ],
  },
  {
    title: '知识与工具',
    items: [
      { key: 'knowledge', label: '知识库', to: '/knowledge', icon: Notebook },
      { key: 'mcp', label: 'MCP 服务', to: '/mcp', icon: Connection },
      { key: 'skills', label: 'Skills', to: '/skills', icon: Setting },
    ],
  },
  {
    title: '系统配置',
    items: [
      { key: 'models', label: '模型', to: '/models', icon: Tools },
      { key: 'dashboard', label: '数据看板', to: '/dashboard', icon: DataBoard },
    ],
  },
]

const currentUserName = computed(() => authStore.currentUser?.displayName ?? 'sdybdc')
const showChatPanel = computed(() => !uiStore.sidebarCollapsed && uiStore.chatPanelOpen)

async function handleNavClick(item: { key: string; to: string }) {
  if (item.key === 'chat') {
    uiStore.openChatPanel()
    if (!conversationStore.conversations.length) {
      await conversationStore.load()
    }
  }
  await router.push(item.to)
}

async function handleCreateConversation() {
  uiStore.openChatPanel()
  await conversationStore.createNewConversation()
  await router.push('/chat')
}

async function handleSelectConversation(conversationId: string) {
  uiStore.openChatPanel()
  await router.push('/chat')
  await conversationStore.selectConversation(conversationId)
}

async function handleLogout() {
  await authStore.logout()
  await router.push('/login')
}

onMounted(() => {
  if (uiStore.currentNav === 'chat' && !conversationStore.conversations.length) {
    conversationStore.load()
  }
})
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: uiStore.sidebarCollapsed, 'chat-open': showChatPanel }">
    <div class="sidebar-nav-rail">
      <div class="sidebar-brand-row">
        <div class="sidebar-logo-mark">P</div>
        <div v-if="!uiStore.sidebarCollapsed" class="sidebar-brand-copy">
          <h1>PaperChatAgent</h1>
          <p>主题级论文问答工作台</p>
        </div>
        <button class="sidebar-icon-button collapse-toggle" type="button" @click="uiStore.toggleSidebarCollapsed()">
          <el-icon>
            <Expand v-if="uiStore.sidebarCollapsed" />
            <Fold v-else />
          </el-icon>
        </button>
      </div>

      <nav class="sidebar-nav-groups">
        <section v-for="group in navGroups" :key="group.title" class="sidebar-nav-group">
          <div v-if="!uiStore.sidebarCollapsed" class="sidebar-group-title">{{ group.title }}</div>
          <button
            v-for="item in group.items"
            :key="item.key"
            class="sidebar-nav-button"
            :class="{ active: uiStore.currentNav === item.key }"
            :title="uiStore.sidebarCollapsed ? item.label : undefined"
            type="button"
            @click="handleNavClick(item)"
          >
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!uiStore.sidebarCollapsed">{{ item.label }}</span>
          </button>
        </section>
      </nav>

      <div class="sidebar-user-card" :class="{ compact: uiStore.sidebarCollapsed }">
        <div class="sidebar-avatar">A</div>
        <div v-if="!uiStore.sidebarCollapsed" class="sidebar-user-copy">
          <strong>{{ currentUserName }}</strong>
          <span>管理员</span>
        </div>
      </div>

      <div class="sidebar-footer-actions">
        <button class="sidebar-icon-button" type="button" title="设置">
          <el-icon><Setting /></el-icon>
        </button>
        <button class="sidebar-icon-button" type="button" title="帮助">
          <el-icon><QuestionFilled /></el-icon>
        </button>
        <button class="sidebar-icon-button sidebar-logout-button" type="button" title="退出登录" @click="handleLogout">
          <el-icon><Right /></el-icon>
        </button>
      </div>
    </div>

    <section v-if="showChatPanel" class="sidebar-chat-panel">
      <div class="sidebar-chat-actions">
        <el-button class="new-chat-button" type="primary" @click="handleCreateConversation">
          <el-icon><Plus /></el-icon>
          新建对话
        </el-button>
        <button class="sidebar-icon-button" type="button" title="收起聊天栏" @click="uiStore.chatPanelOpen = false">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </div>

      <div class="sidebar-chat-heading">最近对话</div>
      <div class="sidebar-chat-scroll">
        <button
          v-for="session in conversationStore.conversations"
          :key="session.id"
          type="button"
          class="chat-session-item"
          :class="{ active: session.active }"
          @click="handleSelectConversation(session.id)"
        >
          <strong>{{ session.title }}</strong>
          <span>{{ session.active ? '当前对话' : '点击继续研究' }}</span>
        </button>
        <div v-if="!conversationStore.conversations.length" class="chat-session-empty">暂无对话，先新建一个研究问题。</div>
      </div>

      <button class="view-all-chat-button" type="button" @click="router.push('/chat')">
        <span>查看全部对话</span>
        <el-icon><ArrowRight /></el-icon>
      </button>
    </section>
  </aside>
</template>
