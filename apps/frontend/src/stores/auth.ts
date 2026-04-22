import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { CurrentUserDTO, LoginPayload, RegisterPayload } from '../types/auth'
import { getCurrentUser, login, logout as logoutRequest, registerAccount } from '../apis/auth'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<CurrentUserDTO | null>(null)
  const restoreState = ref<'idle' | 'loading' | 'done'>('idle')

  const isAuthenticated = computed(() => Boolean(currentUser.value))

  async function restoreSession(force = false) {
    if (restoreState.value === 'loading') return
    if (!force && restoreState.value === 'done') return

    restoreState.value = 'loading'
    try {
      currentUser.value = await getCurrentUser()
    } catch {
      currentUser.value = null
    } finally {
      restoreState.value = 'done'
    }
  }

  async function loginWithSession(payload: LoginPayload) {
    const session = await login(payload)
    currentUser.value = session.user
    restoreState.value = 'done'
  }

  async function register(payload: RegisterPayload) {
    await registerAccount(payload)
  }

  async function logout() {
    try {
      await logoutRequest()
    } finally {
      currentUser.value = null
      restoreState.value = 'done'
    }
  }

  return {
    currentUser,
    restoreState,
    isAuthenticated,
    restoreSession,
    login: loginWithSession,
    register,
    logout,
  }
})
