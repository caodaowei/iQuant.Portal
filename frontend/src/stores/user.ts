import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { supabase } from '@/lib/supabase'
import type { User as SupabaseUser, Session } from '@supabase/supabase-js'

export interface User {
  id: string
  email: string
  role?: string
  created_at?: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const session = ref<Session | null>(null)

  const isLoggedIn = computed(() => !!session.value)
  const userRole = computed(() => user.value?.role || 'user')

  // 初始化时检查 Supabase 会话
  const initAuth = async () => {
    const { data } = await supabase.auth.getSession()
    if (data.session) {
      session.value = data.session
      await updateUserFromSupabase(data.session.user)
    }

    // 监听认证状态变化
    supabase.auth.onAuthStateChange(async (event, newSession) => {
      if (newSession) {
        session.value = newSession
        await updateUserFromSupabase(newSession.user)
      } else {
        clearAuth()
      }
    })
  }

  // 从 Supabase 用户更新本地用户信息
  const updateUserFromSupabase = async (supabaseUser: SupabaseUser) => {
    user.value = {
      id: supabaseUser.id,
      email: supabaseUser.email || '',
      created_at: supabaseUser.created_at,
    }

    // 设置 axios 默认 header 使用 Supabase token
    if (session.value) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${session.value.access_token}`
    }
  }

  // 使用邮箱密码登录
  const login = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      throw error
    }

    if (!data.session) {
      throw new Error('Login failed: No session returned')
    }

    session.value = data.session
    await updateUserFromSupabase(data.user)

    return data
  }

  // 注册新用户
  const signup = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })

    if (error) {
      throw error
    }

    return data
  }

  // 登出
  const logout = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error('Logout error:', error)
    }
    clearAuth()
  }

  // 清除认证信息
  const clearAuth = () => {
    user.value = null
    session.value = null
    delete axios.defaults.headers.common['Authorization']
  }

  // 重置密码
  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })

    if (error) {
      throw error
    }
  }

  // 更新密码
  const updatePassword = async (newPassword: string) => {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    })

    if (error) {
      throw error
    }
  }

  return {
    user,
    session,
    isLoggedIn,
    userRole,
    initAuth,
    login,
    signup,
    logout,
    clearAuth,
    resetPassword,
    updatePassword,
  }
})
