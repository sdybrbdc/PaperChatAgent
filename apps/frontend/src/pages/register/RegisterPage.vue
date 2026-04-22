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
    <p>创建账号后即可进入默认聊天页，逐步建立研究工作区。</p>
    <AuthInfoCard
      title="创建账号后你将获得"
      description="统一的论文调研入口、工作区分组历史、知识库管理和后台任务跟踪能力。"
      :items="['1. 默认收件箱会话', '2. 账号级全局知识库', '3. 完整研究工作流与报告产物']"
      pill="面向研究工作流"
      pill-class="success"
    />
  </div>

  <div class="form-card">
    <h2>创建账号</h2>
    <p>使用邮箱注册，开始你的论文调研与多智能体研究流程。</p>

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
      <el-checkbox v-model="form.agreed" style="margin-bottom: 18px;">
        我已阅读并同意服务条款、隐私政策以及论文资料处理说明。
      </el-checkbox>
      <el-button type="primary" style="width: 100%;" @click="handleRegister">创建账号</el-button>
    </el-form>

    <div class="form-footer-text">
      已有账号？
      <router-link to="/login" style="color: var(--pc-brand); font-weight: 600;">返回登录</router-link>
    </div>
  </div>
</template>
