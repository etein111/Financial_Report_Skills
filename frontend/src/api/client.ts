/**
 * Axios 客户端配置
 *
 * 提供统一的 API 请求实例，包含：
 * - 请求拦截器：自动添加 JWT Token
 * - 响应拦截器：处理 401 未授权响应
 */
import axios from 'axios'

// 从环境变量获取 API 基础 URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// 创建 Axios 实例
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 秒超时
})

// 请求拦截器：自动添加 Token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理错误
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 处理 401 未授权响应
    if (error.response?.status === 401) {
      // 清除本地存储的认证信息
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user_info')

      // 如果不在登录页，跳转到登录页
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
