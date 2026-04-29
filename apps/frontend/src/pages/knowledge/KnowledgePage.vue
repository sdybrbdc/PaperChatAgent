<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import {
  Back,
  ChatLineRound,
  Check,
  DataAnalysis,
  Document,
  Files,
  FolderOpened,
  Link,
  MagicStick,
  Plus,
  Refresh,
  Search,
  UploadFilled,
  Warning,
} from '@element-plus/icons-vue'
import {
  answerKnowledge,
  bindKnowledgeBase,
  createKnowledgeBase,
  getConversationKnowledgeBindings,
  getKnowledgeFileIndexStatus,
  getKnowledgeBases,
  getKnowledgeFiles,
  importArxivFile,
  indexKnowledgeFile,
  retrieveKnowledge,
  uploadKnowledgeFile,
} from '../../apis/knowledge'
import type {
  KnowledgeBaseDTO,
  KnowledgeBindingDTO,
  KnowledgeFileDTO,
  RagAnswerDTO,
  RagRetrieveDTO,
} from '../../types/knowledge'

const bases = ref<KnowledgeBaseDTO[]>([])
const files = ref<KnowledgeFileDTO[]>([])
const bindings = ref<KnowledgeBindingDTO[]>([])
const selectedBaseId = ref('')
const isLoading = ref(false)
const isDetailLoading = ref(false)
const isRetrieving = ref(false)
const isAnswering = ref(false)
const indexingFileId = ref('')
const createVisible = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const fileKeyword = ref('')
const conversationId = ref('')
const arxivId = ref('')
const retrieveQuery = ref('')
const retrieveTopK = ref(8)
const retrieval = ref<RagRetrieveDTO | null>(null)
const ragAnswer = ref<RagAnswerDTO | null>(null)
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
    `${file.originalFilename} ${file.filename} ${file.sourceType} ${file.indexStatus}`.toLowerCase().includes(word),
  )
})

const totalFileCount = computed(() => bases.value.reduce((sum, base) => sum + base.fileCount, 0))
const totalIndexedCount = computed(() => bases.value.reduce((sum, base) => sum + base.indexedFileCount, 0))
const totalPendingCount = computed(() => Math.max(totalFileCount.value - totalIndexedCount.value, 0))
const recentFiles = computed(() => bases.value.flatMap((base) => base.recentFiles ?? []).slice(0, 5))
const retrievalItems = computed(() => retrieval.value?.items ?? [])
const answerTraceCount = computed(() => {
  const calls = ragAnswer.value?.trace?.tool_calls
  return Array.isArray(calls) ? calls.length : 0
})

const selectedIndexedCount = computed(() => files.value.filter((file) => isIndexedStatus(file.indexStatus)).length)
const selectedFailedCount = computed(() => files.value.filter((file) => isFailedStatus(file.indexStatus)).length)
const selectedPendingCount = computed(() =>
  files.value.filter((file) => !isIndexedStatus(file.indexStatus) && !isFailedStatus(file.indexStatus)).length,
)
const selectedStorageText = computed(() => formatSize(files.value.reduce((sum, file) => sum + file.sizeBytes, 0)))
const selectedProgress = computed(() => {
  if (!files.value.length) return 0
  return Math.round((selectedIndexedCount.value / files.value.length) * 100)
})

const sourceStats = computed(() => {
  const counts = files.value.reduce<Record<string, number>>((acc, file) => {
    const key = sourceLabel(file.sourceType)
    acc[key] = (acc[key] ?? 0) + 1
    return acc
  }, {})
  return Object.entries(counts).map(([label, count]) => ({ label, count }))
})

const pipelineItems = computed(() => [
  { label: '资料接入', value: `${totalFileCount.value} 文件`, icon: Files },
  { label: '解析切片', value: `${totalPendingCount.value} 待处理`, icon: MagicStick },
  { label: '索引就绪', value: `${totalIndexedCount.value} 已入库`, icon: Check },
])

function formatDate(value: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

function formatSize(value: number) {
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

function progressLabel(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return '待上传'
  return `${base.indexedFileCount}/${base.fileCount} 已索引`
}

function baseProgress(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return 0
  return Math.round((base.indexedFileCount / base.fileCount) * 100)
}

function baseStatusClass(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return 'warning'
  if (base.indexedFileCount >= base.fileCount) return 'success'
  return 'brand'
}

function fileStatusClass(file: KnowledgeFileDTO) {
  if (isIndexedStatus(file.indexStatus)) return 'success'
  if (isFailedStatus(file.indexStatus)) return 'danger'
  return 'warning'
}

function statusLabel(value: string) {
  const status = normalizedStatus(value)
  const labels: Record<string, string> = {
    active: '运行中',
    completed: '已完成',
    failed: '失败',
    chunking: '分块中',
    embedding: '向量化',
    indexed: '已索引',
    indexing: '入库中',
    parsed: '已解析',
    parsing: '解析中',
    pending: '等待中',
    queued: '排队中',
    running: '运行中',
    uploaded: '已上传',
  }
  return labels[status] ?? value
}

function sourceLabel(value: string) {
  const labels: Record<string, string> = {
    arxiv: 'arXiv',
    upload: '本地上传',
    file: '文件',
  }
  return labels[normalizedStatus(value)] ?? (value || '未知来源')
}

function scoreLabel(score: number) {
  return `${Math.round(score * 100)}%`
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
  bindings.value = []
  retrieval.value = null
  ragAnswer.value = null
  retrieveQuery.value = ''
  await loadFiles()
}

function backToList() {
  selectedBaseId.value = ''
  files.value = []
  bindings.value = []
  retrieval.value = null
  ragAnswer.value = null
  fileKeyword.value = ''
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

async function importArxiv() {
  if (!selectedBaseId.value || !arxivId.value.trim()) return
  try {
    const file = await importArxivFile(selectedBaseId.value, arxivId.value.trim())
    files.value.unshift(file)
    arxivId.value = ''
    await loadBases()
    ElMessage.success('arXiv 文件已导入')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入失败')
  }
}

async function runRetrieval() {
  if (!selectedBaseId.value || !retrieveQuery.value.trim()) {
    ElMessage.warning('请输入检索问题')
    return
  }
  isRetrieving.value = true
  try {
    retrieval.value = await retrieveKnowledge({
      query: retrieveQuery.value.trim(),
      knowledgeBaseIds: [selectedBaseId.value],
      topK: retrieveTopK.value,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '检索失败')
  } finally {
    isRetrieving.value = false
  }
}

async function runAgenticAnswer() {
  if (!selectedBaseId.value || !retrieveQuery.value.trim()) {
    ElMessage.warning('请输入问题')
    return
  }
  isAnswering.value = true
  try {
    ragAnswer.value = await answerKnowledge({
      query: retrieveQuery.value.trim(),
      knowledgeBaseIds: [selectedBaseId.value],
      topK: retrieveTopK.value,
      agentic: true,
    })
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Agentic 回答失败')
  } finally {
    isAnswering.value = false
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

async function indexFile(file: KnowledgeFileDTO) {
  indexingFileId.value = file.id
  try {
    const indexed = await indexKnowledgeFile(file.id)
    files.value = files.value.map((item) =>
      item.id === file.id
        ? { ...item, indexStatus: indexed.status, chunkCount: indexed.chunkCount, updatedAt: indexed.indexedAt }
        : item,
    )
    void pollIndexStatus(file.id)
    await loadBases()
    ElMessage.success('重新索引任务已启动')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '索引失败')
  } finally {
    indexingFileId.value = ''
  }
}

async function loadBindings() {
  if (!conversationId.value.trim()) return
  try {
    bindings.value = await getConversationKnowledgeBindings(conversationId.value.trim())
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '绑定列表加载失败')
  }
}

async function bindSelectedBase() {
  if (!conversationId.value.trim() || !selectedBaseId.value) return
  try {
    const binding = await bindKnowledgeBase({
      conversationId: conversationId.value.trim(),
      knowledgeBaseId: selectedBaseId.value,
    })
    bindings.value.unshift(binding)
    ElMessage.success('知识库已绑定到会话')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '绑定失败')
  }
}

onMounted(loadBases)
</script>

<template>
  <div class="page-shell rag-page-shell">
    <header class="module-header rag-page-header">
      <div class="rag-title-block">
        <span class="rag-title-icon">
          <el-icon><DataAnalysis /></el-icon>
        </span>
        <div>
          <h2>{{ isDetailMode ? 'RAG 知识库工作台' : 'RAG 知识库' }}</h2>
          <p>
            {{
              isDetailMode
                ? '验证检索命中、管理文件索引，并把当前资料范围绑定到对话链路。'
                : '围绕研究主题组织论文资料、上传文件、导入 arXiv，并为聊天与智能体准备可检索上下文。'
            }}
          </p>
        </div>
      </div>
      <div class="page-actions rag-header-actions">
        <el-button v-if="isDetailMode" @click="backToList">
          <el-icon><Back /></el-icon>
          返回
        </el-button>
        <el-upload v-if="isDetailMode" :show-file-list="false" :http-request="uploadFile" :disabled="!selectedBaseId">
          <el-button type="primary" :disabled="!selectedBaseId">
            <el-icon><UploadFilled /></el-icon>
            上传文件
          </el-button>
        </el-upload>
        <el-button v-if="!isDetailMode" type="primary" @click="createVisible = true">
          <el-icon><Plus /></el-icon>
          新建知识库
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <template v-if="!isDetailMode">
      <section class="rag-overview-band">
        <article class="rag-overview-copy">
          <span class="rag-kicker">Retrieval scope</span>
          <h3>把分散论文资料变成可控的检索范围</h3>
          <p>列表中的每个知识库都是一个独立 RAG 上下文，可单独维护文件、索引状态和会话绑定。</p>
        </article>
        <div class="rag-stat-strip">
          <div class="rag-stat-card">
            <span>知识库</span>
            <strong>{{ bases.length }}</strong>
          </div>
          <div class="rag-stat-card">
            <span>文件</span>
            <strong>{{ totalFileCount }}</strong>
          </div>
          <div class="rag-stat-card success">
            <span>已索引</span>
            <strong>{{ totalIndexedCount }}</strong>
          </div>
        </div>
      </section>

      <div class="rag-list-layout">
        <section class="rag-panel rag-library-panel">
          <div class="section-title-row">
            <div>
              <h3>知识库矩阵</h3>
              <p>用文件数量、索引进度和更新时间快速判断每个研究空间的可用状态。</p>
            </div>
            <el-tag type="info">{{ filteredBases.length }} 个</el-tag>
          </div>

          <div class="module-search-row">
            <el-input v-model="keyword" clearable placeholder="搜索知识库名称、主题或描述" @keyup.enter="loadBases">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button :loading="isLoading" @click="loadBases">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </template>
            </el-input>
          </div>

          <div v-loading="isLoading" class="rag-base-grid">
            <el-empty v-if="!filteredBases.length && !isLoading" description="暂无知识库" />
            <button
              v-for="base in filteredBases"
              :key="base.id"
              class="rag-base-card"
              type="button"
              @click="openBase(base.id)"
            >
              <div class="rag-base-card-head">
                <span class="rag-base-icon">
                  <el-icon><FolderOpened /></el-icon>
                </span>
                <el-tag :class="['rag-soft-tag', baseStatusClass(base)]" effect="plain">
                  {{ progressLabel(base) }}
                </el-tag>
              </div>
              <h4>{{ base.name || '未命名知识库' }}</h4>
              <p>{{ base.description || '暂无描述' }}</p>
              <el-progress :percentage="baseProgress(base)" :stroke-width="8" :show-text="false" />
              <div class="rag-base-meta">
                <span>
                  <el-icon><Files /></el-icon>
                  {{ base.fileCount }} 文件
                </span>
                <span>更新于 {{ formatDate(base.updatedAt || base.createdAt) }}</span>
              </div>
            </button>
          </div>
        </section>

        <aside class="rag-side-stack">
          <section class="rag-panel rag-pipeline-card">
            <div class="section-title-row compact">
              <div>
                <h3>RAG 流水线</h3>
                <p>从资料接入到可检索的当前状态。</p>
              </div>
            </div>
            <div class="rag-pipeline-list">
              <div v-for="item in pipelineItems" :key="item.label" class="rag-pipeline-step">
                <span>
                  <el-icon><component :is="item.icon" /></el-icon>
                </span>
                <div>
                  <strong>{{ item.label }}</strong>
                  <small>{{ item.value }}</small>
                </div>
              </div>
            </div>
          </section>

          <section class="rag-panel rag-recent-card">
            <div class="section-title-row compact">
              <div>
                <h3>最近资料</h3>
                <p>最近进入知识库的文件。</p>
              </div>
            </div>
            <div class="module-mini-list">
              <p v-if="!recentFiles.length">暂无最近上传文件。</p>
              <div v-for="file in recentFiles" :key="file.id" class="module-mini-item">
                <div>
                  <strong>{{ file.originalFilename || file.filename }}</strong>
                  <span>{{ statusLabel(file.indexStatus) }} · {{ formatDate(file.createdAt) }}</span>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </template>

    <template v-else>
      <section class="rag-detail-summary">
        <div class="rag-detail-copy">
          <span class="rag-kicker">Active knowledge base</span>
          <h3>{{ selectedBase?.name || '未命名知识库' }}</h3>
          <p>{{ selectedBase?.description || '当前知识库暂无描述。' }}</p>
        </div>
        <div class="rag-detail-metrics">
          <div>
            <span>索引进度</span>
            <strong>{{ selectedProgress }}%</strong>
          </div>
          <div>
            <span>文件</span>
            <strong>{{ files.length }}</strong>
          </div>
          <div>
            <span>待处理</span>
            <strong>{{ selectedPendingCount }}</strong>
          </div>
          <div>
            <span>体积</span>
            <strong>{{ selectedStorageText }}</strong>
          </div>
        </div>
      </section>

      <div class="rag-workspace-grid">
        <main class="rag-main-column">
          <section class="rag-panel rag-retrieval-panel">
            <div class="section-title-row">
              <div>
                <h3>检索预演</h3>
                <p>在接入聊天前先检查当前知识库能否命中正确片段。</p>
              </div>
              <el-tag type="success" effect="plain">{{ selectedIndexedCount }} 个可检索文件</el-tag>
            </div>

            <div class="rag-query-box">
              <el-input
                v-model="retrieveQuery"
                type="textarea"
                :rows="3"
                placeholder="输入一个研究问题，例如：这组论文里有哪些方法使用多智能体协作？"
              />
              <div class="rag-query-controls">
                <label>
                  Top K
                  <el-input-number v-model="retrieveTopK" :min="1" :max="20" controls-position="right" />
                </label>
                <el-button type="primary" :loading="isRetrieving" @click="runRetrieval">
                  <el-icon><Search /></el-icon>
                  运行检索
                </el-button>
                <el-button :loading="isAnswering" @click="runAgenticAnswer">
                  <el-icon><MagicStick /></el-icon>
                  Agentic 回答
                </el-button>
              </div>
            </div>

            <div class="rag-result-shell">
              <el-empty
                v-if="!retrieval && !isRetrieving"
                description="输入问题后运行检索，命中片段会显示在这里。"
              />
              <el-empty
                v-else-if="retrieval && !retrievalItems.length"
                description="当前范围没有命中结果，可调整问题或先补充索引。"
              />
              <article v-for="item in retrievalItems" :key="item.id" class="rag-result-item">
                <div class="rag-result-score">{{ scoreLabel(item.score) }}</div>
                <div>
                  <h4>{{ item.source.title || item.source.filename || '未命名来源' }}</h4>
                  <p>{{ item.text }}</p>
                  <span>{{ sourceLabel(item.source.sourceType) }} · {{ item.source.filename }}</span>
                </div>
              </article>
            </div>

            <article v-if="ragAnswer" class="rag-answer-card">
              <div class="rag-answer-head">
                <div>
                  <h4>Agentic 回答</h4>
                  <p>{{ ragAnswer.citations.length }} 条引用 · {{ answerTraceCount }} 次工具调用</p>
                </div>
                <el-tag type="success" effect="plain">Grounded</el-tag>
              </div>
              <p class="rag-answer-text">{{ ragAnswer.answer }}</p>
              <div class="rag-citation-list">
                <div v-for="citation in ragAnswer.citations" :key="citation.chunkId" class="rag-citation-item">
                  <strong>{{ citation.filename }}</strong>
                  <span>
                    {{ scoreLabel(citation.score) }} ·
                    {{ citation.pageNo ? `p.${citation.pageNo}` : '无页码' }} ·
                    {{ citation.sectionTitle || '无章节' }}
                  </span>
                  <p>{{ citation.snippet }}</p>
                </div>
              </div>
            </article>
          </section>

          <section class="rag-panel rag-file-panel">
            <div class="section-title-row">
              <div>
                <h3>文件与索引队列</h3>
                <p>查看解析状态、手动触发索引，并筛选当前知识库文件。</p>
              </div>
              <div class="rag-file-tools">
                <el-input v-model="fileKeyword" clearable placeholder="搜索文件">
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
                <el-button :loading="isDetailLoading" @click="loadFiles">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
            </div>

            <div v-loading="isDetailLoading" class="rag-file-list">
              <el-empty v-if="!filteredFiles.length && !isDetailLoading" description="暂无文件" />
              <article v-for="file in filteredFiles" :key="file.id" class="rag-file-item">
                <span class="rag-file-icon">
                  <el-icon><Document /></el-icon>
                </span>
                <div class="rag-file-main">
                  <div class="rag-file-title-row">
                    <h4>{{ file.originalFilename || file.filename }}</h4>
                    <el-tag :class="['rag-soft-tag', fileStatusClass(file)]" effect="plain">
                      {{ statusLabel(file.indexStatus) }}
                    </el-tag>
                  </div>
                  <p>
                    {{ sourceLabel(file.sourceType) }} · {{ formatSize(file.sizeBytes) }} ·
                    {{ file.chunkCount }} 个片段
                  </p>
                  <span>解析：{{ statusLabel(file.parserStatus) }} · 更新于 {{ formatDate(file.updatedAt || file.createdAt) }}</span>
                </div>
                <el-button
                  :disabled="isRunningStatus(file.indexStatus) && !isIndexedStatus(file.indexStatus)"
                  :loading="indexingFileId === file.id"
                  @click="indexFile(file)"
                >
                  {{ isIndexedStatus(file.indexStatus) ? '重新索引' : '索引' }}
                </el-button>
              </article>
            </div>
          </section>
        </main>

        <aside class="rag-side-stack">
          <section class="rag-panel">
            <div class="section-title-row compact">
              <div>
                <h3>导入资料</h3>
                <p>支持快速生成 arXiv 元数据占位文件。</p>
              </div>
            </div>
            <div class="module-form-stack">
              <el-input v-model="arxivId" placeholder="arXiv ID，例如 2401.00001" />
              <el-button :disabled="!arxivId" @click="importArxiv">
                <el-icon><Plus /></el-icon>
                导入 arXiv
              </el-button>
            </div>
          </section>

          <section class="rag-panel">
            <div class="section-title-row compact">
              <div>
                <h3>会话绑定</h3>
                <p>把当前知识库绑定到指定 conversation。</p>
              </div>
            </div>
            <div class="module-form-stack">
              <el-input v-model="conversationId" placeholder="conversation_id" />
              <div class="module-rail-actions">
                <el-button @click="loadBindings">查看</el-button>
                <el-button type="primary" :disabled="!conversationId" @click="bindSelectedBase">
                  <el-icon><Link /></el-icon>
                  绑定
                </el-button>
              </div>
            </div>
            <div class="module-mini-list">
              <p v-if="!bindings.length">暂无绑定记录。</p>
              <div v-for="binding in bindings" :key="binding.id" class="module-mini-item">
                <div>
                  <strong>{{ binding.knowledgeBaseName || binding.knowledgeBaseId }}</strong>
                  <span>{{ binding.bindingType }} · {{ formatDate(binding.createdAt) }}</span>
                </div>
              </div>
            </div>
          </section>

          <section class="rag-panel rag-health-card">
            <div class="rag-health-row">
              <span>
                <el-icon><ChatLineRound /></el-icon>
              </span>
              <div>
                <strong>对话注入范围</strong>
                <p>{{ retrieval?.usedKnowledgeBaseIds.length || 0 }} 个知识库参与最近一次预演。</p>
              </div>
            </div>
            <div class="rag-health-row">
              <span class="warning">
                <el-icon><Warning /></el-icon>
              </span>
              <div>
                <strong>异常文件</strong>
                <p>{{ selectedFailedCount }} 个文件需要重新上传或检查解析结果。</p>
              </div>
            </div>
          </section>

          <section class="rag-panel">
            <div class="section-title-row compact">
              <div>
                <h3>来源分布</h3>
                <p>当前知识库文件来源概览。</p>
              </div>
            </div>
            <div class="rag-source-list">
              <p v-if="!sourceStats.length">暂无文件来源。</p>
              <div v-for="item in sourceStats" :key="item.label">
                <span>{{ item.label }}</span>
                <strong>{{ item.count }}</strong>
              </div>
            </div>
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
