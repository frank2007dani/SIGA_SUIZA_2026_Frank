import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const normalizeBase = (value) => (value || '').trim().replace(/\/+$/, '')

function injectPublicApiBase(apiBase) {
  return {
    name: 'siga-inject-public-api-base',
    apply: 'build',
    buildStart() {
      if (!/^https?:\/\//.test(apiBase)) {
        throw new Error('VITE_API_URL es obligatoria en el build y debe ser una URL absoluta.')
      }
    },
    closeBundle() {
      const target = path.resolve(frontendDir, 'dist/boleta.html')
      if (!fs.existsSync(target)) return
      const html = fs.readFileSync(target, 'utf8').replaceAll('__SIGA_API_BASE__', apiBase)
      fs.writeFileSync(target, html)
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, frontendDir, 'VITE_')
  const apiBase = normalizeBase(env.VITE_API_URL)

  if (mode === 'production' && !/^https:\/\//.test(apiBase)) {
    throw new Error('VITE_API_URL debe ser HTTPS en el build de producción de Render.')
  }

  return {
    plugins: [react(), injectPublicApiBase(apiBase)],
    optimizeDeps: {
      include: ['html5-qrcode']
    },
    server: {
      watch: {
        usePolling: true,
      },
      host: true,
    },
  }
})
