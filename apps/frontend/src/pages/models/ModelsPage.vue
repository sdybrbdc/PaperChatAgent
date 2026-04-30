<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Box,
  Cpu,
  DataAnalysis,
  Grid,
  More,
  Plus,
  Refresh,
  Setting,
  Switch,
  ArrowUp,
  ArrowDown,
  VideoPlay,
  WarningFilled,
} from '@element-plus/icons-vue'
import { createModelProvider, getModelProviders, getModelRoutes, testModelRoute, updateModelRoute } from '../../apis/models'
import type { ModelProviderDTO, ModelRouteDTO } from '../../types/models'

const providers = ref<ModelProviderDTO[]>([])
const routes = ref<ModelRouteDTO[]>([])
const selectedRouteKey = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const isTesting = ref(false)
const providerVisible = ref(false)
const routeDetailCollapsed = ref(false)
const errorMessage = ref('')
const testPrompt = ref('请用一句话介绍 PaperChatAgent')
const testOutput = ref('')
const routeForm = ref({ providerId: '', modelName: '', temperature: 0, maxTokens: 0 })
const providerForm = ref({
  name: '',
  providerType: 'openai_compatible',
  baseUrl: '',
  apiKeyRef: '',
  status: 'active',
})

const selectedRoute = computed(() => routes.value.find((item) => item.routeKey === selectedRouteKey.value) ?? null)
const selectedProvider = computed(() => {
  const providerId = routeForm.value.providerId || selectedRoute.value?.providerId
  return providers.value.find((provider) => provider.id === providerId) ?? providers.value[0] ?? null
})
const activeProviderCount = computed(() => providers.value.filter((provider) => isActive(provider.status)).length)
const activeRouteCount = computed(() => routes.value.filter((route) => isActive(route.status)).length)
const issueCount = computed(() => {
  return providers.value.filter((provider) => !isActive(provider.status)).length + routes.value.filter((route) => !isActive(route.status)).length
})
const selectedProviderRouteCount = computed(() => {
  if (!selectedProvider.value) return 0
  return routes.value.filter((route) => route.providerId === selectedProvider.value?.id).length
})

function isActive(status: string) {
  return ['active', 'enabled'].includes(status)
}

function syncForm(route: ModelRouteDTO | null) {
  routeForm.value = {
    providerId: route?.providerId ?? providers.value[0]?.id ?? '',
    modelName: route?.modelName ?? '',
    temperature: route?.temperature ?? 0,
    maxTokens: route?.maxTokens ?? 0,
  }
}

function selectRoute(route: ModelRouteDTO) {
  selectedRouteKey.value = route.routeKey
  syncForm(route)
  testOutput.value = ''
}

function routeTypeLabel(route: ModelRouteDTO) {
  const labels: Record<string, string> = {
    chat: 'GPT',
    embedding: 'Embedding',
    reasoning: 'Reasoning',
    rerank: 'Rerank',
  }
  const label = labels[route.modelType] ?? route.modelType
  return label ? label : 'Model'
}

function routeSubtitle(route: ModelRouteDTO) {
  const labels: Record<string, string> = {
    conversation: '对话与生成',
    embedding: '向量嵌入',
    reasoning: '深度推理',
    rerank: '检索重排',
    summary: '文本摘要',
    tool_call: '工具调用',
  }
  return labels[route.routeKey] ?? route.routeKey
}

function routeIcon(route: ModelRouteDTO) {
  if (route.routeKey === 'embedding') return DataAnalysis
  if (route.routeKey === 'reasoning') return Box
  if (route.routeKey === 'rerank') return Grid
  if (route.routeKey === 'tool_call') return Setting
  return Cpu
}

function backupLabel(route: ModelRouteDTO) {
  const fallback = route.config?.fallback_model ?? route.config?.fallbackModel ?? route.config?.backup
  if (fallback) return String(fallback)
  if (route.routeKey === 'embedding') return '本地 embedding'
  if (route.routeKey === 'rerank') return '关闭重排'
  return '按供应商默认降级'
}

function formatDate(value: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function loadData() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [providerItems, routeItems] = await Promise.all([getModelProviders(), getModelRoutes()])
    providers.value = providerItems
    routes.value = routeItems
    if (!selectedRouteKey.value && routeItems.length > 0) selectedRouteKey.value = routeItems[0].routeKey
    syncForm(selectedRoute.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模型配置加载失败'
  } finally {
    isLoading.value = false
  }
}

async function saveRoute() {
  if (!selectedRouteKey.value || !routeForm.value.providerId || !routeForm.value.modelName) {
    ElMessage.warning('请选择供应商并填写模型名')
    return
  }
  isSaving.value = true
  try {
    const updated = await updateModelRoute(selectedRouteKey.value, routeForm.value)
    const index = routes.value.findIndex((item) => item.routeKey === updated.routeKey)
    if (index >= 0) routes.value[index] = updated
    syncForm(updated)
    ElMessage.success('模型路由已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    isSaving.value = false
  }
}

async function runTest() {
  if (!selectedRouteKey.value || !testPrompt.value.trim()) return
  isTesting.value = true
  try {
    const result = await testModelRoute(selectedRouteKey.value, testPrompt.value.trim())
    testOutput.value = result.output || result.message
    ElMessage[result.ok ? 'success' : 'warning'](`耗时 ${result.latencyMs}ms，输出 ${result.outputTokens} tokens`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '模型测试失败')
  } finally {
    isTesting.value = false
  }
}

async function submitProvider() {
  if (!providerForm.value.name.trim()) {
    ElMessage.warning('请输入供应商名称')
    return
  }
  try {
    const created = await createModelProvider({
      name: providerForm.value.name.trim(),
      providerType: providerForm.value.providerType,
      baseUrl: providerForm.value.baseUrl.trim(),
      apiKeyRef: providerForm.value.apiKeyRef.trim(),
      status: providerForm.value.status,
    })
    providers.value.unshift(created)
    if (!routeForm.value.providerId) routeForm.value.providerId = created.id
    providerVisible.value = false
    providerForm.value = { name: '', providerType: 'openai_compatible', baseUrl: '', apiKeyRef: '', status: 'active' }
    ElMessage.success('模型供应商已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建供应商失败')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="page-shell model-page-shell">
    <header class="module-header model-page-header">
      <div>
        <h2>模型</h2>
        <p>配置逻辑模型槽位与供应商路由，为对话、工具调用、推理和检索链路提供统一的模型基础设施。</p>
      </div>
      <div class="page-actions">
        <el-button @click="providerVisible = true">
          <el-icon><Plus /></el-icon>
          新增供应商
        </el-button>
        <el-button type="primary" :disabled="!selectedRouteKey" :loading="isSaving" @click="saveRoute">
          保存路由配置
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <div class="model-layout">
      <main class="model-main-column">
        <section class="model-stat-grid">
          <article class="model-stat-card blue">
            <span class="model-stat-icon"><el-icon><Box /></el-icon></span>
            <div>
              <span>槽位数</span>
              <strong>{{ routes.length }}</strong>
              <small>已配置模型槽位</small>
            </div>
          </article>
          <article class="model-stat-card green">
            <span class="model-stat-icon"><el-icon><Switch /></el-icon></span>
            <div>
              <span>供应商</span>
              <strong>{{ providers.length }}</strong>
              <small>可用供应商</small>
            </div>
          </article>
          <article class="model-stat-card violet">
            <span class="model-stat-icon"><el-icon><Grid /></el-icon></span>
            <div>
              <span>启用模型</span>
              <strong>{{ activeRouteCount }}</strong>
              <small>当前启用模型数</small>
            </div>
          </article>
          <article class="model-stat-card orange">
            <span class="model-stat-icon"><el-icon><WarningFilled /></el-icon></span>
            <div>
              <span>异常</span>
              <strong>{{ issueCount }}</strong>
              <small>最近失败模型</small>
            </div>
          </article>
        </section>

        <section class="model-slot-panel" v-loading="isLoading">
          <div class="model-section-head">
            <h3>槽位配置</h3>
            <el-button :loading="isLoading" @click="loadData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>

          <div class="model-slot-table">
            <div class="model-slot-table-header">
              <span>槽位名称</span>
              <span>当前模型</span>
              <span>类型</span>
              <span>备用策略</span>
              <span>状态</span>
              <span></span>
            </div>
            <el-empty v-if="!routes.length && !isLoading" description="暂无模型路由" />
            <button
              v-for="route in routes"
              :key="route.routeKey"
              class="model-slot-row"
              :class="{ active: selectedRouteKey === route.routeKey }"
              type="button"
              @click="selectRoute(route)"
            >
              <span class="model-slot-name">
                <span class="model-slot-icon">
                  <el-icon><component :is="routeIcon(route)" /></el-icon>
                </span>
                <span>
                  <strong>{{ route.label || route.routeKey }}</strong>
                  <small>{{ routeSubtitle(route) }}</small>
                </span>
              </span>
              <span>
                <strong>{{ route.modelName || '未配置模型' }}</strong>
              </span>
              <span><em class="model-type-pill">{{ routeTypeLabel(route) }}</em></span>
              <span>{{ backupLabel(route) }}</span>
              <span class="model-health-dot">
                <i></i>
                {{ isActive(route.status) ? '正常' : route.status }}
              </span>
              <span class="model-slot-more">
                <el-button text circle @click.stop>
                  <el-icon><More /></el-icon>
                </el-button>
              </span>
            </button>
          </div>
        </section>

        <section class="model-route-detail-card" :class="{ collapsed: routeDetailCollapsed }">
          <div class="model-section-head">
            <h3>槽位详情 · {{ selectedRoute?.label || '请选择槽位' }}</h3>
            <div class="model-route-detail-actions">
              <el-button :disabled="!selectedRouteKey || routeDetailCollapsed" :loading="isTesting" @click="runTest">
                <el-icon><VideoPlay /></el-icon>
                测试当前槽位
              </el-button>
              <el-button circle @click="routeDetailCollapsed = !routeDetailCollapsed">
                <el-icon>
                  <component :is="routeDetailCollapsed ? ArrowUp : ArrowDown" />
                </el-icon>
              </el-button>
            </div>
          </div>
          <template v-if="selectedRoute && !routeDetailCollapsed">
            <div class="model-route-detail-grid">
              <div class="model-route-facts">
                <div>
                  <span>槽位名称</span>
                  <strong>{{ selectedRoute.label || selectedRoute.routeKey }}</strong>
                </div>
                <div>
                  <span>模型名称</span>
                  <strong>{{ routeForm.modelName || selectedRoute.modelName }}</strong>
                </div>
                <div>
                  <span>模型 ID</span>
                  <strong>{{ selectedRoute.id }}</strong>
                </div>
              </div>
              <div class="model-route-form">
                <label>
                  <span>供应商</span>
                  <el-select v-model="routeForm.providerId" filterable>
                    <el-option v-for="provider in providers" :key="provider.id" :label="provider.name" :value="provider.id" />
                  </el-select>
                </label>
                <label>
                  <span>模型名</span>
                  <el-input v-model="routeForm.modelName" placeholder="模型名，例如 gpt-5.4" />
                </label>
                <label>
                  <span>Temperature</span>
                  <el-input-number v-model="routeForm.temperature" :min="0" :max="2" :step="0.1" controls-position="right" />
                </label>
                <label>
                  <span>Max Tokens</span>
                  <el-input-number v-model="routeForm.maxTokens" :min="0" :max="200000" :step="512" controls-position="right" />
                </label>
              </div>
            </div>
            <el-input v-model="testOutput" class="model-test-output" type="textarea" :rows="3" readonly placeholder="模型测试输出" />
          </template>
          <p v-else class="model-empty-copy">请选择一个模型槽位。</p>
        </section>
      </main>

      <aside class="model-side-rail">
        <section class="model-side-card provider-card">
          <div class="model-section-head">
            <h3>供应商管理</h3>
          </div>
          <article v-if="selectedProvider" class="model-provider-box">
            <div class="model-provider-head">
              <div>
                <strong>{{ selectedProvider.name }}</strong>
                <em>{{ isActive(selectedProvider.status) ? '启用中' : selectedProvider.status }}</em>
              </div>
              <span class="model-health-dot"><i></i>健康</span>
            </div>
            <p>基础地址 <strong>{{ selectedProvider.baseUrl || '未配置' }}</strong></p>
            <p>类型 <strong>{{ selectedProvider.providerType || '-' }}</strong></p>
            <div class="model-provider-metrics">
              <div>
                <span>模型数量</span>
                <strong>{{ selectedProvider.modelCount || selectedProviderRouteCount }}</strong>
              </div>
              <div>
                <span>最后同步</span>
                <strong>{{ formatDate(selectedProvider.updatedAt || selectedProvider.createdAt) }}</strong>
              </div>
              <div>
                <span>路由优先级</span>
                <strong>{{ selectedRoute?.priority ?? 100 }}</strong>
              </div>
            </div>
          </article>
          <button class="model-provider-add" type="button" @click="providerVisible = true">
            <el-icon><Plus /></el-icon>
            新增提供商
          </button>
        </section>

        <section class="model-side-card">
          <div class="model-side-title-row">
            <h3>路由策略</h3>
            <el-icon><Setting /></el-icon>
          </div>
          <ul class="model-side-list">
            <li>主模型失败时优先切换备用模型。</li>
            <li>后台任务节点恢复会继承上次可用路由。</li>
            <li>重要节点允许按槽位单独覆盖。</li>
          </ul>
        </section>

        <section class="model-side-card">
          <div class="model-side-title-row">
            <h3>健康概览</h3>
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="model-health-grid">
            <div>
              <span>健康供应商</span>
              <strong>{{ activeProviderCount }}</strong>
            </div>
            <div>
              <span>健康度</span>
              <strong>{{ routes.length ? Math.round((activeRouteCount / routes.length) * 100) : 0 }}%</strong>
            </div>
            <div>
              <span>最近失败</span>
              <strong>{{ issueCount }}</strong>
            </div>
            <div>
              <span>当前配置版本</span>
              <strong>route-v{{ routes.length + providers.length }}</strong>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <el-dialog v-model="providerVisible" title="新增模型供应商" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="供应商名称">
          <el-input v-model="providerForm.name" placeholder="例如 OpenAI" />
        </el-form-item>
        <el-form-item label="供应商类型">
          <el-select v-model="providerForm.providerType">
            <el-option label="OpenAI Compatible" value="openai_compatible" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="本地模型" value="local" />
          </el-select>
        </el-form-item>
        <el-form-item label="基础地址">
          <el-input v-model="providerForm.baseUrl" placeholder="https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key 引用">
          <el-input v-model="providerForm.apiKeyRef" placeholder="例如 OPENAI_API_KEY" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="providerForm.status">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="providerVisible = false">取消</el-button>
        <el-button type="primary" @click="submitProvider">保存供应商</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.model-page-shell {
  display: flex;
  min-height: 0;
  flex-direction: column;
  overflow: hidden !important;
}

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

.model-page-header {
  flex-shrink: 0;
  margin-bottom: 18px;
}

.model-page-header > div:first-child {
  min-width: 0;
  flex: 1;
}

.model-page-header p {
  max-width: none;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.model-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  flex-shrink: 0;
  gap: 14px;
  margin-bottom: 18px;
}

.model-stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 96px;
  padding: 18px 20px;
  border: 1px solid var(--pc-border);
  border-radius: 14px;
  background: var(--pc-surface);
}

.model-stat-icon {
  display: grid;
  place-items: center;
  flex: 0 0 50px;
  width: 50px;
  height: 50px;
  border-radius: 16px;
  font-size: 24px;
}

.model-stat-card.blue .model-stat-icon {
  background: #eaf2ff;
  color: var(--pc-brand);
}

.model-stat-card.green .model-stat-icon {
  background: #e8f8ef;
  color: var(--pc-success-text);
}

.model-stat-card.violet .model-stat-icon {
  background: #f1eaff;
  color: #7c3aed;
}

.model-stat-card.orange .model-stat-icon {
  background: #fff1e8;
  color: #ef4444;
}

.model-stat-card span,
.model-stat-card small {
  display: block;
  color: var(--pc-text-muted);
  font-size: 13px;
  font-style: normal;
}

.model-stat-card .model-stat-icon,
.model-slot-name .model-slot-icon {
  display: grid;
  place-items: center;
}

.model-stat-card .model-stat-icon {
  font-size: 24px;
}

.model-stat-icon .el-icon,
.model-slot-icon .el-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1em;
  height: 1em;
}

.model-stat-card strong {
  display: block;
  color: var(--pc-text);
  font-size: 26px;
  line-height: 1.15;
}

.model-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  flex: 1;
  min-height: 0;
  gap: 18px;
  overflow: hidden;
}

.model-main-column {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 18px;
  overflow: hidden;
}

.model-slot-panel,
.model-route-detail-card,
.model-side-card {
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
}

.model-slot-panel {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  padding: 18px;
}

.model-section-head,
.model-side-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.model-section-head h3,
.model-side-card h3 {
  margin: 0;
  color: var(--pc-text);
  font-size: 18px;
}

.model-slot-table {
  min-height: 0;
  flex: 1;
  overflow: auto;
  margin-top: 14px;
  border: 1px solid var(--pc-border);
  border-radius: 12px;
}

.model-slot-table-header,
.model-slot-row {
  display: grid;
  grid-template-columns: minmax(210px, 1.2fr) minmax(240px, 1.4fr) 100px minmax(150px, 1fr) 100px 44px;
  align-items: center;
  min-width: 900px;
}

.model-slot-table-header {
  height: 46px;
  padding: 0 16px;
  color: var(--pc-text-muted);
  font-size: 13px;
  font-weight: 650;
}

.model-slot-row {
  width: 100%;
  min-height: 72px;
  padding: 0 16px;
  border: none;
  border-top: 1px solid var(--pc-border);
  background: var(--pc-surface);
  color: var(--pc-text-secondary);
  text-align: left;
  cursor: pointer;
}

.model-slot-row.active {
  outline: 1px solid var(--pc-brand);
  background: #fbfdff;
}

.model-slot-name {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.model-slot-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #eef4ff;
  color: var(--pc-brand);
  font-size: 23px;
}

.model-slot-row strong,
.model-route-facts strong,
.model-provider-box strong {
  overflow: hidden;
  color: var(--pc-text);
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-slot-row small {
  display: block;
  color: var(--pc-text-muted);
  font-size: 12px;
}

.model-type-pill {
  display: inline-flex;
  padding: 3px 8px;
  border-radius: 7px;
  background: #eaf2ff;
  color: var(--pc-brand);
  font-size: 12px;
  font-style: normal;
  font-weight: 650;
}

.model-health-dot {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--pc-text-secondary);
  font-size: 13px;
}

.model-health-dot i {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #22c55e;
}

.model-slot-more {
  justify-self: end;
}

.model-route-detail-card {
  flex-shrink: 0;
  padding: 18px;
}

.model-route-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 0.9fr);
  gap: 22px;
  margin-top: 16px;
}

.model-route-facts,
.model-route-form,
.model-health-grid,
.model-provider-metrics {
  display: grid;
  gap: 10px;
}

.model-route-facts div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 12px;
  color: var(--pc-text-secondary);
  font-size: 13px;
}

.model-route-facts span,
.model-route-form span,
.model-provider-box p,
.model-provider-metrics span,
.model-health-grid span {
  color: var(--pc-text-muted);
  font-size: 13px;
}

.model-route-form {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.model-route-form label {
  display: grid;
  gap: 6px;
}

.model-test-output {
  margin-top: 14px;
}

.model-empty-copy {
  margin: 12px 0 0;
  color: var(--pc-text-muted);
}

.model-side-rail {
  display: grid;
  align-content: start;
  min-height: 0;
  gap: 14px;
  overflow-y: auto;
  padding-right: 4px;
}

.model-side-rail {
  display: flex;
  height: 100%;
  flex-direction: column;
}

.model-side-rail .model-side-card:last-child {
  flex: 1;
}

.model-side-card {
  padding: 18px;
}

.model-provider-box {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--pc-brand);
  border-radius: 12px;
  background: #fbfdff;
}

.model-provider-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.model-provider-head em {
  margin-left: 8px;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--pc-success-bg);
  color: var(--pc-success-text);
  font-size: 12px;
  font-style: normal;
}

.model-provider-box p {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
}

.model-provider-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding-top: 12px;
  border-top: 1px solid var(--pc-border);
}

.model-provider-metrics div,
.model-health-grid div {
  display: grid;
  gap: 4px;
}

.model-provider-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  margin-top: 16px;
  padding: 18px;
  border: 1px dashed #8bb3ff;
  border-radius: 12px;
  background: #fbfdff;
  color: var(--pc-brand);
  cursor: pointer;
}

.model-side-list {
  margin: 14px 0 0;
  padding-left: 18px;
  color: var(--pc-text-secondary);
  font-size: 13px;
  line-height: 1.8;
}

.model-health-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.model-health-grid strong,
.model-provider-metrics strong {
  color: var(--pc-text);
  font-size: 14px;
}
</style>
