<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Connection, DocumentAdd, Plus } from '@element-plus/icons-vue'
import { useAgentsStore } from '../../stores/agents'

const router = useRouter()
const agentsStore = useAgentsStore()

onMounted(() => {
  agentsStore.loadWorkflows()
})

function openWorkflow(workflowId: string) {
  router.push(`/agents/${workflowId}`)
}
</script>

<template>
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>智能体列表</h2>
        <p>查看内置和自定义智能体。点击智能体进入详情页，配置节点模型、执行器和上下游传递规则。</p>
      </div>
      <div class="page-actions">
        <el-button disabled>
          <el-icon><DocumentAdd /></el-icon>
          导入配置
        </el-button>
        <el-button type="primary" disabled>
          <el-icon><Plus /></el-icon>
          新建智能体
        </el-button>
      </div>
    </header>

    <div class="agents-page-grid">
      <section class="agents-surface agents-directory">
        <div class="section-title-row">
          <div>
            <h3>智能体目录</h3>
            <p>智能体既可以是完整流程，也可以是可被节点调用的子 Agent。</p>
          </div>
          <el-tag type="info">{{ agentsStore.workflows.length }} 个可用</el-tag>
        </div>

        <el-alert v-if="agentsStore.errorMessage" :title="agentsStore.errorMessage" type="error" show-icon />

        <div v-loading="agentsStore.isLoading" class="agent-list">
          <button
            v-for="workflow in agentsStore.workflows"
            :key="workflow.id"
            class="agent-list-item"
            type="button"
            @click="openWorkflow(workflow.id)"
          >
            <div>
              <h4>{{ workflow.name }}</h4>
              <p>{{ workflow.description }}</p>
              <span>{{ workflow.nodeCount }} 个节点 · {{ workflow.sourceType === 'builtin' ? '内置流程' : workflow.sourceType }} · v{{ workflow.version }}</span>
            </div>
            <strong>查看详情</strong>
          </button>
        </div>
      </section>

      <aside class="agents-rail">
        <section class="soft-panel agents-rail-card">
          <h3>当前筛选</h3>
          <p>内置：{{ agentsStore.workflows.filter((item) => item.sourceType === 'builtin').length }}</p>
          <p>自定义：0</p>
          <p>项目子 Agent：0</p>
        </section>

        <section class="soft-panel agents-rail-card">
          <h3>使用说明</h3>
          <p>点击智能体进入详情页后，可以查看节点关系、指定执行器，并选择调用其他智能体或项目子 Agent。</p>
        </section>

        <section class="soft-panel agents-rail-card">
          <h3>配置重点</h3>
          <p>节点配置以用户级覆盖保存，不会修改内置智能体定义。</p>
          <el-icon class="rail-icon"><Connection /></el-icon>
        </section>
      </aside>
    </div>
  </div>
</template>
