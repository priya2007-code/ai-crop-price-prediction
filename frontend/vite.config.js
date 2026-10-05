import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backendUrl = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': backendUrl,
      '/api': backendUrl,
    },
  },
  preview: {
    proxy: {
      '/health': backendUrl,
      '/api': backendUrl,
    },
  },
})
