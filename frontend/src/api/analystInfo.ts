/**
 * Analyst Info API
 *
 * 处理 Analyst 信息的 CRUD 操作
 */
import apiClient from './client'

// Analyst 数据接口
export interface Analyst {
  id: string
  full_name: string
  chinese_name?: string
  email: string
  suffix?: string
  region_id?: string
  sfc?: string
  is_active: boolean
  created_at: string
  updated_at: string
  region?: {
    id: string
    name: string
    code: string
  }
}

// 创建请求接口
export interface AnalystCreateRequest {
  full_name: string
  chinese_name?: string
  email: string
  suffix?: string
  region_id?: string
  sfc?: string
}

// 更新请求接口
export interface AnalystUpdateRequest {
  full_name?: string
  chinese_name?: string
  email?: string
  suffix?: string
  region_id?: string
  sfc?: string
  is_active?: boolean
}

// 邮箱检查响应
export interface CheckEmailResponse {
  exists: boolean
}

/**
 * 获取 Analyst 信息列表
 */
export async function getAnalysts(search?: string, isActive?: boolean): Promise<Analyst[]> {
  const params = new URLSearchParams()
  if (search) params.append('search', search)
  if (isActive !== undefined) params.append('is_active', String(isActive))

  const response = await apiClient.get<Analyst[]>(`/api/analyst-info?${params.toString()}`)
  return response.data
}

/**
 * 创建 Analyst 信息
 */
export async function createAnalyst(data: AnalystCreateRequest): Promise<Analyst> {
  const response = await apiClient.post<Analyst>('/api/analyst-info', data)
  return response.data
}

/**
 * 更新 Analyst 信息
 */
export async function updateAnalyst(id: string, data: AnalystUpdateRequest): Promise<Analyst> {
  const response = await apiClient.put<Analyst>(`/api/analyst-info/${id}`, data)
  return response.data
}

/**
 * 删除 Analyst 信息
 */
export async function deleteAnalyst(id: string): Promise<void> {
  await apiClient.delete(`/api/analyst-info/${id}`)
}

/**
 * 检查邮箱唯一性
 */
export async function checkAnalystEmail(email: string): Promise<CheckEmailResponse> {
  const response = await apiClient.post<CheckEmailResponse>('/api/analyst-info/check-email', { email })
  return response.data
}
