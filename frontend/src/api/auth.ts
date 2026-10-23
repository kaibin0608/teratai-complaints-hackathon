import type { Login, LoginRequest, User } from '@/lib/types'
import { request } from './client'

export const authApi = {
  login: (body: LoginRequest, signal?: AbortSignal) =>
    request<Login>('/api/auth/login', { method: 'POST', body, signal }),

  me: (signal?: AbortSignal) => request<User>('/api/auth/me', { signal }),
}
