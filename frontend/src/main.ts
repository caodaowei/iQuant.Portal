import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import App from './App.vue'
import router from './router'
import { useUserStore } from '@/stores/user_simple'
import { useThemeStore } from '@/stores/theme'
import './styles/theme.css'

const app = createApp(App)

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 初始化 Supabase 认证
const userStore = useUserStore()
userStore.initAuth()

// 初始化主题系统
const themeStore = useThemeStore()
themeStore.initTheme()

app.mount('#app')
