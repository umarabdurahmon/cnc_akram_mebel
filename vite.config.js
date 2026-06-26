import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Ключевая роль этого конфига в dev: Vite фронтит Mini App по HTTPS (через
// тоннель), а запросы /api проксирует на локальный uvicorn server-side. Так
// браузер видит один HTTPS-origin и не блокирует mixed content.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
    // Тоннель отдаёт страницу под чужим хостом — Vite должен его пускать.
    allowedHosts: ['.ngrok-free.app', '.ngrok.app', '.trycloudflare.com'],
  },
})
