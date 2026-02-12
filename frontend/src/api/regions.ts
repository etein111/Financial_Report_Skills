/**
 * Region API
 *
 * 处理地区数据的 CRUD 操作
 */
import apiClient from './client'

// Region 数据接口
export interface Region {
  id: string
  name: string
  code: string
  created_at: string
  updated_at: string
}

// 创建/更新请求接口
export interface RegionRequest {
  name: string
  code: string
}

/**
 * 获取地区列表
 */
export async function getRegions(): Promise<Region[]> {
  const response = await apiClient.get<Region[]>('/api/regions')
  return response.data
}

/**
 * 创建地区
 */
export async function createRegion(data: RegionRequest): Promise<Region> {
  const response = await apiClient.post<Region>('/api/regions', data)
  return response.data
}

/**
 * 更新地区
 */
export async function updateRegion(id: string, data: Partial<RegionRequest>): Promise<Region> {
  const response = await apiClient.put<Region>(`/api/regions/${id}`, data)
  return response.data
}

/**
 * 删除地区
 */
export async function deleteRegion(id: string): Promise<void> {
  await apiClient.delete(`/api/regions/${id}`)
}
