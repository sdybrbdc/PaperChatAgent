import type { AuthSessionDTO, CurrentUserDTO, LoginPayload, RegisterPayload } from '../types/auth'
import { apiClient } from '../utils/http'

interface ApiEnvelope<T> {
  code: string
  message: string
  data: T
  request_id: string
}

function normalizeUser(input: Record<string, unknown>): CurrentUserDTO {
  return {
    id: String(input.id ?? ''),
    displayName: String(input.display_name ?? input.displayName ?? ''),
    email: String(input.email ?? ''),
    avatarUrl: String(input.avatar_url ?? input.avatarUrl ?? ''),
  }
}

export async function registerAccount(payload: RegisterPayload) {
  await apiClient.post<ApiEnvelope<Record<string, string>>>('/auth/register', {
    email: payload.email,
    password: payload.password,
    display_name: payload.displayName,
  })
}

export async function login(payload: LoginPayload): Promise<AuthSessionDTO> {
  const response = await apiClient.post<ApiEnvelope<{ user: Record<string, unknown> }>>('/auth/login', {
    email: payload.email,
    password: payload.password,
  })

  return {
    user: normalizeUser(response.data.data.user),
  }
}

export async function logout() {
  await apiClient.post('/auth/logout')
}

export async function getCurrentUser(): Promise<CurrentUserDTO> {
  const response = await apiClient.get<ApiEnvelope<Record<string, unknown>>>('/auth/me')
  return normalizeUser(response.data.data)
}
