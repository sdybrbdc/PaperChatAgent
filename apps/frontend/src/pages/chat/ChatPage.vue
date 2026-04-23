<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import MessageBubble from '../../components/chat/MessageBubble.vue'
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
</script>

<template>
  <section class="page-shell chat-page-shell">
    <header class="page-header">
      <div>
        <h2>{{ conversationStore.currentSession?.title ?? '新聊天' }}</h2>
        <p>先像普通聊天一样了解方向；当问题逐渐清晰时，界面会动态整理研究提示与可执行草案。</p>
      </div>
      <div class="page-actions">
        <el-button>上传资料</el-button>
        <el-button type="primary" @click="handleCreateConversation">
          <el-icon><Plus /></el-icon>
          生成研究草案
        </el-button>
      </div>
    </header>

    <div class="chat-page-layout">
      <div class="chat-surface chat-surface--conversation">
        <div ref="messageViewport" class="message-viewport">
          <div v-if="conversationStore.messages.length" class="message-list">
            <MessageBubble v-for="message in conversationStore.messages" :key="message.id" :message="message" />
          </div>
          <EmptyState v-else text="当前没有消息记录，直接从你的问题开始。" />
        </div>
        <div class="composer composer-fixed">
          <el-button>上传 PDF</el-button>
          <el-input
            v-model="conversationStore.composerText"
            type="textarea"
            :rows="2"
            class="composer-input"
            placeholder="输入研究问题，或继续补充论文、关键词、研究边界..."
          />
          <el-button type="primary" :loading="conversationStore.isStreaming" @click="handleSend">发送</el-button>
        </div>
      </div>
    </div>
  </section>
</template>
