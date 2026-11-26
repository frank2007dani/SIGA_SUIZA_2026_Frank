import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))

function injectPublicApiBase() {
  return {
    name: 'siga-inject-public-api-base',
    apply: 'build',
    closeBundle() {
      const target = path.resolve(frontendDir, 'dist/boleta.html')
      if (!fs.existsSync(target)) return
      const base = (process.env.VITE_API_URL || '').replace(/\/$/, '')
      const html = fs.readFileSync(target, 'utf8').replaceAll('__SIGA_API_BASE__', base)
      fs.writeFileSync(target, html)
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), injectPublicApiBase()],
  optimizeDeps: {
    include: ['html5-qrcode']
  },
  server: {
    watch: {
      usePolling: true,
    },
    host: true, // needed for docker
    proxy: {
      '/api': {
        target: 'http://siga-core:8000',
        changeOrigin: true
      },
      '/auth': {
        target: 'http://siga-core:8000',
        changeOrigin: true
      },
      '/core': {
        target: 'http://siga-core:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'http://siga-core:8000',
        changeOrigin: true,
        ws: true
      }
    }
  }
})
