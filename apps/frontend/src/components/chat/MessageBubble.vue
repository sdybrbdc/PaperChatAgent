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

const toolCalls = computed(() => props.message.metadata?.tool_calls ?? [])

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
    <div v-if="toolCalls.length" class="message-tool-list">
      <div v-for="tool in toolCalls" :key="tool.capability_key" class="message-tool-item" :class="tool.status">
        <span class="message-tool-kind">{{ tool.kind }}</span>
        <strong>{{ tool.name || tool.capability_key }}</strong>
        <span>{{ tool.summary || tool.reason || '能力已调用' }}</span>
      </div>
    </div>
    <div class="message-content markdown-body" v-html="renderedContent" />
  </article>
</template>

<style lang="scss" scoped>
.message-bubble {
  max-width: 82%;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--pc-surface);
  border: 1px solid var(--pc-border);

  &.user {
    justify-self: end;
    background: var(--pc-brand-soft);
    border-color: transparent;
  }
}

.message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.message-role {
  margin-bottom: 8px;
  color: var(--pc-brand);
  font-size: 13px;
  font-weight: 600;

  .message-bubble.user & {
    color: var(--pc-text-secondary);
  }
}

.message-copy-button {
  min-width: auto !important;
  height: auto !important;
  padding: 0 !important;
}

.message-tool-list {
  display: grid;
  gap: 8px;
  margin: 0 0 12px;
}

.message-tool-item {
  display: grid;
  grid-template-columns: auto minmax(80px, auto) minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--pc-border);
  background: var(--pc-surface-soft);
  color: var(--pc-text-secondary);
  font-size: 13px;

  &.failed {
    background: var(--pc-danger-bg);
    color: var(--pc-danger-text);
  }

  span:last-child {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.message-tool-kind {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--pc-surface-accent);
  color: var(--pc-brand);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.message-content {
  font-size: 16px;
  line-height: 1.6;

  > :first-child {
    margin-top: 0;
  }

  > :last-child {
    margin-bottom: 0;
  }

  pre {
    overflow-x: auto;
    padding: 12px 14px;
    border-radius: 12px;
    background: #0f172a;
    color: #f8fafc;
  }

  code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }

  :not(pre) > code {
    padding: 2px 6px;
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.06);
  }

  blockquote {
    margin: 14px 0;
    padding-left: 14px;
    border-left: 3px solid var(--pc-border);
    color: var(--pc-text-secondary);
  }

  ul,
  ol {
    padding-left: 22px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 8px 10px;
    border: 1px solid var(--pc-border);
    text-align: left;
  }
}
</style>
