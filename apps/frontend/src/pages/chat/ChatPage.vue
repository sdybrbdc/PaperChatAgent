<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import MessageBubble from '../../components/chat/MessageBubble.vue'
import ConversationGuidancePanel from '../../components/chat/ConversationGuidancePanel.vue'
import EmptyState from '../../components/shared/EmptyState.vue'
import { useConversationStore } from '../../stores/conversation'

const conversationStore = useConversationStore()
const messageViewport = ref<HTMLElement | null>(null)

onMounted(() => {
  conversationStore.load()
})

watch(
  () => conversationStore.messages.map((message) => `${message.id}-${message.content.length}`).join('|'),
  async () => {
    await nextTick()
    if (messageViewport.value) {
      messageViewport.value.scrollTop = messageViewport.value.scrollHeight
    }
  },
)

async function handleCreateConversation() {
  await conversationStore.createNewConversation()
}

async function handleSend() {
  try {
    await conversationStore.sendCurrentMessage()
    if (conversationStore.errorMessage) {
      ElMessage.error(conversationStore.errorMessage)
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '发送失败')
  }
}

async function handleGenerateDraft() {
  await conversationStore.generateDraft()
  if (conversationStore.guidanceError) {
    ElMessage.error(conversationStore.guidanceError)
  }
}

async function handleComposerKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    await handleSend()
  }
}
</script>

<template>
  <section class="page-shell chat-page-shell">
    <header class="chat-header-fixed">
      <div>
        <h2>{{ conversationStore.currentConversation?.title ?? '新聊天' }}</h2>
        <p>聊天会按需调用知识库、Skills 和 MCP；工具结果会显示在回复气泡顶部。</p>
      </div>
      <div class="page-actions">
        <el-button>上传资料</el-button>
        <el-button type="primary" @click="handleCreateConversation">新聊天</el-button>
      </div>
    </header>

    <div class="chat-content-shell">
      <div class="chat-main-scroll">
        <div ref="messageViewport" class="message-viewport">
          <div v-if="conversationStore.messages.length" class="message-list">
            <MessageBubble v-for="message in conversationStore.messages" :key="message.id" :message="message" />
          </div>
          <EmptyState v-else text="当前没有消息记录，直接从你的问题开始。" />
        </div>
      </div>

      <ConversationGuidancePanel
        :guidance="conversationStore.guidance"
        :is-generating-draft="conversationStore.isGeneratingDraft"
        :draft-enabled="['ready_for_draft', 'draft_ready'].includes(conversationStore.guidance.status)"
        :guidance-error="conversationStore.guidanceError"
        @generate-draft="handleGenerateDraft"
      />

      <div class="chat-composer-bar">
        <el-button>上传文件</el-button>
        <el-input
          v-model="conversationStore.composerText"
          type="textarea"
          :rows="2"
          class="composer-input"
          placeholder="输入研究问题，按回车发送，Shift+Enter 换行..."
          @keydown="handleComposerKeydown"
        />
        <el-button type="primary" :loading="conversationStore.isStreaming" @click="handleSend">发送</el-button>
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.page-shell {
  height: calc(100vh - 48px);
  padding: 24px 28px 28px;
  border-radius: 28px;
  border: 1px solid var(--pc-border);
  background: var(--pc-surface);
  box-shadow: var(--pc-shadow);
  overflow: hidden;

  &:not(.chat-page-shell) {
    overflow-y: auto;
  }
}

.chat-page-shell {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.chat-header-fixed {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-shrink: 0;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 28px;
  }

  p {
    max-width: 640px;
    margin: 8px 0 0;
    color: var(--pc-text-muted);
    font-size: 15px;
  }
}

.page-actions {
  display: flex;
  gap: 12px;
}

.chat-content-shell {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(280px, 3fr);
  grid-template-rows: minmax(0, 1fr) auto;
  flex: 1;
  min-height: 0;
  gap: 20px;
}

.chat-main-scroll {
  min-height: 0;
  overflow: hidden;
  background: var(--pc-surface-soft);
  border: 1px solid var(--pc-border);
  border-radius: 22px;
  padding: 20px;
}

.message-viewport {
  height: 100%;
  overflow-y: auto;
  padding-right: 8px;
}

.message-list {
  display: grid;
  gap: 18px;
}

.chat-composer-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  background: var(--pc-surface);
  border: 1px solid var(--pc-border);
  grid-column: 1 / span 2;
  grid-row: 2;
  margin-top: 0;
}

.composer-input {
  flex: 1;
  color: var(--pc-text-muted);
}
</style>
