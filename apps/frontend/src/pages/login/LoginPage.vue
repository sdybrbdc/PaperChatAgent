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
  email: '',
  password: '',
})

const rules: FormRules<typeof form> = {
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
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
      description="从默认聊天页开始，直接和 AI 讨论研究方向，并在最近会话中持续追问。"
      :items="[
        '1. 直接开始新聊天',
        '2. 上传论文并围绕资料继续追问',
        '3. 在最近会话中持续保留聊天历史',
      ]"
      pill="白色主主题"
    />
  </div>

  <div class="form-card">
    <h2>欢迎回来</h2>
    <p>使用邮箱和密码登录，继续你的论文调研与最近会话。</p>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" placeholder="name@example.com" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
      </el-form-item>
      <div class="form-actions">
        <span>记住我</span>
        <span class="forgot-link">忘记密码？</span>
      </div>
      <el-button type="primary" :loading="loading" class="submit-button" @click="handleLogin">登录</el-button>
    </el-form>

    <div class="form-footer-text">
      还没有账号？
      <router-link to="/register" class="register-link">立即注册</router-link>
    </div>
    <div class="terms-text">登录即表示你同意平台的服务条款与隐私说明。</div>
  </div>
</template>

<style lang="scss" scoped>
.auth-brand-block {
  h1 {
    margin: 0;
    font-size: 56px;
    line-height: 1.05;
    font-weight: 700;
    letter-spacing: 0;
  }

  p {
    max-width: 380px;
    margin: 16px 0 0;
    color: var(--pc-text-muted);
    font-size: 18px;
  }
}

.form-card {
  padding: 40px 48px;
  border-radius: 28px;
  background: var(--pc-surface);
  border: 1px solid var(--pc-border);
  box-shadow: var(--pc-shadow);

  h2 {
    margin: 0;
    font-size: 44px;
    line-height: 1.08;
  }

  > p {
    margin: 12px 0 28px;
    color: var(--pc-text-muted);
    font-size: 16px;
  }
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-bottom: 18px;
  color: var(--pc-text-secondary);
  font-size: 14px;
}

.forgot-link {
  color: var(--pc-brand);
}

.submit-button {
  width: 100%;
}

.form-footer-text {
  margin-top: 18px;
  text-align: center;
  color: var(--pc-text-secondary);
  font-size: 15px;
}

.register-link {
  color: var(--pc-brand);
  font-weight: 600;
}

.terms-text {
  margin-top: 16px;
  color: var(--pc-text-muted);
  font-size: 13px;
}
</style>
