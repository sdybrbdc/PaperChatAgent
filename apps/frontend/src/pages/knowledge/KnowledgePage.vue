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
        <h2>知识库列表</h2>
        <p>按知识库名称管理资料容器。点击某个知识库后，可进入详情页查看相关文件与解析状态。</p>
      </div>
      <div class="page-actions">
        <el-button>上传文件</el-button>
        <el-button type="primary">新建知识库</el-button>
      </div>
    </header>

    <div class="toolbar-search">
      <el-input placeholder="搜索知识库名称、描述或最近上传文件..." />
    </div>

    <div class="knowledge-grid">
      <div style="display: grid; gap: 20px;">
        <KnowledgeSectionCard v-if="knowledgeStore.library" :section="knowledgeStore.library" two-columns />
        <EmptyState v-else text="当前没有资料内容。" />
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
