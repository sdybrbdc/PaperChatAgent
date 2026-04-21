import type { AuthSessionDTO, CurrentUserDTO, LoginPayload } from '../types/auth'

export const MOCK_USER: CurrentUserDTO = {
  id: 'mock-user-sdybdc',
  displayName: 'sdybdc',
  email: 'sdybdc',
  avatarUrl: '',
}

export const MOCK_LOGIN_PAYLOAD: LoginPayload = {
  account: 'sdybdc',
  password: '226113',
}

export const MOCK_AUTH_SESSION: AuthSessionDTO = {
  user: MOCK_USER,
  token: 'mock-token-sdybdc',
}
