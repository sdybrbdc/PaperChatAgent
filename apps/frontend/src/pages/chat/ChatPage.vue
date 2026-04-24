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
        <p>中间保持正常聊天，右侧会在每轮回复后更新专业提示，并在需要时手动生成研究方案。</p>
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
