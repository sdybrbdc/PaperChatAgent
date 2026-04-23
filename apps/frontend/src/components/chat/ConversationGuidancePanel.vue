<script setup lang="ts">
import type { ConversationGuidanceDTO } from '../../types/chat'

const props = defineProps<{
  guidance: ConversationGuidanceDTO
  isGeneratingDraft?: boolean
  draftEnabled?: boolean
  guidanceError?: string
}>()

const emit = defineEmits<{
  generateDraft: []
}>()
</script>

<template>
  <aside class="guidance-panel">
    <div class="guidance-panel-scroll">
      <div class="guidance-panel-headline">{{ guidance.headline }}</div>
      <p v-if="guidanceError" class="guidance-error">{{ guidanceError }}</p>

      <section
        v-for="section in guidance.sections"
        :key="section.key"
        class="guidance-section"
        :class="[`guidance-section--${section.style}`]"
      >
        <h3>{{ section.title }}</h3>
        <p v-if="section.text">{{ section.text }}</p>
        <ul v-if="section.items?.length">
          <li v-for="item in section.items" :key="item">{{ item }}</li>
        </ul>
      </section>

      <section v-if="guidance.draft" class="guidance-section guidance-section--draft">
        <h3>研究草案</h3>
        <div class="guidance-kv">
          <strong>标题</strong>
          <span>{{ guidance.draft.title }}</span>
        </div>
        <div class="guidance-kv">
          <strong>主题</strong>
          <span>{{ guidance.draft.topic }}</span>
        </div>
        <div class="guidance-kv">
          <strong>目标</strong>
          <span>{{ guidance.draft.objective }}</span>
        </div>
        <div class="guidance-kv">
          <strong>范围</strong>
          <span>{{ guidance.draft.scope }}</span>
        </div>
        <div class="guidance-kv-block">
          <strong>建议资料</strong>
          <ul>
            <li v-for="item in guidance.draft.suggestedMaterials" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="guidance-kv-block">
          <strong>建议智能体</strong>
          <ul>
            <li v-for="item in guidance.draft.suggestedAgents" :key="item">{{ item }}</li>
          </ul>
        </div>
        <div class="guidance-kv-block">
          <strong>下一步</strong>
          <ul>
            <li v-for="item in guidance.draft.nextActions" :key="item">{{ item }}</li>
          </ul>
        </div>
      </section>
    </div>

    <div class="guidance-panel-footer">
      <el-button
        type="primary"
        class="guidance-draft-button"
        :disabled="!draftEnabled"
        :loading="isGeneratingDraft"
        @click="emit('generateDraft')"
      >
        生成研究草案
      </el-button>
    </div>
  </aside>
</template>
