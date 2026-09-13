import { ref } from 'vue'

// 主题：light（默认）/ dark，持久化于 localStorage；切换时同步 <html data-theme>
const THEME_KEY = 'theme'
const theme = ref(localStorage.getItem(THEME_KEY) || 'light')

function apply() {
    document.documentElement.dataset.theme = theme.value
}

/** 应用启动时调用（main.js），挂载前设置主题避免闪白 */
export function initTheme() {
    apply()
}

function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem(THEME_KEY, theme.value)
    apply()
}

export function useTheme() {
    return { theme, toggleTheme }
}
