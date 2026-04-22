import { createRouter, createWebHistory } from 'vue-router'
import LoginPage from '../pages/login/LoginPage.vue'
import RegisterPage from '../pages/register/RegisterPage.vue'
import ChatPage from '../pages/chat/ChatPage.vue'
import KnowledgePage from '../pages/knowledge/KnowledgePage.vue'
import AgentsPage from '../pages/agents/AgentsPage.vue'
import TasksPage from '../pages/tasks/TasksPage.vue'
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
        { path: 'knowledge', name: 'knowledge', component: KnowledgePage, meta: { navKey: 'knowledge' } },
        { path: 'agents', name: 'agents', component: AgentsPage, meta: { navKey: 'agents' } },
        { path: 'tasks', name: 'tasks', component: TasksPage, meta: { navKey: 'tasks' } },
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
