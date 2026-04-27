<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Plus, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { createSkill, getCcSwitchSkills, getSkills, importLocalSkill, syncCcSwitchSkills, testSkill } from '../../apis/skills'
import type { SkillDTO } from '../../types/skills'

const skills = ref<SkillDTO[]>([])
const selectedSkillId = ref('')
const isLoading = ref(false)
const isTesting = ref(false)
const isSyncing = ref(false)
const errorMessage = ref('')
const createVisible = ref(false)
const importVisible = ref(false)
const ccSwitchCount = ref(0)
const ccSwitchSource = ref('/Users/sdybdc/.cc-switch/skills')
const testInput = ref('{\n  "query": "RAG evaluation survey"\n}')
const testOutput = ref('')
const skillForm = ref({
  name: '',
  description: '',
  sourceUri: '',
  entrypoint: '',
  status: 'disabled',
})
const importForm = ref({
  sourceUri: '',
  status: 'disabled',
})

const selectedSkill = computed(() => skills.value.find((item) => item.id === selectedSkillId.value) ?? null)
const enabledCount = computed(() => skills.value.filter((skill) => skill.status === 'enabled').length)
const draftCount = computed(() => skills.value.filter((skill) => skill.status !== 'enabled').length)
const categoryCount = computed(() => new Set(skills.value.map((skill) => skill.sourceType || 'local')).size)

function statusClass(status: string) {
  if (status === 'enabled') return 'success'
  if (status === 'draft') return 'warning'
  if (status === 'disabled') return 'danger'
  return 'brand'
}

function schemaKeys(schema: Record<string, unknown>) {
  const properties = schema.properties
  if (properties && typeof properties === 'object' && !Array.isArray(properties)) {
    return Object.keys(properties).slice(0, 4).join('、')
  }
  return Object.keys(schema).slice(0, 4).join('、') || '未声明'
}

function parseInput() {
  try {
    const parsed = JSON.parse(testInput.value)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : {}
  } catch {
    ElMessage.error('测试输入必须是 JSON 对象')
    return null
  }
}

async function loadSkills() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    skills.value = await getSkills()
    if (!selectedSkillId.value && skills.value.length > 0) selectedSkillId.value = skills.value[0].id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Skills 加载失败'
  } finally {
    isLoading.value = false
  }
}

async function loadCcSwitchPreview() {
  try {
    const result = await getCcSwitchSkills()
    ccSwitchCount.value = result.items.length
    ccSwitchSource.value = String(result.source.skills_dir ?? ccSwitchSource.value)
  } catch {
    ccSwitchCount.value = 0
  }
}

async function runTest() {
  if (!selectedSkillId.value) return
  const input = parseInput()
  if (!input) return
  isTesting.value = true
  try {
    const result = await testSkill(selectedSkillId.value, input)
    testOutput.value = JSON.stringify(result.output ?? result, null, 2)
    ElMessage[result.ok ? 'success' : 'warning'](result.message || (result.ok ? '测试成功' : '测试未通过'))
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'Skill 测试失败')
  } finally {
    isTesting.value = false
  }
}

async function syncFromCcSwitch() {
  isSyncing.value = true
  try {
    const result = await syncCcSwitchSkills()
    skills.value = result.items
    if (!selectedSkillId.value && result.items.length > 0) selectedSkillId.value = result.items[0].id
    ccSwitchCount.value = result.total
    ccSwitchSource.value = String(result.source.skills_dir ?? ccSwitchSource.value)
    ElMessage.success(`已同步 ${result.total} 个真实 Skills，新建 ${result.created} 个，更新 ${result.updated} 个`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '同步 .cc-switch Skills 失败')
  } finally {
    isSyncing.value = false
  }
}

async function submitSkill() {
  if (!skillForm.value.name.trim()) {
    ElMessage.warning('请输入 Skill 名称')
    return
  }
  try {
    const created = await createSkill({
      name: skillForm.value.name.trim(),
      description: skillForm.value.description.trim(),
      sourceType: 'local',
      sourceUri: skillForm.value.sourceUri.trim(),
      entrypoint: skillForm.value.entrypoint.trim(),
      status: skillForm.value.status,
    })
    skills.value.unshift(created)
    selectedSkillId.value = created.id
    createVisible.value = false
    skillForm.value = { name: '', description: '', sourceUri: '', entrypoint: '', status: 'disabled' }
    ElMessage.success('Skill 已创建')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建 Skill 失败')
  }
}

async function submitImport() {
  if (!importForm.value.sourceUri.trim()) {
    ElMessage.warning('请输入本地 Skill 路径')
    return
  }
  try {
    const created = await importLocalSkill({
      sourceUri: importForm.value.sourceUri.trim(),
      status: importForm.value.status,
    })
    skills.value.unshift(created)
    selectedSkillId.value = created.id
    importVisible.value = false
    importForm.value = { sourceUri: '', status: 'disabled' }
    ElMessage.success('本地 Skill 已导入')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入 Skill 失败')
  }
}

onMounted(() => {
  loadSkills()
  loadCcSwitchPreview()
})
</script>

<template>
  <div class="page-shell">
    <header class="module-header">
      <div>
        <h2>Skills</h2>
        <p>维护可供模型按需调用的技能集合，覆盖论文检索、文档处理、引用锚定与主题分析。</p>
      </div>
      <div class="page-actions">
        <el-button :loading="isSyncing" @click="syncFromCcSwitch">
          <el-icon><DocumentAdd /></el-icon>
          同步 .cc-switch Skills
        </el-button>
        <el-button type="primary" @click="createVisible = true">
          <el-icon><Plus /></el-icon>
          新增 Skill
        </el-button>
      </div>
    </header>

    <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon />

    <section class="metrics-grid">
      <article class="metric-card success">
        <h4>已启用</h4>
        <strong>{{ String(enabledCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card brand">
        <h4>分类</h4>
        <strong>{{ String(categoryCount).padStart(2, '0') }}</strong>
      </article>
      <article class="metric-card warning">
        <h4>草稿</h4>
        <strong>{{ String(draftCount).padStart(2, '0') }}</strong>
      </article>
    </section>

    <div class="module-content-grid">
      <section class="module-surface">
        <div class="section-title-row">
          <div>
            <h3>技能列表</h3>
            <p>每个 Skill 都需要明确输入输出、调用时机和可观测日志，避免成为黑盒能力。</p>
          </div>
          <el-button :loading="isLoading" @click="loadSkills">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div v-loading="isLoading" class="module-list">
          <el-empty v-if="!skills.length && !isLoading" description="暂无 Skills" />
          <button
            v-for="skill in skills"
            :key="skill.id"
            class="module-list-item"
            :class="{ active: selectedSkillId === skill.id }"
            type="button"
            @click="selectedSkillId = skill.id"
          >
            <div>
              <h4>{{ skill.name || skill.id }}</h4>
              <p>用途：{{ skill.description || skill.sourceUri || '暂无描述' }}</p>
              <span>{{ skill.sourceType || 'local' }} · {{ skill.entrypoint || '未声明入口' }} · v{{ skill.version || 'draft' }}</span>
            </div>
            <strong class="module-list-side" :class="['status-text', statusClass(skill.status)]">{{ skill.status }}</strong>
          </button>
        </div>

        <p class="muted-text">建议每个 Skill 具备：manifest、输入校验、失败提示、最近执行记录。</p>
      </section>

      <aside class="module-rail">
        <section class="soft-panel module-rail-card">
          <h3>选中 Skill</h3>
          <template v-if="selectedSkill">
            <p>名称：{{ selectedSkill.name || selectedSkill.id }}</p>
            <p>输入：{{ schemaKeys(selectedSkill.inputSchema) }}</p>
            <p>输出：{{ schemaKeys(selectedSkill.outputSchema) }}</p>
            <p>版本：{{ selectedSkill.version || '未发布' }}</p>
          </template>
          <p v-else>请选择一个 Skill 查看详情。</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>调用场景</h3>
          <p>聊天回答补证据</p>
          <p>知识库建库后生成引用锚点</p>
          <p>后台任务恢复时校验已有片段引用</p>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>测试运行</h3>
          <div class="module-form-stack">
            <el-input v-model="testInput" type="textarea" :rows="5" placeholder="输入 JSON 对象" />
            <el-button type="primary" :disabled="!selectedSkillId" :loading="isTesting" @click="runTest">
              <el-icon><VideoPlay /></el-icon>
              执行测试
            </el-button>
            <el-input v-model="testOutput" type="textarea" :rows="5" readonly placeholder="测试输出" />
          </div>
        </section>

        <section class="soft-panel module-rail-card">
          <h3>配置提示</h3>
          <p>真实来源：{{ ccSwitchSource }}</p>
          <p>可同步 Skills：{{ ccSwitchCount }} 个</p>
          <p>同步会读取 cc-switch 数据库和 SKILL.md，不再要求手动输入目录。</p>
        </section>
      </aside>
    </div>

    <el-dialog v-model="importVisible" title="导入本地 Skill" width="520px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="本地路径">
          <el-input v-model="importForm.sourceUri" placeholder="/Users/.../skills/example" />
        </el-form-item>
        <el-form-item label="导入状态">
          <el-select v-model="importForm.status">
            <el-option label="停用" value="disabled" />
            <el-option label="启用" value="enabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="submitImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" title="新增 Skill" width="560px">
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="名称">
          <el-input v-model="skillForm.name" placeholder="例如 citation-grounder" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="skillForm.description" type="textarea" :rows="3" placeholder="说明调用场景和输出结果" />
        </el-form-item>
        <el-form-item label="来源路径">
          <el-input v-model="skillForm.sourceUri" placeholder="/Users/.../skills/citation-grounder" />
        </el-form-item>
        <el-form-item label="入口">
          <el-input v-model="skillForm.entrypoint" placeholder="例如 python main.py" />
        </el-form-item>
        <el-form-item label="初始状态">
          <el-select v-model="skillForm.status">
            <el-option label="停用" value="disabled" />
            <el-option label="启用" value="enabled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="submitSkill">保存 Skill</el-button>
      </template>
    </el-dialog>
  </div>
</template>
