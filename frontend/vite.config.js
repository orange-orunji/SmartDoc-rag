import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发期：Vite dev server（5173）把 /api 与 /reports 代理到后端（8000），
// 前端代码统一使用相对路径（/api/...），与生产环境（构建产物由 FastAPI 托管）同构。
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/reports': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
