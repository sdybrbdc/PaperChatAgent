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

<style lang="scss" scoped>
.sidebar {
  display: flex;
  flex-direction: row;
  height: 100vh;
  width: 280px;
  gap: 0;
  overflow: hidden;
  background: var(--pc-surface);
  border-right: 1px solid var(--pc-border);
  transition: width 0.2s ease;

  &.chat-open {
    width: 590px;
  }

  &.collapsed {
    width: 72px;
  }
}

.sidebar-nav-rail {
  display: flex;
  flex: 0 0 280px;
  min-width: 0;
  height: 100vh;
  flex-direction: column;
  gap: 20px;
  padding: 22px 16px;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(37, 99, 235, 0.035), rgba(255, 255, 255, 0) 22%),
    var(--pc-surface);

  .sidebar.collapsed & {
    flex-basis: 72px;
    align-items: center;
    padding: 22px 12px;
  }
}

.sidebar-brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
}

.sidebar-logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--pc-brand);
  color: #fff;
  font-size: 17px;
  font-weight: 700;
}

.sidebar-brand-copy {
  min-width: 0;
  flex: 1;

  h1 {
    margin: 0;
    color: var(--pc-text);
    font-size: 19px;
    font-weight: 700;
    line-height: 1.2;
  }

  p {
    margin: 5px 0 0;
    color: var(--pc-text-muted);
    font-size: 12px;
  }
}

.collapse-toggle {
  margin-left: auto;
}

.sidebar-nav-groups {
  display: grid;
  align-content: start;
  gap: 20px;
  min-height: 0;
  flex: 1;
  overflow-y: auto;

  .sidebar.collapsed & {
    width: 100%;
  }
}

.sidebar-nav-group {
  display: grid;
  gap: 8px;
}

.sidebar-group-title {
  padding: 0 8px;
  color: var(--pc-text-muted);
  font-size: 12px;
  font-weight: 600;
}

.sidebar-nav-button {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 46px;
  gap: 12px;
  padding: 0 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: var(--pc-text-secondary);
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease;

  &:hover {
    background: rgba(37, 99, 235, 0.06);
  }

  &.active {
    background: var(--pc-brand-soft);
    color: var(--pc-brand);
    font-weight: 700;
  }

  .el-icon {
    flex: 0 0 auto;
    font-size: 18px;
  }

  span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 14px;
  }

  .sidebar.collapsed & {
    justify-content: center;
    width: 48px;
    padding: 0;
  }
}

.sidebar-user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface-soft);

  &.compact {
    justify-content: center;
    width: 48px;
    padding: 8px 0;
    border-color: transparent;
    background: transparent;
  }
}

.sidebar-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--pc-brand);
  color: #fff;
  font-weight: 700;
}

.sidebar-user-copy {
  strong {
    display: block;
    color: var(--pc-text);
    font-size: 13px;
    font-weight: 700;
  }

  span {
    display: block;
    margin-top: 2px;
    color: var(--pc-text-muted);
    font-size: 12px;
  }
}

.sidebar-footer-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-top: 2px;

  .sidebar.collapsed & {
    flex-direction: column;
  }
}

.sidebar-icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  border: 1px solid var(--pc-border);
  border-radius: 10px;
  background: var(--pc-surface);
  color: var(--pc-text-secondary);
  cursor: pointer;

  &:hover {
    color: var(--pc-brand);
    border-color: rgba(37, 99, 235, 0.28);
  }
}

.sidebar-logout-button {
  width: 36px;
  min-width: 36px;
  padding: 0;

  &:hover {
    color: var(--pc-danger-text);
    border-color: rgba(217, 45, 32, 0.25);
    background: var(--pc-danger-bg);
  }
}

.sidebar-chat-panel {
  display: flex;
  flex: 0 0 310px;
  min-width: 0;
  height: 100vh;
  flex-direction: column;
  padding: 82px 18px 22px;
  border-left: 1px solid var(--pc-border);
  background: rgba(248, 250, 253, 0.72);
}

.sidebar-chat-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 24px;

  .new-chat-button {
    flex: 1;
    margin: 0;
    min-height: 44px;
  }
}

.sidebar-chat-heading {
  margin-bottom: 12px;
  color: var(--pc-text-muted);
  font-size: 13px;
  font-weight: 700;
}

.sidebar-chat-scroll {
  display: grid;
  align-content: start;
  flex: 1;
  min-height: 0;
  gap: 10px;
  overflow-y: auto;
  padding-right: 4px;
}

.chat-session-item {
  display: grid;
  gap: 6px;
  width: 100%;
  padding: 14px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--pc-text);
  text-align: left;
  cursor: pointer;

  &:hover,
  &.active {
    border-color: rgba(37, 99, 235, 0.22);
    background: var(--pc-brand-soft);
  }

  strong {
    overflow: hidden;
    color: var(--pc-text);
    font-size: 14px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  span {
    color: var(--pc-text-muted);
    font-size: 12px;
  }
}

.chat-session-empty {
  color: var(--pc-text-muted);
  font-size: 12px;
}

.view-all-chat-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 42px;
  margin-top: 18px;
  border: 1px solid var(--pc-border);
  border-radius: 12px;
  background: var(--pc-surface);
  color: var(--pc-text-secondary);
  cursor: pointer;
}

.new-chat-button {
  width: 100%;
  margin: 12px 0;
}
</style>
