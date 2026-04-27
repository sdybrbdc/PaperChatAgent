<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, type UploadRequestOptions } from 'element-plus'
import { Back, Link, Plus, Refresh, Search, UploadFilled } from '@element-plus/icons-vue'
import {
  bindKnowledgeBase,
  createKnowledgeBase,
  getConversationKnowledgeBindings,
  getKnowledgeBases,
  getKnowledgeFiles,
  importArxivFile,
  uploadKnowledgeFile,
} from '../../apis/knowledge'
import type { KnowledgeBaseDTO, KnowledgeBindingDTO, KnowledgeFileDTO } from '../../types/knowledge'

const bases = ref<KnowledgeBaseDTO[]>([])
const files = ref<KnowledgeFileDTO[]>([])
const bindings = ref<KnowledgeBindingDTO[]>([])
const selectedBaseId = ref('')
const isLoading = ref(false)
const isDetailLoading = ref(false)
const createVisible = ref(false)
const errorMessage = ref('')
const keyword = ref('')
const fileKeyword = ref('')
const conversationId = ref('')
const arxivId = ref('')
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
  return files.value.filter((file) => `${file.originalFilename} ${file.filename}`.toLowerCase().includes(word))
})

const totalFileCount = computed(() => bases.value.reduce((sum, base) => sum + base.fileCount, 0))
const totalIndexedCount = computed(() => bases.value.reduce((sum, base) => sum + base.indexedFileCount, 0))
const recentFiles = computed(() =>
  bases.value.flatMap((base) => base.recentFiles ?? []).slice(0, 4),
)

function formatDate(value: string | null) {
  if (!value) return '-'
  return value.slice(0, 10)
}

function formatSize(value: number) {
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  return `${Math.max(1, Math.ceil(value / 1024))} KB`
}

function progressLabel(base: KnowledgeBaseDTO) {
  if (!base.fileCount) return '待上传'
  return `${base.indexedFileCount}/${base.fileCount} 已索引`
}

function fileStatusClass(file: KnowledgeFileDTO) {
  if (file.indexStatus === 'completed' || file.indexStatus === 'indexed') return 'success'
  if (file.indexStatus === 'failed') return 'danger'
  return 'warning'
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
  await loadFiles()
}

function backToList() {
  selectedBaseId.value = ''
  files.value = []
  bindings.value = []
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
    ElMessage.success('文件已提交索引')
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
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>{{ isDetailMode ? '知识库详情' : '知识库列表' }}</h2>
        <p>
          {{
            isDetailMode
              ? '查看文件解析、向量索引和会话绑定状态，让回答过程只使用当前研究资料。'
              : '按主题组织论文资料、解析文件并建立可检索向量索引。'
          }}
        </p>
      </div>
      <div class="page-actions">
        <el-button v-if="isDetailMode" @click="backToList">
          <el-icon><Back /></el-icon>
          返回列表
        </el-button>
        <el-upload :show-file-list="false" :http-request="uploadFile" :disabled="!selectedBaseId">
          <el-button :disabled="!selectedBaseId">
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

    <div v-if="!isDetailMode" class="module-search-row">
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

    <div v-if="isDetailMode" class="module-search-row">
      <el-input v-model="fileKeyword" clearable placeholder="搜索当前知识库文件">
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="module-content-grid">
      <section class="module-surface">
        <template v-if="!isDetailMode">
          <div class="section-title-row">
            <div>
              <h3>我的知识库</h3>
              <p>每个知识库对应一个研究工作区，可独立维护文件与向量索引。</p>
            </div>
            <el-tag type="info">{{ filteredBases.length }} 个</el-tag>
          </div>

          <div v-loading="isLoading" class="module-list">
            <el-empty v-if="!filteredBases.length && !isLoading" description="暂无知识库" />
            <button
              v-for="base in filteredBases"
              :key="base.id"
              class="module-list-item"
              type="button"
              @click="openBase(base.id)"
            >
              <div>
                <h4>{{ base.name || '未命名知识库' }}</h4>
                <p>{{ base.description || '暂无描述' }}</p>
                <span>{{ progressLabel(base) }} · 更新于 {{ formatDate(base.updatedAt || base.createdAt) }}</span>
              </div>
              <strong class="module-list-side">打开详情</strong>
            </button>
          </div>
        </template>

        <template v-else>
          <div class="section-title-row">
            <div>
              <h3>文件列表</h3>
              <p>{{ selectedBase?.name }} · {{ selectedBase?.description || '当前知识库暂无描述。' }}</p>
            </div>
            <el-tag type="info">{{ filteredFiles.length }} 个文件</el-tag>
          </div>

          <div v-loading="isDetailLoading" class="module-list">
            <el-empty v-if="!filteredFiles.length && !isDetailLoading" description="暂无文件" />
            <article v-for="file in filteredFiles" :key="file.id" class="module-list-item">
              <div>
                <h4>{{ file.originalFilename || file.filename }}</h4>
                <p>{{ file.sourceType }} · {{ formatSize(file.sizeBytes) }} · {{ file.chunkCount }} 个片段</p>
                <span>解析：{{ file.parserStatus }} · 更新于 {{ formatDate(file.updatedAt || file.createdAt) }}</span>
              </div>
              <strong class="module-list-side" :class="['status-text', fileStatusClass(file)]">{{ file.indexStatus }}</strong>
            </article>
          </div>
        </template>
      </section>

      <aside class="module-rail">
        <template v-if="!isDetailMode">
          <section class="soft-panel module-rail-card">
            <h3>总体概览</h3>
            <p>知识库数量：{{ bases.length }}</p>
            <p>文件总数：{{ totalFileCount }}</p>
            <p>已索引文件：{{ totalIndexedCount }}</p>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>最近上传</h3>
            <div class="module-mini-list">
              <p v-if="!recentFiles.length">暂无最近上传文件。</p>
              <div v-for="file in recentFiles" :key="file.id" class="module-mini-item">
                <div>
                  <strong>{{ file.originalFilename || file.filename }}</strong>
                  <span>{{ file.indexStatus }} · {{ formatDate(file.createdAt) }}</span>
                </div>
              </div>
            </div>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>交互说明</h3>
            <p>进入详情后上传 PDF 或导入 arXiv，文件解析完成后会进入检索链路。</p>
          </section>
        </template>

        <template v-else>
          <section class="soft-panel module-rail-card">
            <h3>知识库信息</h3>
            <p>名称：{{ selectedBase?.name }}</p>
            <p>状态：{{ selectedBase?.status }}</p>
            <p>文件：{{ selectedBase?.indexedFileCount }}/{{ selectedBase?.fileCount }} 已索引</p>
            <p>更新：{{ formatDate(selectedBase?.updatedAt || selectedBase?.createdAt || null) }}</p>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>解析配置</h3>
            <p>默认切片：按段落与标题结构切分</p>
            <p>向量索引：写入当前用户空间</p>
            <div class="module-form-stack">
              <el-input v-model="arxivId" placeholder="arXiv ID，例如 2401.00001" />
              <el-button :disabled="!arxivId" @click="importArxiv">导入 arXiv</el-button>
            </div>
          </section>

          <section class="soft-panel module-rail-card">
            <h3>会话绑定</h3>
            <p>绑定后，聊天页可按当前会话自动注入对应知识库。</p>
            <div class="module-form-stack">
              <el-input v-model="conversationId" placeholder="conversation_id" />
              <div class="module-rail-actions">
                <el-button @click="loadBindings">查看绑定</el-button>
                <el-button type="primary" :disabled="!conversationId" @click="bindSelectedBase">
                  <el-icon><Link /></el-icon>
                  绑定当前知识库
                </el-button>
              </div>
            </div>
            <div class="module-mini-list">
              <div v-for="binding in bindings" :key="binding.id" class="module-mini-item">
                <div>
                  <strong>{{ binding.knowledgeBaseName || binding.knowledgeBaseId }}</strong>
                  <span>{{ binding.bindingType }} · {{ formatDate(binding.createdAt) }}</span>
                </div>
              </div>
            </div>
          </section>
        </template>
      </aside>
    </div>

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
