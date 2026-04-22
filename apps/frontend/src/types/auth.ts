export interface CurrentUserDTO {
  id: string
  displayName: string
  email: string
  avatarUrl?: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  displayName: string
  email: string
  password: string
}

export interface AuthSessionDTO {
  user: CurrentUserDTO
}
