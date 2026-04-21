<script setup lang="ts">
import { onMounted } from 'vue'
import MessageBubble from '../../components/chat/MessageBubble.vue'
import TaskSuggestionCard from '../../components/chat/TaskSuggestionCard.vue'
import EmptyState from '../../components/shared/EmptyState.vue'
import RightRailCard from '../../components/shared/RightRailCard.vue'
import { useConversationStore } from '../../stores/conversation'

const conversationStore = useConversationStore()

onMounted(() => {
  conversationStore.load()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <h2>默认聊天页</h2>
        <p>先聊明白研究问题，再确认任务、创建工作区，并把结果沉淀成主题探索包。</p>
      </div>
      <div class="page-actions">
        <el-button>上传资料</el-button>
        <el-button type="primary">查看任务建议</el-button>
      </div>
    </header>

    <div class="workspace-grid">
      <div>
        <div class="chat-surface">
          <div v-if="conversationStore.messages.length" class="message-list">
            <MessageBubble v-for="message in conversationStore.messages" :key="message.id" :message="message" />
            <TaskSuggestionCard v-if="conversationStore.taskSuggestion" :suggestion="conversationStore.taskSuggestion" />
          </div>
          <EmptyState v-else text="当前没有消息记录，先从研究问题开始。" />
        </div>
        <div class="composer">
          <el-button>上传 PDF</el-button>
          <div class="composer-input">输入研究问题，或继续补充论文、关键词、研究边界...</div>
          <el-button type="primary">发送</el-button>
        </div>
      </div>

      <aside class="rail">
        <template v-if="conversationStore.railCards.length">
          <RightRailCard
            v-for="card in conversationStore.railCards"
            :key="card.title"
            :title="card.title"
            :lines="card.lines"
          />
        </template>
        <EmptyState v-else text="任务确认面板暂时无内容。" />
      </aside>
    </div>
  </section>
</template>
