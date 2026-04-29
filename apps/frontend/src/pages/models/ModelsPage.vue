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
