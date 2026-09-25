import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const backendProxy = {
  target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
  changeOrigin: true,
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': backendProxy,
      '/auth': backendProxy,
      '/login/': backendProxy,
      '/register/': backendProxy,
      '/admin': backendProxy,
      '/health': backendProxy,
      '/metrics': backendProxy,
    },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    environmentOptions: {
      jsdom: {
        url: 'http://localhost:3000',
      },
    },
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
