import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

// 主题配置
export const useThemeStore = defineStore('theme', () => {
  // 主题列表
  const themes = ref([
    {
      id: 'default',
      name: '默认主题',
      colors: {
        primary: '#409eff',
        success: '#67c23a',
        warning: '#e6a23c',
        danger: '#f56c6c',
        info: '#909399',
        background: '#f0f2f5',
        card: '#ffffff',
        text: '#303133',
        textSecondary: '#606266',
        border: '#dcdfe6'
      }
    },
    {
      id: 'dark',
      name: '深色主题',
      colors: {
        primary: '#409eff',
        success: '#67c23a',
        warning: '#e6a23c',
        danger: '#f56c6c',
        info: '#909399',
        background: '#1a1a1a',
        card: '#2c2c2c',
        text: '#e4e7ed',
        textSecondary: '#c0c4cc',
        border: '#4e4e4e'
      }
    },
    {
      id: 'china-red',
      name: '中国红主题',
      colors: {
        primary: '#e74c3c',
        success: '#e74c3c',
        warning: '#f39c12',
        danger: '#27ae60',
        info: '#3498db',
        background: '#fef5f5',
        card: '#ffffff',
        text: '#333333',
        textSecondary: '#666666',
        border: '#e8e8e8'
      }
    },
    {
      id: 'china-blue',
      name: '稳重蓝主题',
      colors: {
        primary: '#1a73e8',
        success: '#e74c3c',
        warning: '#f39c12',
        danger: '#27ae60',
        info: '#95a5a6',
        background: '#f0f4f8',
        card: '#ffffff',
        text: '#333333',
        textSecondary: '#666666',
        border: '#e8e8e8'
      }
    },
    {
      id: 'china-gold',
      name: '金色主题',
      colors: {
        primary: '#f39c12',
        success: '#e74c3c',
        warning: '#f39c12',
        danger: '#27ae60',
        info: '#95a5a6',
        background: '#fef9f0',
        card: '#ffffff',
        text: '#333333',
        textSecondary: '#666666',
        border: '#e8e8e8'
      }
    }
  ])

  // 当前主题
  const currentTheme = ref('default')

  // 获取当前主题配置
  const getCurrentTheme = () => {
    return themes.value.find(theme => theme.id === currentTheme.value) || themes.value[0]
  }

  // 切换主题
  const switchTheme = (themeId: string) => {
    currentTheme.value = themeId
    applyTheme(getCurrentTheme())
  }

  // 应用主题
  const applyTheme = (theme: any) => {
    const root = document.documentElement
    Object.entries(theme.colors).forEach(([key, value]) => {
      root.style.setProperty(`--el-color-${key}`, value)
    })
  }

  // 初始化主题
  const initTheme = () => {
    // 从 localStorage 读取保存的主题
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme && themes.value.some(t => t.id === savedTheme)) {
      currentTheme.value = savedTheme
    }
    applyTheme(getCurrentTheme())
  }

  // 监听主题变化，保存到 localStorage
  watch(currentTheme, (newTheme) => {
    localStorage.setItem('theme', newTheme)
  })

  return {
    themes,
    currentTheme,
    getCurrentTheme,
    switchTheme,
    initTheme
  }
})