import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../pages/login/LoginPage.vue'
import RegisterPage from '../pages/register/RegisterPage.vue'
import ChatPage from '../pages/chat/ChatPage.vue'
import AgentDetailPage from '../pages/agents/AgentDetailPage.vue'
import AgentRunPage from '../pages/agents/AgentRunPage.vue'
import AgentsListPage from '../pages/agents/AgentsListPage.vue'
import AuthLayout from '../layouts/AuthLayout.vue'
import WorkbenchLayout from '../layouts/WorkbenchLayout.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: AuthLayout,
      meta: { guestOnly: true },
      children: [{ path: '', name: 'login', component: LoginPage }],
    },
    {
      path: '/register',
      component: AuthLayout,
      meta: { guestOnly: true },
      children: [{ path: '', name: 'register', component: RegisterPage }],
    },
    {
      path: '/',
      component: WorkbenchLayout,
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/chat' },
        { path: 'chat', name: 'chat', component: ChatPage, meta: { navKey: 'chat' } },
        { path: 'agents', name: 'agents', component: AgentsListPage, meta: { navKey: 'agents' } },
        { path: 'agents/runs/:runId', name: 'agent-run', component: AgentRunPage, meta: { navKey: 'agents' } },
        { path: 'agents/:workflowId', name: 'agent-detail', component: AgentDetailPage, meta: { navKey: 'agents' } },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  await authStore.restoreSession()

  const isAuthenticated = authStore.isAuthenticated

  if (to.meta.requiresAuth && !isAuthenticated) {
    return '/login'
  }

  if (to.meta.guestOnly && isAuthenticated) {
    return '/chat'
  }

  return true
})

export default router
