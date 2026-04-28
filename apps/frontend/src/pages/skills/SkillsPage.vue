<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CloseBold,
  Delete,
  Document,
  Edit,
  FolderOpened,
  Plus,
  Refresh,
  View,
} from '@element-plus/icons-vue'
import {
  addSkillFile,
  createSkill,
  deleteSkill,
  deleteSkillFile,
  getSkill,
  getSkills,
  importLocalSkill,
  updateSkill,
  updateSkillFile,
} from '../../apis/skills'
import type { SkillDTO, SkillFileNode, SkillFolderNode, SkillTreeNode } from '../../types/skills'

type FlatNode = {
  node: SkillTreeNode
  depth: number
  parent: SkillFolderNode | null
}

const skills = ref<SkillDTO[]>([])
const selectedSkill = ref<SkillDTO | null>(null)
const selectedFile = ref<SkillFileNode | null>(null)
const fileDraft = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const isImporting = ref(false)
const isDrawerVisible = ref(false)
const isCreateVisible = ref(false)
const isImportVisible = ref(false)
const isAddFileVisible = ref(false)
const errorMessage = ref('')

const createForm = ref({
  name: '',
  description: '',
  status: 'enabled',
})

const importForm = ref({
  sourceUri: '',
  status: 'enabled',
})

const detailForm = ref({
  name: '',
  description: '',
  status: 'enabled',
})

const addFileForm = ref({
  path: '',
  name: '',
})

const enabledCount = computed(() => skills.value.filter((item) => item.status === 'enabled').length)

const flatNodes = computed<FlatNode[]>(() => {
  const root = selectedSkill.value?.folder
  if (!root) return []
  const rows: FlatNode[] = []
  const walk = (items: SkillTreeNode[], depth: number, parent: SkillFolderNode | null) => {
    for (const item of items) {
      rows.push({ node: item, depth, parent })
      if (item.type === 'folder') {
        walk(item.folder, depth + 1, item)
      }
    }
  }
  walk(root.folder, 0, root)
  return rows
})

const addableFolders = computed(() =>
  flatNodes.value
    .map((item) => item.node)
    .filter((item): item is SkillFolderNode => item.type === 'folder' && canAddToFolder(item)),
)

function truncateText(value: string, maxLength = 120) {
  if (!value) return '暂无描述'
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

function countFiles(skill: SkillDTO) {
  if (skill.fileCount) return skill.fileCount
  if (!skill.folder) return 0
  let count = 0
  const walk = (items: SkillTreeNode[]) => {
    for (const item of items) {
      if (item.type === 'file') count += 1
      if (item.type === 'folder') walk(item.folder)
    }
  }
  walk(skill.folder.folder)
  return count
}

function formatRelativeTime(value: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const diff = Date.now() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 30) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function canAddToFolder(folder: SkillFolderNode) {
  return ['reference', 'references', 'scripts'].includes(folder.name)
}

function canDeleteFile(file: SkillFileNode) {
  return file.name !== 'SKILL.md' && (/\/scripts\//.test(file.path) || /\/references?\//.test(file.path))
}

function selectFile(file: SkillFileNode) {
  selectedFile.value = file
  fileDraft.value = file.content
}

function selectFirstFile(skill: SkillDTO) {
  const firstFile = flatNodes.value.find((item) => item.node.type === 'file')?.node
  if (firstFile?.type === 'file') {
    selectFile(firstFile)
    return
  }
  const skillMd = skill.folder?.folder.find((item): item is SkillFileNode => item.type === 'file' && item.name === 'SKILL.md')
  if (skillMd) selectFile(skillMd)
}

function resetCreateForm() {
  createForm.value = { name: '', description: '', status: 'enabled' }
}

function resetAddFileForm() {
  addFileForm.value = { path: addableFolders.value[0]?.path ?? '', name: '' }
}

async function loadSkills() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    skills.value = await getSkills()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Skills 加载失败'
  } finally {
    isLoading.value = false
  }
}

async function openSkill(skill: SkillDTO) {
  isLoading.value = true
  try {
    const detail = await getSkill(skill.id)
    selectedSkill.value = detail
    detailForm.value = {
      name: detail.name,
      description: detail.description,
      status: detail.status === 'enabled' ? 'enabled' : 'disabled',
    }
    selectedFile.value = null
    fileDraft.value = ''
    isDrawerVisible.value = true
    selectFirstFile(detail)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Skill 详情加载失败')
  } finally {
    isLoading.value = false
  }
}

async function submitCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入 Skill 名称')
    return
  }
  isSaving.value = true
  try {
    const created = await createSkill({
      name: createForm.value.name.trim(),
      description: createForm.value.description.trim(),
      sourceType: 'custom',
      status: createForm.value.status,
    })
    skills.value = [created, ...skills.value]
    isCreateVisible.value = false
    resetCreateForm()
    ElMessage.success('Skill 已创建')
    await openSkill(created)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建 Skill 失败')
  } finally {
    isSaving.value = false
  }
}

async function submitImport() {
  isImporting.value = true
  try {
    const result = await importLocalSkill({
      sourceUri: importForm.value.sourceUri.trim(),
      status: importForm.value.status,
    })
    await loadSkills()
    isImportVisible.value = false
    importForm.value = { sourceUri: '', status: 'enabled' }
    ElMessage.success(`导入完成：新增 ${result.created.length} 个，跳过 ${result.skipped.length} 个，失败 ${result.failed.length} 个`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入本地 Skill 失败')
  } finally {
    isImporting.value = false
  }
}

async function importAllLocalSkills() {
  isImporting.value = true
  try {
    const result = await importLocalSkill({ status: 'enabled' })
    await loadSkills()
    ElMessage.success(`本地 Skill 导入完成：新增 ${result.created.length} 个，跳过 ${result.skipped.length} 个`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入本地 Skill 失败')
  } finally {
    isImporting.value = false
  }
}

async function saveSkillMeta() {
  if (!selectedSkill.value) return
  if (!detailForm.value.name.trim()) {
    ElMessage.warning('请输入 Skill 名称')
    return
  }
  isSaving.value = true
  try {
    const updated = await updateSkill(selectedSkill.value.id, {
      name: detailForm.value.name.trim(),
      description: detailForm.value.description.trim(),
      status: detailForm.value.status,
    })
    selectedSkill.value = updated
    skills.value = skills.value.map((item) => (item.id === updated.id ? updated : item))
    ElMessage.success('Skill 信息已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存 Skill 信息失败')
  } finally {
    isSaving.value = false
  }
}

async function saveSelectedFile() {
  if (!selectedSkill.value || !selectedFile.value) return
  isSaving.value = true
  try {
    const updated = await updateSkillFile(selectedSkill.value.id, {
      path: selectedFile.value.path,
      content: fileDraft.value,
    })
    selectedSkill.value = updated
    skills.value = skills.value.map((item) => (item.id === updated.id ? updated : item))
    const refreshedFile = flatNodes.value.find((item) => item.node.type === 'file' && item.node.path === selectedFile.value?.path)
    if (refreshedFile?.node.type === 'file') selectFile(refreshedFile.node)
    ElMessage.success('文件已保存')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存文件失败')
  } finally {
    isSaving.value = false
  }
}

async function submitAddFile() {
  if (!selectedSkill.value) return
  if (!addFileForm.value.path || !addFileForm.value.name.trim()) {
    ElMessage.warning('请选择目录并填写文件名')
    return
  }
  isSaving.value = true
  try {
    const updated = await addSkillFile(selectedSkill.value.id, {
      path: addFileForm.value.path,
      name: addFileForm.value.name.trim(),
    })
    selectedSkill.value = updated
    skills.value = skills.value.map((item) => (item.id === updated.id ? updated : item))
    isAddFileVisible.value = false
    resetAddFileForm()
    ElMessage.success('文件已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建文件失败')
  } finally {
    isSaving.value = false
  }
}

async function removeFile(file: SkillFileNode) {
  if (!selectedSkill.value) return
  try {
    await ElMessageBox.confirm(`确定删除文件「${file.name}」吗？`, '删除文件', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  isSaving.value = true
  try {
    const updated = await deleteSkillFile(selectedSkill.value.id, { path: file.path })
    selectedSkill.value = updated
    skills.value = skills.value.map((item) => (item.id === updated.id ? updated : item))
    if (selectedFile.value?.path === file.path) {
      selectedFile.value = null
      fileDraft.value = ''
    }
    ElMessage.success('文件已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除文件失败')
  } finally {
    isSaving.value = false
  }
}

async function removeSkill(skill: SkillDTO) {
  try {
    await ElMessageBox.confirm(`确定删除 Skill「${skill.name}」吗？此操作不可恢复。`, '删除 Skill', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await deleteSkill(skill.id)
    skills.value = skills.value.filter((item) => item.id !== skill.id)
    if (selectedSkill.value?.id === skill.id) {
      isDrawerVisible.value = false
      selectedSkill.value = null
      selectedFile.value = null
    }
    ElMessage.success('Skill 已删除')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '删除 Skill 失败')
  }
}

function openAddFileDialog(folder?: SkillFolderNode) {
  addFileForm.value = {
    path: folder?.path ?? addableFolders.value[0]?.path ?? '',
    name: '',
  }
  isAddFileVisible.value = true
}

onMounted(loadSkills)
</script>

<template>
  <div class="page-shell skill-table-page">
    <header class="skill-table-header">
      <div class="skill-table-title">
        <div class="skill-title-icon">
          <el-icon><FolderOpened /></el-icon>
        </div>
        <h2>Agent Skill</h2>
      </div>
      <div class="skill-table-actions">
        <el-button :loading="isLoading" @click="loadSkills">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button :loading="isImporting" @click="importAllLocalSkills">
          <el-icon><FolderOpened /></el-icon>
          导入本地 Skill
        </el-button>
        <el-button @click="isImportVisible = true">指定路径导入</el-button>
        <el-button type="primary" @click="isCreateVisible = true">
          <el-icon><Plus /></el-icon>
          创建 Skill
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <section class="skill-table-card" v-loading="isLoading">
      <div class="skill-table-grid skill-table-head">
        <span>名称</span>
        <span>描述</span>
        <span>文件数</span>
        <span>创建时间</span>
        <span>操作</span>
      </div>

      <el-empty v-if="!skills.length && !isLoading" description="暂无 Skills">
        <el-button type="primary" @click="isCreateVisible = true">创建第一个 Skill</el-button>
      </el-empty>

      <div v-for="skill in skills" :key="skill.id" class="skill-table-grid skill-table-row" @click="openSkill(skill)">
        <div class="skill-name-cell">
          <div class="skill-row-icon">
            <el-icon><FolderOpened /></el-icon>
          </div>
          <strong>{{ skill.name || skill.id }}</strong>
        </div>
        <p class="skill-desc-cell">{{ truncateText(skill.description || skill.contentPreview) }}</p>
        <div>
          <span class="skill-file-badge">
            <el-icon><Document /></el-icon>
            {{ countFiles(skill) }}
          </span>
        </div>
        <span class="skill-time-cell">{{ formatRelativeTime(skill.createdAt) }}</span>
        <div class="skill-row-actions" @click.stop>
          <el-tooltip content="查看 / 编辑" placement="top">
            <el-button text class="skill-action-button" @click="openSkill(skill)">
              <el-icon><View /></el-icon>
            </el-button>
          </el-tooltip>
          <el-tooltip content="删除" placement="top">
            <el-button text class="skill-action-button danger" @click="removeSkill(skill)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </section>

    <el-drawer v-model="isDrawerVisible" size="86%" direction="rtl" class="skill-detail-drawer">
      <template #header>
        <div class="skill-drawer-header">
          <div>
            <h3>{{ selectedSkill?.name || 'Skill 详情' }}</h3>
            <p>{{ selectedSkill?.asToolName || '未生成工具名' }} · {{ enabledCount }} 个已启用 Skill</p>
          </div>
          <el-tag :type="selectedSkill?.status === 'enabled' ? 'success' : 'info'">
            {{ selectedSkill?.status === 'enabled' ? 'enabled' : 'disabled' }}
          </el-tag>
        </div>
      </template>

      <div v-if="selectedSkill" class="skill-detail-layout">
        <aside class="skill-file-sidebar">
          <section class="skill-meta-panel">
            <div class="skill-meta-title">
              <strong>基本信息</strong>
              <el-button size="small" :loading="isSaving" @click="saveSkillMeta">保存</el-button>
            </div>
            <el-input v-model="detailForm.name" placeholder="Skill 名称" />
            <el-input v-model="detailForm.description" type="textarea" :rows="4" placeholder="Skill 描述" />
            <el-select v-model="detailForm.status">
              <el-option label="启用" value="enabled" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </section>

          <section class="skill-file-panel">
            <div class="skill-meta-title">
              <strong>文件</strong>
              <el-button size="small" :disabled="!addableFolders.length" @click="openAddFileDialog()">
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
            <div class="skill-file-tree">
              <div
                v-for="item in flatNodes"
                :key="item.node.path"
                class="skill-file-row"
                :class="{ active: item.node.type === 'file' && selectedFile?.path === item.node.path, folder: item.node.type === 'folder' }"
                :style="{ paddingLeft: `${12 + item.depth * 18}px` }"
                role="button"
                tabindex="0"
                @click="item.node.type === 'file' ? selectFile(item.node) : undefined"
                @keyup.enter="item.node.type === 'file' ? selectFile(item.node) : undefined"
              >
                <el-icon>
                  <FolderOpened v-if="item.node.type === 'folder'" />
                  <Document v-else />
                </el-icon>
                <span>{{ item.node.name }}</span>
                <button
                  v-if="item.node.type === 'folder' && canAddToFolder(item.node)"
                  class="skill-file-mini-action"
                  type="button"
                  @click.stop="openAddFileDialog(item.node)"
                >
                  <el-icon><Plus /></el-icon>
                </button>
                <button
                  v-if="item.node.type === 'file' && canDeleteFile(item.node)"
                  class="skill-file-mini-action danger"
                  type="button"
                  @click.stop="removeFile(item.node)"
                >
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
          </section>
        </aside>

        <main class="skill-editor-panel">
          <div v-if="selectedFile" class="skill-editor-head">
            <div>
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ selectedFile.path }}</span>
            </div>
            <el-button type="primary" :loading="isSaving" @click="saveSelectedFile">
              <el-icon><Edit /></el-icon>
              保存文件
            </el-button>
          </div>
          <el-input
            v-if="selectedFile"
            v-model="fileDraft"
            class="skill-file-editor"
            type="textarea"
            resize="none"
            spellcheck="false"
          />
          <el-empty v-else description="请选择左侧文件查看或编辑内容" />
        </main>
      </div>
    </el-drawer>

    <el-dialog v-model="isCreateVisible" title="创建 Skill" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="createForm.name" placeholder="例如 paper-review" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="说明该 Skill 什么时候应该被调用" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="createForm.status">
            <el-option label="启用" value="enabled" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="isCreateVisible = false">取消</el-button>
        <el-button type="primary" :loading="isSaving" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="isImportVisible" title="导入本地 Skill" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="本地路径">
          <el-input v-model="importForm.sourceUri" placeholder="留空则扫描 ~/.agents、~/.codex、~/.claude、~/.cc-switch" />
        </el-form-item>
        <el-form-item label="导入状态">
          <el-select v-model="importForm.status">
            <el-option label="启用" value="enabled" />
            <el-option label="停用" value="disabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="isImportVisible = false">取消</el-button>
        <el-button type="primary" :loading="isImporting" @click="submitImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="isAddFileVisible" title="新增 Skill 文件" width="520px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="目录">
          <el-select v-model="addFileForm.path" placeholder="选择 reference 或 scripts">
            <el-option v-for="folder in addableFolders" :key="folder.path" :label="folder.path" :value="folder.path" />
          </el-select>
        </el-form-item>
        <el-form-item label="文件名">
          <el-input v-model="addFileForm.name" placeholder="例如 notes.md 或 helper.py" @keyup.enter="submitAddFile" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="isAddFileVisible = false">
          <el-icon><CloseBold /></el-icon>
          取消
        </el-button>
        <el-button type="primary" :loading="isSaving" @click="submitAddFile">创建文件</el-button>
      </template>
    </el-dialog>
  </div>
</template>
