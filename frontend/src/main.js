import { createApp } from 'vue'
import App from './App.vue'
import './styles/style.css'
import { initTheme } from './composables/useTheme'

// 挂载前应用主题，避免亮暗切换闪白
initTheme()

createApp(App).mount('#app')
