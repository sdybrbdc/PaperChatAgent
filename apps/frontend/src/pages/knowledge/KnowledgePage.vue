<script setup lang="ts">
import { onMounted } from 'vue'
import KnowledgeSectionCard from '../../components/knowledge/KnowledgeSectionCard.vue'
import EmptyState from '../../components/shared/EmptyState.vue'
import RightRailCard from '../../components/shared/RightRailCard.vue'
import { useKnowledgeStore } from '../../stores/knowledge'

const knowledgeStore = useKnowledgeStore()

onMounted(() => {
  knowledgeStore.load()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <h2>知识库</h2>
        <p>管理账号内全局知识库与工作区私有补充库，支持 arXiv 引入和 PDF 上传。</p>
      </div>
      <div class="page-actions">
        <el-button>上传 PDF</el-button>
        <el-button type="primary">新建私有库</el-button>
      </div>
    </header>

    <div class="toolbar-search">
      <el-input placeholder="搜索论文标题、作者、来源或工作区..." />
    </div>

    <div class="knowledge-grid">
      <div style="display: grid; gap: 20px;">
        <KnowledgeSectionCard v-if="knowledgeStore.globalBase" :section="knowledgeStore.globalBase" />
        <EmptyState v-else text="当前没有全局知识库内容。" />
        <KnowledgeSectionCard v-if="knowledgeStore.privateBase" :section="knowledgeStore.privateBase" two-columns />
        <EmptyState v-else text="当前工作区还没有私有知识库内容。" />
      </div>

      <aside class="rail">
        <template v-if="knowledgeStore.railCards.length">
          <RightRailCard
            v-for="card in knowledgeStore.railCards"
            :key="card.title"
            :title="card.title"
            :lines="card.lines"
          />
        </template>
        <EmptyState v-else text="当前没有知识库侧边说明。" />
      </aside>
    </div>
  </section>
</template>
