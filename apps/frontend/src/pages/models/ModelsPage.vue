<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { createModelProvider, getModelProviders, getModelRoutes, testModelRoute, updateModelRoute } from '../../apis/models'
import type { ModelProviderDTO, ModelRouteDTO } from '../../types/models'

const providers = ref<ModelProviderDTO[]>([])
const routes = ref<ModelRouteDTO[]>([])
const selectedRouteKey = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const isTesting = ref(false)
const providerVisible = ref(false)
const errorMessage = ref('')
const testPrompt = ref('请用一句话介绍 PaperChatAgent')
const testOutput = ref('')
const routeForm = ref({ providerId: '', modelName: '', temperature: 0.2, maxTokens: 4096 })
const providerForm = ref({
  name: '',
  providerType: 'openai_compatible',
  baseUrl: '',
  apiKeyRef: '',
  status: 'active',
})

const selectedRoute = computed(() => routes.value.find((item) => item.routeKey === selectedRouteKey.value) ?? null)
const healthyProviderCount = computed(() => providers.value.filter((provider) => ['enabled', 'active'].includes(provider.status)).length)

function syncForm(route: ModelRouteDTO | null) {
  routeForm.value = {
    providerId: route?.providerId ?? '',
    modelName: route?.modelName ?? '',
    temperature: route?.temperature ?? 0.2,
    maxTokens: route?.maxTokens ?? 4096,
  }
}

function backupLabel(route: ModelRouteDTO) {
  const fallback = route.config?.fallback_model ?? route.config?.fallbackModel ?? route.config?.backup
  if (fallback) return String(fallback)
  if (route.routeKey === 'embedding') return '本地 embedding'
  if (route.routeKey === 'rerank') return '关闭重排'
  return '按供应商默认降级'
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

function selectRoute(route: ModelRouteDTO) {
  selectedRouteKey.value = route.routeKey
  syncForm(route)
  testOutput.value = ''
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
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>模型</h2>
        <p>配置逻辑模型槽位与供应商路由，为对话、工具调用、推理和检索链路提供统一的模型基础设施。</p>
      </div>
      <div class="page-actions">
        <el-button @click="providerVisible = true">
          <el-icon><Plus /></el-icon>
          新增供应商
        </el-button>
        <el-button type="primary" :disabled="!selectedRouteKey" :loading="isSaving" @click="saveRoute">保存路由配置</el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <div class="module-content-grid">
      <section class="module-surface">
        <div class="section-title-row">
          <div>
            <h3>逻辑模型槽位</h3>
            <p>不同能力使用不同模型槽位，避免所有链路共用一个模型配置。</p>
          </div>
          <el-button :loading="isLoading" @click="loadData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div v-loading="isLoading" class="module-list">
          <el-empty v-if="!routes.length && !isLoading" description="暂无模型路由" />
          <button
            v-for="route in routes"
            :key="route.routeKey"
            class="module-list-item"
            :class="{ active: selectedRouteKey === route.routeKey }"
            type="button"
            @click="selectRoute(route)"
          >
            <div>
              <h4>{{ route.label || route.routeKey }}</h4>
              <p>{{ route.providerName || route.providerId || '未配置供应商' }} · {{ route.modelName || '未配置模型' }}</p>
              <span>{{ route.routeKey }} · temperature {{ route.temperature }} · max {{ route.maxTokens }} tokens</span>
            </div>
            <strong class="module-list-side">备用：{{ backupLabel(route) }}</strong>
          </button>
        </div>

        <div class="section-title-row provider-title">
          <div>
            <h3>供应商配置</h3>
          </div>
          <el-tag type="info">{{ providers.length }} 个供应商</el-tag>
        </div>
        <div class="module-card-grid">
          <article v-for="provider in providers" :key="provider.id" class="module-info-card">
            <h4>{{ provider.name }}</h4>
            <p>基础地址：{{ provider.baseUrl || '未配置' }}</p>
            <p>类型：{{ provider.providerType || '-' }}</p>
            <p>模型数量：{{ provider.modelCount }}</p>
            <p>状态：<span class="status-text success">{{ provider.status }}</span></p>
          </article>
        </div>
      </section>

      <aside class="module-rail">
        <section class="soft-panel module-rail-card">
          <h3>路由策略</h3>
          <p>主模型失败时优先切换备用模型。</p>
          <p>后台任务节点恢复会继承上次可用路由。</p>
          <p>重要节点允许按槽位单独覆盖。</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>当前槽位</h3>
          <template v-if="selectedRoute">
            <p>槽位：{{ selectedRoute.label || selectedRoute.routeKey }}</p>
            <p>供应商：{{ selectedRoute.providerName || selectedRoute.providerId || '未配置' }}</p>
            <p>模型：{{ selectedRoute.modelName || '未配置' }}</p>
            <div class="module-form-stack">
              <el-select v-model="routeForm.providerId" placeholder="选择供应商" filterable>
                <el-option v-for="provider in providers" :key="provider.id" :label="provider.name" :value="provider.id" />
              </el-select>
              <el-input v-model="routeForm.modelName" placeholder="模型名，例如 gpt-5.4-mini" />
              <el-input-number v-model="routeForm.temperature" :min="0" :max="2" :step="0.1" />
              <el-input-number v-model="routeForm.maxTokens" :min="1" :max="200000" :step="512" />
            </div>
          </template>
          <p v-else>请选择一个模型槽位。</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>健康概览</h3>
          <p>健康供应商：{{ healthyProviderCount }}</p>
          <p>路由槽位：{{ routes.length }}</p>
          <p>最近失败：embedding 超时 1 次</p>
          <p>当前配置版本：route-v7</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>模型测试</h3>
          <div class="module-form-stack">
            <el-input v-model="testPrompt" type="textarea" :rows="4" placeholder="测试 Prompt" />
            <el-button type="primary" :disabled="!selectedRouteKey" :loading="isTesting" @click="runTest">
              <el-icon><VideoPlay /></el-icon>
              测试当前路由
            </el-button>
            <el-input v-model="testOutput" type="textarea" :rows="5" readonly placeholder="模型输出" />
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

<style scoped>
.provider-title {
  margin-top: 34px;
}
</style>
