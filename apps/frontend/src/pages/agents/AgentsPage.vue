<script setup lang="ts">
import { onMounted } from 'vue'
import EmptyState from '../../components/shared/EmptyState.vue'
import WorkflowNodeCard from '../../components/agents/WorkflowNodeCard.vue'
import RightRailCard from '../../components/shared/RightRailCard.vue'
import { useAgentsStore } from '../../stores/agents'

const agentsStore = useAgentsStore()

onMounted(() => {
  agentsStore.load()
})
</script>

<template>
  <section class="page-shell">
    <header class="page-header">
      <div>
        <h2>智能体</h2>
        <p>展示预置研究智能体的工作流编排视图，帮助用户理解搜索、阅读、分析与结果回流链路。</p>
      </div>
      <div class="page-actions">
        <el-button>查看节点说明</el-button>
        <el-button type="primary">运行研究智能体</el-button>
      </div>
    </header>

    <div class="workspace-grid">
      <div class="agents-surface">
        <div v-if="agentsStore.nodes.length" class="workflow-grid">
          <WorkflowNodeCard v-for="node in agentsStore.nodes" :key="node.id" :node="node" />
        </div>
        <EmptyState v-else text="当前没有工作流节点定义。" />
      </div>

      <aside class="rail">
        <template v-if="agentsStore.railCards.length">
          <RightRailCard
            v-for="card in agentsStore.railCards"
            :key="card.title"
            :title="card.title"
            :lines="card.lines"
          />
        </template>
        <EmptyState v-else text="当前没有智能体说明内容。" />
      </aside>
    </div>
  </section>
</template>
