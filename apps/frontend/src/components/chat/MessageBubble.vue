<script setup lang="ts">
import type { MessageDTO } from '../../types/chat'

defineProps<{
  message: MessageDTO
}>()
</script>

<template>
  <article class="message-bubble" :class="{ user: message.role === 'user' }">
    <div class="message-role">
      {{ message.role === 'user' ? '用户' : 'AI 研究助手' }}
    </div>
    <p class="message-content">{{ message.content }}</p>
  </article>
</template>
