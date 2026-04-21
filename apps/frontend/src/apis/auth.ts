import type { AuthSessionDTO, LoginPayload } from '../types/auth'
import { MOCK_AUTH_SESSION, MOCK_LOGIN_PAYLOAD } from '../mocks/auth'

const wait = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms))

export async function loginWithMock(payload: LoginPayload): Promise<AuthSessionDTO> {
  await wait()

  const isValid =
    payload.account.trim() === MOCK_LOGIN_PAYLOAD.account &&
    payload.password === MOCK_LOGIN_PAYLOAD.password

  if (!isValid) {
    throw new Error('账号或密码错误')
  }

  return MOCK_AUTH_SESSION
}

export async function getCurrentUserMock() {
  await wait(100)
  return MOCK_AUTH_SESSION.user
}
