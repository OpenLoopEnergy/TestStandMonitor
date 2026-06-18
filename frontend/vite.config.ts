import { defineConfig, createLogger } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Suppress ECONNABORTED spam from Vite's WS proxy when browsers disconnect
const logger = createLogger()
const originalError = logger.error.bind(logger)
logger.error = (msg, options) => {
  if (msg.includes('ECONNABORTED')) return
  originalError(msg, options)
}

export default defineConfig({
  customLogger: logger,
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/get_': 'http://localhost:8000',
      '/update_': 'http://localhost:8000',
      '/export_': 'http://localhost:8000',
      '/clear_': 'http://localhost:8000',
      '/past_tests': 'http://localhost:8000',
      '/data_backups': 'http://localhost:8000',
      '/rename_backup': 'http://localhost:8000',
      '/delete_backup': 'http://localhost:8000',
      '/download_test': 'http://localhost:8000',
      '/delete_file': 'http://localhost:8000',
      '/rename_file': 'http://localhost:8000',
      '/set_debug_mode': 'http://localhost:8000',
      '/set_log_manual': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', () => {})
        },
      },
    },
  },
})
