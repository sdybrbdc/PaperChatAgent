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
        <h2>智能体列表</h2>
        <p>查看内置和自定义智能体。点击智能体后，可进入详情页配置节点模型、执行器与传递规则。</p>
      </div>
      <div class="page-actions">
        <el-button>导入配置</el-button>
        <el-button type="primary">新建智能体</el-button>
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
