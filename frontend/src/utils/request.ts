import axios from 'axios'
import { supabase } from '@/lib/supabase'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器 - 使用 Supabase token
request.interceptors.request.use(
  async (config) => {
    // 从 Supabase 获取当前 session
    const { data } = await supabase.auth.getSession()
    if (data.session?.access_token) {
      config.headers.Authorization = `Bearer ${data.session.access_token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // Token 过期或无效，跳转到登录页
          console.error('认证失败，请重新登录')
          window.location.href = '/login'
          break
        case 403:
          console.error('权限不足')
          break
        case 429:
          console.error('请求过于频繁，请稍后重试')
          break
        case 500:
          console.error('服务器错误')
          break
      }
    }
    return Promise.reject(error)
  }
)

export default request
