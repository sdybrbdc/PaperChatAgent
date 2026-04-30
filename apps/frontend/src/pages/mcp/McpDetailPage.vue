<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Check, Refresh, SwitchButton, Upload } from '@element-plus/icons-vue'
import { getMcpService, importMcpJson, refreshMcpTools, testMcpService, updateMcpService } from '../../apis/mcp'
import type { McpServiceDTO, McpToolDTO } from '../../types/mcp'

const route = useRoute()
const router = useRouter()

const service = ref<McpServiceDTO | null>(null)
const selectedToolName = ref('')
const isLoading = ref(false)
const isTesting = ref(false)
const isRefreshing = ref(false)
const isSaving = ref(false)
const isImporting = ref(false)
const importVisible = ref(false)
const importText = ref('')
const importRefreshTools = ref(true)
const importOverwrite = ref(true)
const configForm = ref({
  name: '',
  description: '',
  transportType: 'stdio',
  command: '',
  argsText: '',
  endpointUrl: '',
  headersText: '',
  envText: '',
  status: 'enabled',
})

const serviceId = computed(() => String(route.params.serviceId ?? ''))
const tools = computed(() => service.value?.tools ?? [])
const activeTools = computed(() => tools.value.filter((tool) => tool.enabled).length)
const selectedTool = computed(() => tools.value.find((tool) => tool.toolName === selectedToolName.value) ?? tools.value[0] ?? null)
const endpointText = computed(() => {
  if (!service.value) return ''
  return service.value.transportType === 'stdio'
    ? [service.value.command, ...service.value.args].filter(Boolean).join(' ')
    : service.value.endpointUrl || service.value.url
})

function statusLabel(item: McpServiceDTO | McpToolDTO | null) {
  if (!item) return '未知'
  if ('status' in item && item.status === 'disabled') return '停用'
  const raw = 'lastHealthStatus' in item ? item.lastHealthStatus || item.status : item.status
  const status = String(raw || '').toLowerCase()
  if (['ok', 'connected', 'healthy', 'enabled', 'active'].includes(status)) return '已连接'
  if (['pending', 'auth_required', 'unauthorized'].includes(status)) return '待授权'
  if (['failed', 'error', 'offline', 'unhealthy'].includes(status)) return '异常'
  return raw || '未知'
}

function statusClass(item: McpServiceDTO | McpToolDTO | null) {
  const label = statusLabel(item)
  if (label === '已连接') return 'success'
  if (label === '待授权') return 'warning'
  if (label === '异常') return 'danger'
  return 'brand'
}

function transportLabel(value?: string) {
  if (value === 'stdio') return 'stdio'
  if (value === 'sse') return 'SSE'
  if (value === 'websocket') return 'WebSocket'
  if (value === 'streamable_http' || value === 'http') return 'Streamable HTTP'
  return value || '未知'
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2)
}

function parseJsonRecord(text: string, label: string) {
  const trimmed = text.trim()
  if (!trimmed) return undefined
  const parsed = JSON.parse(trimmed)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${label} 必须是 JSON object`)
  }
  return Object.fromEntries(Object.entries(parsed).map(([key, value]) => [key, String(value)]))
}

function fillConfigForm(item: McpServiceDTO) {
  configForm.value = {
    name: item.name,
    description: item.description,
    transportType: item.transportType,
    command: item.command,
    argsText: item.args.join(' '),
    endpointUrl: item.endpointUrl || item.url,
    headersText: Object.keys(item.headers).length ? formatJson(item.headers) : '',
    envText: '',
    status: item.status,
  }
}

async function loadDetail() {
  if (!serviceId.value) return
  isLoading.value = true
  try {
    const detail = await getMcpService(serviceId.value)
    service.value = detail
    fillConfigForm(detail)
    if (!selectedToolName.value || !detail.tools?.some((tool) => tool.toolName === selectedToolName.value)) {
      selectedToolName.value = detail.tools?.[0]?.toolName ?? ''
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'MCP 详情加载失败')
  } finally {
    isLoading.value = false
  }
}

async function runTest() {
  if (!service.value) return
  isTesting.value = true
  try {
    const result = await testMcpService(service.value.id)
    ElMessage[result.ok ? 'success' : 'warning'](result.message || (result.ok ? '连接成功' : '连接失败'))
    await loadDetail()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '连接测试失败')
  } finally {
    isTesting.value = false
  }
}

async function refreshTools() {
  if (!service.value) return
  isRefreshing.value = true
  try {
    const result = await refreshMcpTools(service.value.id)
    ElMessage[result.ok ? 'success' : 'warning'](result.message || (result.ok ? '工具已刷新' : '工具刷新失败'))
    await loadDetail()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '刷新工具失败')
  } finally {
    isRefreshing.value = false
  }
}

async function saveConfig() {
  if (!service.value) return
  isSaving.value = true
  try {
    const headers = parseJsonRecord(configForm.value.headersText, 'Headers')
    const env = parseJsonRecord(configForm.value.envText, 'Env')
    const args = configForm.value.argsText
      .split(/\s+/)
      .map((item) => item.trim())
      .filter(Boolean)
    const updated = await updateMcpService(service.value.id, {
      name: configForm.value.name.trim(),
      description: configForm.value.description.trim(),
      transportType: configForm.value.transportType,
      command: configForm.value.command.trim(),
      args,
      endpointUrl: configForm.value.endpointUrl.trim(),
      headers,
      env,
      status: configForm.value.status,
    })
    service.value = { ...updated, tools: service.value.tools }
    fillConfigForm(service.value)
    ElMessage.success('MCP 配置已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存 MCP 配置失败')
  } finally {
    isSaving.value = false
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
    const target = result.items.find((item) => item.id === serviceId.value || item.name === service.value?.name) ?? result.items[0]
    importVisible.value = false
    importText.value = ''
    ElMessage.success(`已导入 ${result.total} 个 MCP`)
    if (target && target.id !== serviceId.value) {
      router.replace({ name: 'mcp-detail', params: { serviceId: target.id } })
    } else {
      await loadDetail()
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入 MCP JSON 失败')
  } finally {
    isImporting.value = false
  }
}

watch(serviceId, () => {
  loadDetail()
})

onMounted(loadDetail)
</script>

<template>
  <div class="page-shell mcp-page-shell">
    <header class="module-header">
      <div>
        <button class="mcp-back-button" type="button" @click="router.push({ name: 'mcp' })">
          <el-icon><Back /></el-icon>
          MCP 服务
        </button>
        <h2>{{ service?.name || 'MCP 服务详情' }}</h2>
        <p>{{ service?.description || '查看此 MCP Server 对外部服务暴露的工具、连接配置和工具 schema。' }}</p>
      </div>
      <div class="page-actions">
        <el-button :loading="isTesting" :disabled="!service" @click="runTest">
          <el-icon><SwitchButton /></el-icon>
          测试连接
        </el-button>
        <el-button :loading="isRefreshing" :disabled="!service" @click="refreshTools">
          <el-icon><Refresh /></el-icon>
          刷新工具
        </el-button>
        <el-button type="primary" :loading="isSaving" :disabled="!service" @click="saveConfig">
          <el-icon><Check /></el-icon>
          保存
        </el-button>
      </div>
    </header>

    <div v-loading="isLoading" class="mcp-detail-body">
      <section class="metrics-grid">
        <article class="metric-card brand">
          <h4>传输</h4>
          <strong class="mcp-metric-text">{{ transportLabel(service?.transportType) }}</strong>
        </article>
        <article class="metric-card success">
          <h4>启用工具</h4>
          <strong>{{ String(activeTools).padStart(2, '0') }}</strong>
        </article>
        <article class="metric-card warning">
          <h4>状态</h4>
          <strong class="mcp-metric-text">{{ statusLabel(service) }}</strong>
        </article>
        <article class="metric-card">
          <h4>最近检查</h4>
          <strong class="mcp-metric-text">{{ service?.lastCheckedAt || '未检查' }}</strong>
        </article>
      </section>

      <div class="module-content-grid mcp-detail-grid">
        <section class="module-surface">
          <div class="section-title-row">
            <div>
              <h3>工具清单</h3>
              <p>工具来自真实 MCP Server 的发现结果。刷新工具后会更新名称、描述和 input schema。</p>
            </div>
            <span class="status-text" :class="statusClass(service)">{{ statusLabel(service) }}</span>
          </div>

          <div class="mcp-tool-layout">
            <div class="mcp-tool-list">
              <el-empty v-if="!tools.length" description="暂无工具快照，请先测试连接并刷新工具" />
              <button
                v-for="tool in tools"
                :key="tool.id"
                type="button"
                class="mcp-tool-card"
                :class="{ active: selectedToolName === tool.toolName }"
                @click="selectedToolName = tool.toolName"
              >
                <div>
                  <h4>{{ tool.displayName || tool.toolName }}</h4>
                  <p>{{ tool.description || '该工具未提供描述。' }}</p>
                  <span>input: {{ Object.keys(tool.inputSchema?.properties ?? {}).join(', ') || '无参数 schema' }}</span>
                </div>
                <strong class="status-text" :class="statusClass(tool)">{{ tool.enabled ? '启用' : '停用' }}</strong>
              </button>
            </div>

            <aside class="mcp-schema-panel">
              <h3>Schema</h3>
              <template v-if="selectedTool">
                <p>{{ selectedTool.toolName }}</p>
                <pre>{{ formatJson(selectedTool.inputSchema) }}</pre>
              </template>
              <p v-else>选择一个工具查看参数结构。</p>
            </aside>
          </div>
        </section>

        <aside class="module-rail">
          <section class="soft-panel module-rail-card">
            <h3>配置 MCP</h3>
            <div class="module-form-stack">
              <el-form label-position="top" @submit.prevent>
                <el-form-item label="名称">
                  <el-input v-model="configForm.name" />
                </el-form-item>
                <el-form-item label="描述">
                  <el-input v-model="configForm.description" type="textarea" :rows="3" />
                </el-form-item>
                <el-form-item label="Transport">
                  <el-select v-model="configForm.transportType">
                    <el-option label="stdio" value="stdio" />
                    <el-option label="Streamable HTTP" value="streamable_http" />
                    <el-option label="SSE" value="sse" />
                    <el-option label="WebSocket" value="websocket" />
                  </el-select>
                </el-form-item>
                <el-form-item v-if="configForm.transportType === 'stdio'" label="Command">
                  <el-input v-model="configForm.command" placeholder="npx" />
                </el-form-item>
                <el-form-item v-if="configForm.transportType === 'stdio'" label="Args">
                  <el-input v-model="configForm.argsText" placeholder="-y @modelcontextprotocol/server-fetch" />
                </el-form-item>
                <el-form-item v-if="configForm.transportType !== 'stdio'" label="Endpoint URL">
                  <el-input v-model="configForm.endpointUrl" placeholder="https://example.com/mcp" />
                </el-form-item>
                <el-form-item label="Headers JSON">
                  <el-input v-model="configForm.headersText" type="textarea" :rows="3" placeholder='{"Authorization":"Bearer ..."}' />
                </el-form-item>
                <el-form-item label="Env JSON">
                  <el-input v-model="configForm.envText" type="textarea" :rows="3" :placeholder="service?.envKeys.length ? `已有 env keys：${service.envKeys.join(', ')}` : '{ }'" />
                </el-form-item>
                <el-form-item label="状态">
                  <el-select v-model="configForm.status">
                    <el-option label="启用" value="enabled" />
                    <el-option label="停用" value="disabled" />
                  </el-select>
                </el-form-item>
              </el-form>
            </div>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>连接信息</h3>
            <p>入口：{{ endpointText || '未配置' }}</p>
            <p>Env keys：{{ service?.envKeys.length ? service.envKeys.join(', ') : '无' }}</p>
            <p>工具总数：{{ tools.length }}</p>
            <p>配置表记录：paperchat_mcp_servers / {{ service?.id }}</p>
            <p>工具表记录：paperchat_mcp_tools / {{ tools.length }} 条</p>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>导入 JSON</h3>
            <p>可用 JSON 覆盖当前服务配置，或导入同名服务后自动回到最新详情。</p>
            <el-button class="full-width-button" @click="importVisible = true">
              <el-icon><Upload /></el-icon>
              导入 JSON
            </el-button>
          </section>
        </aside>
      </div>
    </div>

    <el-dialog v-model="importVisible" title="导入 MCP JSON" width="720px">
      <div class="module-form-stack">
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

.mcp-detail-grid {
  flex: 1;
  min-height: 0;
}

.mcp-detail-body {
  display: flex;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  flex-direction: column;
}

.mcp-detail-body > .metrics-grid {
  flex-shrink: 0;
}

.mcp-detail-grid .module-surface {
  display: flex;
  min-height: 0;
  overflow: hidden;
  flex-direction: column;
}

.mcp-detail-grid .module-rail {
  min-height: 0;
  padding-right: 4px;
  overflow-y: auto;
}

.mcp-detail-grid .module-rail-card {
  min-width: 0;
}

.mcp-back-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 8px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--pc-brand);
  cursor: pointer;
}

.mcp-metric-text {
  max-width: 100%;
  overflow: hidden;
  font-size: 22px !important;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mcp-tool-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  flex: 1;
  height: 0;
  min-height: 0;
  overflow: hidden;
}

.mcp-tool-list {
  display: grid;
  align-content: start;
  height: 100%;
  min-height: 0;
  gap: 14px;
  padding-right: 4px;
  overflow-x: hidden;
  overflow-y: auto;
}

.mcp-tool-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  padding: 18px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
  color: var(--pc-text);
  text-align: left;
  cursor: pointer;

  &.active,
  &:hover {
    border-color: var(--pc-brand);
    background: var(--pc-surface-accent);
  }

  h4 {
    margin: 0;
    font-size: 17px;
  }

  p {
    margin: 8px 0 0;
    color: var(--pc-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }

  span {
    display: block;
    margin-top: 8px;
    color: var(--pc-text-secondary);
    font-size: 12px;
  }
}

.mcp-schema-panel {
  height: 100%;
  min-height: 0;
  padding: 18px;
  overflow: hidden;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);

  h3 {
    margin: 0;
    font-size: 17px;
  }

  p {
    margin: 8px 0 0;
    color: var(--pc-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }

  pre {
    max-height: calc(100% - 64px);
    margin: 14px 0 0;
    padding: 14px;
    overflow-x: hidden;
    overflow-y: auto;
    border-radius: 12px;
    background: #182230;
    color: #ffffff;
    font-size: 12px;
    line-height: 1.55;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
}

.mcp-dialog-options {
  display: flex;
  gap: 18px;
}

.full-width-button {
  width: 100%;
}
</style>
