/**
 * 认证相关 API
 *
 * 处理登录、登出、获取用户信息等
 */
import apiClient from './client'

// 用户信息接口
export interface User {
  id: string
  email: string
  full_name?: string
  role: 'admin' | 'sa' | 'analyst'
}

// 登录请求接口
export interface LoginRequest {
  email: string
  password: string
}

// 登录响应接口
export interface LoginResponse {
  success: boolean
  message: string
  data?: {
    token: string
    user: User
  }
}

// 用户信息响应接口
export interface UserInfoResponse {
  success: boolean
  message: string
  data?: User
}

/**
 * 用户登录
 */
export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/api/auth/login', data)
  return response.data
}

/**
 * 用户登出
 */
export async function logout(): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post('/api/auth/logout')
  return response.data
}

/**
 * 获取当前用户信息
 */
export async function getCurrentUser(): Promise<UserInfoResponse> {
  const response = await apiClient.get<UserInfoResponse>('/api/auth/me')
  return response.data
}
