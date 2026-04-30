<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import DOMPurify from 'dompurify'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'
import { useAgentsStore } from '../../stores/agents'

const route = useRoute()
const router = useRouter()
const agentsStore = useAgentsStore()
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
let timer: number | undefined

const runId = computed(() => String(route.params.runId ?? ''))
const run = computed(() => agentsStore.currentRun)
const parentNodes = computed(() => run.value?.nodes?.filter((node) => !node.parentNodeId) ?? [])
const renderedReport = computed(() =>
  DOMPurify.sanitize(markdown.render(run.value?.report?.content || ''), { USE_PROFILES: { html: true } }),
)

function statusType(status: string) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function subNodes(parentNodeId: string) {
  return run.value?.nodes?.filter((node) => node.parentNodeId === parentNodeId) ?? []
}

function nodeDescription(metadata: Record<string, unknown>) {
  return String(metadata.description ?? '')
}

async function refresh() {
  await agentsStore.loadRun(runId.value)
}

onMounted(async () => {
  await refresh()
  timer = window.setInterval(() => {
    if (!['completed', 'failed'].includes(run.value?.status ?? '')) {
      refresh()
    }
  }, 3000)
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>智能体运行</h2>
        <p>{{ run?.title ?? '加载中' }}</p>
      </div>
      <div class="page-actions">
        <el-button @click="router.push('/agents')">
          <el-icon><ArrowLeft /></el-icon>
          返回智能体
        </el-button>
        <el-button :loading="agentsStore.isLoading" @click="refresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <el-alert v-if="agentsStore.errorMessage" :title="agentsStore.errorMessage" type="error" show-icon />

    <div class="agents-run-grid" v-loading="agentsStore.isLoading && !run">
      <section class="agents-surface">
        <div class="section-title-row">
          <div>
            <h3>节点进度</h3>
            <p>当前节点：{{ run?.currentNode || '-' }}</p>
          </div>
          <div class="run-status-block">
            <el-tag :type="statusType(run?.status ?? 'pending')">{{ run?.status ?? 'pending' }}</el-tag>
            <el-progress :percentage="run?.progress ?? 0" :stroke-width="8" />
          </div>
        </div>

        <div class="run-node-list">
          <article v-for="node in parentNodes" :key="node.id" class="run-node-item">
            <div>
              <h4>{{ node.title }}</h4>
              <p>{{ node.detail || nodeDescription(node.metadata) || '等待执行' }}</p>
            </div>
            <el-tag :type="statusType(node.status)">{{ node.status }}</el-tag>
            <div v-if="subNodes(node.nodeId).length" class="run-sub-node-list">
              <div v-for="subNode in subNodes(node.nodeId)" :key="subNode.id" class="run-sub-node">
                <span>{{ subNode.title }}</span>
                <el-tag size="small" :type="statusType(subNode.status)">{{ subNode.status }}</el-tag>
              </div>
            </div>
          </article>
        </div>
      </section>

      <aside class="agents-rail">
        <section class="soft-panel agents-rail-card">
          <h3>任务摘要</h3>
          <p>{{ run?.summary || run?.failedReason || '任务正在运行，完成后会生成摘要。' }}</p>
        </section>
        <section class="soft-panel agents-rail-card">
          <h3>运行信息</h3>
          <p>智能体：{{ run?.workflowName ?? '-' }}</p>
          <p>Run ID：{{ run?.id ?? '-' }}</p>
          <p>创建时间：{{ run?.createdAt ?? '-' }}</p>
        </section>
      </aside>
    </div>

    <section class="agents-surface agent-report-surface">
      <div class="section-title-row">
        <div>
          <h3>研究报告</h3>
          <p>智能研究助手完成后会在这里展示最终 Markdown 报告。</p>
        </div>
      </div>
      <div v-if="run?.report?.content" class="markdown-body agent-report-content" v-html="renderedReport" />
      <el-empty v-else description="报告尚未生成" />
    </section>
  </div>
</template>

<style lang="scss" scoped>
.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  flex-shrink: 0;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 28px;
  }

  p {
    max-width: 640px;
    margin: 8px 0 0;
    color: var(--pc-text-muted);
    font-size: 15px;
  }
}

.page-actions {
  display: flex;
  gap: 12px;
}

.run-status-block {
  display: grid;
  grid-template-columns: auto 160px;
  align-items: center;
  gap: 12px;
}

.run-node-list {
  display: grid;
  gap: 14px;
}

.run-node-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 18px 20px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);

  h4 {
    margin: 0;
    font-size: 18px;
  }

  p {
    margin: 6px 0 0;
    color: var(--pc-text-muted);
  }
}

.run-sub-node-list {
  grid-column: 1 / -1;
  display: grid;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid var(--pc-border);
}

.run-sub-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--pc-text-secondary);
  font-size: 14px;
}

.agent-report-surface {
  margin-top: 20px;
}

.agent-report-content {
  padding: 20px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
  line-height: 1.7;
}
</style>
