import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export interface User {
  username: string
  email: string
  role: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const token = ref<string>('')

  const isLoggedIn = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role || 'viewer')

  // 初始化时从 localStorage 恢复 token
  const initAuth = () => {
    const savedToken = localStorage.getItem('access_token')
    const savedUser = localStorage.getItem('user_info')
    if (savedToken && savedUser) {
      token.value = savedToken
      user.value = JSON.parse(savedUser)
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    }
  }

  // 登录
  const login = async (usernameOrEmail: string, password: string) => {
    const response = await axios.post('/api/auth/login', {
      username: usernameOrEmail,
      password: password,
    })

    // 处理后端返回的响应格式
    const data = response.data
    const newToken = data.token || data.access_token
    const newUser = data.user

    if (!newToken || !newUser) {
      throw new Error('登录响应格式错误')
    }

    token.value = newToken
    user.value = newUser

    localStorage.setItem('access_token', newToken)
    localStorage.setItem('user_info', JSON.stringify(newUser))

    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`

    return response.data
  }

  // 登出
  const logout = () => {
    clearAuth()
  }

  // 清除认证信息
  const clearAuth = () => {
    user.value = null
    token.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    delete axios.defaults.headers.common['Authorization']
  }

  return {
    user,
    token,
    isLoggedIn,
    userRole,
    initAuth,
    login,
    logout,
    clearAuth,
  }
})
