<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import {
  ArrowRight,
  Back,
  Check,
  Document,
  Files,
  Filter,
  More,
  Notebook,
  Plus,
  Search,
  Setting,
  UploadFilled,
} from '@element-plus/icons-vue'
import {
  createKnowledgeBase,
  getKnowledgeBases,
  getKnowledgeFileIndexStatus,
  getKnowledgeFiles,
  uploadKnowledgeFile,
} from '../../apis/knowledge'
import type { KnowledgeBaseDTO, KnowledgeFileDTO } from '../../types/knowledge'

const bases = ref<KnowledgeBaseDTO[]>([])
const files = ref<KnowledgeFileDTO[]>([])
const selectedBaseId = ref('')
const isLoading = ref(false)
const isDetailLoading = ref(false)
const createVisible = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const fileKeyword = ref('')
const newBase = ref({ name: '', description: '' })

const selectedBase = computed(() => bases.value.find((item) => item.id === selectedBaseId.value) ?? null)
const isDetailMode = computed(() => Boolean(selectedBase.value))

const filteredBases = computed(() => {
  const word = keyword.value.trim().toLowerCase()
  if (!word) return bases.value
  return bases.value.filter((base) => `${base.name} ${base.description}`.toLowerCase().includes(word))
})

const filteredFiles = computed(() => {
  const word = fileKeyword.value.trim().toLowerCase()
  if (!word) return files.value
  return files.value.filter((file) =>
    `${file.originalFilename} ${file.filename} ${file.sourceType} ${file.parserStatus} ${file.indexStatus}`
      .toLowerCase()
      .includes(word),
  )
})

const allRecentFiles = computed(() => {
  return bases.value
    .flatMap((base) => base.recentFiles ?? [])
    .sort((a, b) => dateTime(b.createdAt || b.updatedAt) - dateTime(a.createdAt || a.updatedAt))
})
const recentFiles = computed(() => allRecentFiles.value.slice(0, 5))
const totalFileCount = computed(() => bases.value.reduce((sum, base) => sum + base.fileCount, 0))
const totalIndexedCount = computed(() => bases.value.reduce((sum, base) => sum + base.indexedFileCount, 0))
const totalStorageText = computed(() => formatSize(allRecentFiles.value.reduce((sum, file) => sum + file.sizeBytes, 0)))

const selectedIndexedCount = computed(() => files.value.filter((file) => isIndexedStatus(file.indexStatus)).length)
const selectedFailedCount = computed(() => files.value.filter((file) => isFailedStatus(file.indexStatus)).length)
const selectedPendingCount = computed(() =>
  files.value.filter((file) => !isIndexedStatus(file.indexStatus) && !isFailedStatus(file.indexStatus)).length,
)
const selectedProgress = computed(() => {
  if (!files.value.length) return 0
  return Math.round((selectedIndexedCount.value / files.value.length) * 100)
})
const selectedStorageText = computed(() => formatSize(files.value.reduce((sum, file) => sum + file.sizeBytes, 0)))
const selectedChunkCount = computed(() => files.value.reduce((sum, file) => sum + file.chunkCount, 0))
const selectedUpdatedAt = computed(() => selectedBase.value?.updatedAt || selectedBase.value?.createdAt || null)

const knowledgeInfoRows = computed(() => [
  ['名称', selectedBase.value?.name || '-'],
  ['描述', selectedBase.value?.description || '暂无描述'],
  ['创建时间', formatDateTime(selectedBase.value?.createdAt ?? null)],
  ['更新时间', formatDateTime(selectedUpdatedAt.value)],
  ['文件数量', `${files.value.length}`],
  ['总分块数', `${selectedChunkCount.value}`],
  ['索引进度', `${selectedProgress.value}%`],
  ['待处理', `${selectedPendingCount.value}`],
  ['存储占用', selectedStorageText.value],
])

function dateTime(value: string | null) {
  if (!value) return 0
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 0 : date.getTime()
}

function formatDateTime(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatCompactDate(value: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

function formatSize(value: number) {
  if (value >= 1024 * 1024 * 1024) return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  if (value <= 0) return '0 KB'
  return `${Math.max(1, Math.ceil(value / 1024))} KB`
}

function normalizedStatus(value: string) {
  return value.trim().toLowerCase()
}

function isIndexedStatus(value: string) {
  return ['completed', 'indexed'].includes(normalizedStatus(value))
}

function isFailedStatus(value: string) {
  return normalizedStatus(value) === 'failed'
}

function isRunningStatus(value: string) {
  return ['queued', 'running', 'parsing', 'chunking', 'embedding', 'indexing', 'pending'].includes(normalizedStatus(value))
}

function baseProgress(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return 0
  return Math.round((base.indexedFileCount / base.fileCount) * 100)
}

function baseIndexText(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return '待整理'
  if (base.indexedFileCount >= base.fileCount) return '已索引'
  return '处理中'
}

function baseStatusClass(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return 'muted'
  if (base.indexedFileCount >= base.fileCount) return 'success'
  return 'warning'
}

function fileStatusClass(file: KnowledgeFileDTO) {
  if (isIndexedStatus(file.indexStatus)) return 'success'
  if (isFailedStatus(file.indexStatus)) return 'danger'
  return 'warning'
}

function statusLabel(value: string) {
  const labels: Record<string, string> = {
    active: '正常',
    chunking: '分块中',
    completed: '已索引',
    embedding: '向量化',
    failed: '异常',
    indexed: '已索引',
    indexing: '索引中',
    parsed: '已解析',
    parsing: '解析中',
    pending: '处理中',
    queued: '排队中',
    running: '处理中',
    uploaded: '已上传',
  }
  return labels[normalizedStatus(value)] ?? value
}

function sourceLabel(value: string) {
  const labels: Record<string, string> = {
    arxiv: 'arXiv 导入',
    file: '上传文件',
    upload: '上传文件',
  }
  const label = labels[normalizedStatus(value)] ?? value
  return label ? label : '未知来源'
}

function fileMetricUnit(file: KnowledgeFileDTO) {
  const name = `${file.originalFilename || file.filename}`.toLowerCase()
  if (name.endsWith('.json') || name.endsWith('.csv')) return 'records'
  return 'chunks'
}

function fileIconClass(file: KnowledgeFileDTO) {
  const name = `${file.originalFilename || file.filename}`.toLowerCase()
  if (name.endsWith('.pdf')) return 'pdf'
  if (name.endsWith('.md') || name.endsWith('.markdown')) return 'markdown'
  if (name.endsWith('.json')) return 'json'
  if (name.endsWith('.csv')) return 'table'
  return 'document'
}

async function loadBases() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    bases.value = await getKnowledgeBases({ keyword: keyword.value || undefined })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '知识库加载失败'
  } finally {
    isLoading.value = false
  }
}

async function loadFiles() {
  if (!selectedBaseId.value) {
    files.value = []
    return
  }
  isDetailLoading.value = true
  try {
    files.value = await getKnowledgeFiles(selectedBaseId.value)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '文件列表加载失败')
  } finally {
    isDetailLoading.value = false
  }
}

async function openBase(baseId: string) {
  selectedBaseId.value = baseId
  fileKeyword.value = ''
  await loadFiles()
}

function backToList() {
  selectedBaseId.value = ''
  files.value = []
  fileKeyword.value = ''
}

function promptUploadInDetail() {
  ElMessage.info('请先进入知识库详情页，再上传文件到对应知识库')
}

async function submitBase() {
  if (!newBase.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  try {
    const created = await createKnowledgeBase(newBase.value)
    bases.value.unshift(created)
    newBase.value = { name: '', description: '' }
    createVisible.value = false
    await openBase(created.id)
    ElMessage.success('知识库已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建失败')
  }
}

async function uploadFile(options: UploadRequestOptions) {
  if (!selectedBaseId.value || !(options.file instanceof File)) return
  try {
    const file = await uploadKnowledgeFile(selectedBaseId.value, options.file)
    files.value.unshift(file)
    await loadBases()
    void pollIndexStatus(file.id)
    ElMessage.success('文件已上传，索引任务已启动')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '上传失败')
  }
}

function updateFile(nextFile: KnowledgeFileDTO) {
  files.value = files.value.map((item) => (item.id === nextFile.id ? nextFile : item))
}

async function pollIndexStatus(fileId: string) {
  for (let attempt = 0; attempt < 24; attempt += 1) {
    const status = await getKnowledgeFileIndexStatus(fileId)
    updateFile(status.file)
    if (!status.job || ['completed', 'failed'].includes(status.job.status) || ['indexed', 'failed'].includes(status.file.indexStatus)) {
      await loadBases()
      return
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1500))
  }
  await loadFiles()
  await loadBases()
}

onMounted(loadBases)
</script>

<template>
  <div class="page-shell kb-page-shell">
    <template v-if="!isDetailMode">
      <header class="module-header kb-page-header">
        <div>
          <h2>知识库</h2>
          <p>管理您的研究资料、解析文件与可检索语料库，构建可靠的知识基础。</p>
        </div>
        <div class="page-actions">
          <el-button @click="promptUploadInDetail">
            <el-icon><UploadFilled /></el-icon>
            上传文件
          </el-button>
          <el-button type="primary" @click="createVisible = true">
            <el-icon><Plus /></el-icon>
            新建知识库
          </el-button>
        </div>
      </header>

      <div class="kb-global-search">
        <el-input v-model="keyword" clearable placeholder="搜索知识库或最近上传的文件..." @keyup.enter="loadBases">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

      <div class="kb-list-layout">
        <section class="kb-base-list-panel" v-loading="isLoading">
          <el-empty v-if="!filteredBases.length && !isLoading" description="暂无知识库" />

          <button
            v-for="(base, index) in filteredBases"
            :key="base.id"
            class="kb-base-card"
            type="button"
            @click="openBase(base.id)"
          >
            <span class="kb-base-icon" :class="`tone-${(index % 4) + 1}`">
              <el-icon><Notebook /></el-icon>
            </span>
            <span class="kb-base-body">
              <span class="kb-base-title-row">
                <strong>{{ base.name || '未命名知识库' }}</strong>
                <em v-if="index === 0">默认</em>
              </span>
              <span class="kb-base-description">{{ base.description || '暂无描述' }}</span>
              <span class="kb-base-metrics">
                <span>
                  <small>文件数</small>
                  <strong>{{ base.fileCount }}</strong>
                </span>
                <span>
                  <small>索引状态</small>
                  <strong :class="baseStatusClass(base)">{{ baseIndexText(base) }}</strong>
                </span>
                <span>
                  <small>进度</small>
                  <span class="kb-progress-line">
                    <i :style="{ width: `${baseProgress(base)}%` }"></i>
                  </span>
                  <strong>{{ baseProgress(base) }}%</strong>
                </span>
                <span>
                  <small>最近更新</small>
                  <strong>{{ formatCompactDate(base.updatedAt || base.createdAt) }}</strong>
                </span>
              </span>
            </span>
            <span class="kb-card-actions">
              <el-button text type="primary">
                查看详情
                <el-icon><ArrowRight /></el-icon>
              </el-button>
              <el-button text circle @click.stop>
                <el-icon><More /></el-icon>
              </el-button>
            </span>
          </button>
        </section>

        <aside class="kb-side-rail">
          <section class="kb-side-card">
            <h3>总体概览</h3>
            <div class="kb-overview-grid">
              <div>
                <span>知识库总数</span>
                <strong>{{ bases.length }}</strong>
              </div>
              <div>
                <span>文件总数</span>
                <strong>{{ totalFileCount }}</strong>
              </div>
              <div>
                <span>已索引文件</span>
                <strong>{{ totalIndexedCount }}</strong>
              </div>
              <div>
                <span>存储占用</span>
                <strong>{{ totalStorageText }}</strong>
              </div>
            </div>
          </section>

          <section class="kb-side-card">
            <div class="kb-side-card-head">
              <h3>最近上传</h3>
              <el-button text type="primary">查看全部 <el-icon><ArrowRight /></el-icon></el-button>
            </div>
            <div class="kb-recent-list">
              <p v-if="!recentFiles.length">暂无最近上传文件。</p>
              <div v-for="file in recentFiles" :key="file.id" class="kb-recent-item">
                <span :class="['kb-file-mini-icon', fileIconClass(file)]">
                  <el-icon><Document /></el-icon>
                </span>
                <strong>{{ file.originalFilename || file.filename }}</strong>
                <small>{{ formatCompactDate(file.createdAt || file.updatedAt) }}</small>
              </div>
            </div>
          </section>

          <section class="kb-side-card">
            <h3>交互说明</h3>
            <div class="kb-guide-list">
              <p>
                <span><el-icon><UploadFilled /></el-icon></span>
                上传文档后系统将自动解析并建立索引，完成后即可检索。
              </p>
              <p>
                <span><el-icon><Files /></el-icon></span>
                支持多种文件格式：PDF、DOCX、Markdown、TXT 等。
              </p>
              <p>
                <span><el-icon><Check /></el-icon></span>
                可在对话、智能体与检索中引用知识库内容，获取更准确的回答。
              </p>
              <p>
                <span><el-icon><Setting /></el-icon></span>
                通过“查看详情”可管理文件、分段、索引与权限等设置。
              </p>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <template v-else>
      <header class="module-header kb-page-header">
        <div>
          <h2>知识库详情</h2>
          <p>知识库 / {{ selectedBase?.name || '未命名知识库' }}</p>
        </div>
        <div class="page-actions">
          <el-button @click="backToList">
            <el-icon><Back /></el-icon>
            返回列表
          </el-button>
          <el-upload :show-file-list="false" :http-request="uploadFile" :disabled="!selectedBaseId">
            <el-button type="primary" :disabled="!selectedBaseId">
              <el-icon><UploadFilled /></el-icon>
              上传文件
            </el-button>
          </el-upload>
        </div>
      </header>

      <section class="kb-detail-search-card">
        <el-input v-model="fileKeyword" clearable placeholder="搜索文件名、标签或解析状态">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button>
          <el-icon><Filter /></el-icon>
          筛选
        </el-button>
      </section>

      <div class="kb-detail-layout">
        <main class="kb-file-table-card" v-loading="isDetailLoading">
          <div class="kb-file-table-head">
            <h3>文件列表</h3>
          </div>

          <div class="kb-file-table">
            <div class="kb-file-table-header">
              <span>文件名</span>
              <span>来源</span>
              <span>分块数 / 记录数</span>
              <span>最近更新</span>
              <span>状态</span>
              <span></span>
            </div>

            <el-empty v-if="!filteredFiles.length && !isDetailLoading" description="暂无文件" />
            <article v-for="file in filteredFiles" :key="file.id" class="kb-file-row">
              <span class="kb-file-name-cell">
                <span :class="['kb-file-icon', fileIconClass(file)]">
                  <el-icon><Document /></el-icon>
                </span>
                <span>
                  <strong>{{ file.originalFilename || file.filename }}</strong>
                  <small>{{ formatSize(file.sizeBytes) }}</small>
                </span>
              </span>
              <span>{{ sourceLabel(file.sourceType) }}</span>
              <span>
                <strong>{{ file.chunkCount.toLocaleString() }}</strong>
                <small>{{ fileMetricUnit(file) }}</small>
              </span>
              <span>{{ formatCompactDate(file.updatedAt || file.createdAt) }}</span>
              <span class="kb-file-status-cell">
                <em :class="['kb-status-pill', fileStatusClass(file)]">{{ statusLabel(file.indexStatus) }}</em>
                <em v-if="isIndexedStatus(file.indexStatus)" class="kb-status-pill info">可用于问答</em>
                <em v-else-if="isRunningStatus(file.indexStatus)" class="kb-status-pill info">解析中</em>
                <em v-else-if="isFailedStatus(file.indexStatus)" class="kb-status-pill danger">需处理</em>
              </span>
              <span class="kb-file-more-cell">
                <el-button text circle>
                  <el-icon><More /></el-icon>
                </el-button>
              </span>
            </article>
          </div>

          <footer class="kb-file-table-footer">
            <span>共 {{ filteredFiles.length }} 项</span>
            <div>
              <el-button>10 条 / 页</el-button>
              <el-button text>‹</el-button>
              <strong>1</strong>
              <el-button text>›</el-button>
            </div>
          </footer>
        </main>

        <aside class="kb-side-rail">
          <section class="kb-side-card">
            <h3>知识库信息</h3>
            <div class="kb-info-list">
              <div v-for="[label, value] in knowledgeInfoRows" :key="label">
                <span>{{ label }}</span>
                <strong>{{ value }}</strong>
              </div>
              <div>
                <span>可用状态</span>
                <strong class="kb-inline-status">
                  <i></i>
                  {{ selectedFailedCount ? `${selectedFailedCount} 个异常` : '正常' }}
                </strong>
              </div>
            </div>
          </section>

          <section class="kb-side-card">
            <h3>解析配置</h3>
            <div class="kb-info-list">
              <div>
                <span>分块策略</span>
                <strong>通用分块（自适应）</strong>
              </div>
              <div>
                <span>平均分块大小</span>
                <strong>800 tokens</strong>
              </div>
              <div>
                <span>重叠大小</span>
                <strong>120 tokens</strong>
              </div>
              <div>
                <span>OCR</span>
                <strong>开启</strong>
              </div>
              <div>
                <span>表格识别</span>
                <strong>开启</strong>
              </div>
              <div>
                <span>语言</span>
                <strong>自动检测</strong>
              </div>
            </div>
            <el-button text type="primary">查看完整配置 <el-icon><ArrowRight /></el-icon></el-button>
          </section>

          <section class="kb-side-card">
            <h3>使用说明</h3>
            <ul class="kb-help-list">
              <li>支持上传 PDF、Markdown、JSON、CSV、Word 等格式文件。</li>
              <li>文件解析完成并索引后，才能用于问答。</li>
              <li>可通过标签或文件名快速检索目标内容。</li>
              <li>如解析异常，请重新上传或检查文件格式。</li>
            </ul>
          </section>
        </aside>
      </div>
    </template>

    <el-dialog v-model="createVisible" title="新建知识库" width="480px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="newBase.name" placeholder="例如 Multi-Agent Literature QA" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newBase.description" type="textarea" :rows="3" placeholder="说明这个知识库服务的研究主题" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitBase">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.kb-page-shell {
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

.kb-page-header {
  flex-shrink: 0;
  margin-bottom: 18px;
}

.kb-global-search {
  width: min(700px, 52%);
  flex-shrink: 0;
  margin: -6px 0 20px;
}

.kb-list-layout,
.kb-detail-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  flex: 1;
  min-height: 0;
  gap: 20px;
  overflow: hidden;
}

.kb-base-list-panel {
  display: grid;
  align-content: start;
  min-height: 0;
  gap: 14px;
  overflow-y: auto;
  padding-right: 6px;
}

.kb-base-card {
  display: grid;
  grid-template-columns: 74px minmax(0, 1fr) auto;
  align-items: center;
  gap: 22px;
  width: 100%;
  min-height: 146px;
  padding: 24px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
  color: var(--pc-text);
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;

  &:hover {
    border-color: rgba(37, 99, 235, 0.45);
    box-shadow: 0 14px 28px rgba(15, 23, 42, 0.08);
    transform: translateY(-1px);
  }
}

.kb-base-icon {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  font-size: 30px;

  &.tone-1 {
    background: #edf4ff;
    color: var(--pc-brand);
  }

  &.tone-2 {
    background: #eafaf2;
    color: #16a34a;
  }

  &.tone-3 {
    background: #fff1e6;
    color: #f97316;
  }

  &.tone-4 {
    background: #f1eaff;
    color: #7c3aed;
  }
}

.kb-base-body {
  display: grid;
  min-width: 0;
  gap: 10px;
}

.kb-base-title-row {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 10px;

  strong {
    overflow: hidden;
    color: var(--pc-text);
    font-size: 18px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  em {
    flex: 0 0 auto;
    padding: 3px 8px;
    border-radius: 8px;
    background: var(--pc-brand-soft);
    color: var(--pc-brand);
    font-size: 12px;
    font-style: normal;
    font-weight: 700;
  }
}

.kb-base-description {
  overflow: hidden;
  color: var(--pc-text-muted);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-base-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(90px, 1fr));
  gap: 18px;

  > span {
    display: grid;
    min-width: 0;
    gap: 3px;
    padding-left: 18px;
    border-left: 1px solid var(--pc-border);

    &:first-child {
      padding-left: 0;
      border-left: none;
    }
  }

  small {
    color: var(--pc-text-muted);
    font-size: 12px;
  }

  strong {
    overflow: hidden;
    color: var(--pc-text-secondary);
    font-size: 14px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;

    &.success {
      color: var(--pc-success-text);
    }

    &.warning {
      color: var(--pc-warning-text);
    }

    &.muted {
      color: var(--pc-text-muted);
    }
  }
}

.kb-file-row small,
.kb-recent-item small,
.kb-overview-grid span,
.kb-info-list span {
  color: var(--pc-text-muted);
  font-size: 12px;
}

.kb-progress-line {
  position: relative;
  width: 80px;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5e7eb;

  i {
    position: absolute;
    inset: 0 auto 0 0;
    border-radius: inherit;
    background: #16a34a;
  }
}

.kb-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.kb-side-rail {
  display: grid;
  align-content: start;
  min-height: 0;
  gap: 14px;
  overflow-y: auto;
  padding-right: 4px;
}

.kb-side-card {
  padding: 20px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);

  h3 {
    margin: 0 0 16px;
    color: var(--pc-text);
    font-size: 18px;
  }
}

.kb-file-table-head h3 {
  margin: 0 0 16px;
  color: var(--pc-text);
  font-size: 18px;
}

.kb-side-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;

  h3 {
    margin: 0;
  }
}

.kb-overview-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;

  div {
    display: grid;
    justify-items: center;
    gap: 4px;
    padding: 18px 12px;
    border: 1px solid var(--pc-border);
    border-radius: 10px;
    background: var(--pc-surface-soft);
  }

  strong {
    color: var(--pc-text);
    font-size: 20px;
  }
}

.kb-recent-list {
  display: grid;
  gap: 10px;

  p {
    margin: 0;
    color: var(--pc-text-muted);
    font-size: 13px;
  }
}

.kb-recent-item {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  min-width: 0;

  strong {
    overflow: hidden;
    color: var(--pc-text-secondary);
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.kb-file-mini-icon,
.kb-file-icon {
  display: grid;
  place-items: center;
  border-radius: 9px;
}

.kb-file-mini-icon {
  width: 22px;
  height: 22px;
  font-size: 13px;
}

.kb-file-icon {
  width: 38px;
  height: 38px;
  font-size: 18px;
}

.kb-file-mini-icon.pdf,
.kb-file-icon.pdf {
  background: #ffe8e8;
  color: #e53935;
}

.kb-file-mini-icon.markdown,
.kb-file-icon.markdown {
  background: #eaf2ff;
  color: var(--pc-brand);
}

.kb-file-mini-icon.json,
.kb-file-icon.json {
  background: #f1eaff;
  color: #7c3aed;
}

.kb-file-mini-icon.table,
.kb-file-icon.table {
  background: #e9f9ef;
  color: #16a34a;
}

.kb-file-mini-icon.document,
.kb-file-icon.document {
  background: #eef4ff;
  color: var(--pc-brand);
}

.kb-guide-list {
  display: grid;
  gap: 14px;

  p {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    align-items: start;
    gap: 12px;
    margin: 0;
    color: var(--pc-text-secondary);
    font-size: 13px;
    line-height: 1.55;
  }

  span {
    display: grid;
    place-items: center;
    width: 30px;
    height: 30px;
    border-radius: 999px;
    background: #eaf2ff;
    color: var(--pc-brand);
  }
}

.kb-detail-search-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 104px;
  flex-shrink: 0;
  gap: 12px;
  width: min(980px, 100%);
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
}

.kb-file-table-card {
  display: flex;
  min-height: 0;
  flex-direction: column;
  padding: 20px;
  border: 1px solid var(--pc-border);
  border-radius: 16px;
  background: var(--pc-surface);
}

.kb-file-table-head {
  flex-shrink: 0;
}

.kb-file-table {
  min-height: 0;
  overflow: auto;
  border: 1px solid var(--pc-border);
  border-radius: 12px;
}

.kb-file-table-header,
.kb-file-row {
  display: grid;
  grid-template-columns: minmax(260px, 1.6fr) minmax(110px, 0.75fr) minmax(130px, 0.8fr) minmax(120px, 0.8fr) minmax(150px, 0.9fr) 44px;
  align-items: center;
  min-width: 860px;
}

.kb-file-table-header {
  min-height: 46px;
  padding: 0 16px;
  background: #fbfdff;
  color: var(--pc-text-muted);
  font-size: 13px;
  font-weight: 650;
}

.kb-file-row {
  min-height: 88px;
  padding: 0 16px;
  border-top: 1px solid var(--pc-border);
  color: var(--pc-text-secondary);
  font-size: 14px;
}

.kb-file-name-cell {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  min-width: 0;
  gap: 12px;

  strong {
    display: block;
    overflow: hidden;
    color: var(--pc-text);
    font-size: 14px;
    font-weight: 650;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.kb-file-row > span > strong {
  display: block;
  overflow: hidden;
  color: var(--pc-text);
  font-size: 14px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-file-status-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kb-status-pill {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 24px;
  padding: 3px 8px;
  border-radius: 7px;
  font-size: 12px;
  font-style: normal;
  font-weight: 650;

  &.success {
    background: var(--pc-success-bg);
    color: var(--pc-success-text);
  }

  &.warning {
    background: var(--pc-warning-bg);
    color: var(--pc-warning-text);
  }

  &.danger {
    background: var(--pc-danger-bg);
    color: var(--pc-danger-text);
  }

  &.info {
    background: #eaf2ff;
    color: var(--pc-brand);
  }
}

.kb-file-more-cell {
  justify-self: end;
}

.kb-file-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 16px 12px 0;
  color: var(--pc-text-secondary);
  font-size: 14px;

  div {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  strong {
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border: 1px solid #d8e5ff;
    border-radius: 9px;
    color: var(--pc-brand);
  }
}

.kb-info-list {
  display: grid;
  gap: 12px;

  div {
    display: grid;
    grid-template-columns: 88px minmax(0, 1fr);
    gap: 12px;
    color: var(--pc-text-secondary);
    font-size: 13px;
  }

  strong {
    min-width: 0;
    color: var(--pc-text-secondary);
    font-weight: 600;
    line-height: 1.45;
  }
}

.kb-inline-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  i {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #22c55e;
  }
}

.kb-help-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-left: 18px;
  color: var(--pc-text-secondary);
  font-size: 13px;
  line-height: 1.55;
}
</style>
