<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import AuthInfoCard from '../../components/auth/AuthInfoCard.vue'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const formRef = ref<FormInstance>()
const authStore = useAuthStore()

const form = reactive({
  displayName: '',
  email: '',
  password: '',
  confirmPassword: '',
  agreed: true,
})

const rules: FormRules<typeof form> = {
  displayName: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback(new Error('请再次输入密码'))
        if (value !== form.password) return callback(new Error('两次输入的密码不一致'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function handleRegister() {
  if (!formRef.value) return

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  if (!form.agreed) {
    ElMessage.error('请先勾选协议说明')
    return
  }

  await authStore.register({
    displayName: form.displayName,
    email: form.email,
    password: form.password,
  })
  ElMessage.success('注册成功，请登录')
  await router.push('/login')
}
</script>

<template>
  <div class="auth-brand-block">
    <h1>PaperChatAgent</h1>
    <p>创建账号后即可进入默认聊天页，直接开始新的研究对话。</p>
    <AuthInfoCard
      title="创建账号后你将获得"
      description="统一的论文调研入口、最近会话历史、知识资料管理和后台任务跟踪能力。"
      :items="['1. 最近会话历史', '2. 账号级资料管理', '3. 完整研究工作流与报告产物']"
      pill="面向研究工作流"
      pill-class="success"
    />
  </div>

  <div class="form-card">
    <h2>创建账号</h2>
    <p>使用邮箱注册，开始你的论文调研与连续对话。</p>

    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="显示名称" prop="displayName">
        <el-input v-model="form.displayName" placeholder="你的昵称" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" placeholder="name@example.com" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位密码" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input v-model="form.confirmPassword" type="password" show-password placeholder="再次输入密码" />
      </el-form-item>
      <el-checkbox v-model="form.agreed" class="agreed-checkbox">
        我已阅读并同意服务条款、隐私政策以及论文资料处理说明。
      </el-checkbox>
      <el-button type="primary" class="submit-button" @click="handleRegister">创建账号</el-button>
    </el-form>

    <div class="form-footer-text">
      已有账号？
      <router-link to="/login" class="login-link">返回登录</router-link>
    </div>
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

.agreed-checkbox {
  margin-bottom: 18px;
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

.login-link {
  color: var(--pc-brand);
  font-weight: 600;
}
</style>
