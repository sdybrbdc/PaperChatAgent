import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { CurrentUserDTO, LoginPayload } from '../types/auth'
import { loginWithMock } from '../apis/auth'

const STORAGE_KEY = 'paperchatagent.auth'

interface StoredAuth {
  user: CurrentUserDTO
  token: string
}

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<CurrentUserDTO | null>(null)
  const token = ref('')

  const isAuthenticated = computed(() => Boolean(currentUser.value && token.value))

  function hydrateFromStorage() {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return

    try {
      const parsed = JSON.parse(raw) as StoredAuth
      currentUser.value = parsed.user
      token.value = parsed.token
    } catch {
      localStorage.removeItem(STORAGE_KEY)
    }
  }

  async function login(payload: LoginPayload) {
    const session = await loginWithMock(payload)
    currentUser.value = session.user
    token.value = session.token
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  }

  function logout() {
    currentUser.value = null
    token.value = ''
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    currentUser,
    token,
    isAuthenticated,
    hydrateFromStorage,
    login,
    logout,
  }
})
