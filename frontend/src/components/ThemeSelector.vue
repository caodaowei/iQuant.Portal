<template>
  <el-dropdown @command="handleThemeChange">
    <el-button type="primary" plain>
      <el-icon><Setting /></el-icon>
      主题
      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item 
          v-for="theme in themes" 
          :key="theme.id" 
          :command="theme.id"
          :class="{ active: currentTheme === theme.id }"
        >
          <div class="theme-item">
            <div class="theme-color" :style="{ backgroundColor: theme.colors.primary }"></div>
            <span>{{ theme.name }}</span>
          </div>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Setting, ArrowDown } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()
const themes = ref(themeStore.themes)
const currentTheme = ref(themeStore.currentTheme)

const handleThemeChange = (themeId: string) => {
  themeStore.switchTheme(themeId)
  currentTheme.value = themeId
}

onMounted(() => {
  // 监听主题变化
  currentTheme.value = themeStore.currentTheme
})
</script>

<style scoped>
.theme-item {
  display: flex;
  align-items: center;
  padding: 4px 0;
}

.theme-color {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin-right: 8px;
  border: 1px solid #dcdfe6;
}

.active {
  font-weight: bold;
  color: var(--el-color-primary);
}
</style>