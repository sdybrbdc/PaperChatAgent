<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, Plus, Refresh, Search, Upload } from '@element-plus/icons-vue'
import {
  createMcpService,
  getMcpServices,
  getMcpTools,
  importMcpJson,
} from '../../apis/mcp'
import type { McpServiceDTO, McpToolDTO } from '../../types/mcp'

const router = useRouter()

const services = ref<McpServiceDTO[]>([])
const tools = ref<McpToolDTO[]>([])
const isLoading = ref(false)
const errorMessage = ref('')
const searchKeyword = ref('')
const statusFilter = ref<'all' | 'connected' | 'error'>('all')
const importVisible = ref(false)
const importText = ref('')
const importRefreshTools = ref(false)
const importOverwrite = ref(true)
const isImporting = ref(false)
const createVisible = ref(false)
const createMode = ref<'local' | 'remote'>('local')
const serviceForm = ref({
  name: '',
  description: '',
  transportType: 'stdio',
  command: '',
  argsText: '',
  endpointUrl: '',
  status: 'disabled',
})

const totalToolCount = computed(() => tools.value.length)
const onlineCount = computed(() => services.value.filter((service) => statusLabel(service) === '已连接').length)
const pendingCount = computed(() => services.value.filter((service) => statusLabel(service) === '待授权').length)
const abnormalCount = computed(() => services.value.filter((service) => statusLabel(service) === '异常').length)
const filteredServices = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  return services.value.filter((service) => {
    const label = statusLabel(service)
    const statusMatched =
      statusFilter.value === 'all' ||
      (statusFilter.value === 'connected' && label === '已连接') ||
      (statusFilter.value === 'error' && label === '异常')
    if (!statusMatched) return false
    if (!keyword) return true
    const serviceTools = tools.value.filter((tool) => tool.serviceId === service.id)
    return [service.name, service.description, service.command, service.endpointUrl, ...serviceTools.map((tool) => tool.toolName)]
      .join(' ')
      .toLowerCase()
      .includes(keyword)
  })
})
const previewService = computed(() => filteredServices.value[0] ?? services.value[0] ?? null)
const previewTools = computed(() => {
  if (!previewService.value) return []
  return tools.value.filter((tool) => tool.serviceId === previewService.value?.id)
})

function statusLabel(service: McpServiceDTO) {
  if (service.status === 'disabled') return '停用'
  const status = service.lastHealthStatus && service.lastHealthStatus !== 'unknown' ? service.lastHealthStatus : service.status
  if (['ok', 'connected', 'healthy', 'enabled'].includes(status.toLowerCase())) return '已连接'
  if (['pending', 'auth_required', 'unauthorized'].includes(status.toLowerCase())) return '待授权'
  if (['failed', 'error', 'offline', 'unhealthy'].includes(status.toLowerCase())) return '异常'
  return status || '未知'
}

function statusClass(service: McpServiceDTO) {
  const label = statusLabel(service)
  if (label === '已连接') return 'success'
  if (label === '待授权') return 'warning'
  if (label === '异常') return 'danger'
  return 'brand'
}

function displayStatusLabel(service: McpServiceDTO) {
  const label = statusLabel(service)
  if (label === '已连接') return '在线'
  return label
}

function serviceActionLabel(service: McpServiceDTO) {
  const label = statusLabel(service)
  if (label === '待授权') return '继续配置'
  if (label === '异常') return '修复配置'
  return '查看详情'
}

function transportLabel(service: McpServiceDTO) {
  if (service.transportType === 'stdio') return 'stdio'
  if (service.transportType === 'sse') return 'sse'
  if (service.transportType === 'websocket') return 'websocket'
  if (service.transportType === 'streamable_http' || service.transportType === 'http') return 'streamable_http'
  return service.transportType
}

function serviceToolCount(service: McpServiceDTO) {
  const count = tools.value.filter((tool) => tool.serviceId === service.id).length
  return count || service.toolCount || 0
}

function serviceEntrypoint(service: McpServiceDTO) {
  if (service.transportType === 'stdio') return [service.command, ...service.args].filter(Boolean).join(' ') || '未配置 command'
  return service.endpointUrl || service.url || '未配置 endpoint_url'
}

async function loadData() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [serviceItems, toolItems] = await Promise.all([getMcpServices(), getMcpTools()])
    services.value = serviceItems
    tools.value = toolItems
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'MCP 数据加载失败'
  } finally {
    isLoading.value = false
  }
}

function openCreateDialog(mode: 'local' | 'remote') {
  createMode.value = mode
  serviceForm.value = {
    name: '',
    description: '',
    transportType: mode === 'local' ? 'stdio' : 'streamable_http',
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
    createVisible.value = false
    ElMessage.success('MCP 服务已创建')
    router.push({ name: 'mcp-detail', params: { serviceId: created.id } })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建 MCP 服务失败')
  }
}

async function submitJsonImport() {
  if (!importText.value.trim()) {
    ElMessage.warning('请粘贴 MCP JSON 配置')
    return
  }
  let config: unknown
  try {
    config = JSON.parse(importText.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? `JSON 格式不正确：${error.message}` : 'JSON 格式不正确')
    return
  }
  isImporting.value = true
  try {
    const result = await importMcpJson({
      config,
      overwriteExisting: importOverwrite.value,
      refreshTools: importRefreshTools.value,
      status: 'enabled',
    })
    await loadData()
    importVisible.value = false
    importText.value = ''
    const suffix = result.refreshErrors.length ? `，${result.refreshErrors.length} 个服务刷新工具失败` : ''
    ElMessage.success(`已导入 ${result.total} 个 MCP，新建 ${result.created} 个，更新 ${result.updated} 个${suffix}`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入 MCP JSON 失败')
  } finally {
    isImporting.value = false
  }
}

function openDetail(service: McpServiceDTO) {
  router.push({ name: 'mcp-detail', params: { serviceId: service.id } })
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="page-shell mcp-page-shell">
    <header class="module-header">
      <div>
        <h2>MCP 服务</h2>
        <p>集中管理本地与远程 MCP Server，查看健康状态、工具暴露范围，并通过 JSON 快速导入配置。</p>
      </div>
      <div class="page-actions">
        <el-button @click="importVisible = true">
          <el-icon><Upload /></el-icon>
          导入 JSON
        </el-button>
        <el-button type="primary" @click="openCreateDialog('remote')">
          <el-icon><Plus /></el-icon>
          新增 MCP
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <div class="mcp-board-grid">
      <div class="mcp-primary-column">
        <section class="metrics-grid mcp-metrics-grid">
          <article class="metric-card success">
            <h4>在线服务</h4>
            <strong>{{ String(onlineCount).padStart(2, '0') }}</strong>
          </article>
          <article class="metric-card brand">
            <h4>可用工具</h4>
            <strong>{{ String(totalToolCount).padStart(2, '0') }}</strong>
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

        <section class="module-surface mcp-service-directory">
          <div class="section-title-row">
            <div>
              <h3>服务目录</h3>
              <p>点击服务进入详情，查看当前 Server 暴露的工具、参数 schema 和连接配置。</p>
            </div>
            <el-button :loading="isLoading" @click="loadData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>

          <div class="mcp-toolbar">
            <el-input v-model="searchKeyword" clearable placeholder="搜索服务、工具或命令">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-radio-group v-model="statusFilter">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="connected">在线</el-radio-button>
              <el-radio-button label="error">异常</el-radio-button>
            </el-radio-group>
          </div>

          <div v-loading="isLoading" class="module-list">
            <el-empty v-if="!filteredServices.length && !isLoading" description="暂无 MCP 服务" />
            <button
              v-for="service in filteredServices"
              :key="service.id"
              class="module-list-item mcp-service-card"
              :class="{ active: previewService?.id === service.id }"
              type="button"
              @click="openDetail(service)"
            >
              <span class="mcp-service-icon" :class="statusClass(service)">
                <el-icon><Connection /></el-icon>
              </span>
              <div class="mcp-service-body">
                <div class="mcp-service-title-row">
                  <h4>{{ service.name || service.id }}</h4>
                  <span class="mcp-status-pill" :class="statusClass(service)">{{ displayStatusLabel(service) }}</span>
                </div>
                <p>{{ service.description || '该 MCP 暂未提供描述；刷新工具后可查看服务暴露能力。' }}</p>
                <span>{{ transportLabel(service) }} · {{ serviceEntrypoint(service) }} · {{ serviceToolCount(service) }} tools</span>
              </div>
              <strong class="mcp-card-action">{{ serviceActionLabel(service) }}</strong>
            </button>
          </div>
        </section>
      </div>

      <aside class="module-rail mcp-list-rail">
        <section class="soft-panel module-rail-card mcp-import-panel">
          <h3>导入 JSON 配置</h3>
          <p>兼容 mcpServers 字段，导入后进入预览校验，再选择保存或覆盖。</p>
          <button class="mcp-upload-card" type="button" @click="importVisible = true">
            <el-icon><Upload /></el-icon>
            <strong>拖入 config.json</strong>
            <span>或粘贴 JSON 内容</span>
          </button>
          <pre class="mcp-json-preview">{
  "mcpServers": {
    "arxiv": { "command": "uvx" }
  }
}</pre>
          <span class="mcp-valid-pill">结构已识别</span>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>选中服务预览</h3>
          <template v-if="previewService">
            <p>服务：{{ previewService.name || previewService.id }}</p>
            <p>传输：{{ transportLabel(previewService) }}</p>
            <p>命令：{{ previewService.command || previewService.endpointUrl || previewService.url || '未配置' }}</p>
            <p>工具：{{ previewTools.map((tool) => tool.toolName).slice(0, 4).join('、') || '待刷新工具清单' }}</p>
            <router-link class="mcp-rail-link" :to="{ name: 'mcp-detail', params: { serviceId: previewService.id } }">进入详情配置工具 →</router-link>
          </template>
          <p v-else>请选择一个服务查看详情。</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>同步与权限</h3>
          <p>导入后先测试连接，再同步工具清单。涉及文件、仓库、浏览器等高权限工具，需要在详情页确认作用域。</p>
          <el-button>查看审计日志</el-button>
        </section>
      </aside>
    </div>

    <el-dialog v-model="importVisible" title="导入 MCP JSON" width="720px">
      <div class="module-form-stack">
        <el-alert
          title="支持 { mcpServers: { name: { command, args, env } } }，也支持远程服务的 url / endpoint_url / headers。"
          type="info"
          show-icon
          :closable="false"
        />
        <el-input
          v-model="importText"
          type="textarea"
          :rows="14"
          placeholder='{"mcpServers":{"fetch":{"command":"npx","args":["-y","@modelcontextprotocol/server-fetch"]}}}'
        />
        <div class="mcp-dialog-options">
          <el-checkbox v-model="importOverwrite">同名服务自动覆盖</el-checkbox>
          <el-checkbox v-model="importRefreshTools">导入后立即刷新工具</el-checkbox>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="isImporting" @click="submitJsonImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" :title="createMode === 'local' ? '导入本地 MCP 服务' : '新增 MCP 服务'" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="服务名称">
          <el-input v-model="serviceForm.name" placeholder="例如 arXiv Gateway" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="serviceForm.description" type="textarea" :rows="3" placeholder="说明服务暴露的外部工具能力" />
        </el-form-item>
        <el-form-item label="传输方式">
          <el-select v-model="serviceForm.transportType">
            <el-option label="stdio" value="stdio" />
            <el-option label="Streamable HTTP" value="streamable_http" />
            <el-option label="SSE" value="sse" />
            <el-option label="WebSocket" value="websocket" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="serviceForm.transportType === 'stdio'" label="启动命令">
          <el-input v-model="serviceForm.command" placeholder="例如 npx" />
        </el-form-item>
        <el-form-item v-if="serviceForm.transportType === 'stdio'" label="命令参数">
          <el-input v-model="serviceForm.argsText" placeholder="例如 -y @modelcontextprotocol/server-fetch" />
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
