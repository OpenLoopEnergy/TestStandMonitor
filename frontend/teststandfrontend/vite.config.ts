import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Proxy REST calls to the FastAPI backend in dev
      '/get_': 'http://localhost:8000',
      '/update_': 'http://localhost:8000',
      '/export_': 'http://localhost:8000',
      '/clear_': 'http://localhost:8000',
      '/past_tests': 'http://localhost:8000',
      '/download_test': 'http://localhost:8000',
      '/delete_file': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      // WebSocket proxy — suppress ECONNABORTED noise from backend hot-reloads
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', () => {}) // reconnect handled by useLiveData hook
        },
      },
    },
  },
})
