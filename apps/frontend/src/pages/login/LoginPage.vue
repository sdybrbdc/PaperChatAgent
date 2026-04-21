<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import AuthInfoCard from '../../components/auth/AuthInfoCard.vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  account: '',
  password: '',
})

const rules: FormRules<typeof form> = {
  account: [{ required: true, message: '请输入用户名或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    loading.value = true
    await authStore.login(form)
    ElMessage.success('登录成功')
    await router.push('/chat')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-brand-block">
    <h1>PaperChatAgent</h1>
    <p>面向科研人员和学生的主题级论文问答工作台</p>
    <AuthInfoCard
      title="登录后你可以"
      description="从默认聊天页开始，先和 AI 讨论研究方向，再逐步形成研究工作区、知识库和后台任务。"
      :items="[
        '1. 在收件箱会话中澄清研究问题',
        '2. 上传论文并确认任务建议',
        '3. 跟踪完整工作流并继续问答',
      ]"
      pill="白色主主题"
    />
  </div>

  <div class="form-card">
    <h2>欢迎回来</h2>
    <p>使用邮箱和密码登录，继续你的论文调研与研究工作流。</p>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="邮箱 / 用户名" prop="account">
        <el-input v-model="form.account" placeholder="sdybdc" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
      </el-form-item>
      <div style="display: flex; justify-content: space-between; margin-bottom: 18px; color: var(--pc-text-secondary); font-size: 14px;">
        <span>记住我</span>
        <span style="color: var(--pc-brand);">忘记密码？</span>
      </div>
      <el-button type="primary" :loading="loading" style="width: 100%;" @click="handleLogin">登录</el-button>
    </el-form>

    <div class="form-footer-text">
      还没有账号？
      <router-link to="/register" style="color: var(--pc-brand); font-weight: 600;">立即注册</router-link>
    </div>
    <div class="terms-text">登录即表示你同意平台的服务条款与隐私说明。</div>
  </div>
</template>
