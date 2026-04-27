<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Plus, Refresh, SwitchButton } from '@element-plus/icons-vue'
import { createMcpService, getCcSwitchMcpServices, getMcpServices, getMcpTools, syncCcSwitchMcpServices, testMcpService } from '../../apis/mcp'
import type { McpServiceDTO, McpToolDTO } from '../../types/mcp'

const services = ref<McpServiceDTO[]>([])
const tools = ref<McpToolDTO[]>([])
const selectedServiceId = ref('')
const isLoading = ref(false)
const isSyncing = ref(false)
const testingId = ref('')
const createVisible = ref(false)
const createMode = ref<'local' | 'remote'>('local')
const errorMessage = ref('')
const ccSwitchCount = ref(0)
const ccSwitchSource = ref('/Users/sdybdc/.cc-switch/cc-switch.db')
const serviceForm = ref({
  name: '',
  description: '',
  transportType: 'stdio',
  command: '',
  argsText: '',
  endpointUrl: '',
  status: 'disabled',
})

const selectedService = computed(() => services.value.find((item) => item.id === selectedServiceId.value) ?? null)
const selectedTools = computed(() => tools.value.filter((tool) => tool.serviceId === selectedServiceId.value))
const onlineCount = computed(() => services.value.filter((service) => statusLabel(service) === '已连接').length)
const pendingCount = computed(() => services.value.filter((service) => statusLabel(service) === '待授权').length)
const abnormalCount = computed(() => services.value.filter((service) => statusLabel(service) === '异常').length)
const queuedServices = computed(() => services.value.filter((service) => service.status !== 'enabled').slice(0, 3))

function statusLabel(service: McpServiceDTO) {
  const status = service.lastHealthStatus && service.lastHealthStatus !== 'unknown' ? service.lastHealthStatus : service.status
  if (['ok', 'connected', 'healthy', 'enabled'].includes(status.toLowerCase())) return '已连接'
  if (['pending', 'auth_required', 'unauthorized'].includes(status.toLowerCase())) return '待授权'
  if (['failed', 'error', 'offline'].includes(status.toLowerCase())) return '异常'
  return status || '未知'
}

function statusClass(service: McpServiceDTO) {
  const label = statusLabel(service)
  if (label === '已连接') return 'success'
  if (label === '待授权') return 'warning'
  if (label === '异常') return 'danger'
  return 'brand'
}

async function loadData() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [serviceItems, toolItems] = await Promise.all([getMcpServices(), getMcpTools()])
    services.value = serviceItems
    tools.value = toolItems
    if (!selectedServiceId.value && serviceItems.length > 0) selectedServiceId.value = serviceItems[0].id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'MCP 数据加载失败'
  } finally {
    isLoading.value = false
  }
}

async function loadCcSwitchPreview() {
  try {
    const result = await getCcSwitchMcpServices()
    ccSwitchCount.value = result.items.length
    ccSwitchSource.value = String(result.source.db_path ?? ccSwitchSource.value)
  } catch {
    ccSwitchCount.value = 0
  }
}

async function runTest(serviceId: string) {
  testingId.value = serviceId
  try {
    const result = await testMcpService(serviceId)
    if (result.tools.length > 0) tools.value = result.tools
    ElMessage[result.ok ? 'success' : 'warning'](result.message || (result.ok ? '连接成功' : '连接失败'))
    await loadData()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '连接测试失败')
  } finally {
    testingId.value = ''
  }
}

async function syncFromCcSwitch() {
  isSyncing.value = true
  try {
    const result = await syncCcSwitchMcpServices()
    services.value = result.items
    selectedServiceId.value = result.items[0]?.id ?? ''
    ccSwitchCount.value = result.total
    ccSwitchSource.value = String(result.source.db_path ?? ccSwitchSource.value)
    await loadData()
    ElMessage.success(`已同步 ${result.total} 个真实 MCP，新建 ${result.created} 个，更新 ${result.updated} 个`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步 .cc-switch MCP 失败')
  } finally {
    isSyncing.value = false
  }
}

function openCreateDialog(mode: 'local' | 'remote') {
  createMode.value = mode
  serviceForm.value = {
    name: '',
    description: '',
    transportType: mode === 'local' ? 'stdio' : 'http',
    command: '',
    argsText: '',
    endpointUrl: '',
    status: 'disabled',
  }
  createVisible.value = true
}

async function submitService() {
  if (!serviceForm.value.name.trim()) {
    ElMessage.warning('请输入服务名称')
    return
  }
  const args = serviceForm.value.argsText
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean)
  try {
    const created = await createMcpService({
      name: serviceForm.value.name.trim(),
      description: serviceForm.value.description.trim(),
      transportType: serviceForm.value.transportType,
      command: serviceForm.value.command.trim(),
      args,
      endpointUrl: serviceForm.value.endpointUrl.trim(),
      status: serviceForm.value.status,
    })
    services.value.unshift(created)
    selectedServiceId.value = created.id
    createVisible.value = false
    ElMessage.success('MCP 服务已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建 MCP 服务失败')
  }
}

onMounted(() => {
  loadData()
  loadCcSwitchPreview()
})
</script>

<template>
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>MCP 服务</h2>
        <p>管理本地与远程工具接入，决定聊天阶段可被模型调用的外部能力范围。</p>
      </div>
      <div class="page-actions">
        <el-button :loading="isSyncing" @click="syncFromCcSwitch">
          <el-icon><DocumentAdd /></el-icon>
          同步 .cc-switch MCP
        </el-button>
        <el-button type="primary" @click="openCreateDialog('remote')">
          <el-icon><Plus /></el-icon>
          新增服务配置
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <section class="metrics-grid">
      <article class="metric-card success">
        <h4>在线</h4>
        <strong>{{ String(onlineCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card warning">
        <h4>待授权</h4>
        <strong>{{ String(pendingCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card danger">
        <h4>异常</h4>
        <strong>{{ String(abnormalCount).padStart(2, '0') }}</strong>
      </article>
    </section>

    <div class="module-content-grid">
      <section class="module-surface">
        <div class="section-title-row">
          <div>
            <h3>服务列表</h3>
            <p>已接入服务覆盖论文检索、文献库同步与网页抓取，支持本地导入与远程配置。</p>
          </div>
          <el-button :loading="isLoading" @click="loadData">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div v-loading="isLoading" class="module-list">
          <el-empty v-if="!services.length && !isLoading" description="暂无 MCP 服务" />
          <button
            v-for="service in services"
            :key="service.id"
            class="module-list-item"
            :class="{ active: selectedServiceId === service.id }"
            type="button"
            @click="selectedServiceId = service.id"
          >
            <div>
              <h4>{{ service.name || service.id }} · {{ service.transportType === 'stdio' ? '本地服务' : '远程服务' }}</h4>
              <p>能力：{{ service.description || service.command || service.url || '暂无描述' }}</p>
              <span>{{ service.toolCount ? `${service.toolCount} 个工具` : '工具待连接发现' }} · {{ service.command || service.url || '未配置启动入口' }}</span>
            </div>
            <strong class="module-list-side" :class="['status-text', statusClass(service)]">{{ statusLabel(service) }}</strong>
          </button>
        </div>

        <div class="module-mini-list">
          <h3>接入队列</h3>
          <p v-if="!queuedServices.length" class="muted-text">暂无待接入服务。</p>
          <div v-for="service in queuedServices" :key="service.id" class="module-mini-item">
            <div>
              <strong>{{ service.name }}</strong>
              <span>{{ service.lastHealthMessage || '等待权限校验与工具描述同步' }}</span>
            </div>
          </div>
          <p class="muted-text">接入路径：导入本地服务 -> 校验权限 -> 注册工具描述 -> 在聊天中按需可调用</p>
        </div>
      </section>

      <aside class="module-rail">
        <section class="soft-panel module-rail-card">
          <h3>选中服务详情</h3>
          <template v-if="selectedService">
            <p>服务：{{ selectedService.name || selectedService.id }}</p>
            <p>传输：{{ selectedService.transportType }}</p>
            <p>状态：{{ statusLabel(selectedService) }}</p>
            <p>暴露工具：{{ selectedService.toolCount }} 个</p>
            <el-button
              :loading="testingId === selectedService.id"
              :disabled="!selectedService.id"
              @click="runTest(selectedService.id)"
            >
              <el-icon><SwitchButton /></el-icon>
              测试连接
            </el-button>
          </template>
          <p v-else>请选择一个服务查看详情。</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>能力暴露</h3>
          <div class="module-mini-list">
            <p v-if="!selectedTools.length">当前服务暂无工具快照。</p>
            <div v-for="tool in selectedTools" :key="tool.id" class="module-mini-item">
              <div>
                <strong>{{ tool.toolName }}</strong>
                <span>{{ tool.description || '未提供描述' }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>接入说明</h3>
          <p>真实来源：{{ ccSwitchSource }}</p>
          <p>可同步 MCP：{{ ccSwitchCount }} 个</p>
          <p>同步会读取 cc-switch 的 mcp_servers 表，保留 command、args、url、headers 与 env keys。</p>
        </section>
      </aside>
    </div>

    <el-dialog v-model="createVisible" :title="createMode === 'local' ? '导入本地 MCP 服务' : '新增远程 MCP 服务'" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="服务名称">
          <el-input v-model="serviceForm.name" placeholder="例如 arXiv Gateway" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="serviceForm.description" type="textarea" :rows="3" placeholder="说明服务暴露的工具能力" />
        </el-form-item>
        <el-form-item label="传输方式">
          <el-select v-model="serviceForm.transportType">
            <el-option label="stdio" value="stdio" />
            <el-option label="HTTP" value="http" />
            <el-option label="SSE" value="sse" />
            <el-option label="WebSocket" value="websocket" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="serviceForm.transportType === 'stdio'" label="启动命令">
          <el-input v-model="serviceForm.command" placeholder="例如 npx" />
        </el-form-item>
        <el-form-item v-if="serviceForm.transportType === 'stdio'" label="命令参数">
          <el-input v-model="serviceForm.argsText" placeholder="例如 -y @paperchat/arxiv-mcp" />
        </el-form-item>
        <el-form-item v-if="serviceForm.transportType !== 'stdio'" label="服务地址">
          <el-input v-model="serviceForm.endpointUrl" placeholder="https://example.com/mcp" />
        </el-form-item>
        <el-form-item label="初始状态">
          <el-select v-model="serviceForm.status">
            <el-option label="停用" value="disabled" />
            <el-option label="启用" value="enabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitService">保存服务</el-button>
      </template>
    </el-dialog>
  </div>
</template>
