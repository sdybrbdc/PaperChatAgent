<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import type { MessageDTO } from '../../types/chat'

const props = defineProps<{
  message: MessageDTO
}>()

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const renderedContent = computed(() =>
  DOMPurify.sanitize(markdown.render(props.message.content || ''), { USE_PROFILES: { html: true } }),
)

async function handleCopy() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制消息内容')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<template>
  <article class="message-bubble" :class="{ user: message.role === 'user' }">
    <div class="message-header">
      <div class="message-role">
        {{ message.role === 'user' ? '用户' : message.role === 'system' ? '系统' : 'AI 研究助手' }}
      </div>
      <el-button text class="message-copy-button" @click="handleCopy">
        <el-icon><CopyDocument /></el-icon>
      </el-button>
    </div>
    <div class="message-content markdown-body" v-html="renderedContent" />
  </article>
</template>
