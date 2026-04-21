export interface CurrentUserDTO {
  id: string
  displayName: string
  email: string
  avatarUrl: string
}

export interface LoginPayload {
  account: string
  password: string
}

export interface AuthSessionDTO {
  user: CurrentUserDTO
  token: string
}
