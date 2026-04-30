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
        <h3>研究方案</h3>
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
        生成研究方案
      </el-button>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
.guidance-panel {
  grid-column: 2;
  grid-row: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--pc-surface-soft);
  border: 1px solid var(--pc-border);
  border-radius: 22px;
  padding: 20px;
}

.guidance-panel-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}

.guidance-panel-headline {
  margin-bottom: 18px;
  color: var(--pc-text-secondary);
  font-size: 15px;
  line-height: 1.7;
}

.guidance-section {
  padding: 0 0 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--pc-border);

  &:last-child {
    margin-bottom: 0;
    border-bottom: none;
    padding-bottom: 0;
  }

  h3 {
    margin: 0 0 10px;
    font-size: 16px;
  }

  p,
  li,
  span,
  strong {
    font-size: 14px;
    line-height: 1.7;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    color: var(--pc-text-secondary);
  }

  &--warning h3 {
    color: var(--pc-warning-text);
  }

  &--draft {
    background: rgba(37, 99, 235, 0.04);
    border: 1px solid var(--pc-border);
    border-radius: 16px;
    padding: 16px;
  }
}

.guidance-kv {
  display: grid;
  gap: 4px;
  margin-bottom: 10px;
}

.guidance-kv-block {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.guidance-kv strong,
.guidance-kv-block strong {
  color: var(--pc-text);
}

.guidance-error {
  color: var(--pc-danger-text);
  margin: 0 0 12px;
}

.guidance-panel-footer {
  flex-shrink: 0;
  padding-top: 16px;
}

.guidance-draft-button {
  width: 100%;
}
</style>
